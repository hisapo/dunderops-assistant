"""
Demonstração do Chain of Verification
"""

import os
from openai import OpenAI
from src.cov.chain_of_verification import ChainOfVerification, CoVConfiguration
from src.core.prompt_config import PromptConfig
from src.core.metrics_tracker import MetricsTracker


def demo_chain_of_verification():
    """Demonstra o funcionamento do Chain of Verification"""
    print("🔍 DEMONSTRAÇÃO DO CHAIN OF VERIFICATION")
    print("=" * 60)
    
    # Verifica se a API key está configurada
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ ERRO: Configure a variável OPENAI_API_KEY para executar este demo")
        return
    
    # Configuração
    client = OpenAI(api_key=openai_api_key)
    prompts = PromptConfig()
    cov = ChainOfVerification(client, prompts)
    
    # Casos de teste
    test_cases = [
        {
            "name": "Resposta incompleta sobre reunião",
            "user_input": "Preciso agendar uma reunião sobre vendas",
            "initial_response": "Claro! Vou agendar uma reunião sobre vendas para você.",
            "function_call": {
                "name": "schedule_meeting",
                "arguments": {"topic": "vendas"}
            }
        },
        {
            "name": "Resposta com informação incorreta",
            "user_input": "Quanto custa papel A4?",
            "initial_response": "Papel A4 custa $50 a resma na Dunder Mifflin.",
            "function_call": None
        },
        {
            "name": "Resposta boa que não precisa correção",
            "user_input": "Qual o nome do chefe da Dunder Mifflin?",
            "initial_response": "O chefe regional da filial de Scranton é Michael Scott! Ele é o World's Best Boss (pelo menos é o que ele mesmo diz). Michael é conhecido por seu estilo de gerenciamento único, suas piadas duvidosas e sua obsessão em ser amado por todos. Ele realmente se importa com seus funcionários, mesmo que às vezes demonstre isso de forma... interessante! 😄",
            "function_call": None
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{'='*20} TESTE {i}: {test_case['name']} {'='*20}")
        print(f"👤 Input: {test_case['user_input']}")
        print(f"🤖 Resposta inicial: {test_case['initial_response']}")
        
        if test_case['function_call']:
            print(f"🔧 Função: {test_case['function_call']['name']}")
            print(f"📋 Parâmetros: {test_case['function_call']['arguments']}")
        
        # Inicia tracking
        tracker = MetricsTracker("chain_of_verification")
        tracker.start_execution(test_case['user_input'])
        
        try:
            # Aplica Chain of Verification
            tracker.start_verification_phase()
            
            final_response, verification_metadata = cov.process_with_verification(
                user_input=test_case['user_input'],
                initial_response=test_case['initial_response'],
                function_call=test_case['function_call']
            )
            
            tracker.end_verification_phase(
                verification_tokens=100,  # Estimativa
                correction_made=verification_metadata.get('correction_applied', False)
            )
            
            print("\n📊 RESULTADOS:")
            print(f"   ✅ Verificação aplicada: {verification_metadata['verification_performed']}")
            print(f"   🔧 Correção feita: {verification_metadata['correction_applied']}")
            
            if verification_metadata['verification_result'].get('has_issues'):
                issues = verification_metadata['verification_result'].get('issues', [])
                print(f"   ⚠️ Issues encontradas: {len(issues)}")
                for issue in issues[:2]:  # Mostra apenas os primeiros 2
                    print(f"      - {issue}")
            
            print("\n🎯 RESPOSTA FINAL:")
            print(f"   {final_response}")
            
            # Finaliza tracking
            metric = tracker.end_execution(final_response)
            print("\n📈 MÉTRICAS:")
            print(f"   • Latência total: {metric.total_latency_ms:.2f}ms")
            print(f"   • Verificação usada: {metric.verification_used}")
            print(f"   • Correção aplicada: {metric.correction_made}")
            
        except Exception as e:
            print(f"❌ Erro no teste: {str(e)}")
            tracker.track_error(str(e))
            tracker.end_execution("Erro durante execução")


def demo_cov_configuration():
    """Demonstra as configurações do CoV"""
    print("\n🔧 DEMONSTRAÇÃO DAS CONFIGURAÇÕES DO COV")
    print("=" * 50)
    
    config = CoVConfiguration()
    
    print("📋 Configurações gerais:")
    print(f"   • Verificação habilitada: {config.verification_enabled}")
    print(f"   • Threshold: {config.verification_threshold}")
    print(f"   • Max tentativas: {config.max_verification_attempts}")
    print(f"   • Temperatura verificação: {config.verification_temperature}")
    print(f"   • Temperatura correção: {config.correction_temperature}")
    
    print("\n🔧 Configurações por função:")
    for func_name, func_config in config.function_specific_config.items():
        print(f"   • {func_name}:")
        print(f"     - Foco: {func_config['verification_focus']}")
        print(f"     - Prioridade: {func_config['correction_priority']}")
        print(f"     - Deve verificar: {config.should_verify(func_name)}")


def demo_verification_types():
    """Demonstra diferentes tipos de verificação"""
    print("\n🎯 TIPOS DE VERIFICAÇÃO DISPONÍVEIS")
    print("=" * 50)
    
    # Verifica se a API key está configurada
    openai_api_key = os.environ.get("OPENAI_API_KEY")
    if not openai_api_key:
        print("❌ Configure OPENAI_API_KEY para ver exemplos de verificação")
        return
    
    client = OpenAI(api_key=openai_api_key)
    prompts = PromptConfig()
    cov = ChainOfVerification(client, prompts)
    
    # Exemplo de verificação geral
    print("1️⃣ VERIFICAÇÃO GERAL:")
    try:
        result = cov.verify_initial_response(
            user_input="Quem é o Michael Scott?",
            initial_response="Michael Scott é um personagem.",
            function_call=None
        )
        print(f"   Has issues: {result.get('has_issues', 'N/A')}")
        print(f"   Severity: {result.get('severity', 'N/A')}")
        print(f"   Should regenerate: {result.get('should_regenerate', 'N/A')}")
        
        if result.get('issues'):
            print(f"   Issues: {result['issues'][:2]}")  # Primeiras 2
            
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")
    
    # Exemplo de verificação de função
    print("\n2️⃣ VERIFICAÇÃO DE FUNÇÃO:")
    try:
        result = cov.verify_initial_response(
            user_input="Agendar reunião",
            initial_response="Reunião agendada!",
            function_call={
                "name": "schedule_meeting",
                "arguments": {"topic": "vendas"}  # Parâmetros incompletos
            }
        )
        print(f"   Function correct: {result.get('function_correct', 'N/A')}")
        print(f"   Missing params: {result.get('missing_params', 'N/A')}")
        print(f"   Should retry: {result.get('should_retry', 'N/A')}")
        
    except Exception as e:
        print(f"   ❌ Erro: {str(e)}")


if __name__ == "__main__":
    print("🚀 DEMONSTRAÇÃO COMPLETA DO CHAIN OF VERIFICATION")
    print("=" * 70)
    
    # Executa todas as demonstrações
    demo_cov_configuration()
    demo_verification_types()
    demo_chain_of_verification()
    
    print("\n🎉 Demonstração do Chain of Verification concluída!")
    print("   • Sistema de auto-verificação implementado")
    print("   • Diferentes tipos de verificação disponíveis")  
    print("   • Configurações flexíveis por função")
    print("   • Integração com métricas funcionando")
    print("   • Pronto para comparar com a versão original!")
