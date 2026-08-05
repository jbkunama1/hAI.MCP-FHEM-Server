# FHEM Command Reference for MCP Agents

This document provides a reference for MCP agents to interact with **FHEM** via the MCP server.

---

## 📡 MCP Server Endpoint

**Base URL**: `http://<mcp-server>:5887/command`

**Authentication**: `X-API-Key: your-secure-random-key-here`

**Example Request**:
```bash
curl -X GET "http://localhost:5887/command?cmd=set%20light%20on" -H "X-API-Key: your-key"
```

---

## 🔧 FHEM Commands

### **1. Basic Commands**
| Command | Description | Example |
|---------|-------------|---------|
| `set <device> <command>` | Control a device | `set light on` |
| `get <device> <reading>` | Get device status | `get light state` |
| `list <device>` | List device details | `list light` |
| `attr <device> <attribute> <value>` | Set device attribute | `attr light room LivingRoom` |
| `define <device> <type> <parameters>` | Define a new device | `define light dummy` |

---

### **2. Device Types & Commands**

#### **Lights (e.g., `HUEDevice`, `Milight`, `dummy`)**
| Command | Description |
|---------|-------------|
| `on` | Turn on the light |
| `off` | Turn off the light |
| `toggle` | Toggle light state |
| `dim <level>` | Set brightness (0-100) |
| `rgb <RRGGBB>` | Set RGB color |

**Example**:
```bash
set light on
set light dim 50
```

---

#### **Switches (e.g., `FS20`, `HM433`, `Shelly`)**
| Command | Description |
|---------|-------------|
| `on` | Turn on the switch |
| `off` | Turn off the switch |
| `toggle` | Toggle switch state |

**Example**:
```bash
set switch off
```

---

#### **Thermostats (e.g., `MAX`, `HM-CC-TC`)**
| Command | Description |
|---------|-------------|
| `desired-temp <value>` | Set target temperature |
| `mode <auto|manual|boost>` | Set operating mode |

**Example**:
```bash
set thermostat desired-temp 22
```

---

#### **Sensors (e.g., `CUL_WS`, `HM-WDS100-C6-O`)**
| Command | Description |
|---------|-------------|
| `readings` | Get all sensor readings |

**Example**:
```bash
get sensor temperature
```

---

## 📋 Device Discovery

### **List All Devices**
```bash
list
```

### **List Devices by Type**
```bash
list type=<device_type>
```

**Example**:
```bash
list type=HUEDevice
```

---

## 🤖 Agent Interaction Guide

### **1. Fetch Device List**
```bash
GET /command?cmd=list
```

### **2. Control a Device**
```bash
GET /command?cmd=set%20<device>%20<command>
```

### **3. Get Device Status**
```bash
GET /command?cmd=get%20<device>%20<reading>
```

---

## 📝 Notes
- Replace `<device>`, `<command>`, and `<reading>` with actual values.
- URL-encode commands (e.g., `set light on` → `set%20light%20on`).
- Use `list` to discover devices dynamically.

---

## 🔄 Dynamic Updates
To keep this document up-to-date:
1. Run `list` to fetch all devices.
2. Run `list type=<device_type>` to fetch device-specific commands.
3. Update this file with new commands or devices.