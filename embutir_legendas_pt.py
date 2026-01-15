#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Embutir legendas PT nos vídeos.
Verifica quais vídeos têm legendas traduzidas (_PT.srt) e embuti-las.

Pipeline:
1. Busca vídeos em proximos_para_traducao/
2. Verifica se existe SRT traduzido em videos_output/subtitles_pt/
3. Se existir, embuti a legenda no vídeo
4. Salva em videos_output/videos_translated/
"""

import os
import subprocess
from pathlib import Path
from config import SUBTITLES_OUTPUT_DIR, VIDEOS_OUTPUT_DIR

# Configurações
PASTA_VIDEOS = "proximos_para_traducao"
PASTA_SRT_PT = str(SUBTITLES_OUTPUT_DIR)
PASTA_SAIDA = str(VIDEOS_OUTPUT_DIR)

def embutir_legenda(video_path, srt_path, output_path):
    """Embuti legenda .srt no vídeo usando FFmpeg"""
    
    # Usar subtitles filter para hard-sub (queimar na imagem)
    # Estilo: fonte branca com borda preta, tamanho 24
    srt_escaped = srt_path.replace('\\', '/').replace(':', r'\:')
    
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', f"subtitles='{srt_escaped}':force_style='FontSize=24,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,Shadow=1'",
        '-c:a', 'copy',
        '-c:v', 'libx264',
        '-preset', 'medium',
        '-crf', '23',
        '-y',
        output_path
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)  # 1 hora timeout
    return result.returncode == 0

def main():
    # Criar pasta de saída se não existir
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    # Listar vídeos
    videos = sorted([
        os.path.join(PASTA_VIDEOS, f)
        for f in os.listdir(PASTA_VIDEOS)
        if f.lower().endswith('.mp4')
    ])
    
    print(f"🎬 Encontrados {len(videos)} vídeos\n")
    
    # Verificar quais têm legenda PT
    para_processar = []
    ja_prontos = 0
    sem_legenda = 0
    
    def normalizar_nome(nome):
        """Remove apóstrofos e caracteres especiais para comparação flexível"""
        import re
        return re.sub(r'[^\w]', '', nome.lower())

    for video in videos:
        nome_video = Path(video).stem
        nome_video_norm = normalizar_nome(nome_video)
        
        # Procura pelo SRT correspondente (verificando normalizado)
        srt_pt = None
        for srt_file in os.listdir(PASTA_SRT_PT):
            if not srt_file.lower().endswith('.srt'):
                continue
                
            nome_srt = Path(srt_file).stem.replace('_pt', '').replace('_PT', '')
            texto_srt_norm = normalizar_nome(nome_srt)
            
            if nome_video_norm == texto_srt_norm:
                srt_pt = os.path.join(PASTA_SRT_PT, srt_file)
                break
        
        video_final = os.path.join(PASTA_SAIDA, f"{nome_video}_PT.mp4")
        
        if os.path.exists(video_final):
            ja_prontos += 1
        elif srt_pt:
            para_processar.append((video, srt_pt, video_final, nome_video))
        else:
            sem_legenda += 1
    
    print(f"📊 Status:")
    print(f"   ✅ Já processados: {ja_prontos}")
    print(f"   📋 Para processar: {len(para_processar)}")
    print(f"   ⏳ Sem legenda PT: {sem_legenda}")
    print()
    
    if not para_processar:
        print("✨ Nenhum vídeo para processar!")
        return
    
    # Processar
    print(f"🚀 Iniciando embutir legendas...\n")
    
    sucesso = 0
    falhas = 0
    
    for i, (video, srt, output, nome) in enumerate(para_processar, 1):
        nome_curto = nome[:50]
        print(f"[{i}/{len(para_processar)}] 📹 {nome_curto}...")
        print(f"  → Embutindo legenda PT...", end=" ", flush=True)
        
        if embutir_legenda(video, srt, output):
            print("✅")
            sucesso += 1
        else:
            print("❌")
            falhas += 1
    
    # Resumo
    print("\n" + "="*70)
    print(f"✅ Concluído: {sucesso}/{len(para_processar)} vídeos com legendas embutidas")
    if falhas > 0:
        print(f"⚠️  {falhas} vídeo(s) falharam")
    print("="*70)

if __name__ == "__main__":
    main()
