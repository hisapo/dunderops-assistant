"""
Prompt configuration loader for DunderOps Assistant
"""
import json
from typing import Dict, Any

class PromptConfig:
    """Loads and manages prompt configurations"""
    
    def __init__(self, config_file: str = "config/prompts.json"):
        self.config_file = config_file
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt configuration file '{self.config_file}' not found")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
    
    @property
    def system_prompt(self) -> str:
        """Get the main system prompt for the AI assistant"""
        return self._config.get("system_prompt", "")
    
    @property
    def final_system_prompt(self) -> str:
        """Get the system prompt for final response generation"""
        return self._config.get("final_system_prompt", "Você é o DunderOps Assistant")
    
    def get_prompt(self, key: str, default: str = "") -> str:
        """Get a specific prompt by key"""
        return self._config.get(key, default)
    
    def get_example(self, key: str, default: str = "") -> str:
        """Get an example by key"""
        return self._config.get("examples", {}).get(key, default)
    
    def get_error_message(self, key: str, **kwargs) -> str:
        """Get an error message by key, with optional formatting"""
        message = self._config.get("error_messages", {}).get(key, "")
        if kwargs:
            return message.format(**kwargs)
        return message
    
    def get_function_template(self, key: str, **kwargs) -> str:
        """Get a function template by key, with optional formatting"""
        template = self._config.get("function_templates", {}).get(key, "")
        if kwargs:
            return template.format(**kwargs)
        return template
    
    def get_humor_response(self, key: str, index: int = 0) -> str:
        """Get a humor response by key and index"""
        responses = self._config.get("humor_responses", {}).get(key, [])
        if responses and 0 <= index < len(responses):
            return responses[index]
        return ""
    
    def get_random_humor_response(self, key: str) -> str:
        """Get a random humor response by key"""
        import random
        responses = self._config.get("humor_responses", {}).get(key, [])
        if responses:
            return random.choice(responses)
        return ""
    
    def get_function_requirements(self, function_name: str) -> dict:
        """Get the requirements for a specific function"""
        return self._config.get("function_requirements", {}).get(function_name, {})
    
    def get_required_params(self, function_name: str) -> list:
        """Get the list of required parameters for a function"""
        return self.get_function_requirements(function_name).get("required_params", [])
    
    def get_param_descriptions(self, function_name: str) -> dict:
        """Get parameter descriptions for a function"""
        return self.get_function_requirements(function_name).get("param_descriptions", {})
    
    def get_missing_params_humor(self, function_name: str) -> str:
        """Get humor response for missing parameters based on function type"""
        humor_key_map = {
            "schedule_meeting": "incomplete_meeting",
            "generate_paper_quote": "incomplete_quote", 
            "prank_dwight": "incomplete_prank"
        }
        key = humor_key_map.get(function_name, "incomplete_meeting")
        return self.get_random_humor_response(key)
    
    def reload(self) -> None:
        """Reload configuration from file"""
        self._config = self._load_config()
