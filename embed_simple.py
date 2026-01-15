#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simples para embutir legendas
"""

import os
import subprocess
import sys
from pathlib import Path

# Força UTF-8
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VIDEOS_INPUT_DIR = Path("videos_input")
VIDEOS_OUTPUT_DIR = Path("videos_output")

def embed_subtitle_simple(video_file, srt_name):
    """Embutir legenda usando FFmpeg"""
    
    video_path = VIDEOS_INPUT_DIR / video_file
    srt_path = VIDEOS_OUTPUT_DIR / srt_name
    output_path = VIDEOS_OUTPUT_DIR / f"{video_file.replace('.mp4', '')}_legendado.mp4"
    
    print(f"\n=== {video_file} ===")
    print(f"Video: {video_path.exists()}")
    print(f"SRT: {srt_path.exists()}")
    
    if not video_path.exists() or not srt_path.exists():
        print("ERRO: Arquivos faltando!")
        return False
    
    # Usar caminho com escape
    srt_escape = str(srt_path.resolve())
    
    cmd = [
        "ffmpeg",
        "-i", str(video_path.resolve()),
        "-vf", f"subtitles={srt_escape}",
        "-c:a", "copy",
        "-y",
        str(output_path.resolve())
    ]
    
    print(f"Processando...")
    result = subprocess.run(cmd, capture_output=True)
    
    if output_path.exists():
        size = output_path.stat().st_size / (1024 * 1024)
        print(f"OK! {size:.1f} MB")
        return True
    else:
        print("ERRO ao criar arquivo!")
        if result.stderr:
            err_text = result.stderr.decode(errors='ignore')
            print("Stderr:")
            print(err_text[-1000:])
        return False

# Executar
videos = [
    ("pri4.mp4", "pri4_pt.srt"),
    ("Nickey.mp4", "Nickey_pt.srt"),
    ("elsa.mp4", "elsa_pt.srt"),
    ("Arya.mp4", "Arya_pt.srt"),
]

print("=== EMBUTIR LEGENDAS ===\n")
for video, srt in videos:
    embed_subtitle_simple(video, srt)
