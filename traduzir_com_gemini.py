#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Traduz SRTs de Inglês para Português usando Gemini API.
Lê de: videos_output/subtitles_en/
Salva em: videos_output/subtitles_pt/
"""

import os
import time
import google.generativeai as genai
from pathlib import Path
from config import SUBTITLES_EN_DIR, SUBTITLES_OUTPUT_DIR, GEMINI_API_KEY, GEMINI_MODEL

# Configurar API
genai.configure(api_key=GEMINI_API_KEY)

def traduzir_srt_gemini(caminho_entrada, caminho_saida):
    print(f"🤖 Traduzindo com Gemini: {Path(caminho_entrada).name}")
    
    try:
        with open(caminho_entrada, 'r', encoding='utf-8') as f:
            conteudo_en = f.read()
            
        if not conteudo_en.strip():
            print("⚠️ Arquivo vazio.")
            return False

        model = genai.GenerativeModel(GEMINI_MODEL)
        
        prompt = f"""
Você é um tradutor profissional de legendas (SRT).
Traduza o seguinte arquivo SRT do Inglês para Português do Brasil (PT-BR).

REGRAS CRITICAS:
1. MANTENHA EXATAMENTE a estrutura do SRT (números de sequência e tempos).
2. NÃO adicione explicações, nem ```markdown```, nem preâmbulos. Apenas o SRT puro.
3. Adapte gírias e expressões para o contexto brasileiro natural (não traduza ao pé da letra).
4. Se houver termos sexuais/bizarros, traduza de forma natural para o contexto adulto, sem censura desnecessária mas mantendo naturalidade.

Arquivo SRT de entrada:
{conteudo_en}
"""
        # Gemini tem limite de tokens. Se o arquivo for muito grande (ex: > 30KB),
        # idealmente deveria dividir. Para vídeos de 20-30min costuma caber no Gemini 1.5 Flash.
        # Se falhar por tamanho, vamos precisar implementar split.
        
        response = model.generate_content(prompt)
        conteudo_pt = response.text
        
        # Limpeza simples de markdown se houver
        conteudo_pt = conteudo_pt.replace("```srt", "").replace("```", "").strip()
        
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(conteudo_pt)
            
        print(f"✅ Tradução salva em: {caminho_saida}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na tradução: {str(e)}")
        return False

def main():
    os.makedirs(SUBTITLES_OUTPUT_DIR, exist_ok=True)
    
    srts = sorted([
        os.path.join(SUBTITLES_EN_DIR, f) 
        for f in os.listdir(SUBTITLES_EN_DIR) 
        if f.lower().endswith('_en.srt')
    ])
    
    if not srts:
        print("Nenhum arquivo _EN.srt encontrado para traduzir.")
        return

    print(f"📋 Encontrados {len(srts)} legendas EN para verificar tradução...")
    
    for srt_path in srts:
        nome_arquivo = Path(srt_path).stem.replace('_EN', '')
        caminho_saida_pt = os.path.join(SUBTITLES_OUTPUT_DIR, f"{nome_arquivo}_PT.srt")
        
        if os.path.exists(caminho_saida_pt):
            continue # Já existe
            
        # Traduzir
        sucesso = traduzir_srt_gemini(srt_path, caminho_saida_pt)
        if sucesso:
            time.sleep(2) # Evitar rate limit agressivo
            
if __name__ == "__main__":
    main()
