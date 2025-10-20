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


app = Flask(__name__)
app.secret_key = os.urandom(24)
sio = socketio.Server(cors_allowed_origins="*", logger=False, max_http_buffer_size=1e8)

def get_json():
    try:
        with open("config.json", "r") as file:
            credentials = json.load(file)
        return credentials
    except FileNotFoundError:
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
        data = {
            "team1": {
                "ubuntu1": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                "ubuntu2": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
            },
            "team2": {
                "ubuntu1": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                "ubuntu2": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
            },
        }
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
        
        # Validate ubuntu1 and ubuntu2 structures
        for ubuntu_key in ["ubuntu1", "ubuntu2"]:
            if ubuntu_key not in team_data:
                return jsonify({"error": f"Missing {ubuntu_key} in payload"}), 400
            ubuntu_cfg = team_data[ubuntu_key]
            ssh = ubuntu_cfg.get('ssh', {})
            web = ubuntu_cfg.get('web', {})
            
            # Coerce ports to int within sane ranges
            if 'port' in ssh:
                try:
                    p = int(ssh['port'])
                    if p < 1 or p > 65535:
                        return jsonify({"error": f"SSH port out of range for {ubuntu_key}"}), 400
                    ssh['port'] = p
                except Exception:
                    return jsonify({"error": f"SSH port invalid for {ubuntu_key}"}), 400
            if 'port' in web:
                try:
                    p = int(web['port'])
                    if p < 1 or p > 65535:
                        return jsonify({"error": f"Web port out of range for {ubuntu_key}"}), 400
                    web['port'] = p
                except Exception:
                    return jsonify({"error": f"Web port invalid for {ubuntu_key}"}), 400
            
            # Normalize
            ubuntu_cfg['ssh'] = {
                'username': ssh.get('username', 'sysadmin'),
                'password': ssh.get('password', 'changeme'),
                'port': ssh.get('port', 22),
            }
            ubuntu_cfg['web'] = {
                'port': web.get('port', 80)
            }
        
        # Read full config, update only this team's section, and write back
        try:
            with open('team_configs.json', 'r') as f:
                full_config = json.load(f)
        except Exception:
            full_config = {
                "team1": {
                    "ubuntu1": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                    "ubuntu2": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                },
                "team2": {
                    "ubuntu1": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                    "ubuntu2": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                },
            }
        
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
    return jsonify({"isGrading": status})

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

def grade_projects(grader):
    while True:
        grader.grade_projects()
        time.sleep(40)

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

if __name__ == "__main__":
    # Reset scores.json to a known initial state on every server start so
    # previous runs don't carry over scores.
    initial_scores = {
        "team1": {
            "ubuntu1ping": {"error": "Not tested", "score": 0},
            "ubuntu2ping": {"error": "Not tested", "score": 0},
            "ubuntu1ssh": {"error": "Not tested", "score": 0},
            "ubuntu2ssh": {"error": "Not tested", "score": 0},
            "ubuntu1web": {"error": "Not tested", "score": 0},
            "ubuntu2web": {"error": "Not tested", "score": 0},
        },
        "team2": {
            "ubuntu1ping": {"error": "Not tested", "score": 0},
            "ubuntu2ping": {"error": "Not tested", "score": 0},
            "ubuntu1ssh": {"error": "Not tested", "score": 0},
            "ubuntu2ssh": {"error": "Not tested", "score": 0},
            "ubuntu1web": {"error": "Not tested", "score": 0},
            "ubuntu2web": {"error": "Not tested", "score": 0},
        },
    }

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
    threading.Thread(target=grade_projects, args=(grader,)).start()
    flaskApp = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), flaskApp)