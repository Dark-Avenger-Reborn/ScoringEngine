"""
Centralized configuration loader for the scoring engine.
This module provides utilities to load and work with the master configuration.
"""

import json
import os
from typing import Dict, List, Any


class ConfigLoader:
    """Handles loading and providing access to centralized configuration."""
    
    def __init__(self, config_path="master_config.json"):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load the master configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Master configuration file not found at {self.config_path}. "
                "Please create it based on master_config.json.example"
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.config_path}: {e}")
    
    def reload(self):
        """Reload the configuration from disk."""
        self.config = self._load_config()
    
    def get_teams(self) -> List[Dict[str, Any]]:
        """Get list of all teams."""
        return self.config.get('teams', [])
    
    def get_team_by_id(self, team_id: str) -> Dict[str, Any]:
        """Get a specific team by its ID."""
        for team in self.get_teams():
            if team['id'] == team_id:
                return team
        return None
    
    def get_systems(self) -> List[Dict[str, Any]]:
        """Get list of all systems to be monitored."""
        return self.config.get('systems', [])
    
    def get_services(self) -> Dict[str, Dict[str, Any]]:
        """Get service definitions."""
        return self.config.get('services', {})
    
    def get_service_config(self, service_name: str) -> Dict[str, Any]:
        """Get configuration for a specific service."""
        return self.get_services().get(service_name, {})
    
    def get_grading_config(self) -> Dict[str, Any]:
        """Get grading configuration."""
        return self.config.get('grading', {
            'interval_seconds': 40,
            'concurrent_threads': True
        })
    
    def get_team_ip(self, team_id: str, system_name: str) -> str:
        """Generate IP address for a team's system."""
        team = self.get_team_by_id(team_id)
        if not team:
            return None
        
        # Extract team number from team_id (e.g., "team1" -> 1)
        team_num = int(team_id.replace('team', ''))
        
        # Find the system
        for system in self.get_systems():
            if system['name'] == system_name:
                ip_offset = system['ip_offset']
                return f"10.0.{team_num}.{ip_offset}"
        
        return None
    
    def generate_login_credentials(self) -> Dict[str, str]:
        """Generate login credentials dict for config.json format."""
        credentials = {}
        for team in self.get_teams():
            credentials[team['name']] = team['password']
        return credentials
    
    def generate_initial_scores(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Generate initial scores structure for all teams and services."""
        scores = {}
        
        for team in self.get_teams():
            team_id = team['id']
            scores[team_id] = {}
            
            # For each system
            for system in self.get_systems():
                system_name = system['name']
                
                # For each service on that system
                for service_name in system.get('services', []):
                    service_config = self.get_service_config(service_name)
                    score_key = f"{system_name}{service_name}"
                    
                    scores[team_id][score_key] = {
                        "error": "Not tested",
                        "score": 0
                    }
        
        return scores
    
    def generate_team_configs(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """Generate team_configs.json structure from master config."""
        team_configs = {}
        
        for team in self.get_teams():
            team_id = team['id']
            team_configs[team_id] = {}
            
            # For each system
            for system in self.get_systems():
                system_name = system['name']
                team_configs[team_id][system_name] = {}
                
                # Check which services this system has and add default configs
                for service_name in system.get('services', []):
                    service_config = self.get_service_config(service_name)
                    
                    if service_name == 'ssh':
                        team_configs[team_id][system_name]['ssh'] = {
                            'username': service_config.get('default_username', 'sysadmin'),
                            'password': service_config.get('default_password', 'changeme'),
                            'port': service_config.get('default_port', 22)
                        }
                    elif service_name == 'web':
                        team_configs[team_id][system_name]['web'] = {
                            'port': service_config.get('default_port', 80)
                        }
                    elif service_name == 'active_directory':
                        team_configs[team_id][system_name]['active_directory'] = {
                            'username': service_config.get('default_username', 'administrator'),
                            'password': service_config.get('default_password', 'changeme'),
                            'domain': service_config.get('default_domain', 'example.com')
                        }
        
        return team_configs
    
    def get_all_test_scenarios(self) -> List[Dict[str, Any]]:
        """
        Generate all test scenarios based on teams, systems, and services.
        Returns a list of test scenario dictionaries.
        """
        scenarios = []
        
        for team in self.get_teams():
            team_id = team['id']
            team_num = int(team_id.replace('team', ''))
            
            for system in self.get_systems():
                system_name = system['name']
                ip_offset = system['ip_offset']
                ip_address = f"10.0.{team_num}.{ip_offset}"
                
                for service_name in system.get('services', []):
                    service_config = self.get_service_config(service_name)
                    
                    scenario = {
                        'team_id': team_id,
                        'team_num': team_num,
                        'system_name': system_name,
                        'system_display_name': system.get('display_name', system_name),
                        'service_name': service_name,
                        'service_display_name': service_config.get('display_name', service_name),
                        'ip_address': ip_address,
                        'ip_offset': ip_offset,
                        'points': service_config.get('points', 10),
                        'timeout': service_config.get('timeout', 20),
                        'score_key': f"{system_name}{service_name}"
                    }
                    
                    # Add service-specific config
                    if service_name == 'ssh':
                        scenario['ssh'] = {
                            'default_username': service_config.get('default_username', 'sysadmin'),
                            'default_password': service_config.get('default_password', 'changeme'),
                            'default_port': service_config.get('default_port', 22)
                        }
                    elif service_name == 'web':
                        scenario['web'] = {
                            'default_port': service_config.get('default_port', 80)
                        }
                    
                    scenarios.append(scenario)
        
        return scenarios


# Singleton instance
_config_loader = None

def get_config_loader(config_path="master_config.json") -> ConfigLoader:
    """Get or create the singleton ConfigLoader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader(config_path)
    return _config_loader
