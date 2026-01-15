#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Limpa alucinações (frases repetidas) dos SRTs existentes.
Detecta dois tipos de alucinações:
1. INTERNAS: palavras repetidas dentro de um segmento (ex: "oh, oh, oh, oh...")
2. CONSECUTIVAS: mesma frase repetida em segmentos seguidos
"""

import os
import re
from pathlib import Path
from collections import Counter
from config import SUBTITLES_EN_DIR

def normalizar_texto(texto):
    """Normaliza texto para comparação"""
    texto = texto.lower().strip()
    texto = re.sub(r'[^\w\s]', '', texto)
    texto = re.sub(r'\s+', ' ', texto)
    return texto

def eh_alucinacao_interna(texto):
    """
    Detecta alucinações DENTRO de um único segmento.
    Exemplo: "oh, oh, oh, oh, oh, oh..." ou "yeah yeah yeah yeah..."
    """
    # Normalizar e dividir em palavras
    texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
    palavras = texto_limpo.split()
    
    if len(palavras) < 5:
        return False
    
    # Contar frequência de cada palavra
    contagem = Counter(palavras)
    palavra_mais_comum, qtd = contagem.most_common(1)[0]
    
    # Palavras comuns que podem repetir legitimamente
    palavras_ok = {'i', 'you', 'the', 'a', 'and', 'to', 'it', 'is', 'of', 'in', 'that', 'me', 'my', 'your'}
    
    if palavra_mais_comum in palavras_ok:
        threshold = 0.7
    else:
        threshold = 0.5
    
    if qtd / len(palavras) >= threshold:
        return True
    
    # Verificar padrão repetitivo
    if len(palavras) >= 10:
        palavras_unicas = set(palavras)
        if len(palavras_unicas) <= 3:
            return True
    
    return False

def parse_srt(srt_path):
    """Lê um arquivo SRT e retorna lista de segmentos"""
    segments = []
    
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    blocos = re.split(r'\n\n+', content.strip())
    
    for bloco in blocos:
        linhas = bloco.strip().split('\n')
        if len(linhas) >= 3:
            try:
                timestamp = linhas[1]
                texto = '\n'.join(linhas[2:])
                
                match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', timestamp)
                if match:
                    segments.append({
                        'start': match.group(1),
                        'end': match.group(2),
                        'text': texto.strip(),
                        'text_norm': normalizar_texto(texto.strip())
                    })
            except:
                continue
    
    return segments

def filtrar_alucinacoes(segments, max_repeticoes=2):
    """Remove alucinações internas e consecutivas"""
    if not segments:
        return segments, 0
    
    # Primeiro: remover alucinações internas
    segs_limpos = []
    internas = 0
    for seg in segments:
        if eh_alucinacao_interna(seg['text']):
            internas += 1
        else:
            segs_limpos.append(seg)
    
    if not segs_limpos:
        return [], internas
    
    # Segundo: remover consecutivas
    filtrados = []
    i = 0
    consecutivas = 0
    
    while i < len(segs_limpos):
        texto_norm = segs_limpos[i]['text_norm']
        
        repeticoes = 1
        j = i + 1
        while j < len(segs_limpos):
            outro = segs_limpos[j]['text_norm']
            if texto_norm == outro or (len(texto_norm) > 3 and (texto_norm in outro or outro in texto_norm)):
                repeticoes += 1
                j += 1
            else:
                break
        
        if repeticoes > max_repeticoes:
            filtrados.append(segs_limpos[i])
            consecutivas += repeticoes - 1
            i = j
        else:
            for k in range(i, j):
                filtrados.append(segs_limpos[k])
            i = j
    
    return filtrados, internas + consecutivas

def salvar_srt(segments, output_path):
    """Salva segmentos em formato SRT"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments, 1):
            f.write(f"{i}\n{seg['start']} --> {seg['end']}\n{seg['text']}\n\n")
    return len(segments)

def main():
    pasta_srt = str(SUBTITLES_EN_DIR)
    
    srts = sorted([
        os.path.join(pasta_srt, f)
        for f in os.listdir(pasta_srt)
        if f.endswith('_EN.srt')
    ])
    
    print(f"🔍 Encontrados {len(srts)} arquivos SRT\n")
    print("📊 Filtros:")
    print("   • INTERNAS: palavras repetidas dentro do segmento (oh, oh, oh...)")
    print("   • CONSECUTIVAS: mesma frase em segmentos seguidos")
    print()
    
    corrigidos = 0
    total_removidos = 0
    
    for srt in srts:
        nome = Path(srt).stem[:50]
        
        segments = parse_srt(srt)
        segments_filtrados, removidos = filtrar_alucinacoes(segments, max_repeticoes=2)
        
        if removidos > 0:
            salvar_srt(segments_filtrados, srt)
            print(f"✅ {nome}... -{removidos} alucinações")
            corrigidos += 1
            total_removidos += removidos
    
    print(f"\n{'='*60}")
    if corrigidos > 0:
        print(f"🧹 Limpeza: {corrigidos} arquivos corrigidos, {total_removidos} alucinações removidas!")
    else:
        print(f"✨ Nenhuma alucinação encontrada!")

if __name__ == "__main__":
    main()
