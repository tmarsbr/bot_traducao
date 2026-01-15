#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para extrair SRT de múltiplos vídeos em paralelo
"""

import os
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel
import json
from datetime import timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configurações
VIDEOS_INPUT_DIR = Path("videos_input")
VIDEOS_OUTPUT_DIR = Path("videos_output")
VIDEOS = [
    "pri4.mp4",
    "Nickey.mp4",
    "elsa.mp4",
    "Arya.mp4"
]

def format_timestamp(seconds):
    """Formata segundos em HH:MM:SS,mmm"""
    td = timedelta(seconds=seconds)
    hours, remainder = divmod(int(td.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    millis = int((td.total_seconds() % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"

def transcribe_video(video_file):
    """Transcreve um vídeo para SRT"""
    video_path = VIDEOS_INPUT_DIR / video_file
    output_srt = VIDEOS_OUTPUT_DIR / f"{video_file.replace('.mp4', '')}_EN.srt"
    
    print(f"\n{'='*70}")
    print(f"🎬 PROCESSANDO: {video_file}")
    print(f"{'='*70}")
    
    # Extrair áudio com FFmpeg
    audio_tmp = f"temp_audio_{video_file.replace('.mp4', '')}.wav"
    cmd_extract = [
        "ffmpeg", "-i", str(video_path),
        "-q:a", "9", "-n", audio_tmp
    ]
    
    print(f"🔊 Extraindo áudio...")
    result = subprocess.run(cmd_extract, capture_output=True, text=True)
    
    if not os.path.exists(audio_tmp):
        print(f"❌ Erro ao extrair áudio de {video_file}")
        return False
    
    # Transcrever com Whisper
    print(f"🎤 Transcrevendo com Whisper (este modelo pode demora)...")
    try:
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        segments, info = model.transcribe(audio_tmp, language="en", beam_size=5)
        
        # Salvar SRT
        with open(output_srt, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, 1):
                start = format_timestamp(segment.start)
                end = format_timestamp(segment.end)
                text = segment.text.strip()
                f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
        
        duration = info.duration
        print(f"✅ Sucesso!")
        print(f"   📝 SRT salvo em: {output_srt}")
        print(f"   🕐 Duração: {format_timestamp(duration)}")
        
        # Limpar arquivo temporário
        if os.path.exists(audio_tmp):
            os.remove(audio_tmp)
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao transcrever {video_file}: {str(e)}")
        if os.path.exists(audio_tmp):
            os.remove(audio_tmp)
        return False

def main():
    """Processa todos os vídeos em paralelo"""
    print("\n" + "="*70)
    print("🎬 EXTRAIR SRT DE MÚLTIPLOS VÍDEOS")
    print("="*70)
    
    # Verificar arquivos
    videos_faltando = []
    for video in VIDEOS:
        if not (VIDEOS_INPUT_DIR / video).exists():
            videos_faltando.append(video)
    
    if videos_faltando:
        print(f"\n⚠️  Vídeos não encontrados:")
        for v in videos_faltando:
            print(f"   - {v}")
        return
    
    print(f"\n📁 Vídeos encontrados:")
    for v in VIDEOS:
        path = VIDEOS_INPUT_DIR / v
        size_mb = path.stat().st_size / (1024 * 1024)
        print(f"   ✓ {v} ({size_mb:.1f} MB)")
    
    # Processar em paralelo (mas com limite para não sobrecarregar CPU)
    print(f"\n🚀 Iniciando transcrição de {len(VIDEOS)} vídeos...")
    print(f"   Limite de workers: 2 (para não sobrecarregar o CPU)\n")
    
    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(transcribe_video, video): video for video in VIDEOS}
        
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
        print(f"{status} {video}")
    
    print(f"\n✅ {sucesso}/{total} vídeos processados com sucesso!")

if __name__ == "__main__":
    main()
