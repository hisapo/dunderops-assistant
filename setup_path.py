#!/usr/bin/env python3
"""
Script para configurar o ambiente Python e adicionar o projeto ao path
"""

import sys
import os

# Adiciona o diretório raiz do projeto ao Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"✅ Projeto adicionado ao Python path: {project_root}")
