"""
Validador de parâmetros para funções do DunderOps Assistant
"""

from typing import Dict, List, Any, Tuple
from .prompt_config import PromptConfig

class FunctionValidator:
    """Valida parâmetros de funções e gera respostas humorísticas para parâmetros faltantes"""
    
    def __init__(self, prompts: PromptConfig):
        self.prompts = prompts
    
    def validate_function_params(self, function_name: str, provided_params: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Valida se todos os parâmetros necessários estão presentes
        
        Args:
            function_name: Nome da função
            provided_params: Parâmetros fornecidos
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message_or_empty)
        """
        required_params = self.prompts.get_required_params(function_name)
        
        if not required_params:
            # Se não há requisitos definidos, assume que está válido
            return True, ""
        
        missing_params = []
        for param in required_params:
            if param not in provided_params or provided_params[param] is None:
                missing_params.append(param)
        
        if missing_params:
            # Gera resposta humorística para parâmetros faltantes
            humor_response = self.prompts.get_missing_params_humor(function_name)
            return False, humor_response
        
        return True, ""
    
    def get_param_info(self, function_name: str, param_name: str) -> str:
        """Obtém descrição de um parâmetro específico"""
        descriptions = self.prompts.get_param_descriptions(function_name)
        return descriptions.get(param_name, param_name)
    
    def list_missing_params(self, function_name: str, provided_params: Dict[str, Any]) -> List[str]:
        """Lista os parâmetros que estão faltando"""
        required_params = self.prompts.get_required_params(function_name)
        missing = []
        
        for param in required_params:
            if param not in provided_params or provided_params[param] is None:
                missing.append(param)
        
        return missing
    
    def format_missing_params_message(self, function_name: str, missing_params: List[str]) -> str:
        """Formata mensagem listando parâmetros faltantes com suas descrições"""
        if not missing_params:
            return ""
        
        descriptions = self.prompts.get_param_descriptions(function_name)
        param_list = []
        
        for param in missing_params:
            desc = descriptions.get(param, param)
            param_list.append(f"• {param}: {desc}")
        
        return "Parâmetros faltantes:\n" + "\n".join(param_list)
