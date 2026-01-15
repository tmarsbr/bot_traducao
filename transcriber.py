# Módulo de Transcrição de Áudio para Vídeos

import os
import subprocess
import pysrt
from pathlib import Path
from typing import Optional
from logger_config import setup_logger
from config import INPUT_DIR, OUTPUT_DIR, WHISPER_MODEL, MODELS_DIR
from alive_progress import alive_bar
import time
import warnings

# Suprimir aviso do Whisper sobre FP16/FP32
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

# Desabilitar aviso de symlinks do HuggingFace (comum no Windows)
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

logger = setup_logger(__name__)


class AudioTranscriber:
    """
    Transcreve áudio de vídeos para arquivos SRT usando Whisper.
    Suporta vídeos sem legendas embutidas.
    """
    
    def __init__(self):
        self.whisper_available = self._check_whisper()
    
    def _check_whisper(self) -> bool:
        """Verifica se Faster-Whisper está instalado."""
        try:
            from faster_whisper import WhisperModel
            logger.info("✓ Biblioteca Faster-Whisper encontrada")
            return True
        except ImportError:
            logger.warning("⚠ Faster-Whisper não encontrada. Instale com: pip install faster-whisper")
            return False
        except Exception as e:
            logger.warning(f"⚠ Erro ao verificar Faster-Whisper: {str(e)}")
            return False
    
    def transcribe_audio(
        self,
        video_path: str,
        language: str = "en",
        model_size: str = WHISPER_MODEL
    ) -> Optional[str]:
        """
        Transcreve áudio usando Faster-Whisper (extremamente rápido no CPU).
        """
        if not self.whisper_available:
            logger.error("Faster-Whisper não disponível.")
            return None
        
        video_name = Path(video_path).stem
        srt_output_path = os.path.join(INPUT_DIR, f"{video_name}_transcribed.srt")
        
        try:
            from faster_whisper import WhisperModel
            from utils import format_timestamp
            
            # Para AMD/CPU no Windows, 'cpu' é a melhor opção.
            # compute_type='int8' economiza memória e é mais rápido sem perder muita qualidade.
            device = "cpu"
            compute_type = "int8"
            
            logger.info(f"Iniciando transcrição com Faster-Whisper ({model_size})...")
            logger.info(f"Modo: Otimizado para AMD/CPU (INT8)")
            
            model = WhisperModel(model_size, device=device, compute_type=compute_type, download_root=str(MODELS_DIR))
            
            # Parâmetros otimizados (Anti-Alucinação)
            segments, info = model.transcribe(
                video_path, 
                language=language, 
                beam_size=5,
                condition_on_previous_text=False,
                vad_filter=True,
                vad_parameters=dict(min_speech_duration_ms=250, min_silence_duration_ms=500),
                no_speech_threshold=0.4,
                log_prob_threshold=-0.9,
                word_timestamps=True
            )
            
            logger.info(f"Idioma: {info.language} | Duração: {info.duration:.2f}s")
            
            # Salvar como SRT
            with open(srt_output_path, "w", encoding="utf-8") as f:
                for i, segment in enumerate(segments, start=1):
                    start = format_timestamp(segment.start)
                    end = format_timestamp(segment.end)
                    text = segment.text.strip()
                    
                    f.write(f"{i}\n")
                    f.write(f"{start} --> {end}\n")
                    f.write(f"{text}\n\n")
            
            logger.info(f"✓ Transcrição concluída: {srt_output_path}")
            return srt_output_path
        
        except Exception as e:
            logger.error(f"Erro durante transcrição com Faster-Whisper: {str(e)}")
            return None
    
    def create_dummy_srt_from_video(self, video_path: str) -> Optional[str]:
        """
        Cria um SRT básico com marcações de tempo (útil para vídeos sem legenda).
        Requer que o usuário preencha o texto depois.
        
        Args:
            video_path: Caminho do arquivo de vídeo
        
        Returns:
            Caminho do arquivo SRT criado
        """
        try:
            from video_processor import VideoProcessor
            processor = VideoProcessor()
            duration = processor.get_video_duration(video_path)
            
            if not duration:
                logger.error("Não foi possível obter duração do vídeo")
                return None
            
            # Criar SRT com marcações a cada 5 segundos
            subtitles = pysrt.SubRipFile()
            index = 1
            
            for start_time in range(0, int(duration), 5):
                end_time = min(start_time + 5, int(duration))
                
                sub = pysrt.SubRipItem()
                sub.index = index
                sub.start = pysrt.SubRipTime(seconds=start_time)
                sub.end = pysrt.SubRipTime(seconds=end_time)
                sub.content = f"[Texto {index}]"  # Placeholder
                
                subtitles.append(sub)
                index += 1
            
            video_name = Path(video_path).stem
            srt_output_path = os.path.join(INPUT_DIR, f"{video_name}_template.srt")
            subtitles.save(srt_output_path, encoding='utf-8')
            
            logger.info(f"✓ SRT template criado: {srt_output_path}")
            logger.info(f"  Preencha o template com o texto desejado e use para tradução")
            return srt_output_path
        
        except Exception as e:
            logger.error(f"Erro ao criar SRT template: {str(e)}")
            return None
    
    def check_for_external_srt(self, video_path: str) -> Optional[str]:
        """
        Verifica se existe arquivo SRT externo correspondente ao vídeo.
        
        Args:
            video_path: Caminho do arquivo de vídeo
        
        Returns:
            Caminho do arquivo SRT se encontrado, None caso contrário
        """
        video_name = Path(video_path).stem
        video_dir = Path(video_path).parent
        
        # Procura por .srt com mesmo nome
        possible_paths = [
            video_dir / f"{video_name}.srt",
            Path(INPUT_DIR) / f"{video_name}.srt",
            video_dir / f"{video_name}_en.srt",
            Path(INPUT_DIR) / f"{video_name}_en.srt",
        ]
        
        for srt_path in possible_paths:
            if srt_path.exists():
                logger.info(f"✓ Arquivo SRT externo encontrado: {srt_path}")
                return str(srt_path)
        
        return None


class VideoWithoutSubtitles:
    """
    Helper para processar vídeos sem legendas.
    Oferece múltiplas estratégias.
    """
    
    @staticmethod
    def get_processing_strategy(video_path: str, transcriber: AudioTranscriber, prefer_whisper: bool = True, gemini_translator=None) -> dict:
        """
        Determina a melhor estratégia para processar o vídeo.
        
        Args:
            video_path: Caminho do vídeo
            transcriber: Instância do AudioTranscriber
            prefer_whisper: Se True, prioriza Whisper sobre arquivos externos
            gemini_translator: Instância do GeminiTranslator (opcional)
        
        Returns:
            Dict com 'strategy', 'srt_path', 'language', 'method'
        """
        logger.info("Analisando vídeo sem legendas...")
        
        if prefer_whisper:
            # Estratégia 1: Usar Whisper se disponível (Prioritário para melhor sincronia)
            # logger.info(f"DEBUG: whisper_available = {transcriber.whisper_available}")
            if transcriber.whisper_available:
                logger.info("🎙️ Iniciando transcrição com Whisper... (pode levar alguns minutos)")
                srt_path = transcriber.transcribe_audio(video_path, language='en', model_size=WHISPER_MODEL)
                # logger.info(f"DEBUG: srt_path retornado = {srt_path}")
                if srt_path:
                    return {
                        'strategy': 'whisper_transcription',
                        'srt_path': srt_path,
                        'language': 'en',
                        'method': 'Transcrição automática com Whisper'
                    }
                else:
                    logger.warning("Whisper falhou. Tentando estratégias alternativas...")
            
            # Estratégia 2: Procurar SRT externo
            external_srt = transcriber.check_for_external_srt(video_path)
            if external_srt:
                return {
                    'strategy': 'external_srt',
                    'srt_path': external_srt,
                    'language': 'en',
                    'method': 'Arquivo SRT externo encontrado'
                }

            # Estratégia 3: Gemini (Fallback - sincronia pode ser inferior)
            if gemini_translator and hasattr(gemini_translator, 'transcribe_audio_with_gemini'):
                logger.info("🤖 Whisper não disponível/falhou. Tentando transcrição direta com Gemini...")
                
                try:
                    return {
                        'strategy': 'gemini_direct',
                        'srt_path': None,
                        'language': 'pt',
                        'method': 'Transcrição/Tradução direta com Gemini'
                    }
                except Exception as e:
                        logger.warning(f"Gemini transcription strategy check falhou: {e}")

        else:
             # Se não preferir Whisper, tenta External -> Whisper -> Gemini
            # Estratégia 1: Procurar SRT externo
            external_srt = transcriber.check_for_external_srt(video_path)
            if external_srt:
                return {
                    'strategy': 'external_srt',
                    'srt_path': external_srt,
                    'language': 'en',
                    'method': 'Arquivo SRT externo encontrado'
                }
            
            # Estratégia 2: Usar Whisper se disponível
            if transcriber.whisper_available:
                logger.info("🎙️ Iniciando transcrição com Whisper... (pode levar alguns minutos)")
                srt_path = transcriber.transcribe_audio(video_path, language='en', model_size=WHISPER_MODEL)
                if srt_path:
                    return {
                        'strategy': 'whisper_transcription',
                        'srt_path': srt_path,
                        'language': 'en',
                        'method': 'Transcrição automática com Whisper'
                    }

            # Estratégia 3: Gemini
            if gemini_translator and hasattr(gemini_translator, 'transcribe_audio_with_gemini'):
                logger.info("🤖 Tentando transcrição direta com Gemini...")
                return {
                    'strategy': 'gemini_direct',
                    'srt_path': None,
                    'language': 'pt',
                    'method': 'Transcrição/Tradução direta com Gemini'
                }
        
        # Estratégia 3: Criar template SRT (último recurso)
        logger.warning("⚠️ Whisper, Gemini e SRT externo não disponíveis ou falharam. Criando template...")
        template_srt = transcriber.create_dummy_srt_from_video(video_path)
        if template_srt:
            return {
                'strategy': 'manual_template',
                'srt_path': template_srt,
                'language': 'en',
                'method': 'Template SRT criado (preencha manualmente)'
            }
        
        # Nenhuma estratégia funcionou
        return {
            'strategy': 'none',
            'srt_path': None,
            'language': 'en',
            'method': 'Nenhuma estratégia disponível'
        }
