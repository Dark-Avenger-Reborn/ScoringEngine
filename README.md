# Scoring Engine

A real-time network infrastructure scoring engine for cybersecurity competitions. This application automatically tests and grades team services (ping, SSH, web) across multiple Ubuntu instances.

## Overview

This scoring engine is designed for team-based competitions where participants configure and maintain network services. The system continuously monitors service availability and awards points based on uptime and functionality.

### Features

- **Real-time Scoring**: Automated testing every 40 seconds (configurable)
- **Multi-Service Testing**: Tests ping connectivity, SSH access, and web servers
- **Live Leaderboard**: WebSocket-based real-time score updates
- **Team Configuration**: Each team can customize their service credentials and ports
- **Thread-Safe**: Concurrent testing with proper file locking mechanisms
- **Web Interface**: Clean, responsive UI with live updates
- **Centralized Configuration**: Easy-to-manage master configuration for teams and systems
- **Scalable**: Add new teams and systems by editing a single configuration file

## Architecture

### Components

- **Flask Application** (`main.py`): Main web server handling routes and authentication
- **Grader Module** (`grader.py`): Core grading logic with threaded testing
- **Service Tester** (`test_services.py`): Service validation methods (ping, SSH, HTTP)
- **Config Loader** (`config_loader.py`): Centralized configuration management utility
- **Socket.IO**: Real-time score broadcasting to connected clients
- **Eventlet**: Green threading for efficient concurrent connections

### Configuration System

The new centralized configuration system uses a single `master_config.json` file that defines:
- **Teams**: Names, IDs, passwords, and network subnets
- **Systems**: Monitored systems with their IP offsets and services
- **Services**: Service definitions with timeouts, points, and default settings
- **Grading**: Interval timing and concurrency settings

This makes it extremely easy to scale by adding new teams or systems - just edit one file!

### Tested Services

Each team has multiple Ubuntu instances (configurable) with:
- **Ping**: Network connectivity test
- **SSH**: Secure shell access verification
- **Web**: HTTP server availability check

## Installation

### Prerequisites

- Python 3.x
- Network access to target systems
- Ubuntu environment (tested on Ubuntu 24.04)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/Dark-Avenger-Reborn/ScoringEngine.git
cd ScoringEngine
```

2. Install dependencies:
```bash
pip3 install -r requirements.txt
```

3. Create `master_config.json` (the main configuration file):
```json
{
  "teams": [
    {
      "name": "Team1",
      "id": "team1",
      "password": "changeme",
      "subnet": "10.0.1.0/24"
    },
    {
      "name": "Team2",
      "id": "team2",
      "password": "changeme",
      "subnet": "10.0.2.0/24"
    }
  ],
  "systems": [
    {
      "name": "ubuntu1",
      "display_name": "Ubuntu Server 1",
      "ip_offset": 20,
      "services": ["ping", "ssh", "web"]
    },
    {
      "name": "ubuntu2",
      "display_name": "Ubuntu Server 2",
      "ip_offset": 30,
      "services": ["ping", "ssh", "web"]
    }
  ],
  "services": {
    "ping": {
      "name": "Ping",
      "display_name": "Network Connectivity",
      "points": 10,
      "timeout": 20
    },
    "ssh": {
      "name": "SSH",
      "display_name": "SSH Service",
      "points": 10,
      "timeout": 20,
      "default_username": "sysadmin",
      "default_password": "changeme",
      "default_port": 22
    },
    "web": {
      "name": "Web",
      "display_name": "Web Service",
      "points": 10,
      "timeout": 20,
      "default_port": 80
    }
  },
  "grading": {
    "interval_seconds": 40,
    "concurrent_threads": true
  }
}
```

4. Start the server:
```bash
python3 main.py
```

The server will automatically generate `config.json` and `team_configs.json` from your `master_config.json` on startup.

## Understanding the Configuration Files

- **`master_config.json`** - **YOU EDIT THIS**: Single source of truth for teams, systems, and services
- **`config.json`** - Auto-generated at startup from `master_config.json` for login credentials
- **`team_configs.json`** - Auto-generated at startup, but **teams can customize their own section** via `/config`
- **`scores.json`** - Auto-generated, tracks live scores (reset on startup)

## Adding Teams and Systems

### Adding a New Team

Simply add a new entry to the `teams` array in `master_config.json`:

```json
{
  "name": "Team3",
  "id": "team3",
  "password": "newpassword",
  "subnet": "10.0.3.0/24"
}
```

Then restart the application. The system will automatically:
- Create login credentials
- Generate initial scores
- Set up team configurations for all systems
- Start monitoring all services

### Adding a New System

Add a new entry to the `systems` array in `master_config.json`:

```json
{
  "name": "ubuntu3",
  "display_name": "Ubuntu Server 3",
  "ip_offset": 40,
  "services": ["ping", "ssh", "web"]
}
```

The IP address will be automatically calculated as `10.0.{team_number}.{ip_offset}`.
For example, Team1's ubuntu3 will be at `10.0.1.40`.

### Changing Service Points or Timeouts

Edit the corresponding service in the `services` section:

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

### Changing Grading Interval

Modify the `grading` section:

```json
"grading": {
  "interval_seconds": 60,  // Changed from 40
  "concurrent_threads": true
}
```

## Usage

### Starting the Server

```bash
python3 main.py
```

The server will start on `http://0.0.0.0:5000`

