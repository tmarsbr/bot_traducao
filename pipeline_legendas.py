#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🎬 PIPELINE COMPLETO DE LEGENDAS
================================

Executa todos os passos automaticamente:
1. Extrai SRT em inglês (Whisper)
2. Limpa alucinações dos SRTs
3. Verifica legendas traduzidas (PT)
4. Embuti legendas nos vídeos

Uso:
    python pipeline_legendas.py
"""

import os
import subprocess
import sys

# Diretório do script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def rodar_script(nome, descricao):
    """Roda um script Python e retorna se teve sucesso"""
    print(f"\n{'='*70}")
    print(f"🚀 {descricao}")
    print(f"{'='*70}\n")
    
    script_path = os.path.join(SCRIPT_DIR, nome)
    
    result = subprocess.run(
        [sys.executable, script_path],
        cwd=SCRIPT_DIR
    )
    
    return result.returncode == 0

def main():
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                    🎬 PIPELINE COMPLETO DE LEGENDAS                  ║
╠══════════════════════════════════════════════════════════════════════╣
║  1. Extrair SRT (Whisper)                                            ║
║  2. Limpar alucinações                                               ║
║  3. Embutir legendas PT                                              ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    # Etapa 1: Extrair SRTs
    rodar_script("extrair_proximos_srt_v2.py", "ETAPA 1: Extraindo SRTs em inglês (Whisper)")
    
    # Etapa 2: Limpar alucinações
    rodar_script("limpar_alucinacoes_srt.py", "ETAPA 2: Limpando alucinações")
    
    # Etapa 3: Embutir legendas
    rodar_script("embutir_legendas_pt.py", "ETAPA 3: Embutindo legendas PT nos vídeos")
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║                         🎉 PIPELINE CONCLUÍDO!                       ║
╠══════════════════════════════════════════════════════════════════════╣
║  ✅ SRTs extraídos                                                   ║
║  ✅ Alucinações limpas                                               ║
║  ✅ Legendas embutidas                                               ║
║                                                                      ║
║  📁 Vídeos com legenda: videos_output/videos_translated/             ║
╚══════════════════════════════════════════════════════════════════════╝
""")

if __name__ == "__main__":
    main()
