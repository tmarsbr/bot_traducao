import os
import subprocess
import numpy as np
import torch
import stable_whisper
from faster_whisper import WhisperModel
from config import MODELS_DIR, WHISPER_MODEL
from core.utils import logger, obter_duracao_video
from core.legenda import format_timestamp, quebrar_legenda_netflix

# Constantes de Decisão
DURACAO_LIMITE_STABLE = 1200 # 20 minutos
THREADS_CPU = 12 # Otimizado para Ryzen 7 3800X

def carregar_audio_pipe_otimizado(video_path):
    """Extrai áudio com filtro 'Aparelho Auditivo' reforçado para sussurros."""
    # Filtro: dynaudnorm agressivo (g=31) para capturar sussurros
    filtro = "afftdn=nr=20:nf=-30,dynaudnorm=f=75:g=31:p=0.95:m=10,highpass=f=200,lowpass=f=3000"
    cmd = [
        "ffmpeg", "-i", str(video_path), "-af", filtro,
        "-ar", "16000", "-ac", "1", "-f", "s16le", "-vn", "-"
    ]
    try:
        processo = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**7)
        out, _ = processo.communicate(timeout=300)
        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    except Exception as e:
        logger.error(f"Erro no Pipe de Áudio: {e}")
        return None

def motor_transcricao(video_path, srt_saida, model_faster_instance):
    """Decide o método de transcrição baseado na duração e executa com segurança."""
    duracao = obter_duracao_video(video_path) or 0
    nome_video = Path(video_path).stem
    
    # Lógica Híbrida: > 20min usa Stable-TS para evitar drift
    usar_stable = (duracao > DURACAO_LIMITE_STABLE)
    metodo = "Stable-TS 🦁" if usar_stable else "Faster-Whisper ⚡"
    
    logger.info(f"Processando '{nome_video}' ({int(duracao/60)}min) via {metodo}")

    try:
        audio = carregar_audio_pipe_otimizado(video_path)
        if audio is None: return False

        if usar_stable:
            # --- STABLE-TS (Modo Seguro e Preciso) ---
            has_gpu = torch.cuda.is_available()
            model_stable = stable_whisper.load_faster_whisper(
                WHISPER_MODEL, 
                device="cuda" if has_gpu else "cpu",
                compute_type="float16" if has_gpu else "int8",
                cpu_threads=4 if has_gpu else THREADS_CPU,
                download_root=str(MODELS_DIR)
            )
            
            # VAD Sensível (0.3) para sussurros
            result = model_stable.transcribe(
                audio, language="en", vad=True, vad_threshold=0.3,
                vad_parameters=dict(min_silence_duration_ms=500, speech_pad_ms=200),
                regroup=True
            )
            
            # Salva versão base IMEDIATAMENTE (Blindagem contra perda de trabalho)
            result.to_srt_vtt(str(srt_saida), word_level=False)
            
            # Pós-processamento Anti-Chiclete
            try:
                if hasattr(result, 'clamp_max_duration'): result.clamp_max_duration(7.0)
                if hasattr(result, 'split_by_gap'): result.split_by_gap(0.5)
                if hasattr(result, 'remove_all_empty'): result.remove_all_empty()
                result.to_srt_vtt(str(srt_saida), word_level=False) # Sobrescreve com otimizado
            except Exception as e_opt:
                logger.warning(f"Otimização falhou (usando base): {e_opt}")
                
        else:
            # --- FASTER-WHISPER (Modo Rápido) ---
            segments, _ = model_faster_instance.transcribe(
                audio, language="en", beam_size=5, vad_filter=True,
                vad_parameters=dict(threshold=0.5)
            )
            
            with open(srt_saida, 'w', encoding='utf-8') as f:
                cnt = 1
                for seg in segments:
                    txt = quebrar_legenda_netflix(seg.text)
                    f.write(f"{cnt}\n{format_timestamp(seg.start)} --> {format_timestamp(seg.end)}\n{txt}\n\n")
                    cnt += 1
                    
        return True

    except Exception as e:
        logger.error(f"Erro crítico na transcrição de {nome_video}: {e}")
        return False
