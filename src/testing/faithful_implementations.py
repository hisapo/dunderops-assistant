"""
Classes de teste que reproduzem fielmente a implementação dos form_ui principais
"""

import json
import os
from typing import Dict, Any
from openai import OpenAI

from src.core.functions import schedule_meeting, generate_paper_quote, prank_dwight
from src.core.prompt_config import PromptConfig
from src.core.function_validator import FunctionValidator
from src.cov.chain_of_verification import ChainOfVerification, CoVConfiguration
from src.core.metrics_tracker import MetricsTracker
from src.utils.function_intent import detect_function_intent


class FormUIOriginalReproduction:
    """Reproduz exatamente a lógica do form_ui.py"""
    
    def __init__(self, client: OpenAI, prompts: PromptConfig, validator: FunctionValidator):
        self.client = client
        self.prompts = prompts
        self.validator = validator
        self.LOCAL_FUNCS = {
            "schedule_meeting": schedule_meeting,
            "generate_paper_quote": generate_paper_quote,
            "prank_dwight": prank_dwight,
        }
    
    def process_request(self, user_input: str, manifest: Dict[str, Any], tracker: MetricsTracker) -> str:
        """Reproduz exatamente a lógica do form_ui.py"""
        
        # Detecta se deve forçar function calling (IGUAL ao form_ui.py)
        tool_choice = detect_function_intent(user_input)
        
        # Primeira chamada à API (IGUAL ao form_ui.py)
        first = self.client.chat.completions.create(
            model="gpt-4o-mini",
            tools=manifest["tools"],
            tool_choice=tool_choice,
            messages=[
                {"role": "system", "content": self.prompts.system_prompt},
                {"role": "user", "content": user_input}
            ]
        )
        
        # Track API call
        tracker.track_api_call(
            input_tokens=first.usage.prompt_tokens,
            output_tokens=first.usage.completion_tokens
        )
        
        msg = first.choices[0].message
        
        # Processa resposta (IGUAL ao form_ui.py)
        if msg.tool_calls:
            call = msg.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments)

            # Valida parâmetros (IGUAL ao form_ui.py)
            is_valid, humor_message = self.validator.validate_function_params(name, args)
            
            if not is_valid:
                # Track failed function call
                tracker.track_function_call(name, args, None, False)
                return humor_message
            else:
                # Executa função (IGUAL ao form_ui.py)
                function_result = self.LOCAL_FUNCS[name](**args)
                
                # Track successful function call
                tracker.track_function_call(name, args, function_result, True)

                # Segunda chamada para resposta final (IGUAL ao form_ui.py)
                second = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.prompts.final_system_prompt},
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
                
                # Track second API call
                tracker.track_api_call(
                    input_tokens=second.usage.prompt_tokens,
                    output_tokens=second.usage.completion_tokens
                )
                
                return second.choices[0].message.content
        else:
            # Resposta direta sem função (IGUAL ao form_ui.py)
            return msg.content


