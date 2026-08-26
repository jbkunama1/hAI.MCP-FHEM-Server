# FHEM MCP Server – Agent Instructions

Diese Anleitung beschreibt, wie Agenten den **FHEM MCP Server** nutzen, um über MCP sicher auf ein FHEM-System zuzugreifen und Geräte zu steuern.

## 1. Überblick

- **Projektname:** hAI.MCP-FHEM-Server  
- **Zweck:** MCP-Server zur Steuerung von FHEM und anderen IoT-Komponenten über KI-Agenten.  
- **Bereitstellung:** Containerisiert (Docker/Portainer) mit einem leichtgewichtigen FastMCP-Server.  
- **Protokoll:** MCP **Streamable HTTP**.

Der Server stellt MCP-Tools bereit, mit denen Agenten FHEM-Geräte auflisten, abfragen und steuern können.

## 2. Voraussetzungen für Agenten

Agenten selbst starten keine Container, sondern arbeiten **auf einem bereits laufenden FHEM MCP Server**.

Für dich als Agent gilt:

- Der Betreiber stellt dir:
  - die **MCP-Endpoint-URL** (z. B. `http://<host>:5887/mcp`),
  - einen **API-Key** (Wert von `MCP_API_KEY`).
- FHEM ist bereits erreichbar unter der vom Betreiber konfigurierten `FHEM_URL`.

Behandle die MCP-URL und den API-Key als vertrauliche Informationen und gib sie nicht aus.

## 3. Verbindung zum MCP Server

Der FHEM MCP Server ist über HTTP erreichbar:

- **Endpoint (Beispiel):**
  - `http://<host>:5887/mcp`
- **Authentifizierung:**
  - HTTP-Header `X-API-Key: <MCP_API_KEY>`

### Verhalten für Agenten

- Konfiguriere deinen MCP-Client (z. B. Copilot, Cursor, Claude Desktop) so, dass:
  - der Endpoint auf die vom Betreiber angegebene `/mcp`-URL zeigt,
  - bei jeder Anfrage der Header `X-API-Key` mit dem bereitgestellten API-Key gesetzt wird.
- Schlage dem Nutzer vor, den API-Key sicher zu speichern (z. B. als Secret/Umgebungsvariable im Client).

Wenn du Fehlermeldungen wie „unauthorized“ oder „invalid API key“ siehst, weise den Nutzer auf eine mögliche Fehlkonfiguration hin.

## 4. Exponierte MCP-Tools

Der Server stellt folgende MCP-Tools zur Verfügung:

- `fhem_list_devices(name_filter, type_filter)`  
  Listet Geräte als JSON, optional gefiltert nach Name oder Typ.

- `fhem_device_search(room, type_filter)`  
  Sucht Geräte nach Raum und/oder Typ.

- `fhem_get(device, reading)`  
  Liest einen einzelnen Reading-Wert eines Geräts.

- `fhem_get_readings(device)`  
  Ruft alle Readings eines Geräts ab.

- `fhem_reading_history(device, reading, start, end)`  
  Holt die Verlaufshistorie eines Readings in einem Zeitintervall.

- `fhem_set(device, value)`  
  Steuert ein Gerät (z. B. an/aus, Temperatur, Dimmer).

- `fhem_set_multiple(device, values)`  
  Setzt mehrere Werte eines Geräts in einem Aufruf.

- `fhem_define(name, type, def_attr)`  
  Legt ein neues FHEM-Gerät an.

- `fhem_attr(device, name, value)`  
  Setzt ein Attribut für ein Gerät.

- `fhem_list_attrs(device)`  
  Listet alle Attribute eines Geräts.

- `fhem_delete(name)`  
  Löscht ein FHEM-Gerät.

- `fhem_command(cmd)`  
  Führt einen Rohbefehl in FHEM aus.

> Für Details zu Befehlen, Parametern und typischen FHEM-Kommandos siehe die Datei `FHEM_COMMANDS.md` im Repository.

