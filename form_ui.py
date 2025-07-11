import json
import os
from openai import OpenAI
from src.core.functions import (
    schedule_meeting,
    generate_paper_quote,
    prank_dwight,
)
from abstra.forms import TextareaInput, MarkdownOutput, run
from src.core.prompt_config import PromptConfig
from src.core.function_validator import FunctionValidator
from src.core.function_intent import detect_function_intent

print("🚀 Iniciando DunderOps Assistant...")

# Load prompt configuration
prompts = PromptConfig()
validator = FunctionValidator(prompts)

# Welcome message específico desta UI
welcome_text = """
# DunderOps Assistant

Olá! Eu sou o assistente de operações da Dunder Mifflin Paper Co! Eu posso te responder trivia sobre The Office, ajudar em coisas como: preparar orçamentos, agendar reuniões, e até planejar trotes para o Dwight 😇 
"""

input_page = [
    MarkdownOutput(welcome_text),
    TextareaInput(label="Como posso te ajudar hoje?", key="textarea_input"),
]

# Pegar o input do usuario
result = run([input_page])
user_input = result["textarea_input"]
print(f"💬 Usuário perguntou: {user_input}")

# Configura cliente OpenAI com variável de ambiente 
openai_api_key = os.environ.get("OPENAI_API_KEY")

client = OpenAI(api_key=openai_api_key)

# Carrega o manifesto com os schemas
with open("config/manifest.json") as f:
    manifest = json.load(f)

# Mapeia nome → função em functions.py
LOCAL_FUNCS = {
    "schedule_meeting": schedule_meeting,
    "generate_paper_quote": generate_paper_quote,
    "prank_dwight": prank_dwight,
}

# Detecta se deve forçar function calling
tool_choice = detect_function_intent(user_input)
print(f"🎯 Detecção de intenção: {tool_choice}")

# Envia a mensagem do usuário para o modelo já com os schemas
print("🤖 Enviando pergunta para a OpenAI...")
first = client.chat.completions.create(
    model="gpt-4o-mini",
    tools=manifest["tools"],
    tool_choice=tool_choice,
    messages=[
        {"role": "system", "content": prompts.system_prompt},
        {"role": "user", "content": user_input}
    ]
)

msg = first.choices[0].message

# Checa se a AI decidiu chamar uma função
if msg.tool_calls:
    print("🔧 AI decidiu usar uma função...")
    call = msg.tool_calls[0]
    name = call.function.name
    args = json.loads(call.function.arguments)

    print(f"🔧 Validando função: {name} com argumentos: {args}")

    # Valida se todos os parâmetros necessários estão presentes
    is_valid, humor_message = validator.validate_function_params(name, args)
    
    if not is_valid:
        print("❌ Parâmetros incompletos - respondendo com humor...")
        # Se parâmetros estão faltando, usa resposta humorística
        final_response = humor_message
    else:
        print("✅ Parâmetros válidos - executando função...")
        # Executa a função
        function_result = LOCAL_FUNCS[name](**args)
        print(f"✅ Resultado da função: {function_result}")

        # Devolve o resultado como mensagem "tool" e pede a resposta final
        print("💭 Gerando resposta final...")
        second = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompts.final_system_prompt},
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": None, "tool_calls": [call]},
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "name": name,
                    "content": json.dumps(function_result)
                }
            ]
        )
        final_response = second.choices[0].message.content
else:
    print("💬 AI respondeu diretamente sem usar funções...")
    # A IA respondeu diretamente sem chamar funções
    final_response = msg.content

print(f"🎯 Resposta final gerada: {final_response}")

# Exibe a resposta final para o usuário
final_page = [MarkdownOutput(final_response)]
run([final_page])