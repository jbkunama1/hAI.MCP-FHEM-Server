import os
import requests
from fastapi import FastAPI, Header, HTTPException

app = FastAPI()

FHEM_URL = "http://192.168.178.15:8085/fhem"
API_KEY = os.getenv("MCP_API_KEY", "secret-key")

def verify_key(key: str):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/command")
async def send_command(cmd: str, x_api_key: str = Header(...)):
    verify_key(x_api_key)
    try:
        response = requests.get(FHEM_URL, params={"cmd": cmd, "XHR": "1"}, timeout=5)
        response.raise_for_status()
        return {"status": "success", "fhem_response": response.text}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"FHEM connection failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

@app.get("/test")
async def test_connection():
    try:
        response = requests.get(FHEM_URL, params={"cmd": "version", "XHR": "1"}, timeout=5)
        response.raise_for_status()
        return {"status": "success", "fhem_response": response.text}
    except requests.exceptions.RequestException as e:
        return {"status": "error", "message": f"FHEM connection failed: {str(e)}"}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error: {str(e)}"}

# ponytail: No auth persistence, add Redis/DB if scaling.
