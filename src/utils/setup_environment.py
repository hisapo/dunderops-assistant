"""
Script de configuração e verificação do ambiente DunderOps
"""

import os
import json
import sys
from pathlib import Path


class EnvironmentChecker:
    """Verifica e configura o ambiente necessário"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.project_root = Path(__file__).parent
    
    def check_python_version(self) -> bool:
        """Verifica versão do Python"""
        major, minor = sys.version_info[:2]
        
        if major < 3 or (major == 3 and minor < 8):
            self.errors.append(f"Python 3.8+ requerido, encontrado {major}.{minor}")
            return False
        
        print(f"✅ Python {major}.{minor} - OK")
        return True
    
    def check_required_files(self) -> bool:
        """Verifica se arquivos necessários existem"""
        required_files = [
            "prompts.json",
            "manifest.json", 
            "functions.py",
            "test_cases.json",
            "requirements.txt"
        ]
        
        missing_files = []
        for file in required_files:
            if not (self.project_root / file).exists():
                missing_files.append(file)
        
        if missing_files:
            self.errors.append(f"Arquivos faltando: {', '.join(missing_files)}")
            return False
        
        print("✅ Arquivos necessários - OK")
        return True
    
    def check_directories(self) -> bool:
        """Verifica e cria diretórios necessários"""
        required_dirs = [
            "experiments",
            "experiments/raw_data",
            "experiments/comparisons", 
            "experiments/reports"
        ]
        
        created_dirs = []
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if not full_path.exists():
                full_path.mkdir(parents=True, exist_ok=True)
                created_dirs.append(dir_path)
        
        if created_dirs:
            print(f"📁 Diretórios criados: {', '.join(created_dirs)}")
        
        print("✅ Estrutura de diretórios - OK")
        return True
    
    def check_api_key(self) -> bool:
        """Verifica configuração da API key"""
        api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            self.warnings.append("OPENAI_API_KEY não configurada - comparações reais não funcionarão")
            print("⚠️ OPENAI_API_KEY não configurada")
            return False
        
        if not api_key.startswith("sk-"):
            self.warnings.append("OPENAI_API_KEY parece inválida")
            print("⚠️ OPENAI_API_KEY parece inválida")
            return False
        
        print("✅ OPENAI_API_KEY configurada - OK")
        return True
    
    def check_json_files(self) -> bool:
        """Verifica se arquivos JSON são válidos"""
        json_files = ["prompts.json", "manifest.json", "test_cases.json"]
        
        for file_name in json_files:
            file_path = self.project_root / file_name
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    json.load(f)
                print(f"✅ {file_name} - JSON válido")
            except json.JSONDecodeError as e:
                self.errors.append(f"{file_name}: JSON inválido - {str(e)}")
                return False
            except FileNotFoundError:
                self.errors.append(f"{file_name}: Arquivo não encontrado")
                return False
        
        return True
    
    def check_test_cases_structure(self) -> bool:
        """Verifica estrutura dos casos de teste"""
        try:
            with open(self.project_root / "test_cases.json", 'r', encoding='utf-8') as f:
                test_data = json.load(f)
            
            required_sections = ["test_suite_info", "test_cases", "evaluation_criteria"]
            for section in required_sections:
                if section not in test_data:
                    self.errors.append(f"test_cases.json: Seção '{section}' faltando")
                    return False
            
            # Verifica categorias
            required_categories = ["complete_params", "incomplete_params", "direct_responses", "edge_cases", "complex_scenarios"]
            test_cases = test_data.get("test_cases", {})
            
            for category in required_categories:
                if category not in test_cases:
                    self.warnings.append(f"Categoria de teste '{category}' faltando")
                elif not test_cases[category].get("cases"):
                    self.warnings.append(f"Categoria '{category}' sem casos de teste")
            
            print("✅ Estrutura de casos de teste - OK")
            return True
            
        except Exception as e:
            self.errors.append(f"Erro ao verificar test_cases.json: {str(e)}")
            return False
    
    def check_imports(self) -> bool:
        """Verifica se imports principais funcionam"""
        try:
            # Testa imports locais essenciais
            modules_to_test = [
                "prompt_config",
                "function_validator", 
                "metrics_tracker",
                "chain_of_verification"
            ]
            
            for module_name in modules_to_test:
                try:
                    __import__(module_name)
                except ImportError as e:
                    self.errors.append(f"Módulo {module_name} não encontrado: {str(e)}")
                    return False
            
            print("✅ Imports locais - OK")
            
            # Testa imports externos críticos
            try:
                __import__("openai")
                print("✅ OpenAI library - OK")
            except ImportError:
                self.errors.append("OpenAI library não instalada - execute 'pip install openai'")
                return False
            
            try:
                __import__("abstra.forms")
                print("✅ Abstra forms - OK")
            except ImportError:
                self.warnings.append("Abstra forms não disponível - UIs não funcionarão")
            
            return True
            
        except Exception as e:
            self.errors.append(f"Erro de import: {str(e)}")
            return False
    
    def generate_sample_env_file(self) -> None:
        """Gera arquivo .env de exemplo"""
        env_content = """# Configuração do DunderOps Assistant
