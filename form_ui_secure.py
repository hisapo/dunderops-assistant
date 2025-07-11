"""
DunderOps Assistant com proteção contra prompt injection
Versão segura com validação e sanitização de entrada
"""

import json
import os
import logging
from openai import OpenAI
from src.core.functions import (
    schedule_meeting,
    generate_paper_quote,
    prank_dwight,
)
from abstra.forms import TextareaInput, MarkdownOutput, run
from src.core.prompt_config import PromptConfig
from src.security.secure_function_validator import SecureFunctionValidator
from src.core.function_intent import detect_function_intent

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

print("🔒 Iniciando DunderOps Assistant Seguro...")

# Load prompt configuration
prompts = PromptConfig()
secure_validator = SecureFunctionValidator(prompts)

# Estatísticas de segurança para monitoramento
security_stats = secure_validator.get_security_stats()
logger.info(f"Configuração de segurança carregada: {security_stats}")

# Welcome message específico desta UI
welcome_text = """
# DunderOps Assistant (+Injection Protection)

Olá! Eu sou o assistente de operações da Dunder Mifflin Paper Co! Eu posso te responder trivia sobre The Office, ajudar em coisas como: preparar orçamentos, agendar reuniões, e até planejar trotes para o Dwight 😇

🔒 **Sistema de Segurança Ativo:** Proteção contra prompt injection e validação de entrada.
"""

input_page = [
    MarkdownOutput(welcome_text),
    TextareaInput(label="Como posso te ajudar hoje?", key="textarea_input"),
]

# Pegar o input do usuario
result = run([input_page])
user_input = result["textarea_input"]

logger.info(f"Entrada recebida do usuário (tamanho: {len(user_input)})")

# 🔒 VALIDAÇÃO DE SEGURANÇA DA ENTRADA
print("🔍 Validando entrada do usuário...")
is_safe, security_error, processed_input = secure_validator.validate_user_input(user_input)

if not is_safe:
    error_message = f"""
# ⚠️ Entrada Rejeitada

Sua mensagem foi rejeitada pelo sistema de segurança:

**Motivo:** {security_error}

Por favor, tente novamente com uma mensagem diferente. Evite:
- Comandos especiais ou caracteres de controle
- Tentativas de modificar o comportamento do sistema
- Conteúdo excessivamente longo ou mal formatado

Obrigado pela compreensão! 🛡️
    """
    
    logger.warning(f"Entrada rejeitada: {security_error}")
    final_page = [MarkdownOutput(error_message)]
    run([final_page])
    exit()

print("✅ Entrada validada e processada com segurança")
logger.info("Entrada do usuário passou na validação de segurança")

# Configura cliente OpenAI com variável de ambiente 
openai_api_key = os.environ.get("OPENAI_API_KEY")

if not openai_api_key:
    error_msg = prompts.get_error_message("no_openai_key")
    final_page = [MarkdownOutput(error_msg)]
    run([final_page])
    exit()

client = OpenAI(api_key=openai_api_key)

# Carrega o manifesto com os schemas
try:
    with open("config/manifest.json") as f:
        manifest = json.load(f)
except Exception as e:
    logger.error(f"Erro ao carregar manifest.json: {e}")
    error_msg = "❌ Erro interno do sistema. Tente novamente mais tarde."
    final_page = [MarkdownOutput(error_msg)]
    run([final_page])
    exit()

# Mapeia nome → função em functions.py
LOCAL_FUNCS = {
    "schedule_meeting": schedule_meeting,
    "generate_paper_quote": generate_paper_quote,
    "prank_dwight": prank_dwight,
}

# Envia a mensagem do usuário (processada de forma segura) para o modelo
# Detecta se deve forçar function calling
tool_choice = detect_function_intent(processed_input)
print(f"🎯 Detecção de intenção: {tool_choice}")

print("🤖 Enviando pergunta segura para a OpenAI...")
try:
    first = client.chat.completions.create(
        model="gpt-4o-mini",
        tools=manifest["tools"],
        tool_choice=tool_choice,
        messages=[
            {"role": "system", "content": prompts.system_prompt},
            {"role": "user", "content": processed_input}  # Usa entrada processada
        ]
    )
except Exception as e:
    logger.error(f"Erro na chamada da OpenAI: {e}")
    error_msg = prompts.get_error_message("api_error")
    final_page = [MarkdownOutput(error_msg)]
    run([final_page])
    exit()

msg = first.choices[0].message

# Checa se a AI decidiu chamar uma função
if msg.tool_calls:
    print("🔧 AI decidiu usar uma função...")
    call = msg.tool_calls[0]
    function_name = call.function.name
    raw_arguments = call.function.arguments

    print(f"🔒 Validando função: {function_name}")
    logger.info(f"Validando chamada de função: {function_name}")

    # 🔒 VALIDAÇÃO SEGURA DA FUNÇÃO
    is_valid, response_or_error, validated_args = secure_validator.validate_function_call(
        function_name, raw_arguments
    )
    
    if not is_valid:
        print("❌ Função rejeitada ou parâmetros incompletos")
        logger.warning(f"Função {function_name} rejeitada: {response_or_error}")
        
        # Pode ser erro de segurança ou parâmetros faltantes (com humor)
        final_response = response_or_error
    else:
        print("✅ Função validada - executando...")
        logger.info(f"Executando função {function_name} com parâmetros validados")
        
        try:
            # Executa a função com argumentos validados
            function_result = LOCAL_FUNCS[function_name](**validated_args)
            print(f"✅ Resultado da função: {function_result}")

            # Gera resposta final
            print("💭 Gerando resposta final...")
            second = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompts.final_system_prompt},
                    {"role": "user", "content": processed_input},
                    {"role": "assistant", "content": None, "tool_calls": [call]},
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "name": function_name,
                        "content": json.dumps(function_result)
                    }
                ]
            )
            final_response = second.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Erro na execução da função {function_name}: {e}")
            error_template = prompts.get_error_message("function_error")
            final_response = error_template.format(function_name=function_name)
else:
    print("💬 AI respondeu diretamente sem usar funções...")
    final_response = msg.content

# 🔒 VALIDAÇÃO E SANITIZAÇÃO DA RESPOSTA
print("🔍 Validando resposta antes de exibir...")
is_response_safe, sanitized_response = secure_validator.validate_and_sanitize_response(final_response)

if not is_response_safe:
    logger.error(f"Resposta rejeitada: {sanitized_response}")
    final_response = "❌ Erro na geração da resposta. Tente reformular sua pergunta."
else:
    final_response = sanitized_response

print("🎯 Resposta final segura gerada")
logger.info("Resposta validada e pronta para exibição")

# Log de estatísticas de segurança para monitoramento
logger.info(f"Sessão concluída com sucesso. Stats: entrada_processada=True, função_chamada={bool(msg.tool_calls)}")

# Exibe a resposta final para o usuário
final_page = [MarkdownOutput(final_response)]
run([final_page])