### Accessing the Interface

1. **Login**: Navigate to `/login` and authenticate with team credentials
2. **Dashboard**: View your team's scores at `/`
3. **Leaderboard**: See all teams' scores at `/leaderboard`
4. **Configuration**: Manage service settings at `/config` (requires login)

### Grading Cycle

- Tests run automatically every 40 seconds
- Each service test has a 20-second timeout
- Points awarded per service:
  - **Success**: 10 points
  - **SSH Partial**: 1 point (connection established but command failed)
  - **Ping/Web Failure**: 0 points

## API Endpoints

### Public Routes
- `GET /` - Team dashboard
- `GET /login` - Authentication page
- `GET /logout` - End session
- `GET /leaderboard` - Public scoreboard
- `GET /scores.json` - Raw scores data

### Authenticated Routes
- `GET /config` - Configuration interface
- `GET /api/team-configs` - Fetch team's service configuration
- `POST /api/team-configs` - Update team's service configuration
- `GET /api/team-scores` - Get logged-in team's scores
- `GET /api/grading-status` - Check if grading is in progress

## WebSocket Events

### Client → Server
- `connect` - Establish WebSocket connection

### Server → Client
- `scores` - Complete score update (all teams)
- `gradingCycle` - Grading cycle counter update

## Configuration Files

### `master_config.json` (Primary Configuration - Edit This!)
**This is the main configuration file that you (the admin) edit.** All teams, systems, and services are defined here.

Structure:
- `teams`: Array of team definitions (name, id, password, subnet)
- `systems`: Array of systems to monitor (name, display_name, ip_offset, services)
- `services`: Object defining service types (ping, ssh, web) with their settings
- `grading`: Grading interval and threading options

**When you add a team or system here and restart the server, everything else is automatically configured.**

### `config.json` (Auto-generated - Don't Edit)
Auto-generated from `master_config.json` at startup. Contains team login credentials for Flask authentication.

### `team_configs.json` (Auto-generated, but Teams Can Edit Their Section)
Initially generated from `master_config.json` at startup with default values. Teams can then customize **their own section only** via the web interface at `/config` to change:
- SSH usernames, passwords, and ports
- Web server ports

This allows teams to configure their services without affecting other teams.

### `scores.json` (Auto-generated - Don't Edit)
Live scoring data. Automatically generated and reset on each server start.

## Development

### Project Structure

```
.
├── main.py                 # Flask application & routes
├── grader.py              # Grading logic & scoring
├── test_services.py       # Service testing utilities
├── config_loader.py       # Centralized config management
├── requirements.txt       # Python dependencies
├── master_config.json     # Master configuration (EDIT THIS!)
├── config.json           # Team credentials (auto-generated)
├── team_configs.json     # Service configurations (auto-generated, teams can edit)
├── scores.json           # Live scores (auto-generated)
├── templates/            # HTML templates
│   ├── index.html       # Team dashboard
│   ├── leaderboard.html # Public scoreboard
│   ├── config.html      # Configuration page
│   └── login.html       # Authentication
└── static/              # Frontend assets
    ├── styles.css
    ├── index_table.js
    ├── leaderboard.js
    └── error_banner.js
```

### Thread Safety

The application uses:
- Global file lock (`_scores_file_lock`) for `scores.json` access
- Atomic file writes (write to `.tmp` then `os.replace()`)
- Session-based authentication
- Grading status flags to prevent concurrent updates

## Security Considerations

⚠️ **Important**: This application is designed for controlled competition environments.

- Credentials are stored in plaintext (`config.json`)
- Sessions use random secret keys (regenerated on restart)
- No rate limiting on API endpoints
- SSH passwords transmitted in configuration updates
- No HTTPS enforcement (use reverse proxy in production)

**Recommendations**:
- Run in isolated network segments
- Use firewall rules to restrict access
- Implement HTTPS with nginx/Apache reverse proxy
- Rotate credentials after events
- Monitor logs for suspicious activity

## Troubleshooting

### Common Issues

**Empty scores.json error**
- Fixed with thread-safe file locking in v1.1
- Scores reset on server restart by design

**Connection timeout**
- Verify network connectivity to target IPs
- Check firewall rules allow testing from scoring engine
- Ensure target services are actually running

**WebSocket not updating**
- Check browser console for connection errors
- Verify Socket.IO client compatibility
- Confirm no proxy/firewall blocking WebSocket protocol

**Configuration locked**
- Cannot update configs during active grading cycle
- Wait 40 seconds for current cycle to complete

## License

This project is provided as-is for educational and competition use.

## Contributing

Contributions welcome! Please submit pull requests or open issues for bugs/features.

## Authors

- Dark-Avenger-Reborn

## Acknowledgments

Built for cybersecurity education and CTF-style competitions focusing on service administration and network infrastructure.
