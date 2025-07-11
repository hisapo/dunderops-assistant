"""
Sistema de testes automatizados para DunderOps Assistant
Executa casos de teste padronizados e analisa resultados
"""

import json
import os
import sys
import time
from typing import Dict, List, Any
from dataclasses import dataclass
from openai import OpenAI

# Carrega variáveis de ambiente do .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # Se dotenv não estiver disponível, continua sem ele
    pass

# Adiciona o diretório pai ao path para imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.faithful_implementations import (
    FormUIOriginalReproduction, 
    FormUICoVReproduction, 
    FormUISecureReproduction
)
from src.core.prompt_config import PromptConfig
from src.core.function_validator import FunctionValidator
from src.core.metrics_tracker import MetricsTracker
from src.core.experiment_logger import ExperimentLogger


@dataclass
class TestResult:
    """Resultado de um teste individual"""
    test_id: str
    test_category: str
    input_text: str
    expected_function: str
    actual_response: str
    success: bool
    execution_time_ms: float
    tokens_used: int
    function_called: str
    function_params: Dict[str, Any]
    validation_passed: bool
    error_message: str
    quality_score: int  # 1-10
    notes: str


class TestEvaluator:
    """Avalia resultados de teste baseado nos critérios definidos"""
    
    def __init__(self):
        pass
    
    def evaluate_test_result(self, test_case: Dict[str, Any], 
                           actual_response: str, 
                           function_called: str,
                           function_params: Dict[str, Any],
                           validation_passed: bool) -> TestResult:
        """
        Avalia um resultado de teste
        
        Args:
            test_case: Caso de teste do JSON
            actual_response: Resposta gerada pelo sistema
            function_called: Nome da função chamada (ou None)
            function_params: Parâmetros da função
            validation_passed: Se a validação passou
            
        Returns:
            TestResult com avaliação completa
        """
        
        test_id = test_case["id"]
        category = test_case["category"]
        input_text = test_case["input"]
        expected_function = test_case.get("expected_function")
        
        # Avalia sucesso básico
        success = self._evaluate_basic_success(test_case, function_called, validation_passed)
        
        # Avalia qualidade da resposta
        quality_score = self._evaluate_quality(test_case, actual_response)
        
        # Gera notas de avaliação
        notes = self._generate_evaluation_notes(test_case, actual_response, function_called, validation_passed)
        
        return TestResult(
            test_id=test_id,
            test_category=category,
            input_text=input_text,
            expected_function=expected_function or "none",
            actual_response=actual_response,
            success=success,
            execution_time_ms=0.0,  # Será preenchido pelo runner
            tokens_used=0,  # Será preenchido pelo runner
            function_called=function_called or "none",
            function_params=function_params or {},
            validation_passed=validation_passed,
            error_message="",
            quality_score=quality_score,
            notes=notes
        )
    
    def _evaluate_basic_success(self, test_case: Dict[str, Any], 
                               function_called: str, 
                               validation_passed: bool) -> bool:
        """Avalia se o teste passou nos critérios básicos"""
        
        expected_function = test_case.get("expected_function")
        expected_success = test_case.get("expected_success", True)
        
        # Casos que não devem chamar função
        if expected_function is None:
            return function_called is None
        
        # Casos que devem falhar (parâmetros incompletos)
        if not expected_success:
            return not validation_passed
        
        # Casos que devem ter sucesso
        if expected_success:
            return (function_called == expected_function and validation_passed)
        
        return False
    
    def _evaluate_quality(self, test_case: Dict[str, Any], response: str) -> int:
        """Avalia qualidade da resposta (1-10) com critérios expandidos"""
        score = 5  # Baseline
        
        if not response or len(response.strip()) < 10:
            return 1
        
        # Verifica humor (The Office)
        if test_case.get("should_be_humorous", False):
            humor_indicators = ["😄", "😂", "🙄", "Michael", "Dwight", "Jim", "Scranton", "Stanley", "Kevin", "Pam"]
            if any(indicator in response for indicator in humor_indicators):
                score += 1
        
        # Verifica se contém termos esperados
        should_mention = test_case.get("should_mention", [])
        if should_mention:
            mentions = sum(1 for term in should_mention if term.lower() in response.lower())
            score += min(2, mentions)
        
        # Verifica se contém humor quando deveria
        if test_case.get("should_contain_humor", False):
            humor_phrases = ["adivinho", "bola de cristal", "mágico", "Stanley", "Kevin", "Creed", "Michael", "assistente"]
            if any(phrase in response for phrase in humor_phrases):
                score += 2
        
        # Verifica completude da resposta
        if len(response) > 100:
            score += 1
        
        # Verifica se não alucina parâmetros
        if "parâmetros" in response.lower() or "informações" in response.lower():
            score += 1
            
        # Novos critérios para CoV
        
        # Verifica detecção de erros lógicos
        if test_case.get("error_type"):
            error_detection_phrases = ["inválido", "impossível", "não existe", "erro", "problema", "incorreto"]
            if any(phrase in response.lower() for phrase in error_detection_phrases):
                score += 2
        
        # Verifica interpretação de contexto
        context_clues = test_case.get("context_clues", [])
        if context_clues:
            context_understanding = sum(1 for clue in context_clues 
                                      if any(word in response.lower() for word in clue.split("_")))
            score += min(2, context_understanding)
        
        # Verifica pontos de verificação específicos
        verification_points = test_case.get("verification_points", [])
        if verification_points:
            verifications_addressed = sum(1 for point in verification_points
                                        if any(word in response.lower() for word in point.split("_")))
            score += min(2, verifications_addressed)
        
        # Verifica se pede clarificação adequadamente
        if test_case.get("should_ask_clarification", False):
            clarification_phrases = ["pode especificar", "preciso saber", "qual", "quando", "onde", "como"]
            if any(phrase in response.lower() for phrase in clarification_phrases):
                score += 1
        
        # Verifica tratamento de urgência
        if test_case.get("urgency_context", False):
            urgency_phrases = ["urgente", "prioridade", "rápido", "imediato"]
            if any(phrase in response.lower() for phrase in urgency_phrases):
                score += 1
        
        # Verifica consideração de constraints
        if test_case.get("resource_constraint", False) or test_case.get("quality_paradox", False):
            constraint_phrases = ["considerando", "levando em conta", "equilibrar", "balance"]
            if any(phrase in response.lower() for phrase in constraint_phrases):
                score += 1
        
        return min(10, max(1, score))
    
    def _generate_evaluation_notes(self, test_case: Dict[str, Any], 
                                 response: str, 
                                 function_called: str,
                                 validation_passed: bool) -> str:
        """Gera notas de avaliação detalhadas com critérios expandidos"""
        notes = []
        
        expected_function = test_case.get("expected_function")
        expected_success = test_case.get("expected_success", True)
        
        # Função chamada
        if expected_function:
            if function_called == expected_function:
                notes.append("✅ Função correta chamada")
            elif function_called:
                notes.append(f"❌ Função errada: esperava {expected_function}, chamou {function_called}")
            else:
                notes.append(f"❌ Nenhuma função chamada, esperava {expected_function}")
        else:
            if function_called:
                notes.append(f"⚠️ Função inesperada chamada: {function_called}")
            else:
                notes.append("✅ Nenhuma função chamada (correto)")
        
        # Validação
        if expected_success:
            if validation_passed:
                notes.append("✅ Validação passou (esperado)")
            else:
                notes.append("❌ Validação falhou (inesperado)")
        else:
            if validation_passed:
                notes.append("⚠️ Validação passou (esperava falha)")
            else:
                notes.append("✅ Validação falhou (esperado)")
        
        # Qualidade da resposta
        if len(response) < 20:
            notes.append("⚠️ Resposta muito curta")
        
        # Verificações específicas para humor
        if test_case.get("should_contain_humor") and not any(word in response.lower() for word in ["😄", "michael", "dwight", "adivinho", "stanley"]):
            notes.append("⚠️ Falta humor esperado")
        
        # Verificações específicas para CoV
        
        # Detecção de erros
        error_type = test_case.get("error_type")
        if error_type:
            error_detected = any(phrase in response.lower() for phrase in ["inválido", "impossível", "erro", "problema"])
            if error_detected:
                notes.append(f"✅ Erro detectado: {error_type}")
            else:
                notes.append(f"❌ Erro não detectado: {error_type}")
        
        # Interpretação de contexto
        context_clues = test_case.get("context_clues", [])
        if context_clues:
            context_addressed = sum(1 for clue in context_clues 
                                  if any(word in response.lower() for word in clue.split("_")))
            if context_addressed > 0:
                notes.append(f"✅ Contexto interpretado: {context_addressed}/{len(context_clues)}")
            else:
                notes.append("❌ Contexto não interpretado")
        
        # Pontos de verificação
        verification_points = test_case.get("verification_points", [])
        if verification_points:
            verifications = sum(1 for point in verification_points
                              if any(word in response.lower() for word in point.split("_")))
            if verifications > 0:
                notes.append(f"✅ Verificações: {verifications}/{len(verification_points)}")
            else:
                notes.append("❌ Verificações insuficientes")
        
        # CoV deve melhorar
        if test_case.get("cov_should_improve", False):
            notes.append("🎯 Caso esperado para melhoria com CoV")
        
        # Urgência e contexto especial
        if test_case.get("urgency_context", False):
            urgency_handled = any(phrase in response.lower() for phrase in ["urgente", "prioridade", "rápido"])
            if urgency_handled:
                notes.append("✅ Urgência reconhecida")
            else:
                notes.append("⚠️ Urgência não reconhecida")
        
        # Clarificação adequada
        if test_case.get("should_ask_clarification", False):
            clarification_asked = any(phrase in response.lower() for phrase in ["pode especificar", "preciso saber", "qual"])
            if clarification_asked:
                notes.append("✅ Pediu clarificação adequadamente")
            else:
                notes.append("❌ Não pediu clarificação necessária")
        
        # Constraints e paradoxos
        if test_case.get("quality_paradox", False):
            paradox_handled = any(phrase in response.lower() for phrase in ["equilibrar", "balance", "considerando"])
            if paradox_handled:
                notes.append("✅ Paradoxo de qualidade reconhecido")
            else:
                notes.append("⚠️ Paradoxo não endereçado")
        
        return " | ".join(notes)


