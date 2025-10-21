import time
from test_services import Services
import json
import math
import threading
import os

# Use a module-level lock to serialize read/write access to scores.json
# This prevents the common race where one thread truncates the file to write
# while another thread attempts to read it and gets an empty file (causing
# json.JSONDecodeError: Expecting value).
_scores_file_lock = threading.Lock()

grading_cycle_count = 0

def first_n_digits(num, n):
    return num // 10 ** (int(math.log(num, 10)) - n + 1)

class Grader:
    def __init__(self, sio):
        # Ensure the scores file exists and contains a valid JSON object. Use the
        # lock during initialization to avoid races with concurrently-starting
        # grader threads.
        self.sio = sio
        self.is_grading = False
        # Initialize instance-level cycle counter mirror
        self.grading_cycle_count = 0

        initial = {
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

        with _scores_file_lock:
            # If file doesn't exist or is empty/invalid, write the initial
            # structure. This avoids json.load() blowing up when reading an
            # empty file.
            try:
                if not os.path.exists("scores.json"):
                    with open("scores.json", "w") as score_file:
                        json.dump(initial, score_file)
                else:
                    # Try to read existing file; if invalid, overwrite with
                    # initial content.
                    with open("scores.json", "r+") as score_file:
                        try:
                            data = json.load(score_file)
                            # If it's not a dict, reset it
                            if not isinstance(data, dict):
                                score_file.seek(0)
                                score_file.truncate()
                                json.dump(initial, score_file)
                        except json.JSONDecodeError:
                            score_file.seek(0)
                            score_file.truncate()
                            json.dump(initial, score_file)
            except Exception:
                # If any unexpected error occurs during initialization,
                # ensure the file has valid JSON so later operations don't
                # fail.
                with open("scores.json", "w") as score_file:
                    json.dump(initial, score_file)

    # Track how many grading cycles have completed
    


    def append_scores(self, team, subject, error, points):
        # Acquire the lock for the shortest practical time to avoid blocking
        # other grading threads while ensuring read/modify/write is atomic.
        with _scores_file_lock:
            # Read scores safely; if file is empty or corrupt, replace with
            # a known-good structure.
            try:
                with open("scores.json", "r") as score_file:
                    scores = json.load(score_file)
            except (FileNotFoundError, json.JSONDecodeError):
                # Recreate the initial structure if missing or invalid.
                scores = {
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

            # Defensive checks in case keys are missing
            if team not in scores:
                scores[team] = {}
            if subject not in scores[team]:
                scores[team][subject] = {"error": "Not tested", "score": 0}

            scores[team][subject]["score"] = scores[team][subject].get("score", 0) + points
            scores[team][subject]["error"] = error

            # Write back atomically by writing to a temp file and renaming.
            tmp_path = "scores.json.tmp"
            with open(tmp_path, "w") as score_file:
                json.dump(scores, score_file)
            os.replace(tmp_path, "scores.json")

    def grade_projects(self):
        print("Grading projects...")
        self.is_grading = True
        # Increment the grading cycle counter at the start of a cycle
        global grading_cycle_count
        grading_cycle_count += 1
        # Mirror to the instance for reliable access from app.grader
        self.grading_cycle_count = grading_cycle_count
        # Push live update of cycle to clients
        try:
            self.sio.emit("gradingCycle", {"cycle": int(self.grading_cycle_count)}, namespace="/")
        except Exception:
            pass
        # If the Flask app is available on the global import, expose the
        # counter there so templates can read it via the app object.
        try:
            import main
            if getattr(main, 'app', None):
                main.app.grading_cycle_count = grading_cycle_count
        except Exception as err:
            print(err)
        services = Services()
        thread_list = []
        # Load team configuration for this grading cycle
        try:
            with open("team_configs.json", "r") as f:
                team_cfg = json.load(f)
        except Exception:
            # Fallback to reasonable defaults with new structure
            team_cfg = {
                "team1": {
                    "ubuntu1": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                    "ubuntu2": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                },
                "team2": {
                    "ubuntu1": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                    "ubuntu2": {"ssh": {"username": "sysadmin", "password": "changeme", "port": 22}, "web": {"port": 80}},
                },
            }

        for team in [1, 2]:
            team_key = f"team{team}"
            for service in ["ping", "ssh", "web"]:
                for instance in [20, 30]:
                    # Map instance IP last octet to ubuntu1 (20) or ubuntu2 (30)
                    ubuntu_key = "ubuntu1" if instance == 20 else "ubuntu2"
                    ubuntu_cfg = team_cfg.get(team_key, {}).get(ubuntu_key, {})
                    
                    ssh_user = ubuntu_cfg.get("ssh", {}).get("username", "sysadmin")
                    ssh_pass = ubuntu_cfg.get("ssh", {}).get("password", "changeme")
                    ssh_port = ubuntu_cfg.get("ssh", {}).get("port", 22)
                    web_port = ubuntu_cfg.get("web", {}).get("port", 80)
                    
                    ip = f"10.0.{team}.{instance}"
                    if service == "ssh":
                        t = threading.Thread(target=self.grade_ssh, args=(team, ssh_user, ssh_pass, ssh_port, ip, instance, services))
                    elif service == "ping":
                        t = threading.Thread(target=self.grade_ping, args=(team, ip, instance, services))
                    elif service == "web":
                        t = threading.Thread(target=self.grade_web, args=(team, web_port, ip, instance, services))
                    else:
                        t = None

                    if t is not None:
                        t.start()
                        thread_list.append(t)

        for thread in thread_list:
            thread.join()

        print("Grading complete. Updating scores.json and notifying clients.")

        with open("scores.json", "r") as score_file:
            scores = json.load(score_file)

        self.sio.emit("scores", scores, namespace="/")
        # Also re-emit cycle at the end in case clients connected mid-cycle
        try:
            self.sio.emit("gradingCycle", {"cycle": int(self.grading_cycle_count)}, namespace="/")
        except Exception:
            pass
        self.is_grading = False


    def grade_ssh(self, team, username, password, port, ip, instance, services):
        result = services.ssh_connection(username, password, ip, port=port)
        if result[0]:
            self.append_scores(f"team{team}", f"ubuntu{first_n_digits(instance, 1)-1}ssh", "Success", 10)
        else:
            self.append_scores(f"team{team}", f"ubuntu{first_n_digits(instance, 1)-1}ssh", result[1], 1)

    def grade_ping(self, team, ip, instance, services):
        result = services.ping_host(ip)
        if result[0]:
            self.append_scores(f"team{team}", f"ubuntu{first_n_digits(instance, 1)-1}ping", "Success", 10)
        else:
            self.append_scores(f"team{team}", f"ubuntu{first_n_digits(instance, 1)-1}ping", result[1], 0)

    def grade_web(self, team, port, ip, instance, services):
        url = f"http://{ip}:{port}"
        result = services.web_request(url)
        if result[0]:
            self.append_scores(f"team{team}", f"ubuntu{first_n_digits(instance, 1)-1}web", "Success", 10)
        else:
            self.append_scores(f"team{team}", f"ubuntu{first_n_digits(instance, 1)-1}web", result[1], 0)