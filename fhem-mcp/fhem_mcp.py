import asyncio
import concurrent.futures
import json
import os
import secrets

import requests
from fastapi import Depends, Header, HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel
from starlette.responses import JSONResponse
from starlette.staticfiles import StaticFiles

MCP_API_KEY = os.getenv("MCP_API_KEY")
FHEM_URL = os.getenv("FHEM_URL", "http://192.168.178.15:8085/fhem")
# Optional auth for the default instance (FHEM_URL):
# "user:password" -> HTTP Basic Auth (FHEMWEB basicAuth), anything else -> Bearer token
FHEM_AUTH = os.getenv("FHEM_AUTH")


# ---------------------------------------------------------------------------
# FHEM helpers
# ---------------------------------------------------------------------------
def _run(coro):
    """Run a coroutine from a sync tool context.

    FastMCP executes sync tools in a worker thread (no running loop), so
    asyncio.run() works there. Fall back to a fresh thread when a loop is
    already running in the current thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


async def _get_instance(instance_id: int | None = None, instance_name: str | None = None):
    """Get an instance row (id, name, url, api_key) from the admin DB by ID or name."""
    if instance_id is None and not instance_name:
        return None
    from admin_db import get_instances

    instances = await get_instances()
    if instance_id is not None:
        return next((i for i in instances if i[0] == instance_id), None)
    return next((i for i in instances if i[1].lower() == instance_name.lower()), None)


def _auth_config(secret: str | None):
    """Build (headers, auth) for a stored secret.

    "user:password" -> HTTP Basic Auth (FHEMWEB basicAuth).
    Anything else   -> "Authorization: Bearer <secret>" header (e.g. reverse proxy).
    """
    if not secret:
        return {}, None
    if ":" in secret:
        user, _, password = secret.partition(":")
        return {}, (user, password)
    return {"Authorization": f"Bearer {secret}"}, None


def _fhem(cmd: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Execute a FHEM command on a specific instance or the default FHEM_URL."""
    instance = _run(_get_instance(instance_id, instance_name))
    url = instance[2] if instance else FHEM_URL
    secret = instance[3] if instance else FHEM_AUTH
    headers, auth = _auth_config(secret)
    resp = requests.get(url, params={"cmd": cmd, "XHR": "1"}, headers=headers, auth=auth, timeout=5)
    resp.raise_for_status()
    return resp.text


def _devices(instance_id: int | None = None, instance_name: str | None = None) -> list[dict]:
    """Return parsed device list from FHEM jsonlist2."""
    return json.loads(_fhem("jsonlist2", instance_id, instance_name)).get("Results", [])


def _device(name: str, instance_id: int | None = None, instance_name: str | None = None) -> dict | None:
    """Return a single device by name."""
    return next((d for d in _devices(instance_id, instance_name) if d.get("Name") == name), None)


def _device_search(room: str = "", type_filter: str = "", instance_id: int | None = None, instance_name: str | None = None) -> list[dict]:
    """Search for FHEM devices by room or type."""
    devs = _devices(instance_id, instance_name)
    if room:
        devs = [d for d in devs if d.get("ATTR", {}).get("room", "").lower() == room.lower()]
    if type_filter:
        devs = [d for d in devs if type_filter.lower() == d.get("TYPE", "").lower()]
    return devs


# ---------------------------------------------------------------------------
# Admin DB bootstrap (lifespan + lazy fallback)
# ---------------------------------------------------------------------------
async def _lifespan(app):
    from admin_db import add_token, get_tokens, init_db

    await init_db()
    if not await get_tokens():
        initial_token = secrets.token_urlsafe(32)
        await add_token(initial_token)
        print(f"Initial admin token created: {initial_token}")
    yield


async def _ensure_db() -> None:
    """Idempotent fallback so admin endpoints work even if the lifespan did not run."""
    from admin_db import init_db

    await init_db()


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
    lifespan=_lifespan,
)


@mcp.custom_route("/health", methods=["GET"])
async def health(request):
    return JSONResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# MCP tools
