def schedule_meeting(topic, date, time, room):
    return {"confirmation_message":
            f"Reunião “{topic}” marcada para {date} às {time} ({room})."}

def generate_paper_quote(paper_type, weight_gsm, quantity):
    price = 0.08 if weight_gsm <= 90 else 0.11
    subtotal = round(price * quantity, 2)
    tax_rate = 0.08  # 8% sales tax
    tax = round(subtotal * tax_rate, 2)
    return {
        "subtotal": subtotal,
        "tax": tax,
        "total": round(subtotal + tax, 2),
        "delivery_days": 3
    }

def prank_dwight(prank_type, max_budget_usd):
    """
    Retorna uma lista de até 10 ideias de pegadinhas leves, dentro do orçamento,
    para o Dwight. Cada ideia vem com custo estimado.
    """
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
        "ideas": selected,
        "hr_compliant": True,
        "max_budget_usd": max_budget_usd
    }
    return result