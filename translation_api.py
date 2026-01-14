# Módulo para interação com Google Cloud Translation e Gemini

import time
import json
from typing import Optional, List
from logger_config import setup_logger
from config import (
    GEMINI_API_KEY,
    GOOGLE_CLOUD_PROJECT,
    GEMINI_MODEL,
    MAX_RETRIES,
    RETRY_DELAY,
    BATCH_SIZE,
    SKIP_BLOCKED_CONTENT,
)
from alive_progress import alive_bar

logger = setup_logger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai não instalado. Funcionalidade Gemini desabilitada.")

try:
    from google.cloud import translate_v2
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False
    logger.warning("google-cloud-translate não instalado. Funcionalidade Google Translate desabilitada.")


class GeminiTranslator:
    """Interface para Gemini API."""
    
    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY não configurada!")
        
        if GEMINI_AVAILABLE:
            genai.configure(api_key=GEMINI_API_KEY)
            
            # Configuração de segurança para evitar bloqueio de conteúdo legítimo
            from google.generativeai.types import HarmCategory, HarmBlockThreshold, RequestOptions
            
            self.api_options = RequestOptions(timeout=600) # 10 minutos de timeout
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
            
            self.model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                safety_settings=safety_settings
            )
        else:
            raise ImportError("google-generativeai não está instalado")
    
    def transcribe_audio_with_gemini(self, audio_path: str, target_language: str = None) -> Optional[str]:
        """
        Transcreve áudio usando Gemini.
        
        Args:
            audio_path: Caminho do arquivo de áudio
            target_language: Idioma alvo para tradução (opcional)
            
        Returns:
            Texto transcrito e traduzido
        """
        try:
            # Obter duração do áudio para incluir no prompt
            import subprocess
            duration_info = ""
            try:
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", 
                     "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    duration_sec = float(result.stdout.strip())
                    duration_min = duration_sec / 60
                    duration_info = f"\n        5. O áudio tem aproximadamente {duration_min:.1f} minutos. TRANSCREVA TODO O CONTEÚDO do início ao fim."
            except:
                pass
            
            prompt = f"""
            Transcreva o áudio deste vídeo/áudio com precisão COMPLETA.
            
            IMPORTANTE - LEIA COM ATENÇÃO:
            1. Formate a saída EXATAMENTE como um arquivo SRT (SubRip).
            2. Inclua índices numéricos, timestamps precisos (00:00:00,000 --> 00:00:05,000) e o texto.
            3. Quebre as legendas em frases curtas (máximo 2 linhas por legenda).
            4. TRANSCREVA O ÁUDIO INTEIRO do início até o final. NÃO pare no meio.{duration_info}
            """
            
            if target_language:
                prompt += f"\n            6. O texto das legendas DEVE ser traduzido diretamente para {target_language} brasileiro."
            else:
                prompt += "\n            6. Mantenha o idioma original do áudio."
            
            prompt += """
            
            ATENÇÃO: Não inclua nenhum texto introdutório ou explicativo.
            Comece diretamente com "1" (o primeiro índice de legenda).
            Não use blocos de código markdown (```).
            """
            
            logger.info(f"Enviando áudio para Gemini: {audio_path}")
            
            # Upload do arquivo para Gemini
            audio_file = genai.upload_file(audio_path)
            
            # Transcrever e/ou traduzir
            response = self.model.generate_content([prompt, audio_file])
            
            logger.info("Transcrição concluída com sucesso")
            return response.text
        
        except Exception as e:
            logger.error(f"Erro ao transcrever com Gemini: {str(e)}")
            return None
    
    def translate_text(self, text: str, source_language: str, target_language: str) -> Optional[str]:
        """
        Traduz texto usando Gemini.
        
        Args:
            text: Texto a traduzir
            source_language: Idioma de origem
            target_language: Idioma alvo
            
        Returns:
            Texto traduzido
        """
        for attempt in range(MAX_RETRIES):
            try:
                # Ajustar para português brasileiro quando aplicável
                target_lang_adjusted = target_language
                if target_language.lower() in ['português', 'portugues', 'pt']:
                    target_lang_adjusted = 'português brasileiro'
                
                prompt = f"""Traduza o seguinte texto de {source_language} para {target_lang_adjusted}.
IMPORTANTE: Use português do Brasil (PT-BR), não português de Portugal.
Use formas verbais brasileiras (ex: "está tentando" não "está a tentar").
Use vocabulário brasileiro (ex: "entender" não "perceber", "legal" não "fixe").
Mantenha a formatação original.
Apenas retorne o texto traduzido, sem comentários adicionais.

Texto:
{text}"""
                
                response = self.model.generate_content(prompt, request_options=self.api_options)
                
                # Verificar se a resposta foi bloqueada ou está vazia
                if not response.candidates or not response.candidates[0].content.parts:
                    block_reason = "Desconhecido"
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                        block_reason = response.prompt_feedback.block_reason
                    elif response.candidates and response.candidates[0].finish_reason:
                        block_reason = f"Finish Reason: {response.candidates[0].finish_reason}"
                    
                    if SKIP_BLOCKED_CONTENT:
                        logger.warning(f"⚠️  Conteúdo bloqueado por segurança (Motivo: {block_reason}). Pulando...")
                        return None
                    
                    raise ValueError(f"Resposta bloqueada ou vazia: {block_reason}")

                logger.info(f"Tradução concluída: {source_language} → {target_lang_adjusted}")
                return response.text
            
            except Exception as e:
                error_str = str(e)
                # Skip automático para conteúdo bloqueado (complementar ao check acima)
                if SKIP_BLOCKED_CONTENT and ("PROHIBITED_CONTENT" in error_str or "SAFETY" in error_str or "candidates is empty" in error_str):
                    logger.warning(f"⚠️  Conteúdo bloqueado detectado no erro. Pulando...")
                    return None
                
                logger.warning(f"Tentativa {attempt + 1}/{MAX_RETRIES} falhou: {error_str}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    time.sleep(wait_time)
                else:
                    logger.error(f"Falha permanente na tradução: {error_str}")
                    return None
    
    def translate_batch(self, texts: List[str], source_language: str, target_language: str) -> List[str]:
        """
        Traduz uma lista de textos em uma única chamada.
        """
        for attempt in range(MAX_RETRIES):
            try:
                target_lang_adjusted = target_language
                if target_language.lower() in ['português', 'portugues', 'pt']:
                    target_lang_adjusted = 'português brasileiro'
                
                prompt = f"""Traduza a lista de textos abaixo de {source_language} para {target_lang_adjusted}.
IMPORTANTE:
1. Retorne APENAS um array JSON de strings.
2. Mantenha a ordem exata.
3. Use português do Brasil (PT-BR).
4. Não inclua markdown (```json) ou explicações.

Textos:
{json.dumps(texts, ensure_ascii=False)}"""
                
                response = self.model.generate_content(prompt, request_options=self.api_options)
                
                # Verificar se a resposta foi bloqueada antes de acessar .text
                if not response.candidates or not response.candidates[0].content.parts:
                    block_reason = "Desconhecido"
                    if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                        block_reason = response.prompt_feedback.block_reason
                    elif response.candidates and response.candidates[0].finish_reason:
                        block_reason = f"Finish Reason: {response.candidates[0].finish_reason}"
                    
                    if "PROHIBITED_CONTENT" in str(block_reason) or "SAFETY" in str(block_reason) or "8" in str(block_reason):
                         logger.warning(f"Batch bloqueado por conteúdo sensível (Motivo: {block_reason}).")
                         return [] # Trigger fallback individual imediato
                    
                    raise ValueError(f"Resposta vazia ou bloqueada: {block_reason}")

                # Limpar resposta para garantir JSON válido
                cleaned_response = response.text.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                elif cleaned_response.startswith("```"):
                    cleaned_response = cleaned_response[3:]
                
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                
                translations = json.loads(cleaned_response)
                
                if len(translations) != len(texts):
                    logger.warning(f"Tamanho da resposta incorreto: {len(translations)} vs {len(texts)}")
                    if attempt < MAX_RETRIES - 1:
                        continue
                
                return translations
            
            except Exception as e:
                error_str = str(e)
                # Skip rápido para conteúdo bloqueado
                if SKIP_BLOCKED_CONTENT and ("PROHIBITED_CONTENT" in error_str or "finish_reason: 8" in error_str or "SAFETY" in error_str):
                    logger.warning(f"⚠️  Batch bloqueado por segurança. Pulando lote...")
                    return [] # Trigger fallback individual imediato
                    
                logger.warning(f"Batch falhou (tentativa {attempt + 1}): {error_str}")
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)  # Backoff exponencial
                    time.sleep(wait_time)
        
        return []

    def translate_srt_subtitles(self, srt_text: str, target_language: str, source_language: str = "inglês") -> Optional[str]:
        """
        Traduz legendas SRT mantendo timestamps usando batch processing.
        """
        try:
            import pysrt
            from alive_progress import alive_bar
            
            srt = pysrt.SubRipFile.from_string(srt_text)
            translated_count = 0
            batch_size = BATCH_SIZE  # Usar config de 20 em vez de 10
            
            logger.info(f"Traduzindo {len(srt)} legendas de {source_language} para {target_language} (Batch: {batch_size})...")
            
            subtitles_to_translate = []
            indices_to_translate = []
            
            # Coletar legendas que têm texto
            for i, subtitle in enumerate(srt):
                if subtitle.text and subtitle.text.strip():
                    subtitles_to_translate.append(subtitle.text)
                    indices_to_translate.append(i)
            
            with alive_bar(len(subtitles_to_translate), title='Translating batches', bar='smooth', spinner='dots_waves') as bar:
                for i in range(0, len(subtitles_to_translate), batch_size):
                    batch_texts = subtitles_to_translate[i:i + batch_size]
                    batch_indices = indices_to_translate[i:i + batch_size]
                    
                    translations = self.translate_batch(batch_texts, source_language, target_language)
                    
                    if translations and len(translations) == len(batch_texts):
                        for idx, translation in zip(batch_indices, translations):
                            srt[idx].text = translation
                            translated_count += 1
                    else:
                        # Fallback: traduzir individualmente se o batch falhar totalmente
                        logger.warning(f"Batch {i//batch_size} falhou, tentando individualmente...")
                        for idx, text in zip(batch_indices, batch_texts):
                            trans = self.translate_text(text, source_language, target_language)
                            if trans:
                                srt[idx].text = trans
                                translated_count += 1
                    
                    bar(len(batch_texts))
                    # Pequena pausa para evitar rate limit mesmo com batch
                    time.sleep(2)
            
            logger.info(f"Legendas traduzidas: {translated_count}/{len(srt)}")
            
            # pysrt objects can be converted to string directly
            output_str = ""
            for subtitle in srt:
                output_str += str(subtitle) + "\n"
            return output_str
        
        except ImportError as ie:
            logger.error(f"Módulo necessário não está instalado: {ie}")
            return None
        except Exception as e:
            logger.error(f"Erro ao traduzir SRT: {e}")
            return None


