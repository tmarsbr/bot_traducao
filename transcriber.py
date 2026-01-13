# Módulo de Transcrição de Áudio para Vídeos

import os
import subprocess
import pysrt
from pathlib import Path
from typing import Optional
from logger_config import setup_logger
from config import INPUT_DIR, OUTPUT_DIR
from alive_progress import alive_bar
import time
import warnings

# Suprimir aviso do Whisper sobre FP16/FP32
warnings.filterwarnings("ignore", message="FP16 is not supported on CPU")

logger = setup_logger(__name__)


class AudioTranscriber:
    """
    Transcreve áudio de vídeos para arquivos SRT usando Whisper.
    Suporta vídeos sem legendas embutidas.
    """
    
    def __init__(self):
        self.whisper_available = self._check_whisper()
    
    def _check_whisper(self) -> bool:
        """Verifica se Whisper está instalado."""
        try:
            result = subprocess.run(
                ["whisper", "--help"],
                capture_output=True,
                text=True,
                timeout=5
            )
            # Whisper retorna 0 com --help, mas erro com --version
            if result.returncode == 0 or "whisper" in result.stderr.lower() or "usage: whisper" in result.stdout.lower():
                logger.info("✓ Whisper encontrado e disponível")
                return True
            return False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("⚠ Whisper não encontrado. Para transcrição automática, instale com: pip install openai-whisper")
            return False
            return False
    
    def transcribe_audio(
        self,
        video_path: str,
        language: str = "en",
        model_size: str = "base"
    ) -> Optional[str]:
        """
        Transcreve áudio do vídeo usando Whisper.
        
        Args:
            video_path: Caminho do arquivo de vídeo
            language: Código do idioma (en, pt, es, etc.)
            model_size: Tamanho do modelo Whisper (tiny, base, small, medium, large)
        
        Returns:
            Caminho do arquivo SRT gerado ou None se falhar
        """
        if not self.whisper_available:
            logger.error("Whisper não disponível. Instale com: pip install openai-whisper")
            return None
        
        video_name = Path(video_path).stem
        srt_output_path = os.path.join(INPUT_DIR, f"{video_name}_transcribed.srt")
        
        try:
            logger.info(f"Transcrevendo áudio com Whisper ({model_size})...")
            logger.info(f"Vídeo: {video_path}")
            logger.info(f"Idioma: {language}")
            
            # Comando Whisper para gerar SRT
            cmd = [
                "whisper",
                video_path,
                "--model", model_size,
                "--language", language,
                "--output_format", "srt",
                "--output_dir", str(INPUT_DIR),
                "--verbose", "False"
            ]
            
            logger.info(f"Executando: {' '.join(cmd)}")
            logger.info("Transcrevendo áudio com Whisper...")
            logger.info("⏳ Aguarde... (isso pode levar vários minutos)")
            
            # Executar sem capturar output para evitar problemas de memória
            result = subprocess.run(cmd, text=True, encoding='utf-8', errors='replace', timeout=3600)
            
            if result.returncode != 0:
                logger.error(f"Erro ao transcrever áudio (código: {result.returncode})")
                return None
            
            # Whisper cria arquivo .srt automaticamente
            expected_srt = os.path.join(INPUT_DIR, f"{video_name}.srt")
            if os.path.exists(expected_srt):
                logger.info(f"✓ Transcrição concluída: {expected_srt}")
                return expected_srt
            elif os.path.exists(srt_output_path):
                logger.info(f"✓ Transcrição concluída: {srt_output_path}")
                return srt_output_path
            else:
                logger.error("Arquivo SRT não foi gerado pelo Whisper")
                return None
        
        except subprocess.TimeoutExpired:
            logger.error("Transcrição demorou muito (timeout de 1 hora)")
            return None
        except Exception as e:
            logger.error(f"Erro durante transcrição: {str(e)}")
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
        
        # Estratégia 0: Gemini (se disponível e configurado, geralmente mais rápido que Whisper CPU)
        if gemini_translator and hasattr(gemini_translator, 'transcribe_audio_with_gemini'):
            logger.info("🤖 Tentando transcrição direta com Gemini...")
            # Extrair áudio para envio (Gemini aceita vídeo também, mas áudio é menor)
            # Na verdade, o método transcribe_audio_with_gemini espera caminho de áudio ou vídeo.
            # Vamos passar o vídeo direto.
            
            try:
                # Transcrição direta para SRT
                # Nota: language é target_language, mas aqui queremos source ou target?
                # Se gemini traduz, já vem em pt.
                # Assumindo que queremos EN -> PT direto.
                # Mas o pipeline espera srt em source e depois traduz. 
                # Porém, se o Gemini já traduz, melhor.
                pass 
                # A implementação no video_translator vai chamar a função se a estratégia for 'gemini'
                return {
                    'strategy': 'gemini_direct',
                    'srt_path': None, # Será gerado
                    'language': 'pt', # Já vem traduzido
                    'method': 'Transcrição/Tradução direta com Gemini'
                }
            except Exception as e:
                 logger.warning(f"Gemini transcription strategy check falhou: {e}")

        if prefer_whisper:
            # Estratégia 1: Usar Whisper se disponível
            logger.info(f"DEBUG: whisper_available = {transcriber.whisper_available}")
            if transcriber.whisper_available:
                logger.info("🎙️ Iniciando transcrição com Whisper... (pode levar alguns minutos)")
                srt_path = transcriber.transcribe_audio(video_path, language='en', model_size='base')
                logger.info(f"DEBUG: srt_path retornado = {srt_path}")
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
        else:
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
                srt_path = transcriber.transcribe_audio(video_path, language='en', model_size='base')
                if srt_path:
                    return {
                        'strategy': 'whisper_transcription',
                        'srt_path': srt_path,
                        'language': 'en',
                        'method': 'Transcrição automática com Whisper'
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
