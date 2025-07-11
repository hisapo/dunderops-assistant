"""
Exemplo de uso do validador de funções
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.prompt_config import PromptConfig
from src.core.function_validator import FunctionValidator

def demonstrate_validation():
    """Demonstra como usar o validador de funções"""
    
    # Carrega configuração e cria validador
    prompts = PromptConfig()
    validator = FunctionValidator(prompts)
    
    print("🔍 Demonstração do Sistema de Validação")
    print("=" * 50)
    
    # Teste 1: Reunião incompleta
    print("\n📅 Teste 1: Agendar reunião (parâmetros incompletos)")
    print("Parâmetros fornecidos: {'room': 'Conference Room'}")
    
    is_valid, message = validator.validate_function_params(
        "schedule_meeting", 
        {"room": "Conference Room"}
    )
    print(f"Válido: {is_valid}")
    print(f"Mensagem: {message}")
    
    # Teste 2: Orçamento incompleto
    print("\n💰 Teste 2: Gerar orçamento (parâmetros incompletos)")
    print("Parâmetros fornecidos: {'paper_type': 'A4'}")
    
    is_valid, message = validator.validate_function_params(
        "generate_paper_quote", 
        {"paper_type": "A4"}
    )
    print(f"Válido: {is_valid}")
    print(f"Mensagem: {message}")
    
    # Teste 3: Pegadinha incompleta
    print("\n🎯 Teste 3: Pegadinha no Dwight (parâmetros incompletos)")
    print("Parâmetros fornecidos: {'prank_type': 'desk'}")
    
    is_valid, message = validator.validate_function_params(
        "prank_dwight", 
        {"prank_type": "desk"}
    )
    print(f"Válido: {is_valid}")
    print(f"Mensagem: {message}")
    
    # Teste 4: Reunião completa
    print("\n✅ Teste 4: Agendar reunião (todos os parâmetros)")
    complete_params = {
        "topic": "Reunião de vendas",
        "date": "2024-01-15",
        "time": "14:00",
        "room": "Conference Room"
    }
    print(f"Parâmetros fornecidos: {complete_params}")
    
    is_valid, message = validator.validate_function_params(
        "schedule_meeting", 
        complete_params
    )
    print(f"Válido: {is_valid}")
    print(f"Mensagem: {message}")
    
    # Teste 5: Listar parâmetros faltantes
    print("\n📋 Teste 5: Listar parâmetros faltantes")
    missing = validator.list_missing_params(
        "generate_paper_quote", 
        {"paper_type": "A4"}
    )
    print(f"Parâmetros faltantes: {missing}")
    
    formatted_message = validator.format_missing_params_message(
        "generate_paper_quote", 
        missing
    )
    print(f"Mensagem formatada:\n{formatted_message}")

if __name__ == "__main__":
    demonstrate_validation()
