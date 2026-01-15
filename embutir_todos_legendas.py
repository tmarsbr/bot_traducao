#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para embutir legendas em múltiplos vídeos em paralelo
"""

import os
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Configurações
VIDEOS_INPUT_DIR = Path("videos_input")
VIDEOS_OUTPUT_DIR = Path("videos_output")
VIDEOS = [
    "pri4.mp4",
    "Nickey.mp4",
    "elsa.mp4",
    "Arya.mp4"
]

def embed_subtitles(video_file):
    """Embute legendas (hard subtitles) em um vídeo"""
    video_path = VIDEOS_INPUT_DIR / video_file
    srt_file = VIDEOS_OUTPUT_DIR / f"{video_file.replace('.mp4', '')}_pt.srt"
    output_file = VIDEOS_OUTPUT_DIR / f"{video_file.replace('.mp4', '')}_legendado.mp4"
    
    print(f"\n{'='*70}")
    print(f"🎬 EMBUTINDO: {video_file}")
    print(f"{'='*70}")
    
    # Verificar se SRT existe
    if not srt_file.exists():
        print(f"❌ Arquivo SRT não encontrado: {srt_file}")
        return False
    
    print(f"📝 Legenda: {srt_file.name}")
    print(f"💾 Saída: {output_file.name}")
    print(f"🔄 Processando com FFmpeg + libass...")
    
    # Comando FFmpeg com subtítulos renderizados (hard subtitles)
    cmd = [
        "ffmpeg",
        "-i", str(video_path),
        "-vf", f"subtitles={str(srt_file)}",
        "-c:a", "copy",
        "-y",
        str(output_file)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
        
        if result.returncode == 0 and output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"✅ Sucesso!")
            print(f"   📹 Vídeo com legendas: {output_file.name}")
            print(f"   📊 Tamanho: {size_mb:.1f} MB")
            return True
        else:
            print(f"❌ Erro ao processar {video_file}")
            if "Error" in result.stderr:
                print(f"   Detalhes: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"❌ Timeout ao processar {video_file} (limite: 1 hora)")
        return False
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        return False

def main():
    """Processa todos os vídeos em paralelo"""
    print("\n" + "="*70)
    print("🎬 EMBUTIR LEGENDAS EM MÚLTIPLOS VÍDEOS")
    print("="*70)
    
    # Verificar arquivos
    videos_validos = []
    videos_faltando = []
    
    for video in VIDEOS:
        video_path = VIDEOS_INPUT_DIR / video
        srt_path = VIDEOS_OUTPUT_DIR / f"{video.replace('.mp4', '')}_pt.srt"
        
        if not video_path.exists():
            videos_faltando.append(f"{video} (vídeo)")
        elif not srt_path.exists():
            videos_faltando.append(f"{video.replace('.mp4', '')}_pt.srt (legenda)")
        else:
            videos_validos.append(video)
    
    if videos_faltando:
        print(f"\n⚠️  Arquivos não encontrados:")
        for v in videos_faltando:
            print(f"   - {v}")
    
    if not videos_validos:
        print("\n❌ Nenhum vídeo + SRT válido encontrado para processar!")
        return
    
    print(f"\n✅ Arquivos prontos para embutir:")
    for v in videos_validos:
        video_path = VIDEOS_INPUT_DIR / v
        srt_name = f"{v.replace('.mp4', '')}_pt.srt"
        video_size = video_path.stat().st_size / (1024 * 1024)
        print(f"   ✓ {v} ({video_size:.1f} MB) + {srt_name}")
    
    # Processar em paralelo (limite de 2 para não sobrecarregar)
    print(f"\n🚀 Iniciando embutição de {len(videos_validos)} vídeos...")
    print(f"   Limite de workers: 2 (para não sobrecarregar o CPU)\n")
    
    results = {}
    start_time = datetime.now()
    
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(embed_subtitles, video): video for video in videos_validos}
        
        for future in as_completed(futures):
            video = futures[future]
            try:
                success = future.result()
                results[video] = success
            except Exception as e:
                print(f"❌ Erro ao processar {video}: {str(e)}")
                results[video] = False
    
    # Resumo
    print("\n" + "="*70)
    print("📊 RESUMO")
    print("="*70)
    
    sucesso = sum(1 for v in results.values() if v)
    total = len(results)
    
    for video, success in results.items():
        status = "✅" if success else "❌"
        output_name = f"{video.replace('.mp4', '')}_legendado.mp4"
        print(f"{status} {video} → {output_name}")
    
    elapsed = datetime.now() - start_time
    minutes = int(elapsed.total_seconds() / 60)
    
    print(f"\n✅ {sucesso}/{total} vídeos processados com sucesso!")
    print(f"⏱️  Tempo total: {minutes} minutos")

if __name__ == "__main__":
    main()