class AutomatedTestRunner:
    """Executa testes automatizados usando os casos de teste padronizados"""
    
    def __init__(self):
        self.client = self._setup_client()
        self.prompts = PromptConfig()
        self.validator = FunctionValidator(self.prompts)
        self.evaluator = TestEvaluator()
        self.logger = ExperimentLogger()
        
        # Carrega casos de teste
        with open("config/test_cases.json", "r", encoding="utf-8") as f:
            self.test_data = json.load(f)
        
        # Carrega manifest
        with open("config/manifest.json") as f:
            self.manifest = json.load(f)
        
        # Inicializa implementações fiéis aos form_ui
        self.original = FormUIOriginalReproduction(self.client, self.prompts, self.validator)
        self.cov = FormUICoVReproduction(self.client, self.prompts, self.validator)
        self.secure = FormUISecureReproduction(self.client, self.prompts, self.validator)
    
    def _setup_client(self) -> OpenAI:
        """Configura cliente OpenAI"""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY não configurada")
        return OpenAI(api_key=api_key)
    
    def run_test_case(self, test_case: Dict[str, Any], implementation: str) -> TestResult:
        """
        Executa um caso de teste específico
        
        Args:
            test_case: Caso de teste do JSON
            implementation: "original" ou "cov"
            
        Returns:
            TestResult com resultado da execução
        """
        
        user_input = test_case["input"]
        
        # Escolhe implementação
        if implementation == "original":
            impl = self.original
        elif implementation == "cov":
            impl = self.cov
        elif implementation == "secure":
            impl = self.secure
        else:
            raise ValueError(f"Implementação inválida: {implementation}")
        
        # Executa teste
        tracker = MetricsTracker(implementation)
        tracker.start_execution(user_input)
        
        try:
            response = impl.process_request(user_input, self.manifest, tracker)
            metric = tracker.end_execution(response)
            
            # Avalia resultado
            result = self.evaluator.evaluate_test_result(
                test_case=test_case,
                actual_response=response,
                function_called=metric.function_called,
                function_params=metric.function_params or {},
                validation_passed=metric.validation_passed
            )
            
            # Atualiza métricas no resultado
            result.execution_time_ms = metric.total_latency_ms
            result.tokens_used = metric.total_tokens
            
            return result
            
        except Exception as e:
            tracker.track_error(str(e))
            metric = tracker.end_execution(f"Erro: {str(e)}")
            
            # Cria resultado de erro
            result = self.evaluator.evaluate_test_result(
                test_case=test_case,
                actual_response=f"Erro: {str(e)}",
                function_called=None,
                function_params={},
                validation_passed=False
            )
            
            result.execution_time_ms = metric.total_latency_ms
            result.tokens_used = metric.total_tokens
            result.error_message = str(e)
            result.success = False
            
            return result
    
    def run_category_tests(self, category: str, implementation: str) -> List[TestResult]:
        """Executa todos os testes de uma categoria"""
        
        if category not in self.test_data["test_cases"]:
            raise ValueError(f"Categoria não encontrada: {category}")
        
        category_data = self.test_data["test_cases"][category]
        test_cases = category_data["cases"]
        
        print(f"🧪 Executando {len(test_cases)} testes da categoria '{category}' para {implementation}")
        
        results = []
        for i, test_case in enumerate(test_cases, 1):
            print(f"   Teste {i}/{len(test_cases)}: {test_case['id']}")
            
            try:
                result = self.run_test_case(test_case, implementation)
                results.append(result)
                
                status = "✅" if result.success else "❌"
                print(f"   {status} {result.quality_score}/10 - {result.execution_time_ms:.1f}ms")
                
            except Exception as e:
                print(f"   ❌ Erro: {str(e)}")
        
        return results
    
    def run_full_test_suite(self, implementation: str) -> Dict[str, List[TestResult]]:
        """Executa toda a suíte de testes"""
        
        print(f"🚀 EXECUTANDO SUÍTE COMPLETA DE TESTES - {implementation.upper()}")
        print("=" * 60)
        
        all_results = {}
        categories = list(self.test_data["test_cases"].keys())
        
        for category in categories:
            print(f"\n📂 CATEGORIA: {category}")
            print("-" * 40)
            
            try:
                results = self.run_category_tests(category, implementation)
                all_results[category] = results
                
                # Estatísticas da categoria
                total = len(results)
                successful = sum(1 for r in results if r.success)
                avg_quality = sum(r.quality_score for r in results) / total if total > 0 else 0
                avg_time = sum(r.execution_time_ms for r in results) / total if total > 0 else 0
                avg_tokens = sum(r.tokens_used for r in results) / total if total > 0 else 0
                
                print("\n📊 Resumo da categoria:")
                print(f"   • Sucessos: {successful}/{total} ({successful/total*100:.1f}%)")
                print(f"   • Qualidade média: {avg_quality:.1f}/10")
                print(f"   • Tempo médio: {avg_time:.1f}ms")
                print(f"   • Tokens médios: {avg_tokens:.0f}")
                
            except Exception as e:
                print(f"❌ Erro na categoria {category}: {str(e)}")
                all_results[category] = []
        
        # Salva resultados automaticamente com timestamp único
        self._save_test_results(all_results, implementation)
        
        return all_results
    
    def compare_implementations(self, categories: List[str] = None) -> Dict[str, Any]:
        """Compara implementações usando os casos de teste"""
        
        if categories is None:
            categories = list(self.test_data["test_cases"].keys())
        
        print("⚖️ COMPARAÇÃO ENTRE IMPLEMENTAÇÕES")
        print("=" * 50)
        
        comparison_results = {
            "original": {},
            "cov": {},
            "secure": {},
            "summary": {}
        }
        
        # Executa testes para todas as implementações
        for implementation in ["original", "cov", "secure"]:
            print(f"\n🔄 Testando implementação: {implementation}")
            
            impl_results = {}
            for category in categories:
                try:
                    results = self.run_category_tests(category, implementation)
                    impl_results[category] = results
                except Exception as e:
                    print(f"❌ Erro na categoria {category}: {str(e)}")
                    impl_results[category] = []
            
            comparison_results[implementation] = impl_results
        
        # Gera comparação
        comparison_results["summary"] = self._generate_comparison_summary(
            comparison_results["original"],
            comparison_results["cov"],
            comparison_results["secure"]
        )
        
        return comparison_results
    
    def _generate_comparison_summary(self, original_results: Dict[str, List[TestResult]], 
                                   cov_results: Dict[str, List[TestResult]],
                                   secure_results: Dict[str, List[TestResult]] = None) -> Dict[str, Any]:
        """Gera resumo da comparação expandido"""
        
        summary = {}
        
        for category in original_results.keys():
            orig_tests = original_results[category]
            cov_tests = cov_results[category]
            secure_tests = secure_results.get(category, []) if secure_results else []
            
            if not orig_tests or not cov_tests:
                continue
            
            # Métricas originais
            orig_metrics = self._calculate_metrics(orig_tests)
            cov_metrics = self._calculate_metrics(cov_tests)
            
            category_summary = {
                "original": orig_metrics,
                "cov": cov_metrics,
                "improvements": {
                    "success_rate_diff": cov_metrics["success_rate"] - orig_metrics["success_rate"],
                    "quality_diff": cov_metrics["avg_quality"] - orig_metrics["avg_quality"],
                    "time_overhead_pct": ((cov_metrics["avg_time_ms"] - orig_metrics["avg_time_ms"]) / orig_metrics["avg_time_ms"]) * 100 if orig_metrics["avg_time_ms"] > 0 else 0,
                    "token_overhead_pct": ((cov_metrics["avg_tokens"] - orig_metrics["avg_tokens"]) / orig_metrics["avg_tokens"]) * 100 if orig_metrics["avg_tokens"] > 0 else 0
                }
            }
            
            # Adiciona métricas secure se disponível
            if secure_tests:
                secure_metrics = self._calculate_metrics(secure_tests)
                category_summary["secure"] = secure_metrics
                category_summary["improvements"]["secure_vs_orig"] = {
                    "success_rate_diff": secure_metrics["success_rate"] - orig_metrics["success_rate"],
                    "quality_diff": secure_metrics["avg_quality"] - orig_metrics["avg_quality"],
                    "time_overhead_pct": ((secure_metrics["avg_time_ms"] - orig_metrics["avg_time_ms"]) / orig_metrics["avg_time_ms"]) * 100 if orig_metrics["avg_time_ms"] > 0 else 0,
                    "token_overhead_pct": ((secure_metrics["avg_tokens"] - orig_metrics["avg_tokens"]) / orig_metrics["avg_tokens"]) * 100 if orig_metrics["avg_tokens"] > 0 else 0
                }
            
            summary[category] = category_summary
        
        return summary
    
    def _calculate_metrics(self, test_results: List[TestResult]) -> Dict[str, float]:
        """Calcula métricas para uma lista de resultados de teste"""
        if not test_results:
            return {"success_rate": 0, "avg_quality": 0, "avg_time_ms": 0, "avg_tokens": 0}
        
        return {
            "success_rate": sum(1 for t in test_results if t.success) / len(test_results) * 100,
            "avg_quality": sum(t.quality_score for t in test_results) / len(test_results),
            "avg_time_ms": sum(t.execution_time_ms for t in test_results) / len(test_results),
            "avg_tokens": sum(t.tokens_used for t in test_results) / len(test_results)
        }
    
    def run_cov_focused_tests(self) -> Dict[str, Any]:
        """Executa testes focados nas categorias onde CoV deve mostrar maior benefício"""
        
        cov_focused_categories = [
            "complex_scenarios", 
            "cov_stress_tests", 
            "context_interpretation", 
            "error_recovery"
        ]
        
        print("🎯 EXECUTANDO TESTES FOCADOS EM COV")
        print("=" * 50)
        print("Categorias selecionadas para análise específica do CoV:")
        for cat in cov_focused_categories:
            if cat in self.test_data["test_cases"]:
                case_count = len(self.test_data["test_cases"][cat]["cases"])
                print(f"   • {cat}: {case_count} casos")
        print()
        
        # Executa comparação focada
        results = self.compare_implementations(categories=cov_focused_categories)
        
        # Análise específica para CoV
        cov_analysis = self._analyze_cov_performance(results)
        results["cov_analysis"] = cov_analysis
        
        return results
    
    def _analyze_cov_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa especificamente a performance do CoV vs outras implementações"""
        
        analysis = {
            "overall_cov_improvement": 0,
            "category_analysis": {},
            "key_insights": [],
            "recommendation": ""
        }
        
        total_improvements = 0
        category_count = 0
        
        for category, data in results["summary"].items():
            if "cov" not in data or "original" not in data:
                continue
                
            category_count += 1
            
            # Calcula melhorias do CoV
            success_improvement = data["improvements"]["success_rate_diff"]
            quality_improvement = data["improvements"]["quality_diff"]
            time_overhead = data["improvements"]["time_overhead_pct"]
            token_overhead = data["improvements"]["token_overhead_pct"]
            
            # Score combinado (success rate tem peso 2, quality peso 1)
            combined_improvement = (success_improvement * 2) + quality_improvement
            total_improvements += combined_improvement
            
            analysis["category_analysis"][category] = {
                "combined_score": combined_improvement,
                "success_improvement": success_improvement,
                "quality_improvement": quality_improvement,
                "efficiency_cost": (time_overhead + token_overhead) / 2,
                "roi": combined_improvement / max(1, (time_overhead + token_overhead) / 2)  # Return on Investment
            }
            
            # Insights específicos
            if success_improvement > 10:
                analysis["key_insights"].append(f"{category}: Melhoria significativa em success rate (+{success_improvement:.1f}%)")
            
            if quality_improvement > 1.0:
                analysis["key_insights"].append(f"{category}: Melhoria notável em qualidade (+{quality_improvement:.1f})")
            
            if time_overhead > 50:
                analysis["key_insights"].append(f"{category}: Alto overhead de tempo (+{time_overhead:.1f}%)")
        
        # Análise geral
        if category_count > 0:
            analysis["overall_cov_improvement"] = total_improvements / category_count
        
        # Recomendação baseada nos resultados
        if analysis["overall_cov_improvement"] > 5:
            analysis["recommendation"] = "CoV mostra melhorias substanciais - recomendado para produção"
        elif analysis["overall_cov_improvement"] > 2:
            analysis["recommendation"] = "CoV mostra melhorias moderadas - considerar para casos específicos"
        else:
            analysis["recommendation"] = "CoV mostra melhorias mínimas - reavaliar implementação"
        
        return analysis
    
    def _save_test_results(self, results: Dict[str, List[TestResult]], implementation: str):
        """Salva resultados de teste com timestamp único para evitar sobrescrita"""
        timestamp = int(time.time())
        filename = f"test_results_{implementation}_{timestamp}.json"
        filepath = f"experiments/{filename}"
        
        # Prepara dados para serialização
        serializable_results = {}
        for category, test_list in results.items():
            serializable_results[category] = [
                {
                    "test_id": t.test_id,
                    "test_category": t.test_category,
                    "input_text": t.input_text,
                    "expected_function": t.expected_function,
                    "actual_response": t.actual_response,
                    "success": t.success,
                    "execution_time_ms": t.execution_time_ms,
                    "tokens_used": t.tokens_used,
                    "function_called": t.function_called,
                    "function_params": t.function_params,
                    "validation_passed": t.validation_passed,
                    "error_message": t.error_message,
                    "quality_score": t.quality_score,
                    "notes": t.notes
                } for t in test_list
            ]
        
        # Adiciona metadados
        serializable_results["_metadata"] = {
            "implementation": implementation,
            "timestamp": timestamp,
            "execution_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
            "total_tests": sum(len(tests) for tests in results.values()),
            "categories": list(results.keys())
        }
        
        # Garante que o diretório experiments existe
        os.makedirs("experiments", exist_ok=True)
        
        # Salva arquivo
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Resultados salvos em: {filepath}")
        
        # Atualiza índice de resultados
        self._update_results_index(filename, implementation, timestamp, results)
    
    def _update_results_index(self, filename: str, implementation: str, timestamp: int, results: Dict[str, List[TestResult]]):
        """Atualiza índice de resultados para facilitar análise histórica"""
        index_file = "experiments/results_index.json"
        
        # Carrega índice existente ou cria novo
        if os.path.exists(index_file):
            with open(index_file, "r", encoding="utf-8") as f:
                index = json.load(f)
        else:
            index = {"results": [], "last_updated": None}
        
        # Calcula estatísticas resumidas
        total_tests = sum(len(tests) for tests in results.values())
        successful_tests = sum(sum(1 for t in tests if t.success) for tests in results.values())
        avg_quality = sum(sum(t.quality_score for t in tests) for tests in results.values()) / total_tests if total_tests > 0 else 0
        
        # Adiciona entrada ao índice
        entry = {
            "filename": filename,
            "implementation": implementation,
            "timestamp": timestamp,
            "execution_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
            "total_tests": total_tests,
            "successful_tests": successful_tests,
            "success_rate": (successful_tests / total_tests * 100) if total_tests > 0 else 0,
            "avg_quality": avg_quality,
            "categories": list(results.keys())
        }
        
        index["results"].append(entry)
        index["last_updated"] = timestamp
        
        # Ordena por timestamp (mais recente primeiro)
        index["results"].sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Salva índice atualizado
        with open(index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

    def _calculate_metrics(self, test_results: List[TestResult]) -> Dict[str, float]:
        """Calcula métricas para uma lista de resultados de teste"""
        if not test_results:
            return {"success_rate": 0, "avg_quality": 0, "avg_time_ms": 0, "avg_tokens": 0}
        
        return {
            "success_rate": sum(1 for t in test_results if t.success) / len(test_results) * 100,
            "avg_quality": sum(t.quality_score for t in test_results) / len(test_results),
            "avg_time_ms": sum(t.execution_time_ms for t in test_results) / len(test_results),
            "avg_tokens": sum(t.tokens_used for t in test_results) / len(test_results)
        }
    
    def run_cov_focused_tests(self) -> Dict[str, Any]:
        """Executa testes focados nas categorias onde CoV deve mostrar maior benefício"""
        
        cov_focused_categories = [
            "complex_scenarios", 
            "cov_stress_tests", 
            "context_interpretation", 
            "error_recovery"
        ]
        
        print("🎯 EXECUTANDO TESTES FOCADOS EM COV")
        print("=" * 50)
        print("Categorias selecionadas para análise específica do CoV:")
        for cat in cov_focused_categories:
            if cat in self.test_data["test_cases"]:
                case_count = len(self.test_data["test_cases"][cat]["cases"])
                print(f"   • {cat}: {case_count} casos")
        print()
        
        # Executa comparação focada
        results = self.compare_implementations(categories=cov_focused_categories)
        
        # Análise específica para CoV
        cov_analysis = self._analyze_cov_performance(results)
        results["cov_analysis"] = cov_analysis
        
        return results
    
    def _analyze_cov_performance(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa especificamente a performance do CoV vs outras implementações"""
        
        analysis = {
            "overall_cov_improvement": 0,
            "category_analysis": {},
            "key_insights": [],
            "recommendation": ""
        }
        
        total_improvements = 0
        category_count = 0
        
        for category, data in results["summary"].items():
            if "cov" not in data or "original" not in data:
                continue
                
            category_count += 1
            
            # Calcula melhorias do CoV
            success_improvement = data["improvements"]["success_rate_diff"]
            quality_improvement = data["improvements"]["quality_diff"]
            time_overhead = data["improvements"]["time_overhead_pct"]
            token_overhead = data["improvements"]["token_overhead_pct"]
            
            # Score combinado (success rate tem peso 2, quality peso 1)
            combined_improvement = (success_improvement * 2) + quality_improvement
            total_improvements += combined_improvement
            
            analysis["category_analysis"][category] = {
                "combined_score": combined_improvement,
                "success_improvement": success_improvement,
                "quality_improvement": quality_improvement,
                "efficiency_cost": (time_overhead + token_overhead) / 2,
                "roi": combined_improvement / max(1, (time_overhead + token_overhead) / 2)  # Return on Investment
            }
            
            # Insights específicos
            if success_improvement > 10:
                analysis["key_insights"].append(f"{category}: Melhoria significativa em success rate (+{success_improvement:.1f}%)")
            
            if quality_improvement > 1.0:
                analysis["key_insights"].append(f"{category}: Melhoria notável em qualidade (+{quality_improvement:.1f})")
            
            if time_overhead > 50:
                analysis["key_insights"].append(f"{category}: Alto overhead de tempo (+{time_overhead:.1f}%)")
        
        # Análise geral
        if category_count > 0:
            analysis["overall_cov_improvement"] = total_improvements / category_count
        
        # Recomendação baseada nos resultados
        if analysis["overall_cov_improvement"] > 5:
            analysis["recommendation"] = "CoV mostra melhorias substanciais - recomendado para produção"
        elif analysis["overall_cov_improvement"] > 2:
            analysis["recommendation"] = "CoV mostra melhorias moderadas - considerar para casos específicos"
        else:
            analysis["recommendation"] = "CoV mostra melhorias mínimas - reavaliar implementação"
        
        return analysis
    
