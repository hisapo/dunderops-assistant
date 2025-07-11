"""
Sistema de comparação entre implementação original e Chain of Verification
"""

import json
import os
import sys
import time
from typing import List, Dict, Any
from openai import OpenAI

# Adiciona o diretório pai ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports das implementações
from src.core.prompt_config import PromptConfig
from src.core.function_validator import FunctionValidator
from src.core.metrics_tracker import MetricsTracker
from src.core.experiment_logger import ExperimentLogger, ExperimentSession
from faithful_implementations import (
    FormUIOriginalReproduction, 
    FormUICoVReproduction, 
    FormUISecureReproduction
)

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Se dotenv não estiver disponível, continua sem ele
    pass


class ComparisonRunner:
    """Executa comparações entre as duas implementações"""
    
    def __init__(self):
        self.client = self._setup_client()
        self.prompts = PromptConfig()
        self.validator = FunctionValidator(self.prompts)
        self.logger = ExperimentLogger()
        
        # Inicializa implementações FIÉIS aos form_ui
        self.original = FormUIOriginalReproduction(self.client, self.prompts, self.validator)
        self.cov = FormUICoVReproduction(self.client, self.prompts, self.validator)
        self.secure = FormUISecureReproduction(self.client, self.prompts, self.validator)
        
        # Carrega manifest
        with open("config/manifest.json") as f:
            self.manifest = json.load(f)
    
    def _setup_client(self) -> OpenAI:
        """Configura cliente OpenAI"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        return OpenAI(api_key=api_key)
    
    def run_single_comparison(self, user_input: str) -> Dict[str, Any]:
        """Executa uma comparação para um input específico"""
        
        print(f"\n{'='*60}")
        print(f"🆚 COMPARANDO: {user_input}")
        print(f"{'='*60}")
        
        results = {}
        
        # Executa versão original
        print("\n🔵 EXECUTANDO VERSÃO ORIGINAL...")
        original_tracker = MetricsTracker("original")
        original_tracker.start_execution(user_input)
        
        try:
            original_response = self.original.process_request(user_input, self.manifest, original_tracker)
            original_metric = original_tracker.end_execution(original_response)
            results["original"] = {
                "response": original_response,
                "metric": original_metric,
                "success": True
            }
            print(f"✅ Original concluída: {original_metric.total_latency_ms:.2f}ms, {original_metric.total_tokens} tokens")
        except Exception as e:
            original_tracker.track_error(str(e))
            original_metric = original_tracker.end_execution(f"Erro: {str(e)}")
            results["original"] = {
                "response": f"Erro: {str(e)}",
                "metric": original_metric,
                "success": False
            }
            print(f"❌ Original falhou: {str(e)}")
        
        # Executa versão CoV
        print("\n🔍 EXECUTANDO VERSÃO CHAIN OF VERIFICATION...")
        cov_tracker = MetricsTracker("chain_of_verification")
        cov_tracker.start_execution(user_input)
        
        try:
            cov_response = self.cov.process_request(user_input, self.manifest, cov_tracker)
            cov_metric = cov_tracker.end_execution(cov_response)
            results["cov"] = {
                "response": cov_response,
                "metric": cov_metric,
                "success": True
            }
            print(f"✅ CoV concluída: {cov_metric.total_latency_ms:.2f}ms, {cov_metric.total_tokens} tokens")
            print(f"   Verificação: {cov_metric.verification_used}, Correção: {cov_metric.correction_made}")
        except Exception as e:
            cov_tracker.track_error(str(e))
            cov_metric = cov_tracker.end_execution(f"Erro: {str(e)}")
            results["cov"] = {
                "response": f"Erro: {str(e)}",
                "metric": cov_metric,
                "success": False
            }
            print(f"❌ CoV falhou: {str(e)}")
        
        # Compara resultados
        print("\n📊 COMPARAÇÃO:")
        if results["original"]["success"] and results["cov"]["success"]:
            orig_metric = results["original"]["metric"]
            cov_metric = results["cov"]["metric"]
            
            latency_diff = ((cov_metric.total_latency_ms - orig_metric.total_latency_ms) / orig_metric.total_latency_ms) * 100
            token_diff = ((cov_metric.total_tokens - orig_metric.total_tokens) / orig_metric.total_tokens) * 100
            
            print(f"   ⏱️ Latência: CoV {latency_diff:+.1f}% vs Original")
            print(f"   🔤 Tokens: CoV {token_diff:+.1f}% vs Original")
            print(f"   🔍 Verificação CoV: {cov_metric.verification_used}")
            print(f"   🔧 Correção CoV: {cov_metric.correction_made}")
        
        print("\n📝 RESPOSTAS:")
        print(f"   🔵 Original: {results['original']['response'][:100]}...")
        print(f"   🔍 CoV: {results['cov']['response'][:100]}...")
        
        return results
    
    def run_experiment(self, test_cases: List[str], experiment_name: str) -> str:
        """Executa experimento completo com múltiplos casos de teste"""
        
        print(f"🎯 INICIANDO EXPERIMENTO: {experiment_name}")
        print(f"📋 Casos de teste: {len(test_cases)}")
        
        session = ExperimentSession(experiment_name, self.logger)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{'='*20} CASO {i}/{len(test_cases)} {'='*20}")
            
            try:
                results = self.run_single_comparison(test_case)
                
                # Adiciona métricas à sessão
                if results["original"]["success"]:
                    session.add_original_metric(results["original"]["metric"])
                
                if results["cov"]["success"]:
                    session.add_cov_metric(results["cov"]["metric"])
                
                # Pausa entre testes para evitar rate limiting
                time.sleep(1)
                
            except Exception as e:
                print(f"❌ Erro no caso de teste {i}: {str(e)}")
        
        # Finaliza experimento
        comparison_file = session.finalize_experiment()
        
        print("\n🏁 EXPERIMENTO CONCLUÍDO!")
        print(f"📊 Arquivo de comparação: {comparison_file}")
        
        return comparison_file


def get_default_test_cases() -> List[str]:
    """Retorna casos de teste padrão para comparação"""
    return [
        # Casos com parâmetros completos
        "Agendar reunião sobre vendas para 2024-01-15 às 14:00 na Conference Room",
        "Gerar orçamento para 1000 folhas de papel A4 120gsm",
        "Sugerir pegadinha no Dwight tipo desk com orçamento de $20",
        
        # Casos com parâmetros incompletos
        "Preciso agendar uma reunião sobre vendas",
        "Quanto custa papel A4?",
        "Quero fazer uma pegadinha no Dwight",
        
        # Casos sem função
        "Quem é o Michael Scott?",
        "Como está o time de vendas hoje?",
        "Qual é a política de feriados da empresa?",
        
        # Casos complexos
        "Agendar reunião urgente sobre o budget Q4 amanhã de manhã",
        "Preciso de papel para impressão em massa, barato mas qualidade boa"
    ]


if __name__ == "__main__":
    try:
        print("🚀 SISTEMA DE COMPARAÇÃO DUNDEROPS")
        print("=" * 50)
        
        runner = ComparisonRunner()
        test_cases = get_default_test_cases()
        
        # Executa experimento padrão
        experiment_file = runner.run_experiment(test_cases, "baseline_comparison")
        
        print("\n🎉 Comparação concluída!")
        print(f"📄 Relatório salvo em: {experiment_file}")
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {str(e)}")
        print("💡 Configure a variável OPENAI_API_KEY para executar comparações")
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")
