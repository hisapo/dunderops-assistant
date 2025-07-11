"""
Enhanced Function Validator com proteção contra prompt injection
Integra validação de parâmetros com segurança de entrada
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
from src.core.prompt_config import PromptConfig
from .input_security import SecureInputProcessor

class SecureFunctionValidator:
    """
    Validador seguro que combina validação de parâmetros com proteção contra injection
    """
    
    def __init__(self, prompts: PromptConfig, security_config_path: str = "config/security_config.json"):
        self.prompts = prompts
        self.security_processor = SecureInputProcessor()
        self.logger = logging.getLogger(__name__)
        
        # Carrega configuração de segurança
        try:
            with open(security_config_path, 'r', encoding='utf-8') as f:
                self.security_config = json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração de segurança: {e}")
            self.security_config = self._get_default_security_config()
    
    def _get_default_security_config(self) -> Dict:
        """Configuração de segurança padrão caso arquivo não seja encontrado"""
        return {
            "security_config": {"max_input_length": 5000},
            "input_schemas": {"function_params": {}},
            "safety_patterns": {"high_risk": [], "medium_risk": []},
            "content_limits": {"max_words": 1000}
        }
    
    def validate_user_input(self, user_input: str) -> Tuple[bool, str, str]:
        """
        Valida entrada do usuário com proteção contra injection
        
        Returns:
            Tuple[bool, str, str]: (is_safe, error_message, processed_input)
        """
        return self.security_processor.process_user_input(user_input)
    
    def validate_function_call(self, function_name: str, raw_arguments: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida chamada de função de forma segura
        
        Args:
            function_name: Nome da função
            raw_arguments: Argumentos em formato JSON (string)
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (is_valid, error_or_humor, parsed_args)
        """
        # 1. Validação de segurança dos argumentos JSON
        function_schema = self.security_config.get("input_schemas", {}).get("function_params", {}).get(function_name)
        
        is_safe, error_msg, parsed_args = self.security_processor.process_json_input(
            raw_arguments, function_schema
        )
        
        if not is_safe:
            self.logger.warning(f"Argumentos inseguros para {function_name}: {error_msg}")
            return False, f"Erro de segurança nos parâmetros: {error_msg}", None
        
        # 2. Validação de parâmetros obrigatórios
        return self._validate_required_params(function_name, parsed_args)
    
    def _validate_required_params(self, function_name: str, provided_params: Dict[str, Any]) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida parâmetros obrigatórios e gera respostas humorísticas
        """
        required_params = self.prompts.get_required_params(function_name)
        
        if not required_params:
            return True, "", provided_params
        
        # Verifica parâmetros faltantes
        missing_params = []
        for param in required_params:
            if param not in provided_params or provided_params[param] is None:
                missing_params.append(param)
        
        # Validação adicional de conteúdo dos parâmetros
        for param, value in provided_params.items():
            if isinstance(value, str):
                is_safe, error_msg, sanitized = self.security_processor.process_user_input(value)
                if not is_safe:
                    self.logger.warning(f"Parâmetro {param} contém conteúdo inseguro: {error_msg}")
                    return False, f"Parâmetro '{param}' contém conteúdo inválido", None
                # Atualiza com versão sanitizada
                provided_params[param] = sanitized
        
        if missing_params:
            humor_response = self.prompts.get_missing_params_humor(function_name)
            return False, humor_response, None
        
        return True, "", provided_params
    
    def validate_and_sanitize_response(self, response_text: str) -> Tuple[bool, str]:
        """
        Valida e sanitiza resposta do LLM antes de enviar ao usuário
        """
        # Verificações básicas de segurança na resposta
        if not response_text or len(response_text.strip()) == 0:
            return False, "Resposta vazia"
        
        # Limite de tamanho da resposta
        max_response_length = self.security_config.get("content_limits", {}).get("max_response_length", 5000)
        if len(response_text) > max_response_length:
            return False, f"Resposta muito longa (máximo {max_response_length} caracteres)"
        
        # Sanitização básica
        sanitized = self._sanitize_response(response_text)
        
        return True, sanitized
    
    def _sanitize_response(self, response: str) -> str:
        """
        Sanitiza resposta para remover conteúdo potencialmente problemático
        """
        # Remove caracteres de controle (mantém quebras de linha normais)
        sanitized = ''.join(char for char in response 
                          if ord(char) >= 32 or char in '\n\r\t')
        
        # Remove múltiplas quebras de linha excessivas
        while '\n\n\n\n' in sanitized:
            sanitized = sanitized.replace('\n\n\n\n', '\n\n\n')
        
        return sanitized.strip()
    
    def log_security_event(self, event_type: str, details: Dict[str, Any]):
        """
        Registra eventos de segurança para análise
        """
        log_entry = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        
        self.logger.warning(f"Security Event: {json.dumps(log_entry)}")
    
    def get_security_stats(self) -> Dict[str, Any]:
        """
        Retorna estatísticas de segurança (para monitoramento)
        """
        return {
            "config_loaded": bool(self.security_config),
            "max_input_length": self.security_config.get("security_config", {}).get("max_input_length", 0),
            "supported_functions": list(self.security_config.get("input_schemas", {}).get("function_params", {}).keys()),
            "security_patterns_count": {
                "high_risk": len(self.security_config.get("safety_patterns", {}).get("high_risk", [])),
                "medium_risk": len(self.security_config.get("safety_patterns", {}).get("medium_risk", []))
            }
        }

# Função utilitária para validação rápida
def quick_validate_input(user_input: str) -> Tuple[bool, str]:
    """
    Função utilitária para validação rápida de entrada
    """
    processor = SecureInputProcessor(max_input_length=5000)
    return processor.process_user_input(user_input)[:2]  # Retorna apenas is_safe e error
