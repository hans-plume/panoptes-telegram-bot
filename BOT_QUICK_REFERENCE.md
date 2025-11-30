# Panoptes Bot - Quick Reference Guide

## Guided Workflow

The bot is designed to guide you. Just follow the suggestions after each command.

**Typical Flow:** `/start` → `/setup` → `/locations` → `/status` → (Choose next step)

---
## Command Reference

### Primary Commands
| Command | Description |
|---|---|
| `/start` | Greets you and suggests the first step. |
| `/setup` | **(Run once)** Starts the guided OAuth 2.0 setup. |
| `/locations`| Select the customer and network location you want to monitor. |
| `/status` | **(Main command)** Shows a full health report for the selected location and suggests next actions. |

### Detailed Commands
*(Use after running `/status`)*
| Command | Description |
|---|---|
| `/nodes` | Shows technical details for each pod (firmware, IP, etc.). |
| `/wifi` | Lists all configured WiFi SSIDs and their security settings. |

---
## After `/status`: What to do next?

After you run `/status`, the bot will present you with a menu of options. This is the core of the guided navigation.

```
What would you like to do next?
  [ Get Node Details ]  -> Runs /nodes
  [ List WiFi Networks ]-> Runs /wifi
  [ Change Location ]   -> Runs /locations
```
---
## Authentication

-   **Command**: `/setup`
-   **Process**: A 2-step conversation where you provide your **Authorization Header** and **Partner ID**.
-   **Token Management**: The bot handles everything automatically (obtaining, storing, and refreshing tokens). There is no need to manually manage tokens.
---
