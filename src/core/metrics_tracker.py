"""
Sistema de rastreamento de métricas para comparação de implementações
"""

import time
import uuid
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from datetime import datetime


@dataclass
class MetricData:
    """Estrutura para armazenar métricas de uma execução"""
    
    # Identificação
    execution_id: str
    timestamp: str
    implementation_type: str  # "original" ou "chain_of_verification"
    
    # Input/Output
    user_input: str
    final_response: str = ""
    function_called: Optional[str] = None
    function_params: Optional[Dict[str, Any]] = None
    function_result: Optional[Any] = None
    
    # Métricas de Performance
    total_latency_ms: float = 0.0
    api_calls_count: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    
    # Métricas de Qualidade
    validation_passed: bool = False
    has_function_call: bool = False
    response_complete: bool = True
    
    # Métricas específicas do Chain of Verification
    verification_used: bool = False
    verification_latency_ms: float = 0.0
    verification_tokens: int = 0
    correction_made: bool = False
    
    # Detalhes adicionais
    error_occurred: bool = False
    error_message: Optional[str] = None
    additional_metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário para serialização"""
        return asdict(self)


class MetricsTracker:
    """Classe para rastrear métricas durante execuções"""
    
    def __init__(self, implementation_type: str):
        self.implementation_type = implementation_type
        self.current_metric: Optional[MetricData] = None
        self.start_time: Optional[float] = None
        
    def start_execution(self, user_input: str) -> str:
        """
        Inicia o rastreamento de uma nova execução
        
        Args:
            user_input: Input do usuário
            
        Returns:
            execution_id: ID único da execução
        """
        execution_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        self.current_metric = MetricData(
            execution_id=execution_id,
            timestamp=timestamp,
            implementation_type=self.implementation_type,
            user_input=user_input
        )
        
        self.start_time = time.time()
        
        print(f"📊 [MetricsTracker] Iniciando rastreamento - ID: {execution_id}")
        return execution_id
    
    def track_api_call(self, input_tokens: int, output_tokens: int):
        """
        Registra uma chamada de API
        
        Args:
            input_tokens: Tokens de entrada
            output_tokens: Tokens de saída
        """
        if not self.current_metric:
            print("⚠️ [MetricsTracker] Nenhuma execução ativa para rastrear API call")
            return
            
        self.current_metric.api_calls_count += 1
        self.current_metric.total_input_tokens += input_tokens
        self.current_metric.total_output_tokens += output_tokens
        self.current_metric.total_tokens += (input_tokens + output_tokens)
        
        print(f"📞 [MetricsTracker] API call #{self.current_metric.api_calls_count} - "
              f"Tokens: {input_tokens} in / {output_tokens} out")
    
    def track_function_call(self, function_name: str, params: Dict[str, Any], 
                           result: Any, validation_passed: bool):
        """
        Registra uma chamada de função
        
        Args:
            function_name: Nome da função chamada
            params: Parâmetros da função
            result: Resultado da função
            validation_passed: Se a validação passou
        """
        if not self.current_metric:
            print("⚠️ [MetricsTracker] Nenhuma execução ativa para rastrear function call")
            return
            
        self.current_metric.function_called = function_name
        self.current_metric.function_params = params
        self.current_metric.function_result = result
        self.current_metric.validation_passed = validation_passed
        self.current_metric.has_function_call = True
        
        print(f"🔧 [MetricsTracker] Função chamada: {function_name} - "
              f"Validação: {'✅' if validation_passed else '❌'}")
    
    def start_verification_phase(self):
        """Marca o início da fase de verificação (Chain of Verification)"""
        if not self.current_metric:
            return
            
        self.current_metric.verification_used = True
        self.verification_start_time = time.time()
        print("🔍 [MetricsTracker] Iniciando fase de verificação")
    
    def end_verification_phase(self, verification_tokens: int, correction_made: bool):
        """
        Marca o fim da fase de verificação
        
        Args:
            verification_tokens: Tokens usados na verificação
            correction_made: Se uma correção foi feita
        """
        if not self.current_metric or not hasattr(self, 'verification_start_time'):
            return
            
        verification_time = time.time() - self.verification_start_time
        self.current_metric.verification_latency_ms = verification_time * 1000
        self.current_metric.verification_tokens = verification_tokens
        self.current_metric.correction_made = correction_made
        
        print(f"✅ [MetricsTracker] Verificação concluída - "
              f"Tempo: {verification_time*1000:.2f}ms - "
              f"Correção: {'✅' if correction_made else '❌'}")
    
    def track_error(self, error_message: str):
        """
        Registra um erro durante a execução
        
        Args:
            error_message: Mensagem de erro
        """
        if not self.current_metric:
            return
            
        self.current_metric.error_occurred = True
        self.current_metric.error_message = error_message
        self.current_metric.response_complete = False
        
        print(f"❌ [MetricsTracker] Erro registrado: {error_message}")
    
    def end_execution(self, final_response: str, 
                     additional_metadata: Optional[Dict[str, Any]] = None) -> MetricData:
        """
        Finaliza o rastreamento e retorna os dados coletados
        
        Args:
            final_response: Resposta final gerada
            additional_metadata: Metadados adicionais
            
        Returns:
            MetricData: Dados coletados da execução
        """
        if not self.current_metric or not self.start_time:
            raise ValueError("Nenhuma execução ativa para finalizar")
            
        # Calcula latência total
        total_time = time.time() - self.start_time
        self.current_metric.total_latency_ms = total_time * 1000
        
        # Armazena resposta final e metadados
        self.current_metric.final_response = final_response
        self.current_metric.additional_metadata = additional_metadata or {}
        
        # Verifica se a resposta está completa (heurística simples)
        if len(final_response.strip()) < 10:
            self.current_metric.response_complete = False
        
        print(f"🏁 [MetricsTracker] Execução finalizada - "
              f"Tempo total: {total_time*1000:.2f}ms - "
              f"Tokens: {self.current_metric.total_tokens}")
        
        # Retorna uma cópia dos dados
        result = MetricData(**asdict(self.current_metric))
        
        # Reset para próxima execução
        self.current_metric = None
        self.start_time = None
        
        return result
    
    def get_current_metrics(self) -> Optional[Dict[str, Any]]:
        """Retorna as métricas atuais (para debug)"""
        if not self.current_metric:
            return None
        return self.current_metric.to_dict()


class MetricsAnalyzer:
    """Classe para analisar e comparar métricas coletadas"""
    
    @staticmethod
    def compare_implementations(original_metrics: List[MetricData], 
                              cov_metrics: List[MetricData]) -> Dict[str, Any]:
        """
        Compara métricas entre implementações
        
        Args:
            original_metrics: Métricas da implementação original
            cov_metrics: Métricas da implementação com Chain of Verification
            
        Returns:
            Relatório de comparação
        """
        def calculate_avg(metrics: List[MetricData], field: str) -> float:
            values = [getattr(m, field) for m in metrics if hasattr(m, field)]
            return sum(values) / len(values) if values else 0.0
        
        def calculate_success_rate(metrics: List[MetricData]) -> float:
            if not metrics:
                return 0.0
            successful = sum(1 for m in metrics if not m.error_occurred and m.response_complete)
            return (successful / len(metrics)) * 100
        
        comparison = {
            "summary": {
                "original_executions": len(original_metrics),
                "cov_executions": len(cov_metrics),
                "timestamp": datetime.now().isoformat()
            },
            "latency": {
                "original_avg_ms": calculate_avg(original_metrics, "total_latency_ms"),
                "cov_avg_ms": calculate_avg(cov_metrics, "total_latency_ms"),
                "improvement_factor": None
            },
            "tokens": {
                "original_avg_total": calculate_avg(original_metrics, "total_tokens"),
                "cov_avg_total": calculate_avg(cov_metrics, "total_tokens"),
                "cov_avg_verification": calculate_avg(cov_metrics, "verification_tokens"),
                "efficiency_ratio": None
            },
            "quality": {
                "original_success_rate": calculate_success_rate(original_metrics),
                "cov_success_rate": calculate_success_rate(cov_metrics),
                "cov_correction_rate": None
            }
        }
        
        # Calcula fatores de melhoria
        if comparison["latency"]["original_avg_ms"] > 0:
            comparison["latency"]["improvement_factor"] = (
                comparison["latency"]["cov_avg_ms"] / comparison["latency"]["original_avg_ms"]
            )
        
        if comparison["tokens"]["original_avg_total"] > 0:
            comparison["tokens"]["efficiency_ratio"] = (
                comparison["tokens"]["cov_avg_total"] / comparison["tokens"]["original_avg_total"]
            )
        
        if cov_metrics:
            corrections_made = sum(1 for m in cov_metrics if m.correction_made)
            comparison["quality"]["cov_correction_rate"] = (corrections_made / len(cov_metrics)) * 100
        
        return comparison
    
    @staticmethod
    def generate_report(comparison: Dict[str, Any]) -> str:
        """Gera um relatório legível da comparação"""
        report = []
        report.append("📊 RELATÓRIO DE COMPARAÇÃO - ORIGINAL vs CHAIN OF VERIFICATION")
        report.append("=" * 70)
        
        # Resumo
        summary = comparison["summary"]
        report.append("\n📈 RESUMO:")
        report.append(f"   • Execuções Original: {summary['original_executions']}")
        report.append(f"   • Execuções CoV: {summary['cov_executions']}")
        report.append(f"   • Data: {summary['timestamp'][:19]}")
        
        # Latência
        latency = comparison["latency"]
        report.append("\n⏱️ LATÊNCIA:")
        report.append(f"   • Original: {latency['original_avg_ms']:.2f}ms")
        report.append(f"   • CoV: {latency['cov_avg_ms']:.2f}ms")
        if latency["improvement_factor"]:
            factor = latency["improvement_factor"]
            change = "mais lenta" if factor > 1 else "mais rápida"
            report.append(f"   • CoV é {abs(factor-1)*100:.1f}% {change}")
        
        # Tokens
        tokens = comparison["tokens"]
        report.append("\n🔤 TOKENS:")
        report.append(f"   • Original (média): {tokens['original_avg_total']:.0f}")
        report.append(f"   • CoV (média): {tokens['cov_avg_total']:.0f}")
        report.append(f"   • CoV verificação: {tokens['cov_avg_verification']:.0f}")
        if tokens["efficiency_ratio"]:
            ratio = tokens["efficiency_ratio"]
            report.append(f"   • CoV usa {ratio:.2f}x mais tokens")
        
        # Qualidade
        quality = comparison["quality"]
        report.append("\n✅ QUALIDADE:")
        report.append(f"   • Taxa sucesso Original: {quality['original_success_rate']:.1f}%")
        report.append(f"   • Taxa sucesso CoV: {quality['cov_success_rate']:.1f}%")
        if quality["cov_correction_rate"] is not None:
            report.append(f"   • CoV fez correções: {quality['cov_correction_rate']:.1f}%")
        
        return "\n".join(report)
