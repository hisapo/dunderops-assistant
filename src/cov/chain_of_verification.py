ab"""
Implementação do Chain of Verification (CoV) para aumentar assertividade das respostas da IA
"""

import json
from typing import Dict, Any, Tuple, Optional
from openai import OpenAI
from src.core.prompt_config import PromptConfig


class ChainOfVerification:
    """
    Implementa o padrão Chain of Verification para auto-crítica e correção de respostas da IA
    
    Fluxo:
    1. Resposta Inicial: AI gera resposta baseada no input
    2. Verificação: AI analisa sua própria resposta buscando erros/melhorias
    3. Resposta Final: AI corrige ou confirma baseado na verificação
    """
    
    def __init__(self, client: OpenAI, prompts: PromptConfig):
        """
        Inicializa o sistema de Chain of Verification
        
        Args:
            client: Cliente OpenAI configurado
            prompts: Configuração de prompts
        """
        self.client = client
        self.prompts = prompts
        self.verification_prompts = self._load_verification_prompts()
    
    def _load_verification_prompts(self) -> Dict[str, str]:
        """Carrega prompts específicos para verificação"""
        return {
            "general_verification": """
Analise a resposta anterior e identifique possíveis problemas:

1. PRECISÃO: A informação está correta?
2. COMPLETUDE: Falta alguma informação importante?
3. CLAREZA: A resposta é clara e bem estruturada?
4. CONTEXTO: A resposta atende ao que foi perguntado?
5. FUNÇÕES: Se uma função foi chamada, os parâmetros estão corretos?

Responda em JSON:
{
    "has_issues": boolean,
    "issues": ["lista de problemas encontrados"],
    "suggestions": ["lista de melhorias sugeridas"],
    "severity": "low|medium|high",
    "should_regenerate": boolean
}
""",
            
            "function_verification": """
Analise especificamente a chamada de função na resposta anterior:

1. PARÂMETROS: Todos os parâmetros necessários estão presentes?
2. VALORES: Os valores dos parâmetros são apropriados?
3. CONTEXTO: A função escolhida é adequada para a pergunta?
4. VALIDAÇÃO: A resposta atende aos requisitos da função?

Responda em JSON:
{
    "function_correct": boolean,
    "missing_params": ["lista de parâmetros faltantes"],
    "invalid_params": ["lista de parâmetros inválidos"],
    "alternative_function": "nome_da_funcao_alternativa_se_aplicavel",
    "should_retry": boolean
}
""",
            
            "response_verification": """
Analise a qualidade da resposta final:

1. HUMOR: A resposta mantém o tom humorístico apropriado para The Office?
2. INFORMAÇÃO: As informações estão completas e úteis?
3. FORMATO: A resposta está bem formatada?
4. ENGAJAMENTO: A resposta é envolvente para o usuário?

Responda em JSON:
{
    "quality_score": "1-10",
    "strengths": ["pontos fortes da resposta"],
    "weaknesses": ["pontos fracos da resposta"],
    "improvements": ["melhorias específicas sugeridas"],
    "regenerate_recommended": boolean
}
"""
        }
    
    def verify_initial_response(self, user_input: str, initial_response: str, 
                              function_call: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa verificação da resposta inicial
        
        Args:
            user_input: Input original do usuário
            initial_response: Resposta inicial da AI
            function_call: Informações sobre chamada de função (se houver)
            
        Returns:
            Resultado da verificação
        """
        print("🔍 [CoV] Iniciando verificação da resposta inicial...")
        
        # Monta contexto para verificação
        verification_context = f"""
INPUT DO USUÁRIO: {user_input}

RESPOSTA INICIAL: {initial_response}
"""
        
        if function_call:
            verification_context += f"""
FUNÇÃO CHAMADA: {function_call.get('name', 'N/A')}
PARÂMETROS: {json.dumps(function_call.get('arguments', {}), indent=2)}
"""
        
        # Escolhe prompt de verificação apropriado
        if function_call:
            verification_prompt = self.verification_prompts["function_verification"]
        else:
            verification_prompt = self.verification_prompts["general_verification"]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system", 
                        "content": "Você é um crítico especializado em analisar respostas de IA. "
                                 "Seja rigoroso mas construtivo na sua análise."
                    },
                    {
                        "role": "user", 
                        "content": f"{verification_context}\n\n{verification_prompt}"
                    }
                ],
                temperature=0.3  # Baixa temperatura para análise mais consistente
            )
            
            verification_text = response.choices[0].message.content
            
            # Tenta parsear JSON
            try:
                verification_result = json.loads(verification_text)
                print(f"✅ [CoV] Verificação concluída - Issues: {verification_result.get('has_issues', False)}")
                return verification_result
            except json.JSONDecodeError:
                print("⚠️ [CoV] Erro ao parsear JSON da verificação, usando análise textual")
                return {
                    "has_issues": True,
                    "issues": ["Formato de resposta inválido"],
                    "verification_text": verification_text,
                    "should_regenerate": False
                }
                
        except Exception as e:
            print(f"❌ [CoV] Erro na verificação: {str(e)}")
            return {
                "has_issues": False,
                "error": str(e),
                "should_regenerate": False
            }
    
    def generate_corrected_response(self, user_input: str, initial_response: str, 
                                  verification_result: Dict[str, Any],
                                  function_call: Optional[Dict[str, Any]] = None) -> str:
        """
        Gera resposta corrigida baseada na verificação
        
        Args:
            user_input: Input original do usuário
            initial_response: Resposta inicial
            verification_result: Resultado da verificação
            function_call: Informações sobre chamada de função
            
        Returns:
            Resposta corrigida
        """
        print("🔧 [CoV] Gerando resposta corrigida...")
        
        # Monta prompt de correção
        correction_context = f"""
INPUT ORIGINAL: {user_input}

RESPOSTA INICIAL: {initial_response}

PROBLEMAS IDENTIFICADOS:
{json.dumps(verification_result, indent=2, ensure_ascii=False)}

Baseado nos problemas identificados, gere uma resposta melhorada que:
1. Corrija os erros apontados
2. Mantenha o tom humorístico do DunderOps Assistant
3. Seja mais precisa e completa
4. Atenda melhor ao que o usuário perguntou

Mantenha o estilo The Office e seja útil!
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": self.prompts.system_prompt
                    },
                    {
                        "role": "user",
                        "content": correction_context
                    }
                ],
                temperature=0.7  # Um pouco mais de criatividade para correção
            )
            
            corrected_response = response.choices[0].message.content
            print("✅ [CoV] Resposta corrigida gerada")
            return corrected_response
            
        except Exception as e:
            print(f"❌ [CoV] Erro ao gerar correção: {str(e)}")
            # Fallback para resposta original se houver erro
            return initial_response
    
    def process_with_verification(self, user_input: str, initial_response: str,
                                function_call: Optional[Dict[str, Any]] = None) -> Tuple[str, Dict[str, Any]]:
        """
        Processo completo de Chain of Verification
        
        Args:
            user_input: Input do usuário
            initial_response: Resposta inicial da AI
            function_call: Informações sobre chamada de função
            
        Returns:
            Tuple[str, Dict]: (resposta_final, metadados_verificacao)
        """
        print("🔍 [CoV] Iniciando Chain of Verification...")
        
        # Etapa 1: Verificação
        verification_result = self.verify_initial_response(
            user_input, initial_response, function_call
        )
        
        # Metadados da verificação
        verification_metadata = {
            "verification_performed": True,
            "verification_result": verification_result,
            "correction_applied": False,
            "verification_tokens_used": 0  # Será atualizado pelo tracker
        }
        
        # Etapa 2: Decisão de correção inteligente
        should_correct = False
        
        # Adjust logic for trivia questions
        if verification_result.get("has_issues", False):
            severity = verification_result.get("severity", "medium")
            should_regenerate = verification_result.get("should_regenerate", False)
            is_trivia = verification_result.get("context", {}).get("type") == "trivia"

            # System threshold for trivia questions
            correction_threshold = self._get_correction_threshold(function_call)

            # Elevate severity for trivia with unmet criteria
            if is_trivia:
                unmet_criteria = verification_result.get("unmet_criteria", [])
                if unmet_criteria:
                    severity = "high" if "critical" not in unmet_criteria else "critical"

            # Apply stricter correction logic for trivia
            if is_trivia and severity in ["high", "critical"]:
                should_correct = True
                print(f"🔧 [CoV] Aplicando correção em trivia - Severidade: {severity}")
            elif should_regenerate and severity == "high":
                should_correct = True
                print(f"🔧 [CoV] Aplicando correção (regenerate + high) - Severidade: {severity}")
            elif severity == "critical":
                should_correct = True
                print(f"🔧 [CoV] Aplicando correção (critical) - Severidade: {severity}")
            elif severity == "high" and correction_threshold == "strict":
                should_correct = True
                print(f"🔧 [CoV] Aplicando correção (high + strict) - Severidade: {severity}")
            else:
                print(f"📋 [CoV] Verificação detectou issues (severity: {severity}) mas não atende threshold para correção")
        
        # Etapa 3: Correção (se necessária)
        if should_correct:
            corrected_response = self.generate_corrected_response(
                user_input, initial_response, verification_result, function_call
            )
            verification_metadata["correction_applied"] = True
            final_response = corrected_response
        else:
            print("✅ [CoV] Resposta inicial aprovada na verificação")
            final_response = initial_response
        
        print(f"🏁 [CoV] Chain of Verification concluído - Correção aplicada: {verification_metadata['correction_applied']}")
        
        return final_response, verification_metadata
    
    def _get_correction_threshold(self, function_call: Optional[Dict[str, Any]]) -> str:
        """
        Determina o threshold de correção baseado no contexto
        
        Returns:
            str: "strict", "moderate", ou "lenient"
        """
        if not function_call:
            # Respostas diretas: threshold leniente (raramente corrige)
            return "lenient"
        
        function_name = function_call.get("name", "")
        
        # Configuração por função
        function_thresholds = {
            "schedule_meeting": "strict",        # Meetings precisam estar corretos
            "generate_paper_quote": "strict",    # Cálculos precisam estar corretos  
            "prank_dwight": "moderate"           # Humor pode ser mais flexível
        }
        
        return function_thresholds.get(function_name, "moderate")


