# Configuration Guide

## Quick Start

The Scoring Engine now uses a centralized configuration system that makes it easy to add teams and systems.

### File Hierarchy

```
master_config.json          ← YOU EDIT THIS (source of truth)
    ↓
config.json                 ← Auto-generated (login credentials)
team_configs.json          ← Auto-generated, teams can edit their section via /config
scores.json                ← Auto-generated (live scores, reset on startup)
```

## Configuration Files Explained

### 1. `master_config.json` - **Edit This File**

This is your **single source of truth**. When you want to add teams or systems, edit this file.

**What it contains:**
- **Teams**: All teams in the competition (name, ID, password, subnet)
- **Systems**: All servers/systems to monitor (name, display name, IP offset, services)
- **Services**: Service definitions with points, timeouts, and defaults
- **Grading**: Global settings like grading interval

**Example:**
```json
{
  "teams": [
    {"name": "Team1", "id": "team1", "password": "changeme", "subnet": "10.0.1.0/24"},
    {"name": "Team2", "id": "team2", "password": "changeme", "subnet": "10.0.2.0/24"}
  ],
  "systems": [
    {"name": "ubuntu1", "display_name": "Ubuntu Server 1", "ip_offset": 20, "services": ["ping", "ssh", "web"]},
    {"name": "ubuntu2", "display_name": "Ubuntu Server 2", "ip_offset": 30, "services": ["ping", "ssh", "web"]}
  ],
  "services": {
    "ping": {"name": "Ping", "display_name": "Network Connectivity", "points": 10, "timeout": 20},
    "ssh": {"name": "SSH", "display_name": "SSH Service", "points": 10, "timeout": 20, 
            "default_username": "sysadmin", "default_password": "changeme", "default_port": 22},
    "web": {"name": "Web", "display_name": "Web Service", "points": 10, "timeout": 20, "default_port": 80}
  },
  "grading": {"interval_seconds": 40, "concurrent_threads": true}
}
```

### 2. `config.json` - **Auto-Generated**

Generated from `master_config.json` at server startup. Contains team login credentials.

**Don't edit this manually** - edit `master_config.json` instead and restart the server.

### 3. `team_configs.json` - **Auto-Generated, But Teams Can Edit**

Initially generated from `master_config.json` with default service settings.

**Teams can customize their own section** via the web interface at `/config`:
- Change SSH usernames, passwords, ports
- Change web server ports

Teams can **only** edit their own configuration, not other teams.

### 4. `scores.json` - **Auto-Generated**

Live scoring data. Reset to zero on every server startup.

**Never edit this file** - it's managed automatically by the grading engine.

## How to Add a New Team

1. Edit `master_config.json`
2. Add a new entry to the `teams` array:

```json
{
  "name": "Team3",
  "id": "team3",
  "password": "team3password",
  "subnet": "10.0.3.0/24"
}
```

3. Restart the server with `python3 main.py`

**That's it!** The system will automatically:
- Create login credentials in `config.json`
- Generate configurations for all systems in `team_configs.json`
- Initialize scores in `scores.json`
- Start monitoring all services

## How to Add a New System

1. Edit `master_config.json`
2. Add a new entry to the `systems` array:

```json
{
  "name": "ubuntu3",
  "display_name": "Ubuntu Server 3",
  "ip_offset": 40,
  "services": ["ping", "ssh", "web"]
}
```

3. Restart the server

**IP Addressing:**
- Team 1's ubuntu3 will be at `10.0.1.40` (team subnet .1, ip_offset 40)
- Team 2's ubuntu3 will be at `10.0.2.40` (team subnet .2, ip_offset 40)
- Team 3's ubuntu3 will be at `10.0.3.40` (team subnet .3, ip_offset 40)

## How to Add a New Service Type

If you want to add a new service type beyond ping, ssh, and web:

1. Add the service definition to `master_config.json`:

```json
"services": {
  "ping": {...},
  "ssh": {...},
  "web": {...},
  "ftp": {
    "name": "FTP",
    "display_name": "FTP Service",
    "points": 15,
    "timeout": 20,
    "default_port": 21
  }
}
```

2. Add the service to your systems:

```json
{
  "name": "ubuntu1",
  "display_name": "Ubuntu Server 1",
  "ip_offset": 20,
  "services": ["ping", "ssh", "web", "ftp"]
}
```

