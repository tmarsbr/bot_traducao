import logging
import subprocess
from pathlib import Path
from config import LOGS_DIR

def setup_logger():
    """Configura um logger que grava em arquivo e mostra na tela."""
    logger = logging.getLogger("BotTraducaoV5")
    logger.setLevel(logging.INFO)
    
    # Formato
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Handler Arquivo
    file_handler = logging.FileHandler(LOGS_DIR / "execucao.log", encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Handler Tela (Console)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    
    # Evita duplicar logs se chamar a função 2x
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)
        
    return logger

logger = setup_logger()

def obter_duracao_video(video_path):
    """Obtém duração em segundos via ffprobe."""
    try:
        cmd = [
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.error(f"Erro ao medir duração: {e}")
    return None
