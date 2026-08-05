import json
import os
import requests
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP

MCP_API_KEY = os.getenv("MCP_API_KEY")

FHEM_URL = os.getenv("FHEM_URL", "http://192.168.178.15:8085/fhem")

def _fhem(cmd: str) -> str:
    resp = requests.get(FHEM_URL, params={"cmd": cmd, "XHR": "1"}, timeout=5)
    resp.raise_for_status()
    return resp.text

def _devices() -> list[dict]:
    """Return parsed device list from FHEM jsonlist2."""
    return json.loads(_fhem("jsonlist2")).get("Results", [])

mcp = FastMCP(
    "fhem-mcp",
    instructions=(
        "This connector controls a FHEM home automation system. "
        "Sent via MCP protocol to help AI understand how to use this connector.\n\n"
        "Workflow:\n"
        "1. Always start with fhem_list_devices() to discover available devices (names, types, readings) — never guess device names.\n"
        "2. To read a value, use fhem_get(device, reading), e.g. fhem_get('WohnzimmerLampe', 'state').\n"
        "3. To control a device, use fhem_set(device, value), e.g. fhem_set('WohnzimmerLampe', 'on'). "
        "Common values per type: on/off/toggle/dim <0-100>/rgb <RRGGBB> for lights; desired-temp <value> for thermostats.\n"
        "4. To create a device, use fhem_define(name, type, def_attr).\n"
        "5. For anything not covered, use fhem_command(cmd) with a raw FHEM command.\n"
        "6. Only call write tools (fhem_set/fhem_define) when the user explicitly asks to change something."
    ),
)

@mcp.tool()
def fhem_command(cmd: str) -> str:
    """Execute a raw FHEM command and return the result."""
    try:
        return _fhem(cmd)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_list_devices(name_filter: str = "", type_filter: str = "") -> str:
    """List FHEM devices as JSON, optionally filtered by name substring or device type (e.g. Dummy, FRITZBOX, Shelly)."""
    try:
        devs = _devices()
        if name_filter:
            devs = [d for d in devs if name_filter.lower() in d.get("Name", "").lower()]
        if type_filter:
            devs = [d for d in devs if type_filter.lower() == d.get("TYPE", "").lower()]
        return json.dumps(devs, ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_get(device: str, reading: str) -> str:
    """Read a single reading of a FHEM device, e.g. fhem_get('WohnzimmerLampe', 'state')."""
    try:
        return _fhem(f"get {device} {reading}")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_set(device: str, value: str) -> str:
    """Control a FHEM device, e.g. fhem_set('WohnzimmerLampe', 'on') or fhem_set('Heizung', 'temperature 21.5')."""
    try:
        return _fhem(f"set {device} {value}")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_define(name: str, type: str, def_attr: str = "") -> str:
    """Create a new FHEM device: fhem_define('Wetter', 'Dummy') or fhem_define('Lampe', 'Shelly', 'http://...')."""
    try:
        return _fhem(f"define {name} {type} {def_attr}".rstrip())
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})

# ASGI app for uvicorn (runs its own lifespan, needed by the MCP session manager)
app = mcp.streamable_http_app()

# X-API-Key auth for the MCP endpoint (health stays public)
if MCP_API_KEY:
    from starlette.middleware.base import BaseHTTPMiddleware

    class ApiKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path == "/health":
                return await call_next(request)
            if request.headers.get("X-API-Key") != MCP_API_KEY:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return await call_next(request)

    app.add_middleware(ApiKeyMiddleware)

# ponytail: read-only list via jsonlist2; add reading-history/statistics tools on demand.
