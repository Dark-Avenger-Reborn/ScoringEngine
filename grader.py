import time
from test_services import Services
import json
import math
import threading
import os
from config_loader import get_config_loader

# Use a module-level lock to serialize read/write access to scores.json
# This prevents the common race where one thread truncates the file to write
# while another thread attempts to read it and gets an empty file (causing
# json.JSONDecodeError: Expecting value).
_scores_file_lock = threading.Lock()

grading_cycle_count = 0

class Grader:
    def __init__(self, sio):
        # Ensure the scores file exists and contains a valid JSON object. Use the
        # lock during initialization to avoid races with concurrently-starting
        # grader threads.
        self.sio = sio
        self.is_grading = False
        # Initialize instance-level cycle counter mirror
        self.grading_cycle_count = 0
        
        # Load centralized configuration
        self.config_loader = get_config_loader()
        
        # Generate initial scores from master config
        initial = self.config_loader.generate_initial_scores()

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
                scores = self.config_loader.generate_initial_scores()

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
            # Fallback to generated defaults from master config
            team_cfg = self.config_loader.generate_team_configs()

        # Get all test scenarios from centralized config
        scenarios = self.config_loader.get_all_test_scenarios()
        
        for scenario in scenarios:
            team_id = scenario['team_id']
            system_name = scenario['system_name']
            service_name = scenario['service_name']
            ip_address = scenario['ip_address']
            
            # Get team-specific config overrides
            system_cfg = team_cfg.get(team_id, {}).get(system_name, {})
            
            # Create appropriate grading thread based on service type
            if service_name == "ssh":
                ssh_user = system_cfg.get("ssh", {}).get("username", scenario['ssh']['default_username'])
                ssh_pass = system_cfg.get("ssh", {}).get("password", scenario['ssh']['default_password'])
                ssh_port = system_cfg.get("ssh", {}).get("port", scenario['ssh']['default_port'])
                
                t = threading.Thread(
                    target=self.grade_ssh,
                    args=(team_id, ssh_user, ssh_pass, ssh_port, ip_address, scenario['score_key'], scenario['points'], services)
                )
            elif service_name == "ping":
                t = threading.Thread(
                    target=self.grade_ping,
                    args=(team_id, ip_address, scenario['score_key'], scenario['points'], services)
                )
            elif service_name == "web":
                web_port = system_cfg.get("web", {}).get("port", scenario['web']['default_port'])
                
                t = threading.Thread(
                    target=self.grade_web,
                    args=(team_id, web_port, ip_address, scenario['score_key'], scenario['points'], services)
                )
            elif service_name == "active_directory":
                ad_user = system_cfg.get("active_directory", {}).get("username", "administrator")
                ad_pass = system_cfg.get("active_directory", {}).get("password", "changeme")
                ad_domain = system_cfg.get("active_directory", {}).get("domain", ip_address)
                
                t = threading.Thread(
                    target=self.grade_active_directory,
                    args=(team_id, ad_domain, ad_user, ad_pass, scenario['score_key'], scenario['points'], services, 20)
                )
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

    def grade_ssh(self, team_id, username, password, port, ip, score_key, points, services):
        result = services.ssh_connection(username, password, ip, port=port)
        if result[0]:
            self.append_scores(team_id, score_key, "Success", points)
        else:
            self.append_scores(team_id, score_key, result[1], 0)

    def grade_ping(self, team_id, ip, score_key, points, services):
        result = services.ping_host(ip)
        if result[0]:
            self.append_scores(team_id, score_key, "Success", points)
        else:
            self.append_scores(team_id, score_key, result[1], 0)

    def grade_web(self, team_id, port, ip, score_key, points, services):
        url = f"http://{ip}:{port}"
        result = services.web_request(url)
        if result[0]:
            self.append_scores(team_id, score_key, "Success", points)
        else:
            self.append_scores(team_id, score_key, result[1], 0)

    def grade_active_directory(self, team_id, domain, username, password, score_key, points, services, timeout):
        result = services.active_directory(domain, username, password, timeout)
        if result[0]:
            self.append_scores(team_id, score_key, "Success", points)
        else:
            self.append_scores(team_id, score_key, result[1], 0)