def main():
    """Função principal para executar testes"""
    try:
        runner = AutomatedTestRunner()
        
        # Executa comparação completa
        results = runner.compare_implementations()
        
        # Salva resultados
        timestamp = "automated_test_" + str(int(time.time()))
        results_file = f"experiments/test_results_{timestamp}.json"
        
        with open(results_file, "w", encoding="utf-8") as f:
            # Converte TestResult para dict para serialização
            serializable_results = {}
            for impl in ["original", "cov", "secure"]:
                if impl in results:
                    serializable_results[impl] = {}
                    for category, test_list in results[impl].items():
                        serializable_results[impl][category] = [
                            {
                                "test_id": t.test_id,
                                "success": t.success,
                                "quality_score": t.quality_score,
                                "execution_time_ms": t.execution_time_ms,
                                "tokens_used": t.tokens_used,
                                "notes": t.notes,
                                "function_called": t.function_called,
                                "validation_passed": t.validation_passed
                            } for t in test_list
                        ]
            
            serializable_results["summary"] = results["summary"]
            serializable_results["test_counts"] = {
                impl: sum(len(tests) for tests in results[impl].values()) 
                for impl in ["original", "cov", "secure"] if impl in results
            }
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        print("\n🎉 Testes concluídos!")
        print(f"📄 Resultados salvos em: {results_file}")
        
        # Mostra resumo
        print("\n📊 RESUMO FINAL:")
        for category, data in results["summary"].items():
            print(f"\n🏷️ {category}:")
            orig = data["original"]
            cov = data["cov"]
            improvements = data["improvements"]
            
            print(f"   Success Rate: {orig['success_rate']:.1f}% → {cov['success_rate']:.1f}% ({improvements['success_rate_diff']:+.1f}%)")
            print(f"   Quality: {orig['avg_quality']:.1f} → {cov['avg_quality']:.1f} ({improvements['quality_diff']:+.1f})")
            print(f"   Time: +{improvements['time_overhead_pct']:.1f}% overhead")
            print(f"   Tokens: +{improvements['token_overhead_pct']:.1f}% overhead")
            
            # Mostra dados do secure se disponível
            if "secure" in data:
                secure = data["secure"]
                secure_improvements = data["improvements"]["secure_vs_orig"]
                print(f"   [SECURE] Success Rate: {secure['success_rate']:.1f}% ({secure_improvements['success_rate_diff']:+.1f}%)")
                print(f"   [SECURE] Quality: {secure['avg_quality']:.1f} ({secure_improvements['quality_diff']:+.1f})")
        
        # Estatísticas gerais
        print("\n📈 ESTATÍSTICAS GERAIS:")
        if "test_counts" in results:
            for impl, count in results["test_counts"].items():
                print(f"   {impl.upper()}: {count} testes executados")
        
        # Identifica categorias onde CoV teve maior impacto
        print("\n🎯 CATEGORIAS COM MAIOR BENEFÍCIO DO COV:")
        cov_benefits = []
        for category, data in results["summary"].items():
            if "improvements" in data:
                success_diff = data["improvements"]["success_rate_diff"]
                quality_diff = data["improvements"]["quality_diff"]
                if success_diff > 5 or quality_diff > 0.5:  # Thresholds para melhorias significativas
                    cov_benefits.append((category, success_diff, quality_diff))
        
        cov_benefits.sort(key=lambda x: x[1] + x[2], reverse=True)
        for category, success_diff, quality_diff in cov_benefits[:5]:
            print(f"   {category}: +{success_diff:.1f}% success, +{quality_diff:.1f} quality")
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {str(e)}")
        print("💡 Configure a variável OPENAI_API_KEY para executar testes")
    except Exception as e:
        print(f"❌ Erro inesperado: {str(e)}")


if __name__ == "__main__":
    import time
    main()
