# Panoptes Bot - Quick Reference Guide

**Version:** 1.0  
**Last Updated:** December 2024

## Guided Workflow

The bot is designed to guide you. Just follow the suggestions after each command.

**Typical Flow:** `/start` → `/setup` → `/locations` → `/status` → (Choose next step)

---
## Command Reference

### Primary Commands
| Command | Description |
|---|---|
| `/start` | Greets you and suggests the first step. |
| `/setup` | **(Run once)** Starts the 2-step OAuth 2.0 setup. |
| `/locations`| Select the customer and network location you want to monitor. |
| `/status` | **(Main command)** Shows a full health report for the selected location and suggests next actions via inline buttons. |

### Detailed Commands
*(Use after running `/status` or directly)*
| Command | Description |
|---|---|
| `/wan` | Shows WAN consumption analytics (peaks, averages, data transfer totals). |
| `/stats` | Shows connection status history with time range selection (3h, 24h, 7d). |
| `/nodes` | Shows technical details for each pod (firmware, IP, MAC, model). |
| `/wifi` | Lists all configured WiFi SSIDs and their security settings. |

---
## After `/status`: What to do next?

After you run `/status`, the bot will present you with a menu of options. This is the core of the guided navigation.

```
What would you like to do next?
  [ WAN Consumption Report ] -> Runs /wan
  [ Online Stats Report ]    -> Runs /stats
  [ Get Node Details ]       -> Runs /nodes
  [ List WiFi Networks ]     -> Runs /wifi
  [ Change Location ]        -> Runs /locations
```
---
## Authentication

-   **Command**: `/setup`
-   **Process**: A 2-step conversation where you provide your **Authorization Header** and **Partner ID**.
-   **Token Management**: The bot handles everything automatically (obtaining, storing, and refreshing tokens). There is no need to manually manage tokens.
---
## Sample Command Outputs

### `/status`
```
📊 Network Health Summary: 🟢 ALL SYSTEMS OPERATIONAL

🏠 Location: Home Network (`loc123`)

📡 Pods Status:
  - `Living Room`: ✅ Online (Excellent Health) (Ethernet)
  - `Bedroom`: ✅ Online (Excellent Health) (Mesh)

📶 Last ISP Speed Test:
  - Download: 245.50 Mbps
  - Upload: 12.30 Mbps
  - Latency: 8.50 ms
  - Last Run: 2024-12-04 10:30:00 Z

📱 Total Devices Connected: 15

[WAN Consumption Report] [Online Stats Report]
[Get Node Details] [List WiFi Networks] [Change Location]
```

### `/wan`
```
📊 WAN Link Consumption Report (Last 24 Hours)

🔴 Peak Capacity: 98.35 Mbps (RX) at 17:00 UTC
  - Transmit Peak: 25.50 Mbps at 17:00 UTC

📈 Average Usage
  - RX: 12.45 Mbps
  - TX: 3.28 Mbps

📊 95th Percentile (Capacity Planning)
  - RX: 45.20 Mbps
  - TX: 12.50 Mbps

💾 Total Data Transferred
  - Download: 6,847 MB (6.7 GB)
  - Upload: 2,156 MB (2.1 GB)

📊 Data Quality: 97.2% valid data points
📁 Data Points Analyzed: 96
```

### `/stats`
```
📊 Connection Status: Home Network
Period: Last 7 Days

[Time range data and uptime statistics]

[ 3 Hrs ] [ 24 Hrs ] [ 7 Days ]
```
---
## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Please run /setup" | Complete the 2-step OAuth setup. |
| "Please select a location" | Run `/locations` first. |
| "An API error occurred" | Check network; may need to re-run `/setup`. |
| Token expired | Bot auto-refreshes; if persistent, re-run `/setup`. |
---
