# 📅 DCBot — Event & Channel Management Discord Bot

DCBot is a **Discord bot built with discord.py 2.x (Slash Commands)** designed to manage events inside Discord servers in a **structured, safe, and extensible** way.

It supports:
- Event creation and lifecycle management
- Optional per-event discussion channels
- Automatic cleanup of expired events and channels
- Category (Discord CategoryChannel) management with autocomplete
- Timezone-aware scheduling (with DST support)
- A clean architecture prepared for RSVP / participation limits

> Design goal: **predictable behavior, clear ownership, and long-term maintainability**  
> — not a one-off script.

---

## ✨ Features

### ✅ Event Creation
- Create events using `/event create`
- Supported parameters:
  - `title`
  - `start` / `end` time (local time)
  - `description` (optional)
  - `member_limit` (optional)
  - `create_channel` (optional)
  - `category` (optional, existing or new)

### ✅ Optional Event Channels
- Automatically create a dedicated text channel for an event
- Channel names are safely slugified
- Channels can be placed under a selected category
- Only channels created by the bot are ever deleted

### ✅ Category Management
- Each guild maintains its own **category option list**
- Sources:
  - Categories previously created by the bot
  - Existing Discord categories in the server
- Slash command autocomplete support
- New categories are automatically added to the list

### ✅ Navigation Button
- After event creation, the bot sends:
  - An embed describing the event
  - A **“Go to channel”** button
- One-click navigation to the event channel

### ✅ Event Lifecycle & Cleanup
- Every event has an expiration timestamp (`expires_at`)
- Expiration rules:
  - If `end` is provided → expires at `end`
  - Otherwise:
    - **test mode** → 10 minutes
    - **prod mode** → 7 days
- Background cleanup task:
  - Deletes expired events
  - Deletes only bot-managed channels (safe by design)

### ✅ Command Restrictions
- `/event create` can be restricted to a **single designated channel**
- Uses `channel_id` (stable, rename-safe)

### ✅ Timezone-Aware Scheduling
- Uses **IANA time zones** (e.g. `Europe/Paris`)
- Automatically handles daylight saving time
- Windows supported via `tzdata`

---

## 🧱 Project Structure

```
dcbot/
├── main.py
├── requirements.txt
├── config.yaml
├── events.db
└── src/
    ├── client.py
    ├── config_loading.py
    ├── restrictions.py
    ├── base/
    ├── channel/
    │   ├── create.py
    │   ├── category.py
    │   └── __init__.py
    └── event/
        ├── create.py
        ├── list.py
        └── __init__.py
```

---

## ⚙️ Requirements

- Python **3.10+**
- Discord bot with Slash Commands enabled
- Windows requires `tzdata`

---

## 📦 Installation

```bash
git clone https://github.com/Hemingzhi/dcrobot.git
cd dcbot
python -m venv .venv
```

Activate venv and install dependencies:


```bash
source .venv/Scripts/activate
pip install -r requirements.txt
```

---

## 🔐 Configuration (`config.yaml`)

Copy config_default.yaml to config.yaml and modify it

---

## ▶️ Run

```bash
python main.py
```

---

## 📄 License
MIT
