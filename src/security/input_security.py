"""
Sistema de segurança para proteção contra prompt injection
Decodifica/normaliza entrada e valida estrutura antes de repassar ao LLM
"""

import json
import re
import base64
import unicodedata
import html
from typing import Dict, Any, Tuple, List, Optional
from urllib.parse import unquote
import logging

class InputSecurityValidator:
    """
    Validador de segurança para entradas do usuário
    Protege contra prompt injection, normaliza Unicode e valida schemas
    """
    
    def __init__(self, max_input_length: int = 10000):
        self.max_input_length = max_input_length
        self.logger = logging.getLogger(__name__)
        
        # Padrões suspeitos de prompt injection
        self.injection_patterns = [
            # Tentativas de quebrar contexto
            r'(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)',
            r'(?i)act\s+as\s+(a\s+)?(different|new|another)\s+(ai|assistant|system|role)',
            r'(?i)(pretend|imagine|roleplay)\s+(you\s+are|to\s+be|that\s+you)',
            
            # Tentativas de injeção de sistema
            r'(?i)(system|admin|root)\s*(:|prompt|instruction|message)',
            r'(?i)(override|bypass|disable|turn\s+off)\s+(safety|security|filter)',
            r'(?i)jailbreak|dan\s+mode|developer\s+mode',
            
            # Tentativas de extrair informações
            r'(?i)(show|reveal|display|print|output)\s+(your\s+)?(system\s+prompt|instructions|rules)',
            r'(?i)(what\s+are|tell\s+me)\s+your\s+(instructions|rules|system\s+prompt)',
            
            # Comandos especiais ou caracteres de controle
            r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F]',  # Caracteres de controle
            r'\\(n|t|r|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4})',  # Escape sequences
            
            # Tentativas de injeção de JSON/código
            r'(?i)(\{|\[).*("role"|"system"|"assistant"|"user").*(\}|\])',
            r'(?i)(```|<script|<iframe|javascript:|data:)',
            
            # Tentativas de manipulação de contexto
            r'(?i)(end\s+of|start\s+of)\s+(conversation|chat|prompt|instruction)',
            r'(?i)(new\s+)?(conversation|session|chat)\s+(starts?|begins?)',
        ]
        
        # Compilar padrões para performance
        self.compiled_patterns = [re.compile(pattern) for pattern in self.injection_patterns]
    
    def normalize_unicode(self, text: str) -> str:
        """
        Normaliza texto Unicode para forma canônica
        Previne ataques usando caracteres Unicode similares
        """
        # Normalização Unicode NFKC (Canonical Decomposition + Canonical Composition)
        normalized = unicodedata.normalize('NFKC', text)
        
        # Remove caracteres de controle (exceto espaços normais)
        normalized = ''.join(char for char in normalized 
                           if unicodedata.category(char) != 'Cc' or char in '\n\r\t ')
        
        return normalized
    
    def decode_input(self, text: str) -> str:
        """
        Decodifica várias formas de encoding que podem ser usadas para evasão
        """
        original_text = text
        
        try:
            # Decodificação HTML
            text = html.unescape(text)
            
            # Decodificação URL
            text = unquote(text)
            
            # Tentativa de decodificação Base64 (se parecer Base64)
            if self._looks_like_base64(text):
                try:
                    decoded = base64.b64decode(text).decode('utf-8', errors='ignore')
                    if self._is_valid_text(decoded):
                        text = decoded
                except Exception:
                    pass  # Se falhar, mantém o texto original
            
            # Decodificação de escape sequences comuns
            text = text.replace('\\n', '\n').replace('\\t', '\t').replace('\\r', '\r')
            
        except Exception as e:
            self.logger.warning(f"Erro na decodificação: {e}")
            return original_text
        
        return text
    
    def _looks_like_base64(self, text: str) -> bool:
        """Verifica se o texto parece ser Base64"""
        # Base64 só tem caracteres específicos e múltiplo de 4
        base64_pattern = re.compile(r'^[A-Za-z0-9+/]*={0,2}$')
        return (len(text) % 4 == 0 and 
                len(text) > 8 and 
                base64_pattern.match(text) and
                '=' not in text[:-2])  # = só no final
    
    def _is_valid_text(self, text: str) -> bool:
        """Verifica se o texto decodificado é válido (não binário/corrupto)"""
        try:
            # Tenta codificar/decodificar para verificar validade
            text.encode('utf-8').decode('utf-8')
            # Verifica se tem proporção razoável de caracteres imprimíveis
            printable_ratio = sum(1 for c in text if c.isprintable() or c.isspace()) / len(text)
            return printable_ratio > 0.8
        except Exception:
            return False
    
    def detect_injection_attempts(self, text: str) -> Tuple[bool, List[str]]:
        """
        Detecta tentativas de prompt injection
        
        Returns:
            Tuple[bool, List[str]]: (has_injection, list_of_matched_patterns)
        """
        matched_patterns = []
        
        for pattern in self.compiled_patterns:
            if pattern.search(text):
                matched_patterns.append(pattern.pattern)
        
        return len(matched_patterns) > 0, matched_patterns
    
    def validate_json_structure(self, text: str, expected_schema: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Valida se entrada JSON está bem formada e segue schema esperado
        
        Returns:
            Tuple[bool, str, Optional[Dict]]: (is_valid, error_message, parsed_json)
        """
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            return False, f"JSON inválido: {e}", None
        
        # Validação básica de segurança em JSON
        if self._contains_dangerous_json_content(parsed):
            return False, "JSON contém conteúdo potencialmente perigoso", None
        
        # Validação de schema se fornecido
        if expected_schema:
            is_valid, error = self._validate_against_schema(parsed, expected_schema)
            if not is_valid:
                return False, error, None
        
        return True, "", parsed
    
    def _contains_dangerous_json_content(self, obj: Any) -> bool:
        """Verifica se objeto JSON contém conteúdo perigoso"""
        if isinstance(obj, dict):
            # Verifica chaves suspeitas
            dangerous_keys = ['__proto__', 'constructor', 'prototype', 'eval', 'function']
            for key in obj.keys():
                if isinstance(key, str) and key.lower() in dangerous_keys:
                    return True
                if self._contains_dangerous_json_content(obj[key]):
                    return True
        elif isinstance(obj, list):
            for item in obj:
                if self._contains_dangerous_json_content(item):
                    return True
        elif isinstance(obj, str):
            # Verifica se string contém tentativas de injection
            has_injection, _ = self.detect_injection_attempts(obj)
            return has_injection
        
        return False
    
    def _validate_against_schema(self, data: Dict, schema: Dict) -> Tuple[bool, str]:
        """Validação básica de schema (implementação simplificada)"""
        # Esta é uma implementação básica - poderia usar jsonschema library para validação completa
        
        if not isinstance(data, dict):
            return False, "Dados devem ser um objeto JSON"
        
        # Verifica campos obrigatórios
        required_fields = schema.get('required', [])
        for field in required_fields:
            if field not in data:
                return False, f"Campo obrigatório '{field}' está faltando"
        
        # Verifica tipos de campos
        properties = schema.get('properties', {})
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get('type')
                if expected_type and not self._check_type(value, expected_type):
                    return False, f"Campo '{field}' deve ser do tipo {expected_type}"
        
        return True, ""
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Verifica se valor corresponde ao tipo esperado"""
        type_mapping = {
            'string': str,
            'integer': int,
            'number': (int, float),
            'boolean': bool,
            'array': list,
            'object': dict
        }
        
        expected_python_type = type_mapping.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True  # Tipo desconhecido, aceita
    
    def validate_input(self, user_input: str, is_json: bool = False, 
                      json_schema: Optional[Dict] = None) -> Tuple[bool, str, str]:
        """
        Validação completa de entrada do usuário
        
        Args:
            user_input: Entrada original do usuário
            is_json: Se True, valida como JSON
            json_schema: Schema para validação JSON (opcional)
        
        Returns:
            Tuple[bool, str, str]: (is_safe, error_message, normalized_input)
        """
        # 1. Verificação de tamanho
        if len(user_input) > self.max_input_length:
            return False, f"Entrada muito longa (máximo {self.max_input_length} caracteres)", ""
        
        # 2. Decodificação
        try:
            decoded_input = self.decode_input(user_input)
        except Exception as e:
            return False, f"Erro na decodificação: {e}", ""
        
        # 3. Normalização Unicode
        try:
            normalized_input = self.normalize_unicode(decoded_input)
        except Exception as e:
            return False, f"Erro na normalização: {e}", ""
        
        # 4. Detecção de prompt injection
        has_injection, patterns = self.detect_injection_attempts(normalized_input)
        if has_injection:
            self.logger.warning(f"Tentativa de prompt injection detectada: {patterns[:3]}")  # Log só primeiros 3
            return False, "Entrada contém padrões de prompt injection", ""
        
        # 5. Validação JSON se necessário
        if is_json:
            is_valid_json, json_error, _ = self.validate_json_structure(normalized_input, json_schema)
            if not is_valid_json:
                return False, f"Erro de validação JSON: {json_error}", ""
        
        return True, "", normalized_input
    
    def sanitize_for_llm(self, text: str) -> str:
        """
        Sanitiza texto para ser seguro para envio ao LLM
        Remove ou escapa caracteres problemáticos
        """
        # Remove ou substitui caracteres problemáticos
        sanitized = text
        
        # Remove múltiplas quebras de linha consecutivas (>3)
        sanitized = re.sub(r'\n{4,}', '\n\n\n', sanitized)
        
        # Remove espaços excessivos
        sanitized = re.sub(r' {10,}', ' ' * 9, sanitized)
        
        # Escapa possíveis tentativas de manipulação de role
        sanitized = sanitized.replace('Assistant:', 'Assistant_:')
        sanitized = sanitized.replace('Human:', 'Human_:')
        sanitized = sanitized.replace('System:', 'System_:')
        
        return sanitized.strip()

class SecureInputProcessor:
    """
    Processador principal que combina validação e sanitização
    """
    
    def __init__(self, max_input_length: int = 10000):
        self.validator = InputSecurityValidator(max_input_length)
        self.logger = logging.getLogger(__name__)
    
    def process_user_input(self, raw_input: str) -> Tuple[bool, str, str]:
        """
        Processa entrada do usuário de forma segura
        
        Returns:
            Tuple[bool, str, str]: (is_safe, error_or_warning, processed_input)
        """
        # Validação e normalização
        is_safe, error_msg, normalized = self.validator.validate_input(raw_input)
        
        if not is_safe:
            self.logger.warning(f"Input rejeitado: {error_msg}")
            return False, error_msg, ""
        
        # Sanitização final
        safe_input = self.validator.sanitize_for_llm(normalized)
        
        return True, "", safe_input
    
    def process_json_input(self, raw_json: str, schema: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
        """
        Processa entrada JSON de forma segura
        
        Returns:
            Tuple[bool, str, Optional[Dict]]: (is_safe, error_message, parsed_data)
        """
        # Validação específica para JSON
        is_safe, error_msg, normalized = self.validator.validate_input(
            raw_json, is_json=True, json_schema=schema
        )
        
        if not is_safe:
            self.logger.warning(f"JSON rejeitado: {error_msg}")
            return False, error_msg, None
        
        # Parse final do JSON validado
        try:
            parsed_data = json.loads(normalized)
            return True, "", parsed_data
        except json.JSONDecodeError as e:
            return False, f"Erro no parsing final do JSON: {e}", None
