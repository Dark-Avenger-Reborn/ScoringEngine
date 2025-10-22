import eventlet
# Patch standard libs (threading, socket, time, etc.) before other imports
# so green threads are used everywhere.
eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for, jsonify
import socketio
import os
import json
import time
import threading
from grader import Grader
from config_loader import get_config_loader


app = Flask(__name__)
app.secret_key = os.urandom(24)
sio = socketio.Server(cors_allowed_origins="*", logger=False, max_http_buffer_size=1e8)

# Default grading cycle count on the app (may be updated by Grader)
app.grading_cycle_count = 0


@app.context_processor
def inject_grading_cycle():
    """Make grading_cycle_count available to all templates.
    Prefer the live grader's attribute when present.
    """
    try:
        grader = getattr(app, 'grader', None)
        if grader is not None and hasattr(grader, 'grading_cycle_count'):
            return {'grading_cycle_count': int(getattr(grader, 'grading_cycle_count', 0))}
        return {'grading_cycle_count': int(getattr(app, 'grading_cycle_count', 0))}
    except Exception as err:
        print('inject_grading_cycle error:', err)
        return {'grading_cycle_count': 0}

def get_json():
    try:
        config_loader = get_config_loader()
        credentials = config_loader.generate_login_credentials()
        return credentials
    except Exception:
        return None

def is_logged_in():
    return ("logged_in" in session and session["logged_in"])

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        credentials = get_json()

        if credentials and (not is_logged_in()) and (username in credentials):
            if password == credentials[username]:
                session["logged_in"] = True
                # Store team name in session (username maps to team)
                # Team1 -> team1, Team2 -> team2
                session["team"] = username.lower()
                if "previous_page" in session:
                    return redirect(url_for(session["previous_page"]))
                return redirect(url_for('index'))
            else:
                return render_template("login.html", error_message="Username or Password is incorrect")
        else:
            return render_template("login.html", error_message="Username or Password is incorrect")


    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for('login'))


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")

# Serve scores.json for clients that fetch it directly
@app.route('/scores.json', methods=['GET'])
def serve_scores_json():
    try:
        with open('scores.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception:
        return jsonify({}), 200

@app.route("/config")
def config():
    if is_logged_in():
        return render_template("config.html")

    session["previous_page"] = "config"
    return render_template("login.html")

# --- Team configuration API ---
@app.route('/api/team-configs', methods=['GET'])
def get_team_configs():
    if not is_logged_in():
        session["previous_page"] = "config"
        return jsonify({"error": "Unauthorized"}), 401
    try:
        with open('team_configs.json', 'r') as f:
            data = json.load(f)
    except Exception:
        # Generate default config from master_config.json
        config_loader = get_config_loader()
        data = config_loader.generate_team_configs()
    # Only return the logged-in team's config
    user_team = session.get("team", "team1")
    return jsonify({user_team: data.get(user_team, {})})

@app.route('/api/team-configs', methods=['POST'])
def update_team_configs():
    if not is_logged_in():
        session["previous_page"] = "config"
        return jsonify({"error": "Unauthorized"}), 401
    # Prevent updates while grading is running
    try:
        # Access grader instance via a global reference
        if getattr(app, 'grader', None) and getattr(app.grader, 'is_grading', False):
            return jsonify({"error": "Grading is in progress. Try again soon."}), 409
    except Exception:
        pass
    
    user_team = session.get("team", "team1")
    
    try:
        payload = request.get_json(force=True, silent=False)
        if not isinstance(payload, dict):
            return jsonify({"error": "Invalid payload"}), 400
        
        # Only allow updating the logged-in team's config
        if user_team not in payload:
            return jsonify({"error": f"You can only update {user_team} configuration"}), 403
        if len(payload) > 1 or list(payload.keys())[0] != user_team:
            return jsonify({"error": f"You can only update {user_team} configuration"}), 403
        
        team_data = payload[user_team]
        
        # Load config loader to get list of systems dynamically
        config_loader = get_config_loader()
        systems = config_loader.get_systems()
        
        # Validate all systems in the configuration
        for system in systems:
            system_name = system['name']
            if system_name not in team_data:
                return jsonify({"error": f"Missing {system_name} in payload"}), 400
            system_cfg = team_data[system_name]
            
            # Validate SSH config if this system has SSH service
            if 'ssh' in system.get('services', []):
                ssh = system_cfg.get('ssh', {})
                if 'port' in ssh:
                    try:
                        p = int(ssh['port'])
                        if p < 1 or p > 65535:
                            return jsonify({"error": f"SSH port out of range for {system_name}"}), 400
                        ssh['port'] = p
                    except Exception:
                        return jsonify({"error": f"SSH port invalid for {system_name}"}), 400
                
                # Normalize SSH config
                ssh_service_config = config_loader.get_service_config('ssh')
                system_cfg['ssh'] = {
                    'username': ssh.get('username', ssh_service_config.get('default_username', 'sysadmin')),
                    'password': ssh.get('password', ssh_service_config.get('default_password', 'changeme')),
                    'port': ssh.get('port', ssh_service_config.get('default_port', 22)),
                }
            
            # Validate Web config if this system has Web service
            if 'web' in system.get('services', []):
                web = system_cfg.get('web', {})
                if 'port' in web:
                    try:
                        p = int(web['port'])
                        if p < 1 or p > 65535:
                            return jsonify({"error": f"Web port out of range for {system_name}"}), 400
                        web['port'] = p
                    except Exception:
                        return jsonify({"error": f"Web port invalid for {system_name}"}), 400
                
                # Normalize Web config
                web_service_config = config_loader.get_service_config('web')
                system_cfg['web'] = {
                    'port': web.get('port', web_service_config.get('default_port', 80))
                }
            
            # Validate Active Directory config if this system has Active Directory service
            if 'active_directory' in system.get('services', []):
                ad = system_cfg.get('active_directory', {})
                
                # Normalize Active Directory config
                ad_service_config = config_loader.get_service_config('active_directory')
                system_cfg['active_directory'] = {
                    'username': ad.get('username', ad_service_config.get('default_username', 'administrator')),
                    'password': ad.get('password', ad_service_config.get('default_password', 'changeme')),
                    'domain': ad.get('domain', ad_service_config.get('default_domain', 'example.com')),
                }
        
        # Read full config, update only this team's section, and write back
        try:
            with open('team_configs.json', 'r') as f:
                full_config = json.load(f)
        except Exception:
            # Generate defaults from master config
            full_config = config_loader.generate_team_configs()
        
        full_config[user_team] = team_data
        
        # Write atomically
        tmp_path = 'team_configs.json.tmp'
        with open(tmp_path, 'w') as f:
            json.dump(full_config, f, indent=2)
        os.replace(tmp_path, 'team_configs.json')
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"error": f"Failed to update configs: {e}"}), 500

