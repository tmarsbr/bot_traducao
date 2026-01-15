# Módulo para extração e processamento de áudio/vídeo

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional
from logger_config import setup_logger
from config import VIDEOS_OUTPUT_DIR
from utils import format_timestamp
from alive_progress import alive_bar
import time

logger = setup_logger(__name__)


class VideoProcessor:
    """Classe para processar vídeos usando ffmpeg."""
    
    def __init__(self):
        self.check_ffmpeg()
    
    @staticmethod
    def check_ffmpeg() -> bool:
        """Verifica se ffmpeg está instalado."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            logger.info("ffmpeg detectado e pronto para usar")
            return True
        except FileNotFoundError:
            logger.error("ffmpeg não encontrado! Instale com: pip install ffmpeg-python ou baixe em ffmpeg.org")
            return False
    
    @staticmethod
    def extract_audio(video_path: str, output_audio_path: str = None, format: str = "wav") -> Optional[str]:
        """
        Extrai áudio de um vídeo.
        
        Args:
            video_path: Caminho do vídeo
            output_audio_path: Caminho de saída (opcional)
            format: Formato de áudio (wav, mp3, aac)
            
        Returns:
            Caminho do arquivo de áudio extraído
        """
        try:
            video = Path(video_path)
            if not video.exists():
                logger.error(f"Vídeo não encontrado: {video_path}")
                return None
            
            if output_audio_path is None:
                output_audio_path = video.parent / f"{video.stem}_audio.{format}"
            
            logger.info(f"Extraindo áudio: {video_path} → {output_audio_path}")
            
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-q:a", "9",
                "-n",  # não sobrescrever
                str(output_audio_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0 and Path(output_audio_path).exists():
                logger.info(f"Áudio extraído com sucesso: {output_audio_path}")
                return str(output_audio_path)
            else:
                logger.error(f"Erro ao extrair áudio: {result.stderr}")
                return None
        
        except Exception as e:
            logger.error(f"Exceção ao extrair áudio: {str(e)}")
            return None
    
    @staticmethod
    def extract_subtitles(video_path: str, output_srt_path: str = None) -> Optional[str]:
        """
        Extrai legendas (SRT) de um vídeo.
        
        Args:
            video_path: Caminho do vídeo
            output_srt_path: Caminho de saída (opcional)
            
        Returns:
            Caminho do arquivo SRT extraído
        """
        try:
            video = Path(video_path)
            if not video.exists():
                logger.error(f"Vídeo não encontrado: {video_path}")
                return None
            
            if output_srt_path is None:
                output_srt_path = video.parent / f"{video.stem}.srt"
            
            logger.info(f"Extraindo legendas: {video_path}")
            
            # Usar ffmpeg para extrair stream de legenda
            cmd = [
                "ffmpeg",
                "-i", str(video_path),
                "-map", "0:s:0",  # mapear primeiro stream de legenda
                "-c", "copy",
                "-n",  # não sobrescrever
                str(output_srt_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0 and Path(output_srt_path).exists():
                logger.info(f"Legendas extraídas: {output_srt_path}")
                return str(output_srt_path)
            else:
                logger.warning(f"Nenhuma legenda encontrada no vídeo")
                return None
        
        except Exception as e:
            logger.error(f"Exceção ao extrair legendas: {str(e)}")
            return None
    
    @staticmethod
    def get_video_duration(video_path: str) -> Optional[float]:
        """
        Obtém a duração de um vídeo em segundos.
        
        Args:
            video_path: Caminho do vídeo
            
        Returns:
            Duração em segundos ou None se falhar
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
            
            if result.returncode == 0:
                return float(result.stdout.strip())
            return None
        except Exception as e:
            logger.error(f"Erro ao obter duração do vídeo: {str(e)}")
            return None
    
    @staticmethod
    def embed_subtitles(video_path: str, srt_path: str, output_video_path: str = None) -> Optional[str]:
        """
        Embutir legendas em um vídeo usando ffmpeg.
        
        Args:
            video_path: Caminho do vídeo
            srt_path: Caminho do arquivo SRT
            output_video_path: Caminho de saída (opcional)
            
        Returns:
            Caminho do vídeo com legendas embutidas
        """
        try:
            video = Path(video_path)
            if not video.exists():
                logger.error(f"Vídeo não encontrado: {video_path}")
                return None
            
            if not Path(srt_path).exists():
                logger.error(f"Legendas não encontradas: {srt_path}")
                return None
            
            if output_video_path is None:
                output_video_path = VIDEOS_OUTPUT_DIR / f"{video.stem}_with_subtitles{video.suffix}"
            
            logger.info(f"Embutindo legendas: {output_video_path}")
            
            # Obter duração do vídeo para barra de progresso
            duration = VideoProcessor.get_video_duration(video_path)
            
            # CORREÇÃO: libass no Windows só consegue acessar arquivos no mesmo diretório do vídeo
            # Copiar SRT para a pasta do vídeo em vez de C:\Temp
            video_dir = Path(video_path).parent
            temp_srt = video_dir / "_temp_subtitle_embed.srt"
            
            try:
                shutil.copy2(srt_path, temp_srt)
                logger.info(f"SRT temporário criado em: {temp_srt}")
                
                # Verificar se o arquivo foi copiado corretamente
                if not temp_srt.exists():
                    logger.error(f"Falha ao copiar SRT para: {temp_srt}")
                    return None
                
                logger.info(f"Arquivo SRT verificado, tamanho: {temp_srt.stat().st_size} bytes")
                
                # Caminhos do vídeo
                video_abs = str(Path(video_path).absolute())
                output_abs = str(Path(output_video_path).absolute())
                srt_filename = temp_srt.name  # Nome relativo do arquivo
                
                logger.info("Embutindo legendas (hard subs) no vídeo...")
                logger.info(f"Duração estimada: {duration:.0f}s" if duration else "Duração desconhecida")
                
                # HARD SUBTITLES: Queimar legendas no vídeo usando filtro subtitles
                # Executar ffmpeg a partir do diretório do vídeo para usar caminho relativo
                # Isso evita o problema de escape de caminhos do Windows com libass
                # force_style: FontSize=32 (maior), Outline=0 (sem contorno), BackColour (preto com transparência 80%), BorderStyle=4 (box)
                cmd = [
                    "ffmpeg",
                    "-i", video_abs,
                    "-vf", f"subtitles={srt_filename}:force_style='FontSize=32,Outline=0,BackColour=&H80000000,BorderStyle=4,MarginV=25'",
                    "-c:a", "copy",
                    "-sn",  # Remover todas as trilhas de legenda existentes
                    "-y",  # sobrescrever
                    output_abs
                ]
                
                logger.info(f"Comando: ffmpeg -i video -vf subtitles={srt_filename} (cwd={video_dir})")
                
                # Executar ffmpeg com Popen para mostrar progresso
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    cwd=str(video_dir)  # Executar no diretório do vídeo
                )
                
                # Mostrar progresso
                if duration:
                    from alive_progress import alive_bar
                    import re
                    
                    stderr_output = []
                    with alive_bar(int(duration), title='Encoding', bar='smooth', spinner='dots_waves') as bar:
                        current_time = 0
                        for line in process.stderr:
                            stderr_output.append(line)
                            # Procurar por "time=HH:MM:SS.xx" no output do ffmpeg
                            time_match = re.search(r'time=(\d+):(\d+):(\d+)', line)
                            if time_match:
                                h, m, s = map(int, time_match.groups())
                                new_time = h * 3600 + m * 60 + s
                                if new_time > current_time:
                                    bar(new_time - current_time)
                                    current_time = new_time
                        
                        # Completar a barra
                        if current_time < int(duration):
                            bar(int(duration) - current_time)
                    
                    process.wait()
                    result_stderr = ''.join(stderr_output)
                else:
                    # Sem duração conhecida, apenas executar
                    _, result_stderr = process.communicate()
                
                result_returncode = process.returncode
                
                # Verificar resultado ANTES de limpar
                if result_returncode == 0 and Path(output_video_path).exists():
                    logger.info(f"Vídeo com legendas salvo: {output_video_path}")
                    
                    # Limpar arquivo temporário somente após sucesso
                    if temp_srt.exists():
                        try:
                            temp_srt.unlink()
                            logger.info("SRT temporário removido")
                        except:
                            pass
                    
                    return str(output_video_path)
                else:
                    logger.error(f"Erro ao embutir legendas: {result_stderr}")
                    # Manter o arquivo temporário para debug em caso de erro
                    logger.info(f"Arquivo SRT mantido para debug: {temp_srt}")
                    return None
            
            except Exception as e:
                # Limpar arquivo temporário em caso de erro
                if 'temp_srt' in locals() and temp_srt.exists():
                    temp_srt.unlink()
                logger.error(f"Exceção ao embutir legendas: {str(e)}")
                return None
        
        except Exception as e:
            logger.error(f"Exceção ao embutir legendas: {str(e)}")
            return None
    
    @staticmethod
    def get_video_duration(video_path: str) -> Optional[float]:
        """
        Obtém a duração de um vídeo em segundos.
        
        Args:
            video_path: Caminho do vídeo
            
        Returns:
            Duração em segundos
        """
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1:noprint_wrappers=1",
                str(video_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                logger.info(f"Duração do vídeo: {format_timestamp(duration)}")
                return duration
            else:
                logger.warning("Não foi possível obter duração do vídeo")
                return None
        
        except Exception as e:
            logger.error(f"Erro ao obter duração: {str(e)}")
            return None