# ---------------------------------------------------------------------------
@mcp.tool()
def fhem_command(cmd: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Execute a raw FHEM command and return the result."""
    try:
        return _fhem(cmd, instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_set(device: str, value: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Set a value for a FHEM device, e.g. fhem_set('WohnzimmerLampe', 'on')."""
    try:
        return _fhem(f"set {device} {value}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_set_multiple(device: str, values: dict, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Set multiple values for a FHEM device at once."""
    try:
        cmd = ";;".join([f"{k} {v}" for k, v in values.items()])
        return _fhem(f"set {device} {cmd}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_define(name: str, type: str, definition: str = "", instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Define a new FHEM device."""
    try:
        cmd = f"define {name} {type} {definition}".strip()
        return _fhem(cmd, instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_attr(device: str, attribute: str, value: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Set an attribute for a FHEM device."""
    try:
        return _fhem(f"attr {device} {attribute} {value}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_delete(device: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Delete a FHEM device definition."""
    try:
        return _fhem(f"delete {device}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_list_devices(name_filter: str = "", type_filter: str = "", instance_id: int | None = None, instance_name: str | None = None) -> str:
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
def fhem_list_attrs(device: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """List all attributes of a FHEM device."""
    try:
        dev = _device(device, instance_id, instance_name)
        if not dev:
            return f"Device {device} not found"
        return json.dumps(dev.get("ATTR", {}), ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_device_search(room: str = "", type_filter: str = "", instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Search for FHEM devices by room or type."""
    try:
        devs = _device_search(room, type_filter, instance_id, instance_name)
        return json.dumps(devs, ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_get(device: str, reading: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Read a single reading of a FHEM device, e.g. fhem_get('WohnzimmerLampe', 'state')."""
    try:
        return _fhem(f"get {device} {reading}", instance_id, instance_name)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_get_readings(device: str, instance_id: int | None = None, instance_name: str | None = None) -> str:
    """Get all readings of a FHEM device."""
    try:
        dev = _device(device, instance_id, instance_name)
        if not dev:
            return f"Device {device} not found"
        return json.dumps(dev.get("READINGS", {}), ensure_ascii=False, indent=1)
    except (requests.exceptions.RequestException, ValueError) as e:
        return f"FHEM connection failed: {e}"


@mcp.tool()
def fhem_reading_history(device: str, reading: str, start: str = "", end: str = "", instance_id: int | None = None, instance_name: str | None = None) -> str:
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


# ---------------------------------------------------------------------------
# Admin API (registered AFTER the app object exists)
# ---------------------------------------------------------------------------
app = mcp.streamable_http_app()


class InstanceCreate(BaseModel):
    name: str
    url: str
    api_key: str | None = None


class InstanceResponse(BaseModel):
    id: int
    name: str
    url: str
    api_key: str | None = None


class TokenRevokeRequest(BaseModel):
    token: str


async def _verify_admin_token(authorization: str | None = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid authorization header, expected 'Bearer <token>'")
    from admin_db import verify_token

    if not await verify_token(token.strip()):
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return True


@app.get("/admin/api/instances", response_model=list[InstanceResponse])
async def list_instances(_: bool = Depends(_verify_admin_token)):
    """List all configured FHEM instances."""
    from admin_db import get_instances

    await _ensure_db()
    instances = await get_instances()
    return [{"id": i[0], "name": i[1], "url": i[2], "api_key": i[3]} for i in instances]


@app.post("/admin/api/instances", response_model=InstanceResponse, status_code=201)
async def create_instance(instance: InstanceCreate, _: bool = Depends(_verify_admin_token)):
    """Add a new FHEM instance."""
    from admin_db import add_instance

    await _ensure_db()
    instance_id = await add_instance(instance.name, instance.url, instance.api_key)
    return {"id": instance_id, "name": instance.name, "url": instance.url, "api_key": instance.api_key}


@app.put("/admin/api/instances/{instance_id}", response_model=InstanceResponse)
async def update_instance(instance_id: int, instance: InstanceCreate, _: bool = Depends(_verify_admin_token)):
    """Update an existing FHEM instance (idempotent, keeps the row id)."""
    from admin_db import update_instance as db_update_instance

    await _ensure_db()
    updated = await db_update_instance(instance_id, instance.name, instance.url, instance.api_key)
    if not updated:
        raise HTTPException(status_code=404, detail="Instance not found")
    return {"id": instance_id, "name": instance.name, "url": instance.url, "api_key": instance.api_key}


@app.delete("/admin/api/instances/{instance_id}")
async def delete_instance(instance_id: int, _: bool = Depends(_verify_admin_token)):
    """Delete a FHEM instance."""
    from admin_db import delete_instance as db_delete_instance

    await _ensure_db()
    await db_delete_instance(instance_id)
    return {"status": "deleted"}


@app.get("/admin/api/tokens", response_model=list[str])
async def list_tokens(_: bool = Depends(_verify_admin_token)):
    """List all MCP API tokens (admin only, returns SHA-256 hashes)."""
    from admin_db import get_tokens

    await _ensure_db()
    return await get_tokens()


@app.post("/admin/api/tokens", status_code=201)
async def create_token(_: bool = Depends(_verify_admin_token)):
    """Create a new MCP API token. The plaintext token is returned exactly once."""
    from admin_db import add_token

    await _ensure_db()
    new_token = secrets.token_urlsafe(32)
    await add_token(new_token)
    return {"token": new_token}


@app.delete("/admin/api/tokens")
async def delete_token(body: TokenRevokeRequest, _: bool = Depends(_verify_admin_token)):
    """Revoke an MCP API token by its hash (JSON body: {"token": "<hash>"})."""
    from admin_db import delete_token as db_delete_token

    await _ensure_db()
    await db_delete_token(body.token)
    return {"status": "revoked"}


# Static file serving for the admin UI
admin_ui_path = os.path.join(os.path.dirname(__file__), "admin_ui")
if os.path.exists(admin_ui_path):
    app.mount("/admin", StaticFiles(directory=admin_ui_path, html=True), name="admin")

# X-API-Key auth for the MCP endpoint (health + admin UI/API use their own auth)
if MCP_API_KEY:
    from starlette.middleware.base import BaseHTTPMiddleware

    class ApiKeyMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            if request.url.path == "/health" or request.url.path == "/admin" or request.url.path.startswith("/admin/"):
                return await call_next(request)
            if request.headers.get("X-API-Key") != MCP_API_KEY:
                return JSONResponse({"detail": "Unauthorized"}, status_code=401)
            return await call_next(request)

    app.add_middleware(ApiKeyMiddleware)