## 5. Empfohlene Workflows für Agenten

### 5.1 Umgebung erkunden (Read-Only)

1. **Geräteüberblick verschaffen**  
   - Nutze `fhem_list_devices` ohne Filter, um alle bekannten Geräte zu sehen.
2. **Geräte nach Raum/Typ filtern**  
   - Nutze `fhem_device_search`, um nur bestimmte Räume oder Gerätetypen zu betrachten.
3. **Readings prüfen**  
   - Nutze `fhem_get_readings`, um den aktuellen Zustand eines Geräts zu verstehen, bevor du Änderungen vornimmst.

### 5.2 Geräte steuern

1. **Zielgerät prüfen**  
   - Hole zuerst Readings mit `fhem_get_readings`, um sicherzustellen, dass du das richtige Gerät steuerst.
2. **Einfache Steuerung**  
   - Nutze `fhem_set`, um z. B. eine Lampe an/aus zu schalten oder eine Temperatur zu setzen.
3. **Mehrere Werte setzen**  
   - Nutze `fhem_set_multiple`, wenn für ein Gerät mehrere Parameter gleichzeitig geändert werden sollen (z. B. Mode + Setpoint).

Frage den Nutzer vor jeder potentiell sicherheitsrelevanten oder destruktiven Änderung (z. B. Heizung aus, Gerät löschen) nach einer expliziten Bestätigung.

### 5.3 Konfiguration & Geräteverwaltung

1. **Neues Gerät anlegen**  
   - Nutze `fhem_define`, wenn der Nutzer ein neues Gerät über FHEM anlegen möchte (Name, Typ, Definition vom Nutzer bestätigen lassen).
2. **Attribute anpassen**  
   - Nutze `fhem_attr` und `fhem_list_attrs`, um Konfigurationen gezielt zu ändern bzw. anzusehen.
3. **Gerät löschen**  
   - Nutze `fhem_delete` nur nach expliziter Zustimmung des Nutzers und nachdem du den Gerätetyp und die Auswirkungen erklärt hast.

### 5.4 Verlaufsauswertung

- Nutze `fhem_reading_history`, um historische Werte (z. B. Temperaturverlauf, Schaltzustände) zwischen `start` und `end` zu analysieren.
- Verwende diese Information, um dem Nutzer Hinweise zu geben (z. B. Energieverbrauch, Schaltverhalten).

## 6. Best Practices & Sicherheitsrichtlinien

- **Transparenz:** Erkläre dem Nutzer vor Ausführung eines Tools, was du tun wirst (Gerät, Aktion, Auswirkungen).  
- **Least Privilege:** Nutze nur die Tools und Parameter, die für die gewünschte Aufgabe nötig sind.  
- **Keine Blind-Kommandos:** Nutze `fhem_command` (rohe FHEM-Befehle) nur, wenn:
  - es keine passende Tool-Alternative gibt und
  - der Nutzer den genauen Befehl autorisiert hat.
- **Kein Infrastruktur-Management:**  
  - Du änderst keine Docker-/Compose-Konfigurationen, startest keine Container neu und passt keine Umgebungsvariablen an.  
  - Diese Aufgaben liegen beim Systembetreiber.

## 7. Hinweis zu Legacy-APIs

- Der frühere REST-Endpunkt `GET /command` wurde entfernt.  
- Alle Interaktionen laufen ausschließlich über das MCP-Protokoll und die oben aufgelisteten Tools.

---

## 8. Kurzfassung für Agenten

- Verbinde dich mit der vom Betreiber angegebenen MCP-URL (z. B. `http://<host>:5887/mcp`) und verwende den bereitgestellten API-Key im Header `X-API-Key`.  
- Nutze zuerst read-only Tools (`fhem_list_devices`, `fhem_get_readings`), um das System zu verstehen.  
- Führe schreibende Aktionen (`fhem_set`, `fhem_set_multiple`, `fhem_define`, `fhem_delete`) nur nach expliziter Zustimmung des Nutzers aus.