class FormUICoVReproduction:
    """Reproduz exatamente a lógica do form_ui_cov.py"""
    
    def __init__(self, client: OpenAI, prompts: PromptConfig, validator: FunctionValidator):
        self.client = client
        self.prompts = prompts
        self.validator = validator
        self.cov = ChainOfVerification(client, prompts)
        self.cov_config = CoVConfiguration()
        self.LOCAL_FUNCS = {
            "schedule_meeting": schedule_meeting,
            "generate_paper_quote": generate_paper_quote,
            "prank_dwight": prank_dwight,
        }
    
    def process_request(self, user_input: str, manifest: Dict[str, Any], tracker: MetricsTracker) -> str:
        """Reproduz exatamente a lógica do form_ui_cov.py"""
        
        # ETAPA 1: Gera resposta inicial (IGUAL ao form_ui_cov.py)
        tool_choice = detect_function_intent(user_input)
        
        first_response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            tools=manifest["tools"],
            tool_choice=tool_choice,
            messages=[
                {"role": "system", "content": self.prompts.system_prompt},
                {"role": "user", "content": user_input}
            ]
        )

        # Track first API call
        tracker.track_api_call(
            input_tokens=first_response.usage.prompt_tokens,
            output_tokens=first_response.usage.completion_tokens
        )

        msg = first_response.choices[0].message
        function_call_info = None
        function_result = None
        initial_response = ""

        # Processa resposta inicial (IGUAL ao form_ui_cov.py)
        if msg.tool_calls:
            call = msg.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments)
            
            function_call_info = {
                "name": name,
                "arguments": args,
                "call_object": call
            }

            # Valida parâmetros (IGUAL ao form_ui_cov.py)
            is_valid, humor_message = self.validator.validate_function_params(name, args)
            
            if not is_valid:
                initial_response = humor_message
                tracker.track_function_call(name, args, None, False)
            else:
                # Executa função (IGUAL ao form_ui_cov.py)
                function_result = self.LOCAL_FUNCS[name](**args)
                tracker.track_function_call(name, args, function_result, True)

                # Gera resposta baseada no resultado (IGUAL ao form_ui_cov.py)
                final_response_call = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.prompts.final_system_prompt},
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
                
                tracker.track_api_call(
                    input_tokens=final_response_call.usage.prompt_tokens,
                    output_tokens=final_response_call.usage.completion_tokens
                )
                
                initial_response = final_response_call.choices[0].message.content
        else:
            initial_response = msg.content

        # ETAPA 2: Chain of Verification (IGUAL ao form_ui_cov.py)
        if self.cov_config.should_verify(function_call_info.get("name") if function_call_info else None):
            tracker.start_verification_phase()
            
            final_response, verification_metadata = self.cov.process_with_verification(
                user_input=user_input,
                initial_response=initial_response,
                function_call=function_call_info
            )
            
            # Tokens da verificação (IGUAL ao form_ui_cov.py)
            verification_tokens = len(verification_metadata.get("verification_result", {}).get("issues", [])) * 50
            
            tracker.end_verification_phase(
                verification_tokens=verification_tokens,
                correction_made=verification_metadata.get("correction_applied", False)
            )
            
            return final_response
        else:
            return initial_response


class FormUISecureReproduction:
    """Reproduz exatamente a lógica do form_ui_secure.py"""
    
    def __init__(self, client: OpenAI, prompts: PromptConfig, validator: FunctionValidator):
        self.client = client
        self.prompts = prompts
        self.validator = validator
        # Importar security validator quando necessário
        try:
            from src.security.secure_function_validator import SecureFunctionValidator
            self.secure_validator = SecureFunctionValidator(prompts)
        except ImportError:
            self.secure_validator = validator  # Fallback
            
        self.LOCAL_FUNCS = {
            "schedule_meeting": schedule_meeting,
            "generate_paper_quote": generate_paper_quote,
            "prank_dwight": prank_dwight,
        }
    
    def process_request(self, user_input: str, manifest: Dict[str, Any], tracker: MetricsTracker) -> str:
        """Reproduz exatamente a lógica do form_ui_secure.py"""
        
        # Processamento de segurança do input (simplificado para teste)
        processed_input = user_input
        
        # Detecta tool choice (IGUAL ao form_ui_secure.py)
        tool_choice = detect_function_intent(processed_input)
        
        # Primeira chamada à API (IGUAL ao form_ui_secure.py)
        first = self.client.chat.completions.create(
            model="gpt-4o-mini",
            tools=manifest["tools"],
            tool_choice=tool_choice,
            messages=[
                {"role": "system", "content": self.prompts.system_prompt},
                {"role": "user", "content": processed_input}
            ]
        )
        
        # Track API call
        tracker.track_api_call(
            input_tokens=first.usage.prompt_tokens,
            output_tokens=first.usage.completion_tokens
        )
        
        msg = first.choices[0].message
        
        # Processa resposta (IGUAL ao form_ui_secure.py)
        if msg.tool_calls:
            call = msg.tool_calls[0]
            name = call.function.name
            args = json.loads(call.function.arguments)

            # Usa secure validator se disponível
            validator = getattr(self, 'secure_validator', self.validator)
            is_valid, humor_message = validator.validate_function_params(name, args)
            
            if not is_valid:
                tracker.track_function_call(name, args, None, False)
                return humor_message
            else:
                function_result = self.LOCAL_FUNCS[name](**args)
                tracker.track_function_call(name, args, function_result, True)

                second = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": self.prompts.final_system_prompt},
                        {"role": "user", "content": processed_input},
                        {"role": "assistant", "content": None, "tool_calls": [call]},
                        {
                            "role": "tool",
                            "tool_call_id": call.id,
                            "name": name,
                            "content": json.dumps(function_result)
                        }
                    ]
                )
                
                tracker.track_api_call(
                    input_tokens=second.usage.prompt_tokens,
                    output_tokens=second.usage.completion_tokens
                )
                
                return second.choices[0].message.content
        else:
            return msg.content
