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

async def _get_instance(instance_id: int = None, instance_name: str = None):
    """Get instance from database by ID or name."""
    if not instance_id and not instance_name:
        return None
    from admin_db import get_instances
    instances = await get_instances()
    if instance_id:
        return next((i for i in instances if i[0] == instance_id), None)
    return next((i for i in instances if i[1].lower() == instance_name.lower()), None)

def _build_fhem_url(instance):
    """Build FHEM URL with optional API key."""
    if not instance:
        return FHEM_URL
    return instance[2]

async def _fhem_async(cmd: str, instance_id: int = None, instance_name: str = None) -> str:
    """Execute FHEM command on specific instance or default."""
    instance = await _get_instance(instance_id, instance_name)
    url = _build_fhem_url(instance)
    headers = {}
    if instance and instance[3]:  # api_key
        headers["Authorization"] = f"Bearer {instance[3]}"
    resp = requests.get(url, params={"cmd": cmd, "XHR": "1"}, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.text

def _fhem(cmd: str, instance_id: int = None, instance_name: str = None) -> str:
    """Sync wrapper for _fhem_async."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Create task if loop is running
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _fhem_async(cmd, instance_id, instance_name))
                return future.result()
        else:
            return asyncio.run(_fhem_async(cmd, instance_id, instance_name))
    except RuntimeError:
        return asyncio.run(_fhem_async(cmd, instance_id, instance_name))

async def _devices_async(instance_id: int = None, instance_name: str = None) -> list[dict]:
    """Return parsed device list from FHEM jsonlist2 for specific instance."""
    result = await _fhem_async("jsonlist2", instance_id, instance_name)
    return json.loads(result).get("Results", [])

def _devices(instance_id: int = None, instance_name: str = None) -> list[dict]:
    """Sync wrapper for _devices_async."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _devices_async(instance_id, instance_name))
                return future.result()
        else:
            return asyncio.run(_devices_async(instance_id, instance_name))
    except RuntimeError:
        return asyncio.run(_devices_async(instance_id, instance_name))

def _device(name: str, instance_id: int = None, instance_name: str = None) -> dict:
    """Return a single device by name from specific instance."""
    devs = _devices(instance_id, instance_name)
    return next((d for d in devs if d.get("Name") == name), None)

def _device_search(room: str = "", type_filter: str = "", instance_id: int = None, instance_name: str = None) -> list[dict]:
    """Search for FHEM devices by room or type on specific instance."""
    devs = _devices(instance_id, instance_name)
    if room:
        devs = [d for d in devs if d.get("ATTR", {}).get("room", "").lower() == room.lower()]
    if type_filter:
        devs = [d for d in devs if type_filter.lower() == d.get("TYPE", "").lower()]
    return devs

# Initialize admin DB on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    from admin_db import init_db, get_tokens, add_token
    await init_db()
    # Create initial admin token if none exists
    tokens = await get_tokens()
    if not tokens:
        initial_token = secrets.token_urlsafe(32)
        await add_token(initial_token)
        print(f"Initial admin token created: {initial_token}")
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

async def _verify_admin_token(authorization: str = Header(None)):
    if authorization is None:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    token = authorization.replace("Bearer ", "")
    from admin_db import verify_token
    if not await verify_token(token):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True

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
def fhem_command(cmd: str, instance_id: int = None, instance_name: str = None) -> str:
    """Execute a raw FHEM command and return the result."""
    try:
        return _fhem(cmd, instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_set(device: str, value: str, instance_id: int = None, instance_name: str = None) -> str:
    """Set a value for a FHEM device, e.g. fhem_set('WohnzimmerLampe', 'on')."""
    try:
        return _fhem(f"set {device} {value}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_set_multiple(device: str, values: dict, instance_id: int = None, instance_name: str = None) -> str:
    """Set multiple values for a FHEM device at once."""
    try:
        cmd = ";;".join([f"{k} {v}" for k, v in values.items()])
        return _fhem(f"set {device} {cmd}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_define(name: str, type: str, definition: str = "", instance_id: int = None, instance_name: str = None) -> str:
    """Define a new FHEM device."""
    try:
        cmd = f"define {name} {type} {definition}".strip()
        return _fhem(cmd, instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_attr(device: str, attribute: str, value: str, instance_id: int = None, instance_name: str = None) -> str:
    """Set an attribute for a FHEM device."""
    try:
        return _fhem(f"attr {device} {attribute} {value}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_list_devices(name_filter: str = "", type_filter: str = "", instance_id: int = None, instance_name: str = None) -> str:
    """List FHEM devices as JSON, optionally filtered by name substring or device type (e.g. Dummy, FRITZBOX, Shelly)."""
    try:
        devs = _devices(instance_id, instance_name)
        if name_filter:
            devs = [d for d in devs if name_filter.lower() in d.get("Name", "").lower()]
        if type_filter:
            devs = [d for d in devs if type_filter.lower() == d.get("TYPE", "").lower()]
        return json.dumps(devs, ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_list_attrs(device: str, instance_id: int = None, instance_name: str = None) -> str:
    """List all attributes of a FHEM device."""
    try:
        dev = _device(device, instance_id, instance_name)
        if not dev:
            return f"Device {device} not found"
        return json.dumps(dev.get("ATTR", {}), ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_device_search(room: str = "", type_filter: str = "", instance_id: int = None, instance_name: str = None) -> str:
    """Search for FHEM devices by room or type."""
    try:
        devs = _device_search(room, type_filter, instance_id, instance_name)
        return json.dumps(devs, ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_get(device: str, reading: str, instance_id: int = None, instance_name: str = None) -> str:
    """Read a single reading of a FHEM device, e.g. fhem_get('WohnzimmerLampe', 'state')."""
    try:
        return _fhem(f"get {device} {reading}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_get_readings(device: str, instance_id: int = None, instance_name: str = None) -> str:
    """Get all readings of a FHEM device."""
    try:
        dev = _device(device, instance_id, instance_name)
        if not dev:
            return f"Device {device} not found"
        return json.dumps(dev.get("READINGS", {}), ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_reading_history(device: str, reading: str, start: str = "", end: str = "", instance_id: int = None, instance_name: str = None) -> str:
    """Get the history of a FHEM reading."""
    try:
        cmd = f"get {device} {reading}"
        if start:
            cmd += f" {start}"
        if end:
            cmd += f" {end}"
        return _fhem(cmd, instance_id, instance_name)
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
    instance_id = await add_instance(instance.name, instance.url, instance.api_key)
    return {"id": instance_id, "name": instance.name, "url": instance.url, "api_key": instance.api_key}

@app.delete("/admin/api/instances/{instance_id}")
async def delete_instance(instance_id: int, _: bool = Depends(_verify_admin_token)):
    """Delete a FHEM instance."""
    from admin_db import delete_instance
    await delete_instance(instance_id)
    return {"status": "deleted"}

@app.get("/admin/api/tokens", response_model=list[str])
async def list_tokens(_: bool = Depends(_verify_admin_token)):
    """List all MCP API tokens (admin only)."""
    from admin_db import get_tokens
    return await get_tokens()

@app.post("/admin/api/tokens", response_model=dict, status_code=201)
async def create_token(token_request: dict, _: bool = Depends(_verify_admin_token)):
    """Create a new MCP API token."""
    from admin_db import add_token
    new_token = secrets.token_urlsafe(32)
    await add_token(new_token)
    return {"token": new_token}

@app.delete("/admin/api/tokens")
async def delete_token(token_hash: str, _: bool = Depends(_verify_admin_token)):
    """Revoke an MCP API token."""
    from admin_db import delete_token
    await delete_token(token_hash)
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
