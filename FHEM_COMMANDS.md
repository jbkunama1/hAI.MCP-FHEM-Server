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

### 2. `fhem_device_search`
Search FHEM devices by room or type.

| Parameter | Type | Description |
|-----------|------|-------------|
| `room` | `str` | Room name (matches the `room` attribute) |
| `type_filter` | `str` | Exact device type, e.g. `Dummy`, `FRITZBOX`, `Shelly` |

**Examples**:
- All devices in a room: `fhem_device_search(room="LivingRoom")`
- Lights in a room: `fhem_device_search(room="LivingRoom", type_filter="HUEDevice")`

### 3. `fhem_get`
Read a single reading of a device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `reading` | `str` | Reading name, e.g. `state`, `temperature` |

**Example**: `fhem_get("WohnzimmerLampe", "state")`

### 4. `fhem_get_readings`
Get all readings of a device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |

**Example**: `fhem_get_readings("WohnzimmerLampe")`

### 5. `fhem_reading_history`
Get the history of a FHEM reading.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `reading` | `str` | Reading name |
| `start` | `str` | Optional start date/time |
| `end` | `str` | Optional end date/time |

**Example**: `fhem_reading_history("Wetter", "temperature", "2026-08-01", "2026-08-05")`

### 6. `fhem_set`
Control a device (set a value/state).

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `value` | `str` | Command value, e.g. `on`, `off`, `temperature 21.5` |

**Examples**:
- `fhem_set("WohnzimmerLampe", "on")`
- `fhem_set("Heizung", "desired-temp 22")`

### 7. `fhem_set_multiple`
Set multiple values of a device in one call.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `values` | `dict` | Map of command → value, e.g. `{"on": "", "rgb": "FF0000"}` |

**Example**: `fhem_set_multiple("Lampe", {"on": "", "rgb": "FF0000"})`

### 8. `fhem_define`
Create a new FHEM device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | New device name |
| `type` | `str` | Device type, e.g. `Dummy`, `Shelly` |
| `def_attr` | `str` | Optional type-specific parameters |

**Example**: `fhem_define("Wetter", "Dummy")`

### 9. `fhem_attr`
Set an attribute of a FHEM device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |
| `name` | `str` | Attribute name |
| `value` | `str` | Attribute value |

**Example**: `fhem_attr("WohnzimmerLampe", "room", "LivingRoom")`

### 10. `fhem_list_attrs`
List all attributes of a FHEM device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `device` | `str` | Device name |

**Example**: `fhem_list_attrs("WohnzimmerLampe")`

### 11. `fhem_delete`
Delete a FHEM device.

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Device name |

**Example**: `fhem_delete("WohnzimmerLampe")`

### 12. `fhem_command`
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

### **List Devices by Room**
```bash
list room=<room_name>
```

**Example**:
```bash
list room=LivingRoom
```

---

## 🤖 Agent Interaction Guide

### **1. Discover Devices**
Call `fhem_list_devices()` first — returns all devices as JSON with names, types and readings. Filter by room with `fhem_device_search(room=...)`.

### **2. Read Device Status**
Call `fhem_get(<device>, <reading>)` — e.g. `fhem_get("light", "state")`. To get all readings at once, use `fhem_get_readings(<device>)`.

### **3. Control a Device**
Call `fhem_set(<device>, <value>)` — e.g. `fhem_set("light", "on")`. For several values at once use `fhem_set_multiple(<device>, {...})`.

### **4. Manage Devices**
Use `fhem_define` to create, `fhem_attr`/`fhem_list_attrs` to manage attributes, and `fhem_delete` to remove devices.

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