class CoVConfiguration:
    """Configurações específicas para Chain of Verification"""
    
    def __init__(self):
        self.verification_enabled = True
        self.verification_threshold = "high"  # Mudança: de medium para high
        self.max_verification_attempts = 1
        self.verification_temperature = 0.3
        self.correction_temperature = 0.7
        
        # Configurações por tipo de função com thresholds mais rigorosos
        self.function_specific_config = {
            "schedule_meeting": {
                "verification_focus": ["completeness", "date_format", "time_validity"],
                "correction_priority": "high",
                "correction_threshold": "strict"
            },
            "generate_paper_quote": {
                "verification_focus": ["calculation_accuracy", "parameter_completeness"],
                "correction_priority": "high", 
                "correction_threshold": "strict"
            },
            "prank_dwight": {
                "verification_focus": ["humor_appropriateness", "creativity"],
                "correction_priority": "medium",
                "correction_threshold": "moderate"
            }
        }
        
        # Configurações para respostas diretas (sem function calling)
        self.direct_response_config = {
            "correction_priority": "high",
            "correction_threshold": "strict",
            "verification_focus": ["accuracy", "helpfulness", "completeness", "context"]
        }
    
    def get_function_config(self, function_name: str) -> Dict[str, Any]:
        """Retorna configuração específica para uma função"""
        return self.function_specific_config.get(function_name, {
            "verification_focus": ["general"],
            "correction_priority": "medium",
            "correction_threshold": "moderate"
        })
    
    def get_direct_response_config(self) -> Dict[str, Any]:
        """Retorna configuração para respostas diretas (sem function calling)"""
        return self.direct_response_config
    
    def should_verify(self, function_name: Optional[str] = None) -> bool:
        """Determina se deve aplicar verificação baseado em configurações mais inteligentes"""
        if not self.verification_enabled:
            return False
        
        if function_name:
            config = self.get_function_config(function_name)
            return config.get("correction_priority") != "low"
        else:
            # Para respostas diretas, usa configuração específica
            direct_config = self.get_direct_response_config()
            return direct_config.get("correction_priority") != "low"
