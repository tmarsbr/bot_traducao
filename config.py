from pathlib import Path
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Diretórios
BASE_DIR = Path(__file__).parent
VIDEOS_INPUT_DIR = BASE_DIR / "videos_input"
INPUT_DIR = VIDEOS_INPUT_DIR  # Alias para compatibilidade
OUTPUT_DIR = BASE_DIR / "videos_output"
LOGS_DIR = BASE_DIR / "logs"

# Criar diretórios se não existirem
OUTPUT_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)

# Configurações de Log
LOG_FILE = LOGS_DIR / "translation_agent.log"
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Configurações de Vídeo
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv']
MAX_VIDEO_SIZE_MB = 2048  # 2GB
MAX_VIDEO_DURATION_SECONDS = 3600  # 1 hora

# Idiomas Suportados
SUPPORTED_LANGUAGES = {
    'pt': 'Português',
    'en': 'English',
    'es': 'Español',
    'fr': 'Français',
    'de': 'Deutsch',
    'it': 'Italiano',
    'ja': '日本語',
    'ko': '한국어',
    'zh': '中文',
    'ru': 'Русский'
}

# Configurações de API
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "tiny")
MAX_RETRIES = 3
RETRY_DELAY = 5
BATCH_SIZE = 20
SKIP_BLOCKED_CONTENT = True
