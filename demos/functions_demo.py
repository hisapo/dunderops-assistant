"""
Example of how to use the decoupled prompts in functions.py

This file demonstrates how to integrate the PromptConfig class into your existing functions
to use externalized prompt templates instead of hardcoded strings.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.prompt_config import PromptConfig

# Load the prompt configuration
prompts = PromptConfig()

def schedule_meeting_with_template(topic, date, time, room):
    """
    Example of using the prompt configuration for meeting confirmations
    """
    confirmation_message = prompts.get_function_template(
        "meeting_confirmation",
        topic=topic,
        date=date,
        time=time,
        room=room
    )
    return {"confirmation_message": confirmation_message}

def prank_dwight_with_template(prank_type, max_budget_usd):
    """
    Example of using the prompt configuration for prank descriptions
    """
    # Get the intro description from the template
    intro_description = prompts.get_function_template("prank_intro")
    
    # Your existing prank logic here...
    ideas_catalog = {
        "desk": [
            ("Envolver o grampeador dele em gelatina.", 12.75),
            ("Colocar seu estojo de canetas no freezer e devolver congelado.", 5.00),
            ("Trocar todas as gavetas de posição durante a noite.", 0.00),
        ],
        "food": [
            ("Substituir o papel alumínio do almoço por plástico filme transparente.", 3.50),
            ("Adicionar corante alimentício azul no leite dele (comestível e seguro).", 2.00),
            ("Colocar uma passas de chocolate que parecem azeitonas na salada dele.", 4.00),
        ],
        "misc": [
            ("Colar post-its amarelos cobrindo completamente o monitor dele.", 6.00),
            ("Configurar o celular dele para idioma Klingon.", 0.00),
            ("Colocar um falso sinal de 'Fechado para Inventário' na porta de sua mesa.", 1.00),
            ("Alterar o som de inicialização do PC dele para um miado de gato.", 0.00),
        ],
    }

    options = ideas_catalog.get(prank_type, sum(ideas_catalog.values(), []))
    selected = [idea for idea, cost in options if cost <= max_budget_usd][:10]

    result = {
        "description": intro_description,
        "ideas": selected,
        "hr_compliant": True,
        "max_budget_usd": max_budget_usd
    }
    return result
