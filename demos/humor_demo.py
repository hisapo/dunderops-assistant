"""
Exemplo de uso do sistema de humor do DunderOps Assistant

Este arquivo demonstra como o sistema responde a solicitações incompletas
de agendamento de reuniões com humor no estilo The Office.

Note: UI elements like welcome messages are kept hardcoded in each UI file.
Only AI system prompts and function-related configurations are externalized.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.prompt_config import PromptConfig

def demonstrate_humor_system():
    """Demonstra como o sistema de humor funciona"""
    
    # Carrega a configuração
    prompts = PromptConfig()
    
    # Cenários de teste
    scenarios = [
        "marque uma reunião para o conference room amanhã",
        "preciso agendar uma reunião",
        "marque uma reunião sobre vendas",
        "agende uma reunião para amanhã às 14:00"
    ]
    
    print("🎭 Demonstração do Sistema de Humor")
    print("=" * 50)
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n📝 Cenário {i}: '{scenario}'")
        
        # Simula a resposta que a IA deveria dar
        humor_response = prompts.get_humor_response("incomplete_meeting", (i-1) % 4)
        print(f"🤖 Resposta: {humor_response}")
        
        # Mostra uma resposta aleatória também
        random_response = prompts.get_random_humor_response("incomplete_meeting")
        print(f"🎲 Resposta aleatória: {random_response}")
        print("-" * 40)

if __name__ == "__main__":
    demonstrate_humor_system()
