# Admin Interface & Multi-Instance Control Plan for hAI.FHEMMCP

## 1. Overview
The Admin Interface will provide a web dashboard to manage:
- FHEM Server target instances and their connection credentials (URLs, API keys, basic auth).
- MCP Server API keys for client authorization.
- Dynamic tool generation/registration (e.g. creating specialized tools per room or device type).

## 2. Architecture Components
- **Backend (Python/FastAPI inside `fhem_mcp.py` or separate service)**:
  - SQLite database for storing instance configurations, API keys, and custom tool bindings.
  - Endpoints for managing instances (`/admin/api/instances`).
  - Endpoints for generating MCP tokens (`/admin/api/tokens`).
- **Frontend (Static HTML/JS dashboard)**:
  - Served via a lightweight route or companion static page.
  - UI panels: Instances, API Keys, Tool Inspector.

## 3. Implementation Steps
1. Add an SQLite configuration store (`admin.db`).
2. Implement backend settings API for instances and API keys.
3. Build admin UI web page.