@app.route('/api/grading-status', methods=['GET'])
def grading_status():
    try:
        status = bool(getattr(app, 'grader', None) and getattr(app.grader, 'is_grading', False))
    except Exception:
        status = False
    try:
        grader = getattr(app, 'grader', None)
        if grader is not None and hasattr(grader, 'grading_cycle_count'):
            cycle = int(getattr(grader, 'grading_cycle_count', 0))
        else:
            cycle = int(getattr(app, 'grading_cycle_count', 0))
    except Exception:
        cycle = 0
    return jsonify({"isGrading": status, "cycle": cycle})

@app.route('/api/systems', methods=['GET'])
def get_systems():
    """Get list of systems from master config for dynamic UI rendering."""
    try:
        config_loader = get_config_loader()
        systems = config_loader.get_systems()
        services = config_loader.get_services()
        return jsonify({"systems": systems, "services": services})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Logged-in team's scores (subset of scores.json)
@app.route('/api/team-scores', methods=['GET'])
def team_scores():
    if not is_logged_in():
        session["previous_page"] = "config"
        return jsonify({"error": "Unauthorized"}), 401
    team_key = session.get('team')
    if not team_key:
        return jsonify({}), 200
    try:
        with open('scores.json', 'r') as f:
            data = json.load(f)
        team_scores = data.get(team_key, {})
        return jsonify({team_key: team_scores})
    except Exception:
        return jsonify({team_key: {}})

@sio.on("connect")
def connect(sid, environ):
    # Emit current scores to the connecting client
    try:
        with open("scores.json", "r") as score_file:
            scores = json.load(score_file)
    except Exception:
        scores = {}

    print("Client connected:", sid)
    sio.emit("scores", scores, to=sid)
    try:
        # Also send the current cycle to new client for instant navbar update
        cycle = 0
        grader = getattr(app, 'grader', None)
        if grader is not None and hasattr(grader, 'grading_cycle_count'):
            cycle = int(getattr(grader, 'grading_cycle_count', 0))
        else:
            cycle = int(getattr(app, 'grading_cycle_count', 0))
        sio.emit("gradingCycle", {"cycle": cycle}, to=sid)
    except Exception:
        pass

if __name__ == "__main__":
    # Load centralized configuration
    config_loader = get_config_loader()
    
    # Reset scores.json to a known initial state on every server start so
    # previous runs don't carry over scores.
    initial_scores = config_loader.generate_initial_scores()

    # Write atomically: write to a temp file then replace
    try:
        tmp_path = "scores.json.tmp"
        with open(tmp_path, "w") as f:
            json.dump(initial_scores, f)
        os.replace(tmp_path, "scores.json")
        print("scores.json reset to initial state on startup")
    except Exception as e:
        print("Failed to reset scores.json on startup:", repr(e))

    grader = Grader(sio)
    # Expose grader on app for API access to is_grading
    app.grader = grader
    
    # Get grading interval from master config
    grading_config = config_loader.get_grading_config()
    grading_interval = grading_config.get('interval_seconds', 40)
    
    def grade_with_interval(grader, interval):
        while True:
            grader.grade_projects()
            time.sleep(interval)
    
    threading.Thread(target=grade_with_interval, args=(grader, grading_interval)).start()
    flaskApp = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), flaskApp)