# Módulo para extração e processamento de áudio/vídeo

import subprocess
import os
import shutil
from pathlib import Path
from typing import Optional
from logger_config import setup_logger
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
                output_video_path = video.parent / f"{video.stem}_with_subtitles{video.suffix}"
            
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
                srt_abs = str(temp_srt.absolute())
                
                logger.info("Embutindo legendas no vídeo...")
                
                # SOLUÇÃO: Usar soft subtitles (stream embutido) em vez de hardcoded
                # Isso evita completamente o problema do filtro subtitles + libass no Windows
                # As legendas ficam como uma faixa separada no MP4, selecionável pelo player
                cmd = [
                    "ffmpeg",
                    "-i", video_abs,
                    "-i", srt_abs,  # Segundo input: arquivo SRT
                    "-c:v", "copy",  # Copiar vídeo sem recodificar
                    "-c:a", "copy",  # Copiar áudio sem recodificar
                    "-c:s", "mov_text",  # Converter legenda para formato MP4
                    "-map", "0:v",  # Mapear vídeo do primeiro input
                    "-map", "0:a",  # Mapear áudio do primeiro input
                    "-map", "1:s",  # Mapear legenda do segundo input
                    "-metadata:s:s:0", "language=por",  # Definir idioma da legenda
                    "-y",  # Sobrescrever
                    output_abs
                ]
                
                logger.info(f"Comando: ffmpeg -i video -i srt -c:s mov_text ...")
                
                # Executar ffmpeg
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace')
                
                # Verificar resultado ANTES de limpar
                if result.returncode == 0 and Path(output_video_path).exists():
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
                    logger.error(f"Erro ao embutir legendas: {result.stderr}")
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
