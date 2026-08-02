"""License-protected loopback API used exclusively by the Electron MCP host."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from mcp_chart_service import (
    McpInputError,
    calculate_chart,
    calculate_planetary_hours,
    capabilities_payload,
)
from mcp_feature_service import calculate_synastry


mcp_bp = Blueprint("licensed_mcp", __name__, url_prefix="/api/mcp")
MAX_MCP_REQUEST_BYTES = 64 * 1024


def _ok(data):
    return jsonify({"success": True, "data": data})


def _json_body():
    if request.content_length is not None and request.content_length > MAX_MCP_REQUEST_BYTES:
        raise McpInputError("request body exceeds the MCP size limit")
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        raise McpInputError("request body must be a JSON object")
    return payload


def _calculation_response(callback):
    try:
        return _ok(callback())
    except McpInputError as exc:
        return jsonify({"success": False, "error": "invalid_request", "detail": str(exc)}), 400
    except ValueError as exc:
        return jsonify({"success": False, "error": "calculation_rejected", "detail": str(exc)}), 400


@mcp_bp.get("/capabilities")
def get_capabilities():
    return _ok(capabilities_payload())


@mcp_bp.post("/chart")
def calculate_chart_route():
    return _calculation_response(lambda: calculate_chart(_json_body(), use_current_time=False))


@mcp_bp.post("/current-positions")
def current_positions_route():
    return _calculation_response(lambda: calculate_chart(_json_body(), use_current_time=True))


@mcp_bp.post("/planetary-hours")
def planetary_hours_route():
    return _calculation_response(lambda: calculate_planetary_hours(_json_body()))


@mcp_bp.post("/synastry")
def synastry_route():
    return _calculation_response(lambda: calculate_synastry(_json_body()))


__all__ = ["mcp_bp"]