class GoogleCloudTranslator:
    """Interface para Google Cloud Translation API."""
    
    def __init__(self):
        if not GOOGLE_CLOUD_PROJECT:
            logger.warning("GOOGLE_CLOUD_PROJECT não configurada. Google Cloud Translation desabilitado.")
            self.client = None
        else:
            if GOOGLE_TRANSLATE_AVAILABLE:
                self.client = translate_v2.Client()
            else:
                logger.warning("google-cloud-translate não está instalado")
                self.client = None
    
    def translate_text(self, text: str, target_language: str, source_language: str = "pt") -> Optional[str]:
        """
        Traduz texto usando Google Cloud Translation.
        
        Args:
            text: Texto a traduzir
            target_language: Idioma alvo (código: en, es, etc)
            source_language: Idioma de origem (padrão: pt)
            
        Returns:
            Texto traduzido
        """
        if not self.client:
            logger.error("Google Cloud Translation não configurado")
            return None
        
        try:
            for attempt in range(MAX_RETRIES):
                try:
                    result = self.client.translate(
                        values=text,
                        target_language=target_language,
                        source_language=source_language
                    )
                    
                    if isinstance(result, dict):
                        translated = result.get("translatedText", text)
                    else:
                        translated = result["translatedText"] if hasattr(result, '__getitem__') else text
                    
                    logger.info(f"Tradução Google Cloud: {source_language} → {target_language}")
                    return translated
                
                except Exception as e:
                    logger.warning(f"Tentativa {attempt + 1}/{MAX_RETRIES} falhou: {str(e)}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(RETRY_DELAY)
                    else:
                        raise
        
        except Exception as e:
            logger.error(f"Erro na tradução Google Cloud: {str(e)}")
            return None
    
    def translate_srt_subtitles(self, srt_text: str, target_language: str, source_language: str = "inglês") -> Optional[str]:
        """
        Traduz legendas SRT mantendo timestamps.
        
        Args:
            srt_text: Conteúdo do arquivo SRT
            target_language: Idioma alvo (ex: "português", será convertido para PT-BR)
            source_language: Idioma fonte (padrão: "inglês")
            
        Returns:
            SRT com legendas traduzidas
        """
        try:
            import pysrt
            
            srt = pysrt.SubRipFile.from_string(srt_text)
            translated_count = 0
            
            logger.info(f"Traduzindo {len(srt)} legendas de {source_language} para {target_language}...")
            with alive_bar(len(srt), title='Translating subtitles', bar='smooth', spinner='dots_waves') as bar:
                for subtitle in srt:
                    if subtitle.text:
                        translated = self.translate_text(
                            subtitle.text,
                            source_language,
                            target_language
                        )
                        if translated:
                            subtitle.text = translated
                            translated_count += 1
                    bar()
            
            logger.info(f"Legendas traduzidas: {translated_count}/{len(srt)}")
            return srt.to_string()
        
        except ImportError:
            logger.error("pysrt não está instalado")
            return None
        except Exception as e:
            logger.error(f"Erro ao traduzir SRT: {str(e)}")
            return None


def get_translator(use_gemini: bool = True) -> Optional[object]:
    """
    Factory para obter o tradutor apropriado.
    
    Args:
        use_gemini: Se True, tenta usar Gemini; caso contrário, usa Google Cloud Translation
        
    Returns:
        Instância do tradutor ou None se falhar
    """
    try:
        if use_gemini and GEMINI_AVAILABLE:
            return GeminiTranslator()
        elif GOOGLE_TRANSLATE_AVAILABLE:
            return GoogleCloudTranslator()
        else:
            logger.error("Nenhum serviço de tradução disponível")
            return None
    except Exception as e:
        logger.error(f"Erro ao inicializar tradutor: {str(e)}")
        return None
