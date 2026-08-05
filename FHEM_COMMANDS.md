# FHEM Command Reference for MCP Agents

This document describes the tools exposed by the FHEM MCP server so MCP agents (e.g. Copilot, Cursor) can control **FHEM**.

---

## 📡 Protocol

The server speaks the **MCP Streamable HTTP** protocol. Clients connect to:

**Endpoint**: `POST http://<mcp-server>:5887/mcp`

**Authentication**: `X-API-Key: your-secure-random-key-here` header.

No REST `/command` endpoint is exposed anymore — use the MCP tools below instead.

---

## 🧰 Available MCP Tools

### 1. `fhem_list_devices`
Lists FHEM devices as JSON, optionally filtered.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name_filter` | `str` | Substring filter on device name (case-insensitive) |
| `type_filter` | `str` | Exact device type, e.g. `Dummy`, `FRITZBOX`, `Shelly` |

**Examples**:
- All devices: `fhem_list_devices()`
- Lights by type: `fhem_list_devices(type_filter="HUEDevice")`
- Devices matching name: `fhem_list_devices(name_filter="Wohnzimmer")`

### 2. `fhem_get`
Read a single reading of a device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `reading` | `str` | Reading name, e.g. `state`, `temperature` |

**Example**: `fhem_get("WohnzimmerLampe", "state")`

### 3. `fhem_set`
Control a device (set a value/state).

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `value` | `str` | Command value, e.g. `on`, `off`, `temperature 21.5` |

**Examples**:
- `fhem_set("WohnzimmerLampe", "on")`
- `fhem_set("Heizung", "desired-temp 22")`

### 4. `fhem_define`
Create a new FHEM device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | New device name |
| `type` | `str` | Device type, e.g. `Dummy`, `Shelly` |
| `def_attr` | `str` | Optional type-specific parameters |

**Example**: `fhem_define("Wetter", "Dummy")`

### 5. `fhem_command`
Execute a raw FHEM command (escape hatch for anything not covered above).

**Example**: `fhem_command("attr light room LivingRoom")`

---

## 🔧 Common FHEM Backend Commands

These are the underlying FHEM commands the tools wrap. Useful to understand the `value` format for `fhem_set`.

### **Basic Commands**
| Command | Description | Example |
|---------|-------------|---------|
| `set <device> <command>` | Control a device | `set light on` |
| `get <device> <reading>` | Get device status | `get light state` |
| `list` / `jsonlist2` | List devices | `jsonlist2` |
| `attr <device> <attribute> <value>` | Set device attribute | `attr light room LivingRoom` |
| `define <device> <type> <parameters>` | Define a new device | `define light Dummy` |

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

### **1. Discover Devices**
Call `fhem_list_devices()` first — returns all devices as JSON with names, types and readings.

### **2. Control a Device**
Call `fhem_set(<device>, <value>)` — e.g. `fhem_set("light", "on")`.

### **3. Read Device Status**
Call `fhem_get(<device>, <reading>)` — e.g. `fhem_get("light", "state")`.

---

## 📝 Notes
- Replace `<device>`, `<command>`, and `<reading>` with actual values.
- Use `fhem_list_devices` to discover devices dynamically instead of hardcoding names.
- All tool calls require the `X-API-Key` header on the MCP connection.
- If a task is not covered by the typed tools, fall back to `fhem_command` with a raw FHEM command.

---

## 🔄 Dynamic Updates
To keep this document up-to-date:
1. Run `fhem_list_devices()` to fetch all devices.
2. Map device types to their supported `set` values (see FHEM docs per module).
3. Update this file with new commands or devices.