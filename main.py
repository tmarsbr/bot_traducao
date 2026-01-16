import os
import torch
import time
from faster_whisper import WhisperModel
from config import (
    INPUT_DIR, SUBTITLES_EN_DIR, SUBTITLES_PT_DIR, VIDEOS_FINAL_DIR,
    MODELS_DIR, WHISPER_MODEL_SIZE
)
from core.utils import logger
from core.transcricao import motor_transcricao
from core.traducao import traduzir_srt_lotes
from core.legenda import embutir_legendas_ffmpeg

def main():
    logger.info("=== 🚀 INICIANDO BOT DE TRADUÇÃO V5 (MODULAR) ===")
    
    # 1. Carregar Modelo Faster-Whisper Base (Compartilhado)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute_type = "float16" if device == "cuda" else "int8"
    
    logger.info(f"⚙️ Carregando Whisper ({WHISPER_MODEL_SIZE}) em {device}...")
    try:
        model_faster = WhisperModel(
            WHISPER_MODEL_SIZE, device=device, compute_type=compute_type, 
            download_root=str(MODELS_DIR)
        )
    except Exception as e:
        logger.error(f"Erro ao carregar modelo Whisper: {e}")
        return

    # 2. Listar Vídeos para processar
    extensoes = ('.mp4', '.avi', '.mkv', '.mov', '.webm')
    videos = sorted([f for f in INPUT_DIR.glob("*") if f.suffix.lower() in extensoes])
    
    if not videos:
        logger.warning(f"Nenhum vídeo encontrado em: {INPUT_DIR}")
        return

    logger.info(f"📋 Encontrados {len(videos)} vídeos para processar.")
    
    for i, video in enumerate(videos, 1):
        nome = video.stem
        logger.info(f"\n--- 🎬 [{i}/{len(videos)}] PROCESSANDO: {video.name} ---")
        
        # Caminhos relativos
        srt_en = SUBTITLES_EN_DIR / f"{nome}_EN.srt"
        srt_pt = SUBTITLES_PT_DIR / f"{nome}_PT.srt"
        video_final = VIDEOS_FINAL_DIR / f"{nome}_PT.mp4"
        
        # --- ETAPA 1: EXTRAÇÃO (EN) ---
        if srt_en.exists():
            logger.info("✅ SRT Inglês já existe. Pulando transcrição.")
        else:
            sucesso = motor_transcricao(video, srt_en, model_faster)
            if not sucesso:
                logger.error(f"❌ Falha na transcrição de {nome}. Pulando para o próximo.")
                continue
            
        # --- ETAPA 2: TRADUÇÃO (PT) ---
        if srt_pt.exists():
            logger.info("✅ SRT PT já existe. Pulando tradução.")
        else:
            sucesso = traduzir_srt_lotes(srt_en, srt_pt)
            if not sucesso:
                logger.error(f"❌ Falha na tradução de {nome}. Pulando embutimento.")
                continue
            
        # --- ETAPA 3: EMBUTIR (HARDCODE) ---
        if video_final.exists():
            logger.info(f"✅ Vídeo final já existe: {video_final.name}")
        else:
            sucesso = embutir_legendas_ffmpeg(video, srt_pt, video_final)
            if sucesso:
                logger.info(f"✨ Concluído com sucesso: {video_final.name}")
            else:
                logger.error(f"❌ Falha ao embutir legenda em {nome}")

        # Cooldown básico entre vídeos
        if i < len(videos):
            time.sleep(2)
        
    logger.info("\n=== 🏁 TODOS OS VÍDEOS PROCESSADOS! ===")

if __name__ == "__main__":
    main()