3. Implement the testing logic in `test_services.py`:

```python
def ftp_connection(self, username, password, ip, port=21):
    # Your FTP testing code here
    return (True, "Success") or (False, "Error message")
```

4. Add the grading method in `grader.py`:

```python
def grade_ftp(self, team_id, username, password, port, ip, score_key, points, services):
    result = services.ftp_connection(username, password, ip, port=port)
    if result[0]:
        self.append_scores(team_id, score_key, "Success", points)
    else:
        self.append_scores(team_id, score_key, result[1], 0)
```

5. Update the grading logic in `grader.py` `grade_projects()` method to handle the new service type

## Changing Service Points or Timeouts

Edit the service definition in `master_config.json`:

```json
"ssh": {
  "name": "SSH",
  "display_name": "SSH Service",
  "points": 15,        // Changed from 10
  "timeout": 30,       // Changed from 20
  "default_username": "sysadmin",
  "default_password": "changeme",
  "default_port": 22
}
```

Restart the server. All SSH checks will now award 15 points and have a 30-second timeout.

## Changing Grading Interval

Edit the `grading` section in `master_config.json`:

```json
"grading": {
  "interval_seconds": 60,  // Changed from 40
  "concurrent_threads": true
}
```

Restart the server. Grading cycles will now run every 60 seconds instead of 40.

## UI Updates

The web interface automatically adapts to your configuration:

- **Dashboard** (`/`): Displays all teams and all systems/services from master_config.json
- **Leaderboard** (`/leaderboard`): Shows stacked bar chart with all services
- **Team Config** (`/config`): Dynamically generates form fields for all systems the team has

No need to edit HTML templates when adding teams or systems!

## Example: 4 Teams, 3 Systems

```json
{
  "teams": [
    {"name": "Team1", "id": "team1", "password": "pass1", "subnet": "10.0.1.0/24"},
    {"name": "Team2", "id": "team2", "password": "pass2", "subnet": "10.0.2.0/24"},
    {"name": "Team3", "id": "team3", "password": "pass3", "subnet": "10.0.3.0/24"},
    {"name": "Team4", "id": "team4", "password": "pass4", "subnet": "10.0.4.0/24"}
  ],
  "systems": [
    {"name": "ubuntu1", "display_name": "Ubuntu Server 1", "ip_offset": 20, "services": ["ping", "ssh", "web"]},
    {"name": "ubuntu2", "display_name": "Ubuntu Server 2", "ip_offset": 30, "services": ["ping", "ssh", "web"]},
    {"name": "ubuntu3", "display_name": "Ubuntu Server 3", "ip_offset": 40, "services": ["ping", "ssh", "web"]}
  ],
  "services": {
    "ping": {"name": "Ping", "display_name": "Network Connectivity", "points": 10, "timeout": 20},
    "ssh": {"name": "SSH", "display_name": "SSH Service", "points": 10, "timeout": 20, 
            "default_username": "sysadmin", "default_password": "changeme", "default_port": 22},
    "web": {"name": "Web", "display_name": "Web Service", "points": 10, "timeout": 20, "default_port": 80}
  },
  "grading": {"interval_seconds": 40, "concurrent_threads": true}
}
```

This configuration will:
- Monitor 4 teams × 3 systems × 3 services = **36 total checks** per grading cycle
- Team1's systems at 10.0.1.20, 10.0.1.30, 10.0.1.40
- Team2's systems at 10.0.2.20, 10.0.2.30, 10.0.2.40
- etc.

## Troubleshooting

**Q: I added a team but it's not showing up**
- Make sure you restarted the server after editing `master_config.json`
- Check that your JSON syntax is valid (use a JSON validator)

**Q: The UI still shows the old systems**
- Hard refresh your browser (Ctrl+F5 or Cmd+Shift+R)
- The UI dynamically loads from `/api/systems` endpoint

**Q: Team configurations were reset**
- If you delete and recreate `team_configs.json`, teams will need to reconfigure their settings
- The initial values come from the `default_*` fields in service definitions

**Q: Scores keep resetting**
- This is by design. `scores.json` is reset on every server restart
- If you want persistent scores, remove the reset logic in `main.py` (see `if __name__ == "__main__"` section)
