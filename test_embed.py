#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para embutir legendas com debug detalhado
"""

import os
import subprocess
from pathlib import Path

VIDEOS_INPUT_DIR = Path("videos_input")
VIDEOS_OUTPUT_DIR = Path("videos_output")

def test_single_embed():
    """Testa embutição de um vídeo com debug"""
    
    video_file = "pri4.mp4"
    video_path = VIDEOS_INPUT_DIR / video_file
    srt_file = VIDEOS_OUTPUT_DIR / f"{video_file.replace('.mp4', '')}_pt.srt"
    output_file = VIDEOS_OUTPUT_DIR / f"{video_file.replace('.mp4', '')}_legendado.mp4"
    
    print(f"📁 Verificando arquivos:")
    print(f"   Vídeo: {video_path} (existe: {video_path.exists()})")
    print(f"   SRT: {srt_file} (existe: {srt_file.exists()})")
    print(f"   Output: {output_file}")
    
    if not video_path.exists() or not srt_file.exists():
        print("❌ Arquivos faltando!")
        return
    
    # Substituir barras invertidas por forward slash para FFmpeg (Windows)
    video_abs = str(video_path.resolve()).replace("\\", "/")
    srt_abs = str(srt_file.resolve()).replace("\\", "/")
    output_abs = str(output_file.resolve()).replace("\\", "/")
    
    print(f"\n📍 Caminhos absolutos:")
    print(f"   Vídeo: {video_abs}")
    print(f"   SRT: {srt_abs}")
    print(f"   Output: {output_abs}")
    
    # Remover se já existe
    if output_file.exists():
        print(f"\n🗑️  Removendo arquivo anterior...")
        output_file.unlink()
    
    # Para FFmpeg no Windows, usar escape apropriado
    srt_escaped = str(srt_file.resolve()).replace("\\", "\\\\")
    
    cmd = [
        "ffmpeg",
        "-i", str(video_path.resolve()),
        "-vf", f"subtitles={srt_escaped}",
        "-c:a", "copy",
        "-y",
        str(output_file.resolve())
    ]
    
    print(f"\n🎬 Comando FFmpeg:")
    print(f"   {' '.join(cmd)}")
    
    print(f"\n⏳ Processando...")
    result = subprocess.run(cmd, capture_output=False, text=True)
    
    print(f"\n📊 Resultado:")
    print(f"   Return code: {result.returncode}")
    print(f"   Arquivo criado: {output_file.exists()}")
    
    if output_file.exists():
        size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"   Tamanho: {size_mb:.1f} MB")
        print(f"✅ Sucesso!")
    else:
        print(f"❌ Falha ao criar arquivo!")

if __name__ == "__main__":
    test_single_embed()
