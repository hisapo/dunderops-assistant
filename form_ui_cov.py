"""
DunderOps Assistant com Chain of Verification
Versão melhorada que usa auto-crítica para aumentar assertividade das respostas
"""

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
from src.core.function_intent import detect_function_intent
from src.core.function_validator import FunctionValidator
from src.cov.chain_of_verification import ChainOfVerification, CoVConfiguration
from src.core.metrics_tracker import MetricsTracker

print("🚀 Iniciando DunderOps Assistant com Chain of Verification...")

# Configuração
prompts = PromptConfig()
validator = FunctionValidator(prompts)
cov_config = CoVConfiguration()

# Welcome message específico desta UI
welcome_text = """
# DunderOps Assistant (+CoVe)

Olá! Eu sou o assistente de operações da Dunder Mifflin Paper Co! Eu posso te responder trivia sobre The Office, ajudar em coisas como: preparar orçamentos, agendar reuniões, e até planejar trotes para o Dwight 😇

🔍 **Chain of Verification Ativo:** Esta versão usa auto-verificação para dar respostas mais precisas!
"""

input_page = [
    MarkdownOutput(welcome_text),
    TextareaInput(label="Como posso te ajudar hoje?", key="textarea_input"),
]

# Pegar o input do usuario
result = run([input_page])
user_input = result["textarea_input"]
print(f"💬 Usuário perguntou: {user_input}")

# Configura cliente OpenAI
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    error_message = "❌ Erro: API Key da OpenAI não configurada. Por favor, configure a variável de ambiente OPENAI_API_KEY."
    final_page = [MarkdownOutput(error_message)]
    run([final_page])
    exit(1)

client = OpenAI(api_key=openai_api_key)

# Inicializa Chain of Verification
cov = ChainOfVerification(client, prompts)

# Inicializa metrics tracker
tracker = MetricsTracker("chain_of_verification")
execution_id = tracker.start_execution(user_input)

try:
    # Carrega o manifesto com os schemas
    with open("config/manifest.json") as f:
        manifest = json.load(f)

    # Mapeia nome → função em functions.py
    LOCAL_FUNCS = {
        "schedule_meeting": schedule_meeting,
        "generate_paper_quote": generate_paper_quote,
        "prank_dwight": prank_dwight,
    }

    # ETAPA 1: Gera resposta inicial
    # Detecta se deve forçar function calling
    tool_choice = detect_function_intent(user_input)
    print(f"🎯 Detecção de intenção: {tool_choice}")
    
    print("🤖 Enviando pergunta para a OpenAI (resposta inicial)...")
    first_response = client.chat.completions.create(
        model="gpt-4o-mini",
        tools=manifest["tools"],
        tool_choice=tool_choice,
        messages=[
            {"role": "system", "content": prompts.system_prompt},
            {"role": "user", "content": user_input}
        ]
    )

    # Registra primeira chamada de API
    tracker.track_api_call(
        input_tokens=first_response.usage.prompt_tokens,
        output_tokens=first_response.usage.completion_tokens
    )

    msg = first_response.choices[0].message
    function_call_info = None
    function_result = None
    initial_response = ""

    # Processa resposta inicial
    if msg.tool_calls:
        print("🔧 AI decidiu usar uma função...")
        call = msg.tool_calls[0]
        name = call.function.name
        args = json.loads(call.function.arguments)
        
        function_call_info = {
            "name": name,
            "arguments": args,
            "call_object": call
        }

        print(f"🔧 Validando função: {name} com argumentos: {args}")

        # Valida se todos os parâmetros necessários estão presentes
        is_valid, humor_message = validator.validate_function_params(name, args)
        
        if not is_valid:
            print("❌ Parâmetros incompletos - respondendo com humor...")
            initial_response = humor_message
            
            # Registra chamada de função (falhou na validação)
            tracker.track_function_call(name, args, None, False)
        else:
            print("✅ Parâmetros válidos - executando função...")
            # Executa a função
            function_result = LOCAL_FUNCS[name](**args)
            print(f"✅ Resultado da função: {function_result}")

            # Registra chamada de função (sucesso)
            tracker.track_function_call(name, args, function_result, True)

            # Gera resposta final baseada no resultado da função
            print("💭 Gerando resposta baseada no resultado da função...")
            final_response_call = client.chat.completions.create(
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
            
            # Registra segunda chamada de API
            tracker.track_api_call(
                input_tokens=final_response_call.usage.prompt_tokens,
                output_tokens=final_response_call.usage.completion_tokens
            )
            
            initial_response = final_response_call.choices[0].message.content
    else:
        print("💬 AI respondeu diretamente sem usar funções...")
        initial_response = msg.content

    print(f"📝 Resposta inicial: {initial_response}")

    # ETAPA 2: Chain of Verification
    if cov_config.should_verify(function_call_info.get("name") if function_call_info else None):
        print("🔍 Aplicando Chain of Verification...")
        
        # Inicia fase de verificação no tracker
        tracker.start_verification_phase()
        
        # Executa verificação e possível correção
        final_response, verification_metadata = cov.process_with_verification(
            user_input=user_input,
            initial_response=initial_response,
            function_call=function_call_info
        )
        
        # Simula tokens da verificação (em implementação real, seria calculado)
        verification_tokens = len(verification_metadata.get("verification_result", {}).get("issues", [])) * 50
        
        # Finaliza fase de verificação no tracker
        tracker.end_verification_phase(
            verification_tokens=verification_tokens,
            correction_made=verification_metadata.get("correction_applied", False)
        )
        
        if verification_metadata.get("correction_applied", False):
            print("✅ Resposta foi melhorada pelo Chain of Verification")
        else:
            print("✅ Resposta inicial aprovada na verificação")
            
    else:
        print("⏭️ Verificação pulada para este tipo de resposta")
        final_response = initial_response

    print(f"🎯 Resposta final: {final_response}")

except Exception as e:
    print(f"❌ Erro durante execução: {str(e)}")
    tracker.track_error(str(e))
    final_response = f"❌ Desculpe, ocorreu um erro: {str(e)}"

finally:
    # Finaliza tracking de métricas
    try:
        metric_data = tracker.end_execution(final_response)
        print(f"📊 Métricas coletadas - ID: {metric_data.execution_id}")
        print(f"   • Tokens totais: {metric_data.total_tokens}")
        print(f"   • Latência: {metric_data.total_latency_ms:.2f}ms")
        print(f"   • Verificação usada: {metric_data.verification_used}")
        print(f"   • Correção aplicada: {metric_data.correction_made}")
    except Exception as e:
        print(f"⚠️ Erro ao finalizar métricas: {str(e)}")

# Exibe a resposta final para o usuário
final_page = [MarkdownOutput(final_response)]
run([final_page])
