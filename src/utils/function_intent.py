"""
Utilitários para detecção inteligente de function calling
"""

def detect_function_intent(user_input: str) -> str:
    """
    Detecta se deve forçar function calling baseado no input do usuário
    
    Returns:
        str: "required" se deve forçar função, "auto" caso contrário
    """
    input_lower = user_input.lower()
    
    # Padrões que indicam intenção clara de function calling
    meeting_patterns = [
        "agendar reunião", "marcar reunião", "schedule meeting",
        "reunião sobre", "reunião para", "meeting about"
    ]
    
    paper_patterns = [
        "orçamento", "cotação", "preço de papel", "papel a4", "papel legal", "papel letter",
        "quote", "budget", "gsm", "folhas", "gerar orçamento"
    ]
    
    prank_patterns = [
        "pegadinha", "prank", "dwight", "brincadeira",
        "desk", "food", "misc", "sugerir pegadinha"
    ]
    
    # Verifica se há palavras-chave + parâmetros específicos
    has_meeting_intent = any(pattern in input_lower for pattern in meeting_patterns)
    has_paper_intent = any(pattern in input_lower for pattern in paper_patterns)
    has_prank_intent = any(pattern in input_lower for pattern in prank_patterns)
    
    # Se detectar intenção clara com parâmetros suficientes, força function calling
    if has_meeting_intent and any(keyword in input_lower for keyword in ["conference room", "annex", "break room", "2024-", "às", ":"]):
        return "required"
    elif has_paper_intent and any(keyword in input_lower for keyword in ["gsm"]) and any(keyword in input_lower for keyword in ["a4", "legal", "letter"]) and any(keyword in input_lower for keyword in ["folhas", "1000", "500", "100"]):
        return "required"
    elif has_prank_intent and any(keyword in input_lower for keyword in ["$", "dólar", "orçamento", "budget"]) and any(keyword in input_lower for keyword in ["desk", "food", "misc"]):
        return "required"
    
    return "auto"
