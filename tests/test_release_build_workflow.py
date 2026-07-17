from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RELEASE_SCRIPT = REPO_ROOT / "docs" / "release-tools" / "release-build.ps1"
RELEASE_WRAPPER = REPO_ROOT / "docs" / "release-tools" / "release-build.bat"
RELEASE_DOCS = REPO_ROOT / "docs" / "electron_updates.md"


def test_upload_only_is_rejected_instead_of_bypassing_packaging():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")
    wrapper = RELEASE_WRAPPER.read_text(encoding="utf-8")
    docs = RELEASE_DOCS.read_text(encoding="utf-8")

    assert "[switch]$UploadOnly" not in script
    assert "if ($UploadOnly)" not in script
    assert "Skipping packaging because -UploadOnly" not in script
    assert 'if /I "%~1"=="-UploadOnly" goto :upload_only_removed' in wrapper
    assert "`-UploadOnly` is deliberately rejected" in docs


def test_clean_head_and_tree_are_rechecked_at_release_boundaries():
    script = RELEASE_SCRIPT.read_text(encoding="utf-8")

    package_call = "& cmd.exe /c package-app-new.bat"
    post_package_guard = (
        "Assert-ReleaseSourceStateUnchanged $RepoRoot $SourceState "
        "'after package-app-new'"
    )
    pre_upload_guard = (
        "Assert-ReleaseSourceStateUnchanged $repoRoot $sourceState "
        "'immediately before draft asset upload'"
    )
    upload_call = (
        "Publish-ReleaseAssets $repoFullName $apiBase $github.Headers "
        "$github.Token $release $artifactState.AssetPaths $repoRoot $sourceState"
    )
    per_asset_guard = (
        'Assert-ReleaseSourceStateUnchanged $RepoRoot $SourceState '
        '"immediately before draft asset upload of $($file.Name)"'
    )
    asset_post = (
        "$uploaded = Invoke-RestMethod -Headers $uploadHeaders -Uri $uploadUri "
        "-Method Post"
    )

    assert "function Assert-ReleaseSourceStateUnchanged" in script
    assert script.index(package_call) < script.index(post_package_guard)
    assert script.index(pre_upload_guard) < script.index(upload_call)
    assert script.index(per_asset_guard) < script.index(asset_post)
    assert "'status', '--porcelain=v1', '--untracked-files=all'" in script
    assert "@('rev-parse', 'HEAD')" in script
    assert "@('rev-parse', 'HEAD^{tree}')" in script


def test_release_batch_wrapper_keeps_crlf_line_endings():
    payload = RELEASE_WRAPPER.read_bytes()

    assert b"\n" in payload
    assert payload.count(b"\r\n") == payload.count(b"\n")
