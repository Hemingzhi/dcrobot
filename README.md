# dcbot

A Discord bot built with Python, focusing on event management with lifecycle control (TTL) and basic community interactions.

This project is designed as a **small but production-minded system**:
persistent storage, background cleanup, explicit time handling, and predictable behavior.

---

## Features

### Event Management (Slash Commands)

- `/event_create`
  - Create a new event in a server channel
  - Required:
    - `title`
    - `start` (format: `YYYY-MM-DD HH:MM`, UTC+2)
  - Optional:
    - `end`
    - `description`

**Event expiration rules (TTL):**

- If `end` is provided  
  → event expires **at end time**
- If `end` is NOT provided  
  - `test` mode: expires **10 minutes after start**
  - `prod` mode: expires **7 days after start**

Expired events are **automatically deleted** by a background cleanup task.

---

### Event Listing

- `/event_list`
  - List active (non-expired) events in the current channel
  - Results are sorted by start time
  - Expired events never appear

---

### Community Interaction

- **Welcome message**
  - When a new member joins the server, the bot sends a welcome message
  - The welcome channel is explicitly configured (not relying on Discord system defaults)

- **Ping test**
  - When a user sends `ping`
  - Bot replies with:  
    > 爱你哦（仅用于测试）

---

## Architecture Overview

```text
dcbot/
├── main.py              # Bot entry point
├── config.yaml          # Runtime configuration (not committed)
├── events.db            # SQLite database (generated at runtime)
├── src/
│   ├── config_loading.py
│   ├── event_storage.py # SQLite persistence + TTL deletion
│   └── __init__.py
├── README.md
└── .gitignore