# Copie este arquivo para .env e configure suas chaves

# API Key da OpenAI (obrigatória para comparações reais)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Configurações opcionais
DEBUG=false
LOG_LEVEL=info
"""
        
        env_example_path = self.project_root / ".env.example"
        with open(env_example_path, 'w', encoding='utf-8') as f:
            f.write(env_content)
        
        print(f"📝 Arquivo de exemplo criado: {env_example_path}")
    
    def run_full_check(self) -> bool:
        """Executa verificação completa"""
        print("🔍 VERIFICAÇÃO DO AMBIENTE DUNDEROPS")
        print("=" * 50)
        
        all_good = True
        
        # Verificações críticas
        all_good &= self.check_python_version()
        all_good &= self.check_required_files()
        all_good &= self.check_directories()
        all_good &= self.check_json_files()
        all_good &= self.check_test_cases_structure()
        all_good &= self.check_imports()
        
        # Verificações não-críticas
        self.check_api_key()
        
        # Gera arquivo de exemplo se não existir
        if not (self.project_root / ".env.example").exists():
            self.generate_sample_env_file()
        
        # Resumo
        print("\n" + "=" * 50)
        print("📊 RESUMO DA VERIFICAÇÃO")
        
        if self.errors:
            print(f"\n❌ ERROS ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️ AVISOS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if all_good and not self.errors:
            print("\n✅ AMBIENTE CONFIGURADO CORRETAMENTE!")
            print("🚀 Pronto para executar comparações")
        else:
            print("\n❌ PROBLEMAS ENCONTRADOS")
            print("🔧 Corrija os erros antes de continuar")
        
        return all_good and not self.errors


class QuickSetup:
    """Configuração rápida para novos usuários"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
    
    def install_requirements(self) -> bool:
        """Instala dependências"""
        import subprocess
        
        print("📦 Instalando dependências...")
        try:
            result = subprocess.run([
                sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Dependências instaladas com sucesso")
                return True
            else:
                print(f"❌ Erro ao instalar dependências: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao instalar dependências: {str(e)}")
            return False
    
    def setup_api_key_interactive(self) -> None:
        """Configuração interativa da API key"""
        print("\n🔑 CONFIGURAÇÃO DA API KEY")
        print("=" * 30)
        
        if os.environ.get("OPENAI_API_KEY"):
            print("✅ OPENAI_API_KEY já configurada")
            return
        
        print("Para usar comparações reais, você precisa de uma API Key da OpenAI")
        print("1. Acesse: https://platform.openai.com/api-keys")
        print("2. Crie uma nova API key")
        print("3. Configure a variável de ambiente:")
        print()
        
        if sys.platform == "win32":
            print("   Windows:")
            print("   set OPENAI_API_KEY=sk-your-key-here")
        else:
            print("   Linux/Mac:")
            print("   export OPENAI_API_KEY=sk-your-key-here")
        
        print("\nOu adicione ao arquivo .env:")
        print("   OPENAI_API_KEY=sk-your-key-here")
    
    def show_next_steps(self) -> None:
        """Mostra próximos passos"""
        print("\n🎯 PRÓXIMOS PASSOS")
        print("=" * 20)
        print("1. Configure OPENAI_API_KEY (se ainda não fez)")
        print("2. Execute demos:")
        print("   python metrics_demo.py")
        print("   python cov_demo.py")
        print("3. Execute testes automatizados:")
        print("   python tests/automated_test_runner.py")
        print("4. Execute comparação completa:")
        print("   python tests/comparison_runner.py")
        print("5. Acesse interfaces:")
        print("   python form_ui.py (original)")
        print("   python form_ui_cov.py (chain of verification)")


def main():
    """Função principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuração do ambiente DunderOps")
    parser.add_argument("--install", action="store_true", help="Instala dependências")
    parser.add_argument("--setup", action="store_true", help="Configuração interativa completa")
    parser.add_argument("--check-only", action="store_true", help="Apenas verifica o ambiente")
    
    args = parser.parse_args()
    
    if args.setup:
        print("🚀 CONFIGURAÇÃO COMPLETA DO DUNDEROPS")
        print("=" * 40)
        
        setup = QuickSetup()
        
        # Instala dependências
        if args.install or input("Instalar dependências? (s/N): ").lower() == 's':
            setup.install_requirements()
        
        # Verifica ambiente
        checker = EnvironmentChecker()
        checker.run_full_check()
        
        # Configuração da API key
        setup.setup_api_key_interactive()
        
        # Próximos passos
        setup.show_next_steps()
        
    elif args.install:
        setup = QuickSetup()
        setup.install_requirements()
        
    else:
        # Verificação padrão
        checker = EnvironmentChecker()
        success = checker.run_full_check()
        
        if not success:
            sys.exit(1)


if __name__ == "__main__":
    main()
