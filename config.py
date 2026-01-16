import os
from pathlib import Path
from dotenv import load_dotenv

# --- Detecção de Ambiente ---
IS_COLAB = os.path.exists("/content/drive/MyDrive")

# --- Carregar Variáveis ---
load_dotenv()

# --- Configurações para Windows (evita erro de symlink) ---
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

# --- Diretórios ---
if IS_COLAB:
    # Ajuste este caminho se sua pasta no Drive tiver outro nome
    BASE_DIR = Path("/content/drive/MyDrive/bot_traducao")
else:
    BASE_DIR = Path(__file__).parent.resolve()

# Definição das Subpastas
INPUT_DIR = BASE_DIR / "proximos_para_traducao"
VIDEOS_INPUT_DIR = BASE_DIR / "videos_input" # Legado
OUTPUT_DIR = BASE_DIR / "videos_output"
MODELS_DIR = BASE_DIR / "models"
LOGS_DIR = BASE_DIR / "logs"

# Subpastas de Saída
SUBTITLES_EN_DIR = OUTPUT_DIR / "subtitles_en"
SUBTITLES_PT_DIR = OUTPUT_DIR / "subtitles_pt"
VIDEOS_FINAL_DIR = OUTPUT_DIR / "videos_translated"
VIDEOS_OUTPUT_DIR = VIDEOS_FINAL_DIR # Alias legado

# Criar tudo se não existir
for d in [INPUT_DIR, VIDEOS_INPUT_DIR, OUTPUT_DIR, MODELS_DIR, LOGS_DIR, 
          SUBTITLES_EN_DIR, SUBTITLES_PT_DIR, VIDEOS_FINAL_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# --- Configurações da IA ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")

# --- Configurações Técnicas ---
MAX_VIDEO_SIZE_MB = 2048
MAX_VIDEO_DURATION_SECONDS = 3600
BATCH_SIZE = 20
RETRY_DELAY = 5
MAX_RETRIES = 3
