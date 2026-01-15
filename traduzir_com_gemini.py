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
    """Traduz SRT do inglês para português com contexto histórico para consistência."""
    print(f"🤖 Traduzindo com Gemini: {Path(caminho_entrada).name}")
    
    try:
        with open(caminho_entrada, 'r', encoding='utf-8') as f:
            conteudo_en = f.read()
            
        if not conteudo_en.strip():
            print("⚠️ Arquivo vazio.")
            return False

        model = genai.GenerativeModel(GEMINI_MODEL)
        
        # Configurações de segurança para evitar bloqueios desnecessários
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        
        # Parsear o SRT para processar em lotes com contexto
        import re
        blocos = re.split(r'\n\n+', conteudo_en.strip())
        legendas_traduzidas = []
        contexto_anterior = ""  # Últimas legendas traduzidas para contexto
        
        # Processar em lotes de 10 legendas
        BATCH_SIZE = 10
        
        for i in range(0, len(blocos), BATCH_SIZE):
            lote_atual = blocos[i:i + BATCH_SIZE]
            lote_texto = "\n\n".join(lote_atual)
            
            # MELHORIA: Prompt com contexto histórico para consistência
            prompt = f"""Você é um tradutor profissional de legendas (SRT).
Traduza o seguinte trecho do Inglês para Português do Brasil (PT-BR).

CONTEXTO (legendas anteriores já traduzidas - use para manter consistência):
{contexto_anterior if contexto_anterior else "(início do vídeo)"}

REGRAS CRÍTICAS:
1. MANTENHA EXATAMENTE a estrutura do SRT (números de sequência e tempos).
2. NÃO adicione explicações, nem ```markdown```, nem preâmbulos. Apenas o SRT puro.
3. MANTENHA CONSISTÊNCIA: se já usou "você", continue usando "você" (não mude para "tu").
4. MANTENHA O GÊNERO: observe o contexto para usar concordância correta (ele/ela).
5. Adapte gírias e expressões para o contexto brasileiro natural.
6. Para conteúdo adulto, traduza de forma natural sem censura, mantendo naturalidade.
7. Termos de parentesco: "Step-" = "Padrasto/Madrasta/Enteado(a)".

Trecho SRT para traduzir:
{lote_texto}
"""
            
            try:
                response = model.generate_content(prompt, safety_settings=safety_settings)
                traducao_lote = response.text
                
                # Limpeza de markdown se houver
                traducao_lote = traducao_lote.replace("```srt", "").replace("```", "").strip()
                
                legendas_traduzidas.append(traducao_lote)
                
                # Atualizar contexto com as últimas 3 legendas traduzidas
                ultimas_legendas = "\n\n".join(traducao_lote.split("\n\n")[-3:])
                contexto_anterior = ultimas_legendas
                
                # Pequena pausa para evitar rate limit
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Erro no lote {i//BATCH_SIZE + 1}: {str(e)[:50]}")
                # Em caso de erro, manter o original
                legendas_traduzidas.append(lote_texto)
        
        # Juntar todas as traduções
        conteudo_pt = "\n\n".join(legendas_traduzidas)
        
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
