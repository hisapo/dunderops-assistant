#!/usr/bin/env python3
"""
Script dedicado para avaliar o impacto do Chain of Verification (CoV)
Executa testes focados nas áreas onde CoV deve mostrar maior benefício
"""

import json
import time
import sys
from tests.automated_test_runner import AutomatedTestRunner

def main():
    """Executa avaliação focada do CoV"""
    
    print("🔬 AVALIAÇÃO ESPECÍFICA DO CHAIN OF VERIFICATION (CoV)")
    print("=" * 60)
    print("Este script avalia especificamente o impacto do CoV em:")
    print("• Cenários complexos e ambíguos")
    print("• Interpretação de contexto")
    print("• Recuperação de erros")
    print("• Verificação de consistência")
    print("• Detecção de problemas lógicos")
    print()
    
    try:
        # Inicializa o runner
        runner = AutomatedTestRunner()
        
        # Executa testes focados em CoV
        results = runner.run_cov_focused_tests()
        
        # Salva resultados específicos do CoV
        timestamp = int(time.time())
        cov_results_file = f"experiments/cov_evaluation_{timestamp}.json"
        
        # Prepara dados para serialização
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
                            "validation_passed": t.validation_passed,
                            "category": t.test_category
                        } for t in test_list
                    ]
        
        serializable_results["summary"] = results["summary"]
        serializable_results["cov_analysis"] = results["cov_analysis"]
        serializable_results["evaluation_timestamp"] = timestamp
        serializable_results["test_focus"] = "Chain of Verification Impact Assessment"
        
        with open(cov_results_file, "w", encoding="utf-8") as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        # Relatório detalhado
        print("\n" + "="*60)
        print("📋 RELATÓRIO DETALHADO DA AVALIAÇÃO CoV")
        print("="*60)
        
        cov_analysis = results["cov_analysis"]
        
        print("\n🎯 PERFORMANCE GERAL DO CoV:")
        print(f"   Score combinado de melhoria: {cov_analysis['overall_cov_improvement']:.2f}")
        print(f"   Recomendação: {cov_analysis['recommendation']}")
        
        print("\n📊 ANÁLISE POR CATEGORIA:")
        for category, analysis in cov_analysis["category_analysis"].items():
            print(f"\n   🏷️ {category}:")
            print(f"      • Score combinado: {analysis['combined_score']:.1f}")
            print(f"      • Melhoria em success rate: {analysis['success_improvement']:+.1f}%")
            print(f"      • Melhoria em qualidade: {analysis['quality_improvement']:+.1f}")
            print(f"      • Custo de eficiência: {analysis['efficiency_cost']:.1f}%")
            print(f"      • ROI (Return on Investment): {analysis['roi']:.2f}")
        
        print("\n💡 INSIGHTS PRINCIPAIS:")
        for insight in cov_analysis["key_insights"]:
            print(f"   • {insight}")
        
        print(f"\n📁 Resultados salvos em: {cov_results_file}")
        
        # Estatísticas de teste
        total_tests = sum(
            len(tests) for impl_data in results.values() 
            if isinstance(impl_data, dict) and "test_cases" not in impl_data
            for tests in impl_data.values() if isinstance(tests, list)
        ) // 3  # Divide por 3 porque temos 3 implementações
        
        print("\n📈 ESTATÍSTICAS:")
        print(f"   • Total de casos de teste executados: {total_tests}")
        print("   • Implementações comparadas: Original, CoV, Secure")
        print(f"   • Categorias avaliadas: {len(cov_analysis['category_analysis'])}")
        
        # Recomendações específicas
        print("\n🚀 PRÓXIMOS PASSOS RECOMENDADOS:")
        
        if cov_analysis["overall_cov_improvement"] > 5:
            print("   ✅ CoV demonstra benefícios significativos")
            print("   • Implemente CoV em produção")
            print("   • Monitore performance em casos reais")
            print("   • Considere otimizações para reduzir overhead")
        elif cov_analysis["overall_cov_improvement"] > 2:
            print("   ⚠️ CoV demonstra benefícios moderados")
            print("   • Use CoV seletivamente para casos complexos")
            print("   • Implemente sistema híbrido (CoV apenas quando necessário)")
            print("   • Continue otimizando a implementação")
        else:
            print("   ❌ CoV não demonstra benefícios suficientes")
            print("   • Revise a implementação do CoV")
            print("   • Analise se os casos de teste são adequados")
            print("   • Considere abordagens alternativas")
        
        print("\n🎉 Avaliação CoV concluída com sucesso!")
        
    except FileNotFoundError as e:
        print(f"❌ Erro: Arquivo não encontrado - {e}")
        print("💡 Certifique-se de que todos os arquivos de configuração estão presentes")
        sys.exit(1)
        
    except ValueError as e:
        print(f"❌ Erro de configuração: {e}")
        print("💡 Configure a variável OPENAI_API_KEY para executar os testes")
        sys.exit(1)
        
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        print("💡 Verifique os logs para mais detalhes")
        sys.exit(1)

if __name__ == "__main__":
    main()
