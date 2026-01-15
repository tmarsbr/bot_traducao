#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Isola voz de vídeos usando Spleeter e re-transcreve com Whisper
Cria SRTs limpos com melhor qualidade de áudio
"""

import os
import subprocess
import tempfile
import shutil
from pathlib import Path
from faster_whisper import WhisperModel

# Configurações
PASTA_ENTRADA = "proximos_para_traducao"
PASTA_SAIDA = "videos_output"
PASTA_SEPARADO = "audio_separado"
MODELO = "tiny"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

def instalar_spleeter():
    """Instala Spleeter"""
    print("📦 Instalando Spleeter...")
    subprocess.run([
        'pip', 'install', '-U', 'spleeter',
        '--no-cache-dir'
    ], check=True)
    print("✅ Spleeter instalado!")

def extrair_audio(video_path):
    """Extrai áudio do vídeo"""
    audio_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_tmp.close()
    
    cmd = [
        'ffmpeg', '-i', video_path,
        '-acodec', 'pcm_s16le',
        '-ar', '44100',
        '-ac', '2',
        '-v', 'error',
        '-y',
        audio_tmp.name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        return audio_tmp.name
    else:
        if os.path.exists(audio_tmp.name):
            os.unlink(audio_tmp.name)
        return None

def isolar_voz(audio_path):
    """Isola voz usando Spleeter via Python"""
    try:
        from spleeter.separator import Separator
        
        print("  🎵 Isolando voz com Spleeter...")
        
        # Usar modelo 2stems (vocals + accompaniment)
        separator = Separator("spleeter:2stems", multiprocess=False)
        
        # Output temporário
        output_tmp = tempfile.mkdtemp()
        
        # Separar
        separator.separate_to_file(audio_path, output_tmp, overwrite=True)
        
        # Encontrar arquivo de voz
        stem_name = Path(audio_path).stem
        voz_path = os.path.join(output_tmp, stem_name, 'vocals.wav')
        
        if os.path.exists(voz_path):
            return voz_path, output_tmp
        else:
            shutil.rmtree(output_tmp, ignore_errors=True)
            return None, None
            
    except Exception as e:
        print(f"  ⚠️  Erro ao isolar: {str(e)[:100]}")
        return None, None

def transcrever_voz(voz_path, model):
    """Transcreve áudio isolado com Whisper"""
    try:
        segments, info = model.transcribe(
            voz_path,
            language="en",
            beam_size=5,
            without_timestamps=False
        )
        return list(segments)
    except Exception as e:
        print(f"  ❌ Erro ao transcrever: {e}")
        return None

def salvar_srt(segments, output_path):
    """Salva transcrição em SRT"""
    contador = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for segment in segments:
            if segment.text.strip():
                contador += 1
                start = format_timestamp(segment.start)
                end = format_timestamp(segment.end)
                text = segment.text.strip()
                f.write(f"{contador}\n{start} --> {end}\n{text}\n\n")
    
    return contador

def format_timestamp(seconds):
    """Converte segundos para formato SRT HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def processar_video(video_path, model):
    """Processa um vídeo: extrai -> isola -> transcreve"""
    nome_video = Path(video_path).stem
    srt_saida = os.path.join(PASTA_SAIDA, f"{nome_video}_EN_CLEAN.srt")
    
    # Pular se já existe
    if os.path.exists(srt_saida):
        print(f"  ✓ {nome_video}_EN_CLEAN.srt já existe")
        return True
    
    temp_dir = None
    try:
        print(f"  1️⃣  Extraindo áudio...")
        audio = extrair_audio(video_path)
        if not audio:
            print(f"  ❌ Falha ao extrair áudio")
            return False
        
        print(f"  2️⃣  Isolando voz...")
        voz, temp_dir = isolar_voz(audio)
        if not voz:
            print(f"  ❌ Falha ao isolar voz")
            if os.path.exists(audio):
                os.unlink(audio)
            return False
        
        print(f"  3️⃣  Transcrevendo voz isolada...")
        segments = transcrever_voz(voz, model)
        if not segments:
            print(f"  ❌ Falha ao transcrever")
            if os.path.exists(audio):
                os.unlink(audio)
            return False
        
        print(f"  4️⃣  Salvando SRT...")
        contador = salvar_srt(segments, srt_saida)
        
        # Limpeza
        if os.path.exists(audio):
            os.unlink(audio)
        
        print(f"  ✅ {contador} legendas LIMPAS criadas")
        return True
        
    except Exception as e:
        print(f"  ❌ Erro geral: {str(e)[:80]}")
        return False
    finally:
        # Limpeza de diretório temporário
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except:
                pass

def main():
    # Instalar Spleeter
    try:
        from spleeter.separator import Separator
    except ImportError:
        print("⚠️  Spleeter não encontrado. Instalando...")
        instalar_spleeter()
    
    # Carregar Whisper
    print("⏳ Carregando modelo Whisper...")
    model = WhisperModel(MODELO, device=DEVICE, compute_type=COMPUTE_TYPE)
    print("✅ Modelo carregado!\n")
    
    # Criar pastas de saída
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    os.makedirs(PASTA_SEPARADO, exist_ok=True)
    
    # Listar vídeos
    videos = sorted([
        os.path.join(PASTA_ENTRADA, f)
        for f in os.listdir(PASTA_ENTRADA)
        if f.lower().endswith('.mp4')
    ])
    
    print(f"🎬 Processando {len(videos)} vídeos com isolamento de voz\n")
    
    sucesso = 0
    for i, video in enumerate(videos, 1):
        nome = Path(video).stem[:40]
        print(f"[{i}/{len(videos)}] 📹 {nome}...")
        
        if processar_video(video, model):
            sucesso += 1
    
    # Resumo
    print("\n" + "="*70)
    print(f"✅ Concluído: {sucesso}/{len(videos)} vídeos com voz isolada")
    print(f"📁 Novos SRTs salvos com sufixo '_EN_CLEAN'")
    print("="*70 + "\n")
    
    print("💡 Próximo passo: Traduzir os SRTs _CLEAN com DeepL ou manual")

if __name__ == "__main__":
    main()
