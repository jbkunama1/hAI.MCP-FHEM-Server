import json
import os
import requests
import hashlib
import secrets
from contextlib import asynccontextmanager
from starlette.responses import JSONResponse
from mcp.server.fastmcp import FastMCP
from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel

MCP_API_KEY = os.getenv("MCP_API_KEY")
FHEM_URL = os.getenv("FHEM_URL", "http://192.168.178.15:8085/fhem")

# Initialize admin DB on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    from admin_db import init_db
    await init_db()
    yield

# Admin API Models
class InstanceCreate(BaseModel):
    name: str
    url: str
    api_key: str | None = None

class InstanceResponse(BaseModel):
    id: int
    name: str
    url: str
    api_key: str | None = None

class TokenCreate(BaseModel):
    name: str

class TokenResponse(BaseModel):
    token: str

# Simple token store (in-memory for demo, use DB in production)
_valid_tokens = set()

def _verify_admin_token(authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    if token not in _valid_tokens:
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True

# Initialize admin token on startup
_admin_token = secrets.token_urlsafe(32)
_valid_tokens.add(_admin_token)
print(f"Admin token: {_admin_token}")

def _fhem(cmd: str) -> str:
    resp = requests.get(FHEM_URL, params={"cmd": cmd, "XHR": "1"}, timeout=5)
    resp.raise_for_status()
    return resp.text

def _devices() -> list[dict]:
    """Return parsed device list from FHEM jsonlist2."""
    return json.loads(_fhem("jsonlist2")).get("Results", [])


def _device(name: str) -> dict:
    """Return a single device by name."""
    return next((d for d in _devices() if d.get("Name") == name), None)


def _device_search(room: str = "", type_filter: str = "") -> list[dict]:
    """Search for FHEM devices by room or type."""
    devs = _devices()
    if room:
        devs = [d for d in devs if d.get("ATTR", {}).get("room", "").lower() == room.lower()]
    if type_filter:
        devs = [d for d in devs if type_filter.lower() == d.get("TYPE", "").lower()]
    return devs

mcp = FastMCP(
    "fhem-mcp",
    instructions=(
        "This connector controls a FHEM home automation system. "
        "Sent via MCP protocol to help AI understand how to use this connector.\n\n"
        "Workflow:\n"
        "1. Always start with fhem_list_devices() to discover available devices (names, types, readings) — never guess device names. "
        "Use fhem_device_search(room=...) to filter by room.\n"
        "2. To read a value, use fhem_get(device, reading) or fhem_get_readings(device) for all readings at once.\n"
        "3. To control a device, use fhem_set(device, value), e.g. fhem_set('WohnzimmerLampe', 'on'). "
        "Common values per type: on/off/toggle/dim <0-100>/rgb <RRGGBB> for lights; desired-temp <value> for thermostats. "
        "For several values at once use fhem_set_multiple(device, {...}).\n"
        "4. To create a device, use fhem_define(name, type, def_attr); manage attributes with fhem_attr/fhem_list_attrs; delete with fhem_delete.\n"
        "5. For anything not covered, use fhem_command(cmd) with a raw FHEM command.\n"
        "6. Only call write tools (fhem_set/fhem_set_multiple/fhem_define/fhem_attr/fhem_delete) when the user explicitly asks to change something."
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
def fhem_set(device: str, value: str) -> str:
    """Set a value for a FHEM device, e.g. fhem_set('WohnzimmerLampe', 'on')."""
    try:
        return _fhem(f"set {device} {value}")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_set_multiple(device: str, values: dict) -> str:
    """Set multiple values for a FHEM device at once."""
    try:
        cmd = ";;".join([f"{k} {v}" for k, v in values.items()])
        return _fhem(f"set {device} {cmd}")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_define(name: str, type: str, definition: str = "") -> str:
    """Define a new FHEM device."""
    try:
        cmd = f"define {name} {type} {definition}".strip()
        return _fhem(cmd)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_attr(device: str, attribute: str, value: str) -> str:
    """Set an attribute for a FHEM device."""
    try:
        return _fhem(f"attr {device} {attribute} {value}")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"
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
def fhem_list_attrs(device: str) -> str:
    """List all attributes of a FHEM device."""
    try:
        dev = _device(device)
        if not dev:
            return f"Device {device} not found"
        return json.dumps(dev.get("ATTR", {}), ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_device_search(room: str = "", type_filter: str = "") -> str:
    """Search for FHEM devices by room or type."""
    try:
        devs = _device_search(room, type_filter)
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
def fhem_get_readings(device: str) -> str:
    """Get all readings of a FHEM device."""
    try:
        dev = _device(device)
        if not dev:
            return f"Device {device} not found"
        return json.dumps(dev.get("READINGS", {}), ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_reading_history(device: str, reading: str, start: str = "", end: str = "") -> str:
    """Get the history of a FHEM reading."""
    try:
        cmd = f"get {device} {reading}"
        if start:
            cmd += f" {start}"
        if end:
            cmd += f" {end}"
        return _fhem(cmd)
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
def fhem_set_multiple(device: str, values: dict) -> str:
    """Set multiple attributes of a FHEM device at once."""
    try:
        results = {}
        for key, value in values.items():
            results[key] = _fhem(f"set {device} {key} {value}")
        return json.dumps(results, ensure_ascii=False, indent=1)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_define(name: str, type: str, def_attr: str = "") -> str:
    """Create a new FHEM device: fhem_define('Wetter', 'Dummy') or fhem_define('Lampe', 'Shelly', 'http://...')."""
    try:
        return _fhem(f"define {name} {type} {def_attr}".rstrip())
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_attr(device: str, name: str, value: str) -> str:
    """Set an attribute of a FHEM device."""
    try:
        return _fhem(f"attr {device} {name} {value}")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"
@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})

# Admin API Routes
@app.get("/admin/api/instances", response_model=list[InstanceResponse])
async def list_instances(_: bool = Depends(_verify_admin_token)):
    """List all configured FHEM instances."""
    from admin_db import get_instances
    instances = get_instances()
    return [{"id": i[0], "name": i[1], "url": i[2], "api_key": i[3]} for i in instances]

@app.post("/admin/api/instances", response_model=InstanceResponse, status_code=201)
async def create_instance(instance: InstanceCreate, _: bool = Depends(_verify_admin_token)):
    """Add a new FHEM instance."""
    from admin_db import add_instance
    instance_id = add_instance(instance.name, instance.url, instance.api_key)
    return {"id": instance_id, "name": instance.name, "url": instance.url, "api_key": instance.api_key}

@app.delete("/admin/api/instances/{instance_id}")
async def delete_instance(instance_id: int, _: bool = Depends(_verify_admin_token)):
    """Delete a FHEM instance."""
    from admin_db import delete_instance
    delete_instance(instance_id)
    return {"status": "deleted"}

@app.get("/admin/api/tokens", response_model=list[TokenResponse])
async def list_tokens(_: bool = Depends(_verify_admin_token)):
    """List all MCP API tokens (admin only)."""
    return [{"token": t} for t in _valid_tokens]

@app.post("/admin/api/tokens", response_model=TokenResponse, status_code=201)
async def create_token(token: TokenCreate, _: bool = Depends(_verify_admin_token)):
    """Create a new MCP API token."""
    new_token = secrets.token_urlsafe(32)
    _valid_tokens.add(new_token)
    return {"token": new_token}

@app.delete("/admin/api/tokens")
async def delete_token(token: str, _: bool = Depends(_verify_admin_token)):
    """Revoke an MCP API token."""
    if token in _valid_tokens:
        _valid_tokens.remove(token)
    return {"status": "revoked"}

# Static file serving for admin UI
from starlette.staticfiles import StaticFiles
import os

admin_ui_path = os.path.join(os.path.dirname(__file__), "admin_ui")
if os.path.exists(admin_ui_path):
    app.mount("/admin", StaticFiles(directory=admin_ui_path, html=True), name="admin")

# ASGI app for uvicorn (runs its own lifespan, needed by the MCP session manager)
app = mcp.streamable_http_app()

# X-API-Key auth for the MCP endpoint (health stays public)
if MCP_API_KEY:
    from starlette.middleware.base import BaseHTTPMiddleware

    class ApiKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path in ["/health", "/admin"] or request.url.path.startswith("/admin/"):
                return await call_next(request)
            if request.headers.get("X-API-Key") != MCP_API_KEY:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return await call_next(request)

    app.add_middleware(ApiKeyMiddleware)
