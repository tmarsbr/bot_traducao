# Módulo principal: Agente de Tradução de Vídeos

import argparse
import sys
from pathlib import Path
from typing import Optional
from logger_config import setup_logger
from config import (
    SUPPORTED_LANGUAGES,
    SUPPORTED_VIDEO_FORMATS,
    OUTPUT_DIR,
    MAX_VIDEO_SIZE_MB,
    MAX_VIDEO_DURATION_SECONDS,
)
from utils import VideoTranslationMetrics, validate_input_file, get_file_size_mb
from video_processor import VideoProcessor
from translation_api import get_translator
from transcriber import AudioTranscriber, VideoWithoutSubtitles

logger = setup_logger(__name__)


class VideoTranslationAgent:
    """Agente principal para tradução de vídeos."""
    
    def __init__(self):
        self.video_processor = VideoProcessor()
        self.transcriber = AudioTranscriber()
        self.translator = None
        self.metrics = None
    
    def validate_video(self, video_path: str) -> bool:
        """Valida o arquivo de vídeo."""
        logger.info(f"Validando vídeo: {video_path}")
        
        # Validar existência e formato
        if not validate_input_file(video_path, SUPPORTED_VIDEO_FORMATS):
            return False
        
        # Validar tamanho
        file_size = get_file_size_mb(video_path)
        if file_size > MAX_VIDEO_SIZE_MB:
            logger.error(f"Arquivo muito grande: {file_size:.2f}MB (máximo: {MAX_VIDEO_SIZE_MB}MB)")
            return False
        
        logger.info(f"Tamanho do arquivo: {file_size:.2f}MB")
        
        # Validar duração
        duration = self.video_processor.get_video_duration(video_path)
        if duration and duration > MAX_VIDEO_DURATION_SECONDS:
            logger.error(f"Vídeo muito longo: {duration}s (máximo: {MAX_VIDEO_DURATION_SECONDS}s)")
            return False
        
        logger.info("✓ Vídeo validado com sucesso")
        return True
    
    def translate_video(
        self,
        video_path: str,
        target_language: str,
        embed_subs: bool = False,
        use_gemini: bool = True,
        auto_transcribe: bool = False
    ) -> Optional[str]:
        """
        Pipeline completo de tradução de vídeo.
        
        Args:
            video_path: Caminho do vídeo
            target_language: Código do idioma alvo (ex: 'en', 'es')
            embed_subs: Se True, embutir legendas no vídeo
            use_gemini: Se True, usar Gemini; senão, Google Cloud Translation
            auto_transcribe: Se True, tenta transcrever áudio se não houver legendas
            
        Returns:
            Caminho do arquivo final (SRT ou MP4)
        """
        video_name = Path(video_path).stem
        self.metrics = VideoTranslationMetrics(video_name, target_language)
        
        try:
            # 1. Validar vídeo
            if not self.validate_video(video_path):
                self.metrics.add_error("validation", "Validação falhou")
                self.metrics.finish()
                self.metrics.save_report(OUTPUT_DIR)
                return None
            
            # 2. Inicializar tradutor
            logger.info("Inicializando serviço de tradução...")
            self.translator = get_translator(use_gemini=use_gemini)
            if not self.translator:
                self.metrics.add_error("translator", "Falha ao inicializar tradutor")
                self.metrics.finish()
                self.metrics.save_report(OUTPUT_DIR)
                return None

            # [OTIMIZAÇÃO] Verificar se já existe tradução na pasta de saída
            expected_output_srt = OUTPUT_DIR / f"{video_name}_{target_language}.srt"
            if expected_output_srt.exists():
                logger.info(f"⚡ Tradução existente encontrada: {expected_output_srt}")
                logger.info("Pulando etapas de transcrição e tradução...")
                
                if embed_subs:
                    logger.info("Etapa 3/4: Embutindo legendas (arquivo existente)...")
                    output_video = self.video_processor.embed_subtitles(
                        video_path,
                        str(expected_output_srt)
                    )
                    
                    if output_video:
                        self.metrics.complete_stage("embed")
                        logger.info(f"✓ Vídeo com legendas: {output_video}")
                        result = output_video
                        
                        self.metrics.finish()
                        self.metrics.save_report(OUTPUT_DIR)
                        return result
                    else:
                        logger.error("Falha ao embutir legendas existentes.")
                
                # Se não for embutir ou falhar, retorna o SRT
                return str(expected_output_srt)
            
            # 3. Tentar extrair legendas existentes
            logger.info("Etapa 1/4: Procurando legendas...")
            srt_path = self.video_processor.extract_subtitles(video_path)
            
            # Se não encontrou legendas embutidas, procura arquivo .srt externo
            if not srt_path:
                video_path_obj = Path(video_path)
                external_srt = video_path_obj.parent / f"{video_path_obj.stem}.srt"
                if external_srt.exists():
                    srt_path = str(external_srt)
                    logger.info(f"✓ Arquivo SRT externo encontrado: {srt_path}")
            
            if srt_path:
                logger.info("✓ Legendas encontradas")
                self.metrics.complete_stage("extract")
                
                # Traduzir legendas SRT
                logger.info("Etapa 2/4: Traduzindo legendas...")
                translated_srt = self._translate_srt_file(srt_path, target_language)
                
                if not translated_srt:
                    self.metrics.add_error("translate", "Falha ao traduzir legendas")
                    self.metrics.finish()
                    self.metrics.save_report(OUTPUT_DIR)
                    return None
                
                output_srt = OUTPUT_DIR / f"{video_name}_{target_language}.srt"
                self._save_srt_file(translated_srt, output_srt)
                self.metrics.complete_stage("translate")
                
                logger.info(f"✓ Legendas traduzidas salvas: {output_srt}")
                
                # Embutir legendas se solicitado
                if embed_subs:
                    logger.info("Etapa 3/4: Embutindo legendas no vídeo...")
                    output_video = self.video_processor.embed_subtitles(
                        video_path,
                        str(output_srt)
                    )
                    
                    if output_video:
                        self.metrics.complete_stage("embed")
                        logger.info(f"✓ Vídeo com legendas: {output_video}")
                        result = output_video
                    else:
                        self.metrics.add_error("embed", "Falha ao embutir legendas")
                        result = str(output_srt)
                else:
                    result = str(output_srt)
            
            else:
                # Vídeo sem legendas embutidas
                logger.info("Sem legendas embutidas encontradas.")
                
                if auto_transcribe:
                    logger.info("\n⚡ Tentando processar vídeo sem legendas...")
                    
                    # Passar translator para estratégia
                    strategy = VideoWithoutSubtitles.get_processing_strategy(
                        video_path,
                        self.transcriber,
                        gemini_translator=self.translator if use_gemini else None
                    )
                    
                    logger.info(f"Estratégia selecionada: {strategy['method']}")
                    
                    if strategy['strategy'] == 'gemini_direct':
                        # Estratégia Gemini: Transcreve e traduz diretamente
                        logger.info("Extraindo áudio para Gemini...")
                        audio_path = self.video_processor.extract_audio(video_path)
                        
                        if audio_path:
                            try:
                                logger.info(f"Enviando para Gemini (convertendo para SRT): {audio_path}")
                                # Solicita transcrição já traduzida para target_language
                                translated_srt_content = self.translator.transcribe_audio_with_gemini(
                                    audio_path, 
                                    target_language=target_language
                                )
                                
                                if translated_srt_content:
                                    # Salvar SRT gerado
                                    output_srt = OUTPUT_DIR / f"{video_name}_{target_language}.srt"
                                    self._save_srt_file(translated_srt_content, output_srt)
                                    
                                    self.metrics.complete_stage("extract") # Considera extração e transcrição como uma etapa
                                    self.metrics.complete_stage("translate")
                                    
                                    logger.info(f"✓ Legendas (Gemini) salvas: {output_srt}")
                                    
                                    # Configurar result para embed
                                    result = str(output_srt)
                                    
                                    # Embutir legendas se solicitado
                                    if embed_subs:
                                        logger.info("Etapa 3/4: Embutindo legendas no vídeo (Gemini output)...")
                                        output_video = self.video_processor.embed_subtitles(
                                            video_path,
                                            str(output_srt)
                                        )
                                        
                                        if output_video:
                                            self.metrics.complete_stage("embed")
                                            logger.info(f"✓ Vídeo com legendas: {output_video}")
                                            result = output_video
                                        else:
                                            self.metrics.add_error("embed", "Falha ao embutir legendas")
                                else:
                                    result = None
                                    self.metrics.add_error("transcribe", "Gemini retornou conteúdo vazio")
                            except Exception as e:
                                logger.error(f"Erro na transcrição Gemini: {e}")
                                result = None
                        else:
                            logger.error("Falha ao extrair áudio para Gemini")
                            result = None

                    elif strategy['srt_path']:
                        srt_path = strategy['srt_path']
                        source_language = strategy['language']
                        
                        logger.info(f"Etapa 2/4: Traduzindo legendas de {source_language} para {target_language}...")
                        translated_srt = self._translate_srt_file(srt_path, target_language)
                        
                        if translated_srt:
                            output_srt = OUTPUT_DIR / f"{video_name}_{target_language}.srt"
                            self._save_srt_file(translated_srt, output_srt)
                            self.metrics.complete_stage("extract")
                            self.metrics.complete_stage("translate")
                            
                            logger.info(f"✓ Legendas traduzidas salvas: {output_srt}")
                            
                            # Embutir legendas se solicitado
                            if embed_subs:
                                logger.info("Etapa 3/4: Embutindo legendas no vídeo...")
                                output_video = self.video_processor.embed_subtitles(
                                    video_path,
                                    str(output_srt)
                                )
                                
                                if output_video:
                                    self.metrics.complete_stage("embed")
                                    logger.info(f"✓ Vídeo com legendas: {output_video}")
                                    result = output_video
                                else:
                                    self.metrics.add_error("embed", "Falha ao embutir legendas")
                                    result = str(output_srt)
                            else:
                                result = str(output_srt)
                        else:
                            self.metrics.add_error("translate", "Falha ao traduzir legendas extraídas")
                            result = None
                    else:
                        self.metrics.add_error("transcribe", f"Nenhuma estratégia de extração funcionou: {strategy['method']}")
                        logger.error(f"✗ {strategy['method']}")
                        result = None
                
                else:
                    logger.info("⚠️ Vídeo sem legendas embutidas")
                    logger.info("Opções disponíveis:")
                    logger.info("  1. Coloque arquivo .srt externo com o mesmo nome do vídeo")
                    logger.info("  2. Use --auto_transcribe para tentar transcrição automática (requer Whisper)")
                    logger.info("  3. Use Speech-to-Text: Google Cloud, OpenAI Whisper, AssemblyAI")
                    
                    self.metrics.add_error("transcribe", "Vídeo sem legendas. Use --auto_transcribe ou forneça arquivo .srt externo.")
                    result = None
            
            # Salvar relatório
            if result:
                self.metrics.finish()
                self.metrics.save_report(OUTPUT_DIR)
                logger.info(f"\n✓ Tradução concluída com sucesso em {self.metrics.get_duration():.2f}s")
            
            return result
        
        except Exception as e:
            logger.error(f"Erro não tratado: {str(e)}")
            self.metrics.add_error("main", str(e))
            self.metrics.finish()
            self.metrics.save_report(OUTPUT_DIR)
            return None
    
    def _translate_srt_file(self, srt_path: str, target_language: str) -> Optional[str]:
        """Traduz arquivo SRT."""
        try:
            with open(srt_path, "r", encoding="utf-8") as f:
                srt_content = f.read()
            
            # Mapear código do idioma para nome completo
            language_map = {
                "pt": "português",
                "en": "inglês",
                "es": "espanhol",
                "fr": "francês",
                "de": "alemão",
                "it": "italiano",
                "ja": "japonês",
                "ko": "coreano",
                "zh": "chinês",
                "ru": "russo",
            }
            
            target_lang_name = language_map.get(target_language, target_language)
            
            # Traduzir usando Gemini (legenda por legenda para arquivos grandes)
            if hasattr(self.translator, 'translate_srt_subtitles'):
                logger.info(f"Traduzindo SRT de inglês para {target_lang_name}...")
                translated = self.translator.translate_srt_subtitles(srt_content, target_lang_name)
                return translated
            elif hasattr(self.translator, 'translate_text'):
                logger.info(f"Traduzindo SRT de inglês para {target_lang_name}...")
                translated = self.translator.translate_text(srt_content, "inglês", target_lang_name)
                return translated
            else:
                logger.warning("Translator não suporta tradução. Retornando SRT original.")
                return srt_content
        
        except Exception as e:
            logger.error(f"Erro ao traduzir SRT: {str(e)}")
            return None
    
    @staticmethod
    def _save_srt_file(srt_content: str, output_path: Path):
        """Salva conteúdo SRT em arquivo."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(srt_content)
            logger.info(f"Arquivo SRT salvo: {output_path}")
        except Exception as e:
            logger.error(f"Erro ao salvar SRT: {str(e)}")


def main():
    """Função principal com argumentos de linha de comando."""
    parser = argparse.ArgumentParser(
        description="Agente de Tradução de Vídeos com Gemini e Google Cloud Translation"
    )
    
    parser.add_argument(
        "--input_video",
        required=True,
        help="Caminho do arquivo de vídeo de entrada"
    )
    
    parser.add_argument(
        "--target_language",
        required=True,
        choices=list(SUPPORTED_LANGUAGES.keys()),
        help=f"Idioma alvo. Suportados: {', '.join(f'{k} ({v})' for k, v in SUPPORTED_LANGUAGES.items())}"
    )
    
    parser.add_argument(
        "--output_subtitle",
        default=None,
        help="Caminho personalizado para arquivo SRT de saída (opcional)"
    )
    
    parser.add_argument(
        "--embed_subs",
        action="store_true",
        help="Embutir legendas traduzidas no vídeo final"
    )
    
    parser.add_argument(
        "--auto_transcribe",
        action="store_true",
        help="Tentar transcrição automática para vídeos sem legendas (requer Whisper)"
    )
    
    parser.add_argument(
        "--use_gemini",
        action="store_true",
        default=True,
        help="Usar Gemini para transcrição (padrão: True)"
    )
    
    parser.add_argument(
        "--input_dir",
        default=None,
        help="Processar múltiplos vídeos em um diretório"
    )
    
    args = parser.parse_args()
    
    # Verificar ffmpeg
    if not VideoProcessor.check_ffmpeg():
        logger.error("ffmpeg não está disponível. Instalação necessária.")
        return 1
    
    agent = VideoTranslationAgent()
    
    # Processar múltiplos vídeos ou um único
    if args.input_dir:
        logger.info(f"Processando vídeos do diretório: {args.input_dir}")
        input_path = Path(args.input_dir)
        
        if not input_path.is_dir():
            logger.error(f"Diretório não encontrado: {args.input_dir}")
            return 1
        
        video_files = []
        for fmt in SUPPORTED_VIDEO_FORMATS:
            video_files.extend(input_path.glob(f"*{fmt}"))
        
        if not video_files:
            logger.warning(f"Nenhum vídeo encontrado em: {args.input_dir}")
            return 0
        
        logger.info(f"Encontrados {len(video_files)} vídeo(s)")
        
        for video_file in video_files:
            logger.info(f"\n{'='*60}")
            logger.info(f"Processando: {video_file.name}")
            logger.info(f"{'='*60}")
            
            result = agent.translate_video(
                str(video_file),
                args.target_language,
                embed_subs=args.embed_subs,
                use_gemini=args.use_gemini,
                auto_transcribe=args.auto_transcribe
            )
            
            if result:
                logger.info(f"✓ Concluído: {result}")
            else:
                logger.error(f"✗ Falha ao processar: {video_file.name}")
    
    else:
        result = agent.translate_video(
            args.input_video,
            args.target_language,
            embed_subs=args.embed_subs,
            use_gemini=args.use_gemini,
            auto_transcribe=args.auto_transcribe
        )
        
        if result:
            logger.info(f"\n✓ Tradução concluída!")
            logger.info(f"Resultado: {result}")
            return 0
        else:
            logger.error("Tradução falhou")
            return 1


if __name__ == "__main__":
    sys.exit(main())
