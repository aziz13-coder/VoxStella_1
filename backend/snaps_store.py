from __future__ import annotations

import contextlib
import copy
import hashlib
import json
import os
import shutil
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional
from uuid import uuid4

try:
    from snapshot_schema import (
        SNAP_STORE_SCHEMA_VERSION,
        annotate_semantic_duplicates,
        canonicalize_snapshot_record,
        migrate_snapshot_store_document,
    )
except ImportError:  # pragma: no cover - package-style test imports
    from .snapshot_schema import (
        SNAP_STORE_SCHEMA_VERSION,
        annotate_semantic_duplicates,
        canonicalize_snapshot_record,
        migrate_snapshot_store_document,
    )


_LOCK = threading.RLock()
_CORRUPT_QUARANTINE_RETENTION = 5


class SnapStoreCorruptionError(RuntimeError):
    """Raised when a store cannot be read without risking user-data loss."""

    def __init__(self, message: str, *, quarantine_path: Optional[str] = None) -> None:
        super().__init__(message)
        self.quarantine_path = quarantine_path


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class SnapStore:
    """JSON snapshot store with versioned migration and loss-safe writes."""

    def __init__(self, path: str, max_snaps: int = 500, *, auto_migrate: bool = True) -> None:
        self.path = os.path.abspath(path)
        self.max_snaps = max(1, int(max_snaps or 1))
        self.auto_migrate = bool(auto_migrate)
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with _LOCK, self._file_lock():
            if not os.path.exists(self.path):
                self._save_unlocked({
                    "schema_version": SNAP_STORE_SCHEMA_VERSION,
                    "snaps": [],
                    "tombstones": {},
                    "legacy_imports": {},
                    "migration_report": {
                        "schema_version": SNAP_STORE_SCHEMA_VERSION,
                        "record_count": 0,
                        "migrated_records": 0,
                        "semantic_duplicate_groups": [],
                        "duplicates_removed": 0,
                    },
                })
            elif self.auto_migrate:
                self._load_unlocked(migrate=True)

    @property
    def _lock_path(self) -> str:
        return self.path + ".lock"

    @contextlib.contextmanager
    def _file_lock(self) -> Iterator[None]:
        """Serialize store mutations across duplicate backend processes."""
        lock_parent = os.path.dirname(self._lock_path)
        if lock_parent:
            os.makedirs(lock_parent, exist_ok=True)
        handle = open(self._lock_path, "a+b")
        try:
            handle.seek(0, os.SEEK_END)
            if handle.tell() == 0:
                handle.write(b"\0")
                handle.flush()
            handle.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:  # pragma: no cover - release platform is Windows
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:  # pragma: no cover - release platform is Windows
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def _unique_sidecar_path(self, marker: str, suffix: str = ".json") -> str:
        base = Path(self.path)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        return str(base.with_name(
            f"{base.name}.{marker}.{stamp}.{os.getpid()}.{uuid4().hex[:8]}{suffix}"
        ))

    def _backup_unlocked(self, reason: str) -> Optional[str]:
        if not os.path.exists(self.path):
            return None
        backup_path = self._unique_sidecar_path(f"backup-{reason}")
        shutil.copy2(self.path, backup_path)
        return backup_path

    def _quarantine_corrupt_unlocked(self, exc: Exception) -> str:
        try:
            source = Path(self.path)
            source_bytes = source.read_bytes()
            source_stat = source.stat()
            source_sha256 = hashlib.sha256(source_bytes).hexdigest()
            fingerprint = (
                f"{source_sha256}.{len(source_bytes)}."
                f"{int(source_stat.st_mtime_ns)}"
            )
            quarantine_path = str(source.with_name(
                f"{source.name}.corrupt-quarantine.{fingerprint}.json"
            ))
            existing = Path(quarantine_path)
            if (
                existing.exists()
                and hashlib.sha256(existing.read_bytes()).hexdigest()
                == source_sha256
            ):
                self._prune_corrupt_quarantines_unlocked(
                    keep_path=quarantine_path
                )
                return quarantine_path
        except Exception as fingerprint_exc:
            raise SnapStoreCorruptionError(
                f"Snapshot store is unreadable and could not be fingerprinted: {fingerprint_exc}"
            ) from exc
        try:
            shutil.copy2(self.path, quarantine_path)
        except Exception as copy_exc:
            raise SnapStoreCorruptionError(
                f"Snapshot store is unreadable and could not be quarantined: {copy_exc}"
            ) from exc
        self._prune_corrupt_quarantines_unlocked(keep_path=quarantine_path)
        return quarantine_path

    def _prune_corrupt_quarantines_unlocked(self, *, keep_path: str) -> None:
        """Bound corrupt sidecars without touching the live source document."""
        source = Path(self.path)
        parent = source.parent.resolve()
        keep_key = os.path.normcase(os.path.abspath(keep_path))
        candidates: List[tuple[Path, int, str]] = []
        for candidate in source.parent.glob(
            f"{source.name}.corrupt-quarantine.*.json"
        ):
            try:
                # Never follow a matching-name symlink during retention cleanup:
                # unlinking its resolved target could remove unrelated user data.
                if candidate.is_symlink():
                    continue
                if candidate.parent.resolve() != parent or not candidate.is_file():
                    continue
                candidate_key = os.path.normcase(
                    os.path.abspath(str(candidate))
                )
                candidates.append(
                    (candidate, candidate.stat().st_mtime_ns, candidate_key)
                )
            except OSError:
                continue
        candidates.sort(
            key=lambda item: item[1],
            reverse=True,
        )
        retained = {
            keep_key,
            *[
                candidate_key
                for _candidate, _mtime, candidate_key in candidates
                if candidate_key != keep_key
            ][:_CORRUPT_QUARANTINE_RETENTION - 1],
        }
        for candidate, _mtime, candidate_key in candidates:
            if candidate_key in retained:
                continue
            try:
                candidate.unlink()
            except OSError:
                pass

    def _load_raw_unlocked(self) -> Dict[str, Any]:
        try:
            with open(self.path, "r", encoding="utf-8-sig") as handle:
                data = json.load(handle)
        except Exception as exc:
            quarantine_path = self._quarantine_corrupt_unlocked(exc)
            raise SnapStoreCorruptionError(
                "Snapshot store is unreadable. The original file was preserved and "
                f"a quarantine copy was created at {quarantine_path}.",
                quarantine_path=quarantine_path,
            ) from exc
        if not isinstance(data, dict) or not isinstance(data.get("snaps", []), list):
            exc = ValueError("snapshot document must contain a snaps array")
            quarantine_path = self._quarantine_corrupt_unlocked(exc)
            raise SnapStoreCorruptionError(
                "Snapshot store has an invalid structure. The original file was preserved and "
                f"a quarantine copy was created at {quarantine_path}.",
                quarantine_path=quarantine_path,
            )
        return data

    def _load_unlocked(self, *, migrate: bool) -> Dict[str, Any]:
        raw = self._load_raw_unlocked()
        if not migrate:
            return raw
        migrated, changed = migrate_snapshot_store_document(raw)
        if changed:
            backup_path = self._backup_unlocked(
                f"pre-schema-v{SNAP_STORE_SCHEMA_VERSION}"
            )
            report = dict(migrated.get("migration_report") or {})
            report["backup_path"] = backup_path
            migrated["migration_report"] = report
            self._save_unlocked(migrated)
        return migrated

    def _save_unlocked(self, data: Dict[str, Any]) -> None:
        parent = os.path.dirname(self.path) or os.getcwd()
        prefix = f".{Path(self.path).name}.{os.getpid()}."
        fd, tmp_path = tempfile.mkstemp(prefix=prefix, suffix=".tmp", dir=parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))
                handle.flush()
                os.fsync(handle.fileno())
            # Validate the complete temporary document before replacing the store.
            with open(tmp_path, "r", encoding="utf-8") as handle:
                validated = json.load(handle)
            if not isinstance(validated, dict) or not isinstance(validated.get("snaps"), list):
                raise ValueError("refusing to replace snapshot store with an invalid document")
            os.replace(tmp_path, self.path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    def preview_migration(self, *, include_document: bool = False) -> Dict[str, Any]:
        """Dry-run schema migration without writing the store."""
        with _LOCK, self._file_lock():
            raw = self._load_raw_unlocked()
            migrated, changed = migrate_snapshot_store_document(raw)
            preview: Dict[str, Any] = {
                "changed": bool(changed),
                "path": self.path,
                "from_schema_version": raw.get("schema_version"),
                "to_schema_version": SNAP_STORE_SCHEMA_VERSION,
                "report": copy.deepcopy(migrated.get("migration_report") or {}),
                "review_required_ids": [
                    snap.get("id")
                    for snap in migrated.get("snaps", [])
                    if isinstance(snap, dict)
                    and bool((snap.get("calculation_context") or {}).get("review_required"))
                ],
            }
            if include_document:
                preview["document"] = migrated
            return preview

    def migrate(self) -> Dict[str, Any]:
        """Persist a schema migration after creating a byte-for-byte backup."""
        with _LOCK, self._file_lock():
            return copy.deepcopy(self._load_unlocked(migrate=True).get("migration_report") or {})

    def migration_report(self) -> Dict[str, Any]:
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=self.auto_migrate)
            return copy.deepcopy(data.get("migration_report") or {})

    def add(
        self,
        snap: Dict[str, Any],
        *,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=True)
            snaps: List[Dict[str, Any]] = [
                item for item in data.get("snaps", []) if isinstance(item, dict)
            ]
            clean_key = str(idempotency_key or "").strip() or None
            if clean_key:
                for existing in snaps:
                    persistence = existing.get("persistence")
                    if isinstance(persistence, dict) and persistence.get("idempotency_key") == clean_key:
                        return copy.deepcopy(existing)

            canonical = canonicalize_snapshot_record(snap)
            if clean_key:
                persistence = dict(canonical.get("persistence") or {})
                persistence["idempotency_key"] = clean_key
                canonical["persistence"] = persistence
            snaps.append(canonical)
            data["snaps"] = annotate_semantic_duplicates(snaps)
            migrated, _changed = migrate_snapshot_store_document(data)
            if len(snaps) > self.max_snaps:
                report = dict(migrated.get("migration_report") or {})
                report["retention_limit_exceeded"] = {
                    "configured_limit": self.max_snaps,
                    "record_count": len(snaps),
                    "records_removed": 0,
                }
                migrated["migration_report"] = report
            self._save_unlocked(migrated)
            snap_id = canonical.get("id")
            for stored in migrated.get("snaps", []):
                if isinstance(stored, dict) and stored.get("id") == snap_id:
                    return copy.deepcopy(stored)
            return copy.deepcopy(canonical)

    def list(self) -> List[Dict[str, Any]]:
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=self.auto_migrate)
            return copy.deepcopy([
                snap for snap in data.get("snaps", []) if isinstance(snap, dict)
            ])

    def get(self, snap_id: str) -> Optional[Dict[str, Any]]:
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=self.auto_migrate)
            for snap in data.get("snaps", []):
                if isinstance(snap, dict) and snap.get("id") == snap_id:
                    return copy.deepcopy(snap)
            return None

    def delete(self, snap_id: str) -> bool:
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=True)
            snaps = [
                snap for snap in data.get("snaps", [])
                if isinstance(snap, dict)
            ]
            deleted = next(
                (snap for snap in snaps if snap.get("id") == snap_id),
                None,
            )
            if deleted is None:
                return False
            new_snaps = [snap for snap in snaps if snap.get("id") != snap_id]
            backup_path = self._backup_unlocked("pre-delete")
            deleted_at = _utc_now_iso()
            relationship_repairs: List[Dict[str, Any]] = []

            prior_revision_id = str(deleted.get("supersedes") or "").strip()
            prior_revision = next(
                (
                    snap for snap in new_snaps
                    if str(snap.get("id")) == prior_revision_id
                ),
                None,
            )
            for linked in new_snaps:
                if str(linked.get("superseded_by") or "") != str(snap_id):
                    continue
                linked_id = str(linked.get("id") or "")
                if (
                    prior_revision is not None
                    and linked_id != prior_revision_id
                ):
                    linked["superseded_by"] = prior_revision_id
                    repair_status = "replacement_revision_reverted"
                    repair_kind = "repointed_to_prior_live_revision"
                    replacement_pointer = prior_revision_id
                else:
                    linked.pop("superseded_by", None)
                    repair_status = "replacement_deleted_source_reopened"
                    repair_kind = "source_reopened_for_correction"
                    replacement_pointer = None
                history = list(linked.get("supersession_history") or [])
                history.append({
                    "event": "replacement_deleted",
                    "replacement_id": str(snap_id),
                    "reverted_to_replacement_id": replacement_pointer,
                    "occurred_at": deleted_at,
                    "source_reopened_for_correction": replacement_pointer is None,
                })
                linked["supersession_history"] = history
                linked["supersession"] = {
                    "status": repair_status,
                    "replacement_id": replacement_pointer,
                    "deleted_replacement_id": str(snap_id),
                    "occurred_at": deleted_at,
                    "records_removed": 1,
                }
                relationship_repairs.append({
                    "kind": repair_kind,
                    "source_id": linked_id,
                    "deleted_replacement_id": str(snap_id),
                    "replacement_id": replacement_pointer,
                })

            replacement_id = str(deleted.get("superseded_by") or "").strip()
            if replacement_id:
                replacement = next(
                    (
                        snap for snap in new_snaps
                        if str(snap.get("id")) == replacement_id
                    ),
                    None,
                )
                if (
                    replacement is not None
                    and str(replacement.get("supersedes") or "") == str(snap_id)
                ):
                    replacement.pop("supersedes", None)
                    history = list(replacement.get("supersession_history") or [])
                    history.append({
                        "event": "source_deleted",
                        "source_id": str(snap_id),
                        "occurred_at": deleted_at,
                        "replacement_retained": True,
                    })
                    replacement["supersession_history"] = history
                    relationship_repairs.append({
                        "kind": "replacement_detached_from_deleted_source",
                        "deleted_source_id": str(snap_id),
                        "replacement_id": replacement_id,
                    })

            tombstones = dict(data.get("tombstones") or {})
            tombstones[str(snap_id)] = {
                "deleted_at": deleted_at,
                "reason": "user_deleted",
                "backup_path": backup_path,
                "backup_contains_deleted_record": bool(backup_path),
                "relationship_repairs": relationship_repairs,
            }
            data["tombstones"] = tombstones
            data["snaps"] = annotate_semantic_duplicates(new_snaps)
            migrated, _changed = migrate_snapshot_store_document(data)
            self._save_unlocked(migrated)
            return True

    def import_legacy(self, legacy_path: str) -> Dict[str, Any]:
        """Import a legacy file once; tombstoned records never reappear."""
        source_path = os.path.abspath(legacy_path)
        source_key = hashlib.sha256(source_path.casefold().encode("utf-8")).hexdigest()
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=True)
            legacy_imports = dict(data.get("legacy_imports") or {})
            prior = legacy_imports.get(source_key)
            try:
                source_bytes = Path(source_path).read_bytes()
                legacy_raw = json.loads(source_bytes.decode("utf-8-sig"))
            except Exception as exc:
                raise SnapStoreCorruptionError(
                    f"Legacy snapshot store could not be imported safely: {source_path}"
                ) from exc
            source_sha256 = hashlib.sha256(source_bytes).hexdigest()
            if (
                isinstance(prior, dict)
                and prior.get("completed")
                and prior.get("source_sha256") == source_sha256
            ):
                return copy.deepcopy(prior)
            legacy_document, _changed = migrate_snapshot_store_document(legacy_raw)
            current_snaps = [
                snap for snap in data.get("snaps", []) if isinstance(snap, dict)
            ]
            current_ids = {str(snap.get("id")) for snap in current_snaps if snap.get("id")}
            tombstones = {
                str(key) for key in (data.get("tombstones") or {}).keys()
            }
            imported_ids: List[str] = []
            skipped_existing: List[str] = []
            skipped_tombstoned: List[str] = []
            legacy_to_prepend: List[Dict[str, Any]] = []
            for snap in legacy_document.get("snaps", []):
                if not isinstance(snap, dict):
                    continue
                snap_id = str(snap.get("id") or "")
                if snap_id and snap_id in tombstones:
                    skipped_tombstoned.append(snap_id)
                    continue
                if snap_id and snap_id in current_ids:
                    skipped_existing.append(snap_id)
                    continue
                legacy_to_prepend.append(snap)
                if snap_id:
                    current_ids.add(snap_id)
                    imported_ids.append(snap_id)
            current_snaps = legacy_to_prepend + current_snaps
            backup_path = (
                self._backup_unlocked("pre-legacy-import")
                if imported_ids
                else (
                    prior.get("backup_path")
                    if isinstance(prior, dict)
                    else None
                )
            )
            prior_imported_ids = (
                list(prior.get("imported_ids") or [])
                if isinstance(prior, dict)
                else []
            )
            cumulative_imported_ids = list(dict.fromkeys(
                prior_imported_ids + imported_ids
            ))
            import_report = {
                "completed": True,
                "source_path": source_path,
                "source_sha256": source_sha256,
                "imported_ids": cumulative_imported_ids,
                "last_imported_ids": imported_ids,
                "skipped_existing_ids": skipped_existing,
                "skipped_tombstoned_ids": skipped_tombstoned,
                "records_removed": 0,
                "backup_path": backup_path,
            }
            legacy_imports[source_key] = import_report
            data["legacy_imports"] = legacy_imports
            data["snaps"] = annotate_semantic_duplicates(current_snaps)
            migrated, _changed = migrate_snapshot_store_document(data)
            if len(current_snaps) > self.max_snaps:
                report = dict(migrated.get("migration_report") or {})
                report["retention_limit_exceeded"] = {
                    "configured_limit": self.max_snaps,
                    "record_count": len(current_snaps),
                    "records_removed": 0,
                }
                migrated["migration_report"] = report
            self._save_unlocked(migrated)
            return copy.deepcopy(import_report)

    def add_replacement(
        self,
        original_id: str,
        replacement: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Add a corrected chart and mark, but never delete, its legacy source."""
        with _LOCK, self._file_lock():
            data = self._load_unlocked(migrate=True)
            snaps = [
                snap for snap in data.get("snaps", []) if isinstance(snap, dict)
            ]
            original = next((snap for snap in snaps if snap.get("id") == original_id), None)
            if original is None:
                raise KeyError(f"Snapshot not found: {original_id}")
            canonical = canonicalize_snapshot_record(replacement)
            replacement_id = canonical.get("id")
            if not replacement_id:
                raise ValueError("Replacement snapshot requires an id")
            existing_replacement_id = original.get("superseded_by")
            if existing_replacement_id:
                existing = next(
                    (snap for snap in snaps if snap.get("id") == existing_replacement_id),
                    None,
                )
                if existing is not None:
                    existing_context = (
                        existing.get("calculation_context")
                        if isinstance(existing.get("calculation_context"), dict)
                        else {}
                    )
                    new_context = (
                        canonical.get("calculation_context")
                        if isinstance(canonical.get("calculation_context"), dict)
                        else {}
                    )
                    if (
                        existing_context.get("context_fingerprint")
                        and existing_context.get("context_fingerprint")
                        == new_context.get("context_fingerprint")
                    ):
                        return copy.deepcopy(existing)
                    if any(
                        str(snap.get("id")) == str(replacement_id)
                        for snap in snaps
                    ):
                        raise ValueError(
                            "Changed correction context requires a new replacement id"
                        )
                    canonical["supersedes"] = str(existing_replacement_id)
                    canonical["correction_source_id"] = original_id
                    canonical["correction_revision"] = int(
                        existing.get("correction_revision") or 1
                    ) + 1
                    existing["superseded_by"] = replacement_id
                    existing_history = list(
                        existing.get("supersession_history") or []
                    )
                    existing_history.append({
                        "event": "correction_revised",
                        "replacement_id": replacement_id,
                        "occurred_at": _utc_now_iso(),
                    })
                    existing["supersession_history"] = existing_history
                else:
                    canonical["supersedes"] = original_id
                    canonical["correction_source_id"] = original_id
                    canonical["correction_revision"] = 1
            else:
                canonical["supersedes"] = original_id
                canonical["correction_source_id"] = original_id
                canonical["correction_revision"] = 1
            original["superseded_by"] = replacement_id
            original["supersession"] = {
                "status": "preserved_legacy_source",
                "replacement_id": replacement_id,
                "revision": canonical.get("correction_revision"),
                "records_removed": 0,
            }
            snaps.append(canonical)
            data["snaps"] = annotate_semantic_duplicates(snaps)
            migrated, _changed = migrate_snapshot_store_document(data)
            if len(snaps) > self.max_snaps:
                report = dict(migrated.get("migration_report") or {})
                report["retention_limit_exceeded"] = {
                    "configured_limit": self.max_snaps,
                    "record_count": len(snaps),
                    "records_removed": 0,
                }
                migrated["migration_report"] = report
            self._save_unlocked(migrated)
            return copy.deepcopy(canonical)
