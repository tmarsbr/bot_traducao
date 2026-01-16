import subprocess
import os
from pathlib import Path
from core.utils import logger

def format_timestamp(seconds):
    """Converte segundos para HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def quebrar_legenda_netflix(texto, max_chars=42, max_linhas=2):
    """Formata texto para padrão visual agradável (Netflix style)."""
    texto = texto.replace('\n', ' ').strip()
    palavras = texto.split()
    linhas = []
    linha_atual = ""
    
    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if len(teste) <= max_chars:
            linha_atual = teste
        else:
            if linha_atual: linhas.append(linha_atual)
            linha_atual = palavra
    if linha_atual: linhas.append(linha_atual)
    
    return "\n".join(linhas[:max_linhas])

def embutir_legendas_ffmpeg(video_path, srt_path, output_path):
    """Queima a legenda no vídeo (Hardcode) com FFmpeg."""
    if not os.path.exists(srt_path):
        logger.error(f"SRT não encontrado: {srt_path}")
        return False

    # Tratamento de caminho para FFmpeg (especialmente no Windows com : e \)
    srt_absolute = str(Path(srt_path).absolute()).replace("\\", "/").replace(":", "\\:")
    
    # Estilo visual profissional: Fundo opaco (BorderStyle=3)
    estilo = "FontSize=20,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=3,Outline=1,Shadow=0,Alignment=2"

    comando = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vf", f"subtitles='{srt_absolute}':force_style='{estilo}'",
        "-c:a", "copy", str(output_path)
    ]
    
    try:
        logger.info(f"📽️ Renderizando vídeo: {Path(output_path).name}")
        subprocess.run(comando, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except subprocess.CalledProcessError:
        logger.error(f"❌ Erro crítico no FFmpeg ao processar {video_path}")
        return False
