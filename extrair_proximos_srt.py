#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrai SRT em inglês de todos os vídeos da pasta proximos_para_traducao
"""

import os
import sys
from pathlib import Path
import tempfile
import subprocess

from faster_whisper import WhisperModel

# Configurações
PASTA_ENTRADA = "proximos_para_traducao"
PASTA_SAIDA = "videos_output"
MODELO = "tiny"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# Carregar modelo uma única vez
print("⏳ Carregando modelo Whisper...")
model = WhisperModel(MODELO, device=DEVICE, compute_type=COMPUTE_TYPE)
print("✅ Modelo carregado!\n")

def extrair_srt(video_path):
    """Extrai SRT de um vídeo usando Whisper"""
    nome_video = Path(video_path).stem
    srt_saida = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
    
    # Pular se já existe
    if os.path.exists(srt_saida):
        print(f"✓ {nome_video}_EN.srt já existe")
        return nome_video, True
    
    try:
        print(f"📹 Processando: {nome_video[:50]}...")
        
        # Extrair áudio temporário com ffmpeg
        audio_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_tmp.close()
        
        try:
            # Usar subprocess em vez de os.system para melhor controle
            cmd = [
                'ffmpeg', '-i', video_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                '-v', 'error',
                '-y',
                audio_tmp.name
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0:
                print(f"  ⚠️  FFmpeg erro: {result.stderr[:100]}")
                return nome_video, False
            
            # Transcrever com disable_tqdm para evitar problemas de threading
            segments, info = model.transcribe(
                audio_tmp.name, 
                language="en", 
                beam_size=5,
                without_timestamps=False
            )
            
            # Salvar SRT
            contador = 0
            with open(srt_saida, 'w', encoding='utf-8') as f:
                for segment in segments:
                    contador += 1
                    start = format_timestamp(segment.start)
                    end = format_timestamp(segment.end)
                    text = segment.text.strip()
                    if text:
                        f.write(f"{contador}\n{start} --> {end}\n{text}\n\n")
            
            print(f"  ✅ {contador} legendas criadas")
            return nome_video, True
            
        finally:
            if os.path.exists(audio_tmp.name):
                try:
                    os.unlink(audio_tmp.name)
                except:
                    pass
    
    except Exception as e:
        print(f"  ❌ Erro: {str(e)[:80]}")
        return nome_video, False

def format_timestamp(seconds):
    """Converte segundos para formato SRT HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def main():
    # Criar pasta de saída se não existir
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    # Listar vídeos
    videos = sorted([
        os.path.join(PASTA_ENTRADA, f) 
        for f in os.listdir(PASTA_ENTRADA) 
        if f.lower().endswith('.mp4')
    ])
    
    print(f"\n🎬 Encontrados {len(videos)} vídeos\n")
    
    # Processar sequencialmente (evita problemas com Whisper e threading)
    resultados = {}
    for i, video in enumerate(videos, 1):
        print(f"[{i}/{len(videos)}] ", end="")
        nome, sucesso = extrair_srt(video)
        resultados[nome] = sucesso
    
    # Resumo
    print("\n" + "="*60)
    sucesso = sum(1 for v in resultados.values() if v)
    total = len(resultados)
    falhados = total - sucesso
    
    print(f"✅ Concluído: {sucesso}/{total} vídeos processados")
    if falhados > 0:
        print(f"⚠️  {falhados} vídeo(s) falharam (sem áudio ou formato inválido)")
    print("="*60 + "\n")
    
    if sucesso == total:
        print("🎉 Todos os SRTs foram extraídos com sucesso!")
    else:
        print(f"💡 Dica: Verifique se os vídeos falhados têm áudio válido")

if __name__ == "__main__":
    main()
