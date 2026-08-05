import os
import requests
from fastapi import FastAPI, Request, Response, JSONResponse
from mcp.server.fastmcp import FastMCP

MCP_API_KEY = os.getenv("MCP_API_KEY")

FHEM_URL = os.getenv("FHEM_URL", "http://192.168.178.15:8085/fhem")

def _fhem(cmd: str) -> str:
    resp = requests.get(FHEM_URL, params={"cmd": cmd, "XHR": "1"}, timeout=5)
    resp.raise_for_status()
    return resp.text

mcp = FastMCP("fhem-mcp")

@mcp.tool()
def fhem_command(cmd: str) -> str:
    """Execute a raw FHEM command and return the result."""
    try:
        return _fhem(cmd)
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

@mcp.tool()
def fhem_list() -> str:
    """List all devices registered in FHEM."""
    try:
        return _fhem("list")
    except requests.exceptions.RequestException as e:
        return f"FHEM connection failed: {e}"

# FastAPI app with MCP Streamable HTTP endpoint mounted at /mcp
app = FastAPI()
app.mount("/mcp", mcp.streamable_http_app())

@app.middleware("http")
async def require_api_key(request, call_next):
    path = request.url.path.rstrip("/")
    if path != "/mcp" or not MCP_API_KEY:
        return await call_next(request)
    if request.headers.get("X-API-Key") != MCP_API_KEY:
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)

@app.get("/health")
async def health():
    return {"status": "ok"}

# ponytail: raw passthrough only; add typed get/set tools once FHEM device schema is known.
