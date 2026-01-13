#!/usr/bin/env python3
"""
Script para processar todos os vídeos em lote
Processa múltiplos vídeos de forma automatizada
"""

import os
import sys
import glob
import subprocess
from pathlib import Path
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_pending_videos():
    """Retorna lista de vídeos que ainda não foram processados"""
    videos_input = Path("videos_input")
    
    # Encontrar todos os mp4
    all_videos = list(videos_input.glob("*.mp4"))
    
    # Filtrar vídeos já processados (com _with_subtitles)
    pending_videos = []
    for video in all_videos:
        if "_with_subtitles" not in video.name:
            # Verificar se já existe versão processada
            processed_name = video.stem + "_with_subtitles.mp4"
            processed_path = videos_input / processed_name
            
            if not processed_path.exists():
                pending_videos.append(video)
    
    return sorted(pending_videos)

def process_video(video_path):
    """Processa um único vídeo"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Processando: {video_path.name}")
    logger.info(f"{'='*60}\n")
    
    cmd = [
        sys.executable,
        "video_translator.py",
        "--input_video", str(video_path),
        "--target_language", "pt",
        "--embed_subs",
        "--auto_transcribe"
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=False,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info(f"✓ Vídeo processado com sucesso: {video_path.name}")
            return True
        else:
            logger.error(f"✗ Erro ao processar {video_path.name} (código: {result.returncode})")
            return False
            
    except KeyboardInterrupt:
        logger.warning(f"\n⚠️ Processamento interrompido pelo usuário em: {video_path.name}")
        raise
    except Exception as e:
        logger.error(f"✗ Erro inesperado ao processar {video_path.name}: {e}")
        return False

def main():
    logger.info("🎬 Iniciando processamento em lote de vídeos")
    
    # Obter lista de vídeos pendentes
    pending_videos = get_pending_videos()
    
    if not pending_videos:
        logger.info("✓ Nenhum vídeo pendente para processar!")
        return 0
    
    logger.info(f"\n📋 Encontrados {len(pending_videos)} vídeos para processar:")
    for i, video in enumerate(pending_videos, 1):
        size_mb = video.stat().st_size / (1024 * 1024)
        logger.info(f"  {i}. {video.name} ({size_mb:.2f} MB)")
    
    # Processar cada vídeo
    processed = 0
    failed = 0
    
    try:
        for i, video in enumerate(pending_videos, 1):
            logger.info(f"\n\n{'#'*60}")
            logger.info(f"VÍDEO {i}/{len(pending_videos)}")
            logger.info(f"{'#'*60}")
            
            success = process_video(video)
            
            if success:
                processed += 1
            else:
                failed += 1
                
    except KeyboardInterrupt:
        logger.warning("\n\n⚠️ Processamento interrompido pelo usuário")
    
    # Resumo final
    logger.info(f"\n\n{'='*60}")
    logger.info(f"RESUMO FINAL")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Processados com sucesso: {processed}")
    logger.info(f"✗ Falharam: {failed}")
    logger.info(f"📊 Pendentes: {len(pending_videos) - processed - failed}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
