# Scoring Engine

A real-time network infrastructure scoring engine for cybersecurity competitions. This application automatically tests and grades team services (ping, SSH, web) across multiple Ubuntu instances.

## Overview

This scoring engine is designed for team-based competitions where participants configure and maintain network services. The system continuously monitors service availability and awards points based on uptime and functionality.

### Features

- **Real-time Scoring**: Automated testing every 40 seconds
- **Multi-Service Testing**: Tests ping connectivity, SSH access, and web servers
- **Live Leaderboard**: WebSocket-based real-time score updates
- **Team Configuration**: Each team can customize their service credentials and ports
- **Thread-Safe**: Concurrent testing with proper file locking mechanisms
- **Web Interface**: Clean, responsive UI with live updates

## Architecture

### Components

- **Flask Application** (`main.py`): Main web server handling routes and authentication
- **Grader Module** (`grader.py`): Core grading logic with threaded testing
- **Service Tester** (`test_services.py`): Service validation methods (ping, SSH, HTTP)
- **Socket.IO**: Real-time score broadcasting to connected clients
- **Eventlet**: Green threading for efficient concurrent connections

### Tested Services

Each team has two Ubuntu instances (10.0.{team}.20 and 10.0.{team}.30) with:
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

3. Configure team credentials in `config.json`:
```json
{
    "Team1": "password1",
    "Team2": "password2"
}
```

4. (Optional) Customize team service configurations in `team_configs.json`:
```json
{
    "team1": {
        "ubuntu1": {
            "ssh": {"username": "sysadmin", "password": "changeme", "port": 22},
            "web": {"port": 80}
        },
        "ubuntu2": {
            "ssh": {"username": "sysadmin", "password": "changeme", "port": 22},
            "web": {"port": 80}
        }
    },
    "team2": { /* similar structure */ }
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

### `config.json`
Team login credentials (username → password mapping)

### `team_configs.json`
Service-specific settings for each team:
- SSH username, password, and port
- Web server port

### `scores.json`
Live scoring data (auto-generated, reset on server start)

## Development

### Project Structure

```
.
├── main.py                 # Flask application & routes
├── grader.py              # Grading logic & scoring
├── test_services.py       # Service testing utilities
├── requirements.txt       # Python dependencies
├── config.json           # Team credentials
├── team_configs.json     # Service configurations
├── scores.json           # Live scores (generated)
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
