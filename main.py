from flask import Flask, render_template, request, redirect, send_from_directory, session, url_for, jsonify
import eventlet
import socketio
import os
import json
from grader import Grader
import time
import threading
import eventlet
eventlet.monkey_patch()


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

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/leaderboard")
def leaderboard():
    return render_template("leaderboard.html")

@app.route("/config")
def config():
    if is_logged_in():
        return render_template("config.html")

    session["previous_page"] = "config"
    return render_template("login.html")

def grade_projects(grader):
    while True:
        grader.grade_projects()
        time.sleep(40)

@sio.on("connect")
def connect(sid, environ):
    with open("scores.json", "r") as score_file:
            scores = json.load(score_file)

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
    threading.Thread(target=grade_projects, args=(grader,)).start()
    flaskApp = socketio.Middleware(sio, app)
    eventlet.wsgi.server(eventlet.listen(("0.0.0.0", 5000)), flaskApp)