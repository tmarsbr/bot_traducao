#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Transcritor para VÍDEOS LONGOS usando Stable-TS
Resolve o problema de "Time Drift" (desvio temporal) que ocorre em vídeos de 50min+

VANTAGENS sobre faster-whisper puro:
- DTW (Dynamic Time Warping): Realinha timestamps palavra por palavra
- VAD Silero: Detecta silêncios reais (não tenta transcrever música/ruído)
- Regroup: Agrupa palavras em frases naturais (não quebra no meio)
- Zero deriva temporal mesmo em vídeos de 2h+

QUANDO USAR:
- Vídeos com mais de 45 minutos
- Vídeos com muita música de fundo
- Quando a sincronia é crítica (legendas profissionais)
"""

import subprocess
import numpy as np
import os
from pathlib import Path

# Importações condicionais
try:
    import stable_whisper
    STABLE_TS_AVAILABLE = True
except ImportError:
    STABLE_TS_AVAILABLE = False
    print("⚠️ stable-ts não instalado. Instale com: pip install stable-ts")

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except:
    CUDA_AVAILABLE = False


def carregar_audio_pipe(arquivo_video):
    """
    Extrai áudio do vídeo direto para RAM usando FFmpeg.
    
    - Sem arquivos temporários (streaming puro)
    - 16kHz mono (formato nativo do Whisper)
    - Normalização dinâmica para lidar com picos/sussurros
    
    Returns:
        numpy.array: Áudio em float32 normalizado, ou None se falhar
    """
    print(f"🔄 Carregando áudio via pipe: {Path(arquivo_video).name}")
    
    comando = [
        "ffmpeg",
        "-i", arquivo_video,
        "-vn",                              # Sem vídeo
        "-af", "dynaudnorm=f=150:g=15",     # Normalização dinâmica
        "-ar", "16000",                     # 16kHz (Whisper native)
        "-ac", "1",                         # Mono
        "-f", "s16le",                      # PCM 16-bit raw
        "-"                                 # stdout
    ]

    try:
        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            bufsize=10**7  # Buffer grande para vídeos longos
        )
        
        dados_raw, _ = processo.communicate()
        
        if processo.returncode != 0 or len(dados_raw) == 0:
            print("❌ FFmpeg falhou ao processar o vídeo")
            return None
        
        # Converte bytes para float32 normalizado (-1.0 a 1.0)
        audio_array = np.frombuffer(dados_raw, np.int16).flatten().astype(np.float32) / 32768.0
        
        duracao_min = len(audio_array) / 16000 / 60
        print(f"✓ Áudio carregado: {duracao_min:.1f} minutos")
        
        return audio_array
        
    except Exception as e:
        print(f"❌ Erro no pipe: {e}")
        return None


def transcrever_video_longo(
    video_path, 
    modelo="large-v3", 
    usar_gpu=None,
    vad_threshold=0.35,
    idioma="en"
):
    """
    Transcreve vídeo longo usando Stable-TS com alinhamento preciso.
    
    Args:
        video_path: Caminho do vídeo
        modelo: Modelo Whisper (large-v3, medium, etc)
        usar_gpu: True/False/None (None = auto-detecta)
        vad_threshold: Sensibilidade do VAD (0.35 = padrão, menor = mais sensível)
        idioma: Código do idioma (en, pt, es, etc)
    
    Returns:
        Path do SRT gerado ou None se falhar
    """
    if not STABLE_TS_AVAILABLE:
        print("❌ stable-ts não está instalado. Execute: pip install stable-ts")
        return None
    
    # Auto-detecta GPU se não especificado
    if usar_gpu is None:
        usar_gpu = CUDA_AVAILABLE
    
    device = "cuda" if usar_gpu else "cpu"
    print(f"\n{'='*70}")
    print(f"🎬 TRANSCRIÇÃO DE VÍDEO LONGO - Stable-TS")
    print(f"{'='*70}")
    print(f"📹 Arquivo: {Path(video_path).name}")
    print(f"🔧 Modelo: {modelo}")
    print(f"💻 Device: {device.upper()}")
    print(f"🌍 Idioma: {idioma}")
    print(f"{'='*70}\n")
    
    # 1. Carregar modelo Stable-TS
    print(f"⏳ Carregando modelo {modelo}...")
    try:
        model = stable_whisper.load_model(modelo, device=device)
        print("✓ Modelo carregado\n")
    except Exception as e:
        print(f"❌ Erro ao carregar modelo: {e}")
        return None
    
    # 2. Obter áudio via pipe
    audio = carregar_audio_pipe(video_path)
    if audio is None:
        return None
    
    # 3. Transcrição com realinhamento temporal
    print(f"🎙️ Transcrevendo e alinhando timestamps...")
    print(f"   (Isso pode demorar ~2-5x o tempo do vídeo)\n")
    
    try:
        result = model.transcribe(
            audio,
            language=idioma,
            
            # VAD (Voice Activity Detection) - CRÍTICO para vídeos longos
            vad=True,                    # Usa Silero VAD (superior ao VAD nativo)
            vad_threshold=vad_threshold, # 0.35 = padrão (menor = mais sensível)
            
            # Reagrupamento para frases naturais
            regroup=True,               # Evita quebras no meio de frases
            
            # Timestamps precisos palavra por palavra
            word_timestamps=True,       # Fundamental para DTW funcionar
            
            # Anti-alucinação
            condition_on_previous_text=False,  # Evita deriva temporal
            compression_ratio_threshold=2.4,   # Detecta repetições
            no_speech_threshold=0.6,           # Ignora silêncios
        )
        
        print("✓ Transcrição concluída\n")
        
    except Exception as e:
        print(f"❌ Erro na transcrição: {e}")
        return None
    
    # 4. Salvar resultados
    base_name = os.path.splitext(video_path)[0]
    
    # SRT (padrão universal)
    srt_path = f"{base_name}_STABLE.srt"
    result.to_srt_vtt(srt_path, word_level=False)
    print(f"✅ SRT salvo: {srt_path}")
    
    # ASS (formato avançado com estilos)
    ass_path = f"{base_name}_STABLE.ass"
    result.to_ass(ass_path)
    print(f"✅ ASS salvo: {ass_path}")
    
    # Estatísticas
    num_segmentos = len(result.segments)
    print(f"\n📊 Estatísticas:")
    print(f"   • {num_segmentos} segmentos gerados")
    print(f"   • Duração: {result.duration:.1f}s ({result.duration/60:.1f}min)")
    
    print(f"\n{'='*70}")
    print("✅ PROCESSAMENTO CONCLUÍDO")
    print(f"{'='*70}\n")
    
    return srt_path


def processar_pasta_videos(pasta_entrada="proximos_para_traducao", modelo="large-v3"):
    """
    Processa todos os vídeos de uma pasta usando Stable-TS.
    Ideal para processamento em lote de vídeos longos.
    """
    if not STABLE_TS_AVAILABLE:
        print("❌ Instale stable-ts primeiro: pip install stable-ts")
        return
    
    pasta = Path(pasta_entrada)
    videos = list(pasta.glob("*.mp4"))
    
    if not videos:
        print(f"⚠️ Nenhum vídeo encontrado em {pasta_entrada}/")
        return
    
    print(f"🎬 Encontrados {len(videos)} vídeos para processar\n")
    
    sucessos = 0
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] Processando: {video.name}")
        
        # Pular se já existe SRT stable
        srt_esperado = video.with_name(f"{video.stem}_STABLE.srt")
        if srt_esperado.exists():
            print(f"⏭️ Já existe: {srt_esperado.name}")
            continue
        
        resultado = transcrever_video_longo(str(video), modelo=modelo)
        if resultado:
            sucessos += 1
    
    print(f"\n{'='*70}")
    print(f"✅ Processamento em lote concluído: {sucessos}/{len(videos)} vídeos")
    print(f"{'='*70}\n")


if __name__ == "__main__":
    import sys
    
    # Verificar instalação
    if not STABLE_TS_AVAILABLE:
        print("\n" + "="*70)
        print("⚠️ STABLE-TS NÃO INSTALADO")
        print("="*70)
        print("\nPara usar este script, instale a biblioteca:")
        print("\n  pip install stable-ts\n")
        print("Isso também instalará as dependências necessárias:")
        print("  - torch (PyTorch)")
        print("  - openai-whisper")
        print("  - stable-ts\n")
        sys.exit(1)
    
    # Exemplo de uso
    print("\n💡 MODOS DE USO:\n")
    print("1. Vídeo único:")
    print('   python transcritor_stable_ts.py "caminho/video.mp4"\n')
    print("2. Pasta inteira:")
    print('   python transcritor_stable_ts.py --pasta "proximos_para_traducao"\n')
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--pasta":
            pasta = sys.argv[2] if len(sys.argv) > 2 else "proximos_para_traducao"
            processar_pasta_videos(pasta)
        else:
            video_path = sys.argv[1]
            if os.path.exists(video_path):
                transcrever_video_longo(video_path)
            else:
                print(f"❌ Arquivo não encontrado: {video_path}")
    else:
        # Demo (edite o caminho)
        VIDEO_EXEMPLO = "proximos_para_traducao/video_longo.mp4"
        if os.path.exists(VIDEO_EXEMPLO):
            transcrever_video_longo(VIDEO_EXEMPLO)
        else:
            print("📝 Edite a variável VIDEO_EXEMPLO no script ou passe o caminho como argumento")
