#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Embutir legendas com caminho correto
"""

import os
import subprocess
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def embed_video(video_path, srt_path, output_path):
    """Embutir legenda em vídeo"""
    
    # Converter para string simples (sem Path object)
    video_str = str(video_path)
    srt_str = str(srt_path)
    output_str = str(output_path)
    
    print(f"Processando: {os.path.basename(video_str)}")
    
    cmd = [
        "ffmpeg",
        "-i", video_str,
        "-vf", f"subtitles={srt_str}",
        "-c:a", "copy",
        "-y",
        output_str
    ]
    
    result = subprocess.run(cmd, capture_output=True)
    
    if os.path.exists(output_str):
        size = os.path.getsize(output_str) / (1024 * 1024)
        print(f"  OK - {size:.1f} MB\n")
        return True
    else:
        print(f"  ERRO\n")
        if result.stderr:
            msg = result.stderr.decode(errors='ignore')
            # Mostrar apenas a mensagem de erro do subtitles
            if "Unable to parse" in msg:
                for line in msg.split('\n'):
                    if "Unable to parse" in line or "Error applying" in line:
                        print(f"  {line.strip()}")
        return False

# Limpar arquivos anteriores
print("Limpando arquivos anteriores...")
for f in os.listdir("videos_output"):
    if f.endswith("_legendado.mp4"):
        try:
            os.remove(f"videos_output/{f}")
        except:
            pass

print("\n=== EMBUTIR LEGENDAS ===\n")

videos = [
    ("videos_input/pri4.mp4", "videos_output/pri4_pt.srt", "videos_output/pri4_legendado.mp4"),
    ("videos_input/Nickey.mp4", "videos_output/Nickey_pt.srt", "videos_output/Nickey_legendado.mp4"),
    ("videos_input/elsa.mp4", "videos_output/elsa_pt.srt", "videos_output/elsa_legendado.mp4"),
    ("videos_input/Arya.mp4", "videos_output/Arya_pt.srt", "videos_output/Arya_legendado.mp4"),
]

ok = 0
for video, srt, output in videos:
    if os.path.exists(video) and os.path.exists(srt):
        if embed_video(video, srt, output):
            ok += 1
    else:
        print(f"Arquivos faltando: {video} ou {srt}\n")

print(f"Sucesso: {ok}/{len(videos)} vídeos")
