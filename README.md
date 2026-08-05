# hAI.MCPServers 🚀

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Build](https://github.com/jbkunama1/hAI.MCPServers/actions/workflows/docker-build-push.yml/badge.svg)](https://github.com/jbkunama1/hAI.MCPServers/actions/workflows/docker-build-push.yml)
[![GitHub Stars](https://img.shields.io/github/stars/jbkunama1/hAI.MCPServers.svg)](https://github.com/jbkunama1/hAI.MCPServers/stargazers)
[![GitHub Issues](https://img.shields.io/github/issues/jbkunama1/hAI.MCPServers.svg)](https://github.com/jbkunama1/hAI.MCPServers/issues)

**MCP Servers for Home Automation and IoT Control**

A collection of lightweight, containerized MCP servers for controlling home automation systems like **FHEM**, **Home Assistant**, and more. Designed for **low RAM usage** and easy deployment via **Portainer** or Docker Compose.

---

## 📄 Documentation
- [FHEM Command Reference](FHEM_COMMANDS.md) – Guide for MCP agents to interact with FHEM.

---

## 📦 Features

- **FHEM MCP Server**: Control FHEM via a REST API.
- **Dockerized**: Ready to deploy with `docker-compose` or Portainer.
- **GitHub Actions**: Automated builds and pushes to **GHCR.io**.
- **MIT License**: Free to use, modify, and distribute.

---

## 🚀 Quick Start

### Deploy with Docker Compose

```yaml
version: '3.8'

services:
  fhem-mcp:
    image: ghcr.io/jbkunama1/hai.mcpservers/fhem-mcp:latest
    container_name: fhem-mcp
    restart: unless-stopped
    environment:
      - MCP_API_KEY=${MCP_API_KEY:-your-secure-random-key-here}
      - FHEM_URL=${FHEM_URL:-your-fhem-url-here}
    ports:
      - "5887:8000"
    networks:
      - highfishNetwork

networks:
  highfishNetwork:
    external: true
```

### Environment Variables

Set the following variables in Portainer:

```ini
MCP_API_KEY=your-secure-random-key-here
FHEM_URL=http://192.168.178.15:8085/fhem
```

### Run the Container

```bash
docker-compose up -d
```

---

## 🛠️ Usage

### Send a Command to FHEM

```bash
curl -X GET "http://localhost:5887/command?cmd=set%20light%20on" -H "X-API-Key: your-secure-random-key-here"
```

---

## 📂 Repository Structure

```
├── fhem-mcp/
│   ├── Dockerfile          # Lightweight Python Alpine image
│   ├── fhem_mcp.py         # FastAPI server for FHEM
│   ├── requirements.txt    # Python dependencies
│   └── .env.example        # Example environment variables
├── .github/
│   └── workflows/
│       └── docker-build-push.yml  # GitHub Actions workflow
├── README.md              # This file
├── docker-compose.yml     # Docker Compose for Portainer
├── FHEM_COMMANDS.md       # FHEM command reference for agents
└── LICENSE                 # MIT License
```

---

## 🤝 Contributing

Contributions are welcome! Open an **issue** or submit a **pull request**.

---

## 📜 License

This project is licensed under the **MIT License**. See [LICENSE](LICENSE) for details.

---

## 📬 Contact

For questions or feedback, reach out via [GitHub Issues](https://github.com/jbkunama1/hAI.MCPServers/issues).
