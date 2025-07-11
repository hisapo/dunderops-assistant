"""
Sistema de logging para experimentos de comparação entre implementações
"""

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from .metrics_tracker import MetricData, MetricsAnalyzer


class ExperimentLogger:
    """Classe para salvar e carregar resultados de experimentos"""
    
    def __init__(self, experiments_dir: str = "experiments"):
        """
        Inicializa o logger de experimentos
        
        Args:
            experiments_dir: Diretório onde salvar os experimentos
        """
        self.experiments_dir = Path(experiments_dir)
        self.experiments_dir.mkdir(exist_ok=True)
        
        # Cria subdiretórios se não existirem
        (self.experiments_dir / "raw_data").mkdir(exist_ok=True)
        (self.experiments_dir / "comparisons").mkdir(exist_ok=True)
        (self.experiments_dir / "reports").mkdir(exist_ok=True)
        
        print(f"📁 [ExperimentLogger] Diretório configurado: {self.experiments_dir}")
    
    def save_metrics(self, metrics: List[MetricData], 
                    implementation_type: str, 
                    experiment_name: Optional[str] = None) -> str:
        """
        Salva métricas brutas de uma implementação
        
        Args:
            metrics: Lista de métricas coletadas
            implementation_type: Tipo da implementação ("original" ou "cov")
            experiment_name: Nome do experimento (opcional)
            
        Returns:
            Caminho do arquivo salvo
        """
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"experiment_{timestamp}"
        
        filename = f"{experiment_name}_{implementation_type}_metrics.json"
        filepath = self.experiments_dir / "raw_data" / filename
        
        # Converte métricas para dicionário serializável
        data = {
            "experiment_name": experiment_name,
            "implementation_type": implementation_type,
            "timestamp": datetime.now().isoformat(),
            "total_executions": len(metrics),
            "metrics": [metric.to_dict() for metric in metrics]
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 [ExperimentLogger] Métricas salvas: {filepath}")
        return str(filepath)
    
    def load_metrics(self, filepath: str) -> List[MetricData]:
        """
        Carrega métricas de um arquivo
        
        Args:
            filepath: Caminho do arquivo
            
        Returns:
            Lista de métricas carregadas
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metrics = []
        for metric_dict in data["metrics"]:
            # Reconstrói o objeto MetricData
            metric = MetricData(**metric_dict)
            metrics.append(metric)
        
        print(f"📂 [ExperimentLogger] Métricas carregadas: {len(metrics)} execuções")
        return metrics
    
    def save_comparison(self, original_metrics: List[MetricData], 
                       cov_metrics: List[MetricData],
                       experiment_name: Optional[str] = None) -> str:
        """
        Salva uma comparação completa entre implementações
        
        Args:
            original_metrics: Métricas da implementação original
            cov_metrics: Métricas da implementação CoV
            experiment_name: Nome do experimento
            
        Returns:
            Caminho do arquivo de comparação salvo
        """
        if not experiment_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            experiment_name = f"comparison_{timestamp}"
        
        # Gera comparação usando o analyzer
        comparison = MetricsAnalyzer.compare_implementations(original_metrics, cov_metrics)
        
        # Adiciona dados brutos
        comparison_data = {
            "experiment_name": experiment_name,
            "timestamp": datetime.now().isoformat(),
            "comparison": comparison,
            "raw_data": {
                "original_metrics": [m.to_dict() for m in original_metrics],
                "cov_metrics": [m.to_dict() for m in cov_metrics]
            }
        }
        
        # Salva comparação
        comparison_file = self.experiments_dir / "comparisons" / f"{experiment_name}.json"
        with open(comparison_file, 'w', encoding='utf-8') as f:
            json.dump(comparison_data, f, indent=2, ensure_ascii=False)
        
        # Gera e salva relatório legível
        report = MetricsAnalyzer.generate_report(comparison)
        report_file = self.experiments_dir / "reports" / f"{experiment_name}_report.txt"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📊 [ExperimentLogger] Comparação salva: {comparison_file}")
        print(f"📄 [ExperimentLogger] Relatório salvo: {report_file}")
        
        return str(comparison_file)
    
    def load_comparison(self, filepath: str) -> Dict[str, Any]:
        """
        Carrega uma comparação salva
        
        Args:
            filepath: Caminho do arquivo de comparação
            
        Returns:
            Dados da comparação
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def list_experiments(self) -> Dict[str, List[str]]:
        """
        Lista todos os experimentos salvos
        
        Returns:
            Dicionário com listas de arquivos por categoria
        """
        result = {
            "raw_metrics": [],
            "comparisons": [],
            "reports": []
        }
        
        # Lista métricas brutas
        raw_dir = self.experiments_dir / "raw_data"
        if raw_dir.exists():
            result["raw_metrics"] = [f.name for f in raw_dir.glob("*.json")]
        
        # Lista comparações
        comp_dir = self.experiments_dir / "comparisons"
        if comp_dir.exists():
            result["comparisons"] = [f.name for f in comp_dir.glob("*.json")]
        
        # Lista relatórios
        report_dir = self.experiments_dir / "reports"
        if report_dir.exists():
            result["reports"] = [f.name for f in report_dir.glob("*.txt")]
        
        return result
    
    def get_experiment_summary(self) -> str:
        """
        Gera um resumo de todos os experimentos
        
        Returns:
            String com resumo dos experimentos
        """
        experiments = self.list_experiments()
        
        summary = []
        summary.append("📚 RESUMO DOS EXPERIMENTOS")
        summary.append("=" * 40)
        summary.append(f"📊 Métricas brutas: {len(experiments['raw_metrics'])}")
        summary.append(f"⚖️ Comparações: {len(experiments['comparisons'])}")
        summary.append(f"📄 Relatórios: {len(experiments['reports'])}")
        summary.append("")
        
        if experiments["comparisons"]:
            summary.append("🔍 COMPARAÇÕES DISPONÍVEIS:")
            for comp in sorted(experiments["comparisons"]):
                summary.append(f"   • {comp}")
        
        return "\n".join(summary)
    
    def cleanup_old_experiments(self, days_old: int = 30) -> int:
        """
        Remove experimentos antigos
        
        Args:
            days_old: Idade em dias para considerar "antigo"
            
        Returns:
            Número de arquivos removidos
        """
        import time
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        removed_count = 0
        
        for directory in [self.experiments_dir / "raw_data", 
                         self.experiments_dir / "comparisons",
                         self.experiments_dir / "reports"]:
            if directory.exists():
                for file_path in directory.glob("*"):
                    if file_path.stat().st_mtime < cutoff_time:
                        file_path.unlink()
                        removed_count += 1
        
        print(f"🧹 [ExperimentLogger] Removidos {removed_count} arquivos antigos")
        return removed_count


class ExperimentSession:
    """Classe para gerenciar uma sessão de experimento completa"""
    
    def __init__(self, experiment_name: str, logger: ExperimentLogger):
        """
        Inicializa uma sessão de experimento
        
        Args:
            experiment_name: Nome do experimento
            logger: Instance do ExperimentLogger
        """
        self.experiment_name = experiment_name
        self.logger = logger
        self.original_metrics: List[MetricData] = []
        self.cov_metrics: List[MetricData] = []
        self.start_time = datetime.now()
        
        print(f"🎯 [ExperimentSession] Iniciando experimento: {experiment_name}")
    
    def add_original_metric(self, metric: MetricData):
        """Adiciona uma métrica da implementação original"""
        self.original_metrics.append(metric)
        print(f"📈 [ExperimentSession] Métrica original adicionada "
              f"({len(self.original_metrics)} total)")
    
    def add_cov_metric(self, metric: MetricData):
        """Adiciona uma métrica da implementação CoV"""
        self.cov_metrics.append(metric)
        print(f"🔍 [ExperimentSession] Métrica CoV adicionada "
              f"({len(self.cov_metrics)} total)")
    
    def finalize_experiment(self) -> str:
        """
        Finaliza o experimento e salva todos os dados
        
        Returns:
            Caminho do arquivo de comparação gerado
        """
        duration = datetime.now() - self.start_time
        
        print(f"🏁 [ExperimentSession] Finalizando experimento {self.experiment_name}")
        print(f"   • Duração: {duration}")
        print(f"   • Métricas originais: {len(self.original_metrics)}")
        print(f"   • Métricas CoV: {len(self.cov_metrics)}")
        
        # Salva métricas brutas
        if self.original_metrics:
            self.logger.save_metrics(
                self.original_metrics, "original", self.experiment_name
            )
        
        if self.cov_metrics:
            self.logger.save_metrics(
                self.cov_metrics, "cov", self.experiment_name
            )
        
        # Salva comparação se ambas existem
        if self.original_metrics and self.cov_metrics:
            comparison_file = self.logger.save_comparison(
                self.original_metrics, self.cov_metrics, self.experiment_name
            )
            return comparison_file
        
        print("⚠️ [ExperimentSession] Não foi possível gerar comparação - "
              "dados insuficientes")
        return ""
    
    def get_current_status(self) -> str:
        """Retorna status atual do experimento"""
        duration = datetime.now() - self.start_time
        
        return (f"🎯 Experimento: {self.experiment_name}\n"
                f"⏱️ Duração: {duration}\n"
                f"📊 Original: {len(self.original_metrics)} execuções\n"
                f"🔍 CoV: {len(self.cov_metrics)} execuções")
