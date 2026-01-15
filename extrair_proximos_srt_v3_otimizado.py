#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrai SRT em inglês de todos os vídeos da pasta proximos_para_traducao

OTIMIZAÇÕES V3:
- FFmpeg Piping: Áudio processado direto para memória (sem arquivos temporários)
- dynaudnorm: Normalização dinâmica para áudio com picos (superior ao loudnorm)
- Filtros de Confiança: Usa no_speech_prob e avg_logprob para detectar alucinações
- CPS: Verifica Caracteres Por Segundo para legibilidade
- VAD robusto para evitar transcrição de silêncios

ANTI-ALUCINAÇÃO:
- VAD (Voice Activity Detection): remove silêncios antes de transcrever
- condition_on_previous_text=False: quebra loops de repetição
- no_speech_prob: descarta segmentos com alta probabilidade de silêncio
- Thresholds rigorosos para evitar transcrever ruído
"""

import os
import subprocess
import tempfile
from pathlib import Path
import time
import numpy as np
from faster_whisper import WhisperModel
from config import SUBTITLES_EN_DIR, SUBTITLES_OUTPUT_DIR, VIDEOS_OUTPUT_DIR, WHISPER_MODEL, MODELS_DIR

# Importar ferramentas do pipeline
try:
    from traduzir_com_gemini import traduzir_srt_gemini
    from embutir_legendas import embutir_legendas as embutir_legenda
except ImportError:
    print("⚠️ Módulos traduzir_com_gemini ou embutir_legendas não encontrados!")
    def traduzir_srt_gemini(*args): return False
    def embutir_legenda(*args): return False

# Configurações
PASTA_ENTRADA = "proximos_para_traducao"
PASTA_SAIDA = str(SUBTITLES_EN_DIR)
MODELO = WHISPER_MODEL
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# Parâmetros de Qualidade
LIMITE_NO_SPEECH = 0.6  # Se > 0.6, provavelmente é silêncio/ruído
LIMITE_AVG_LOGPROB = -1.0  # Confiança mínima da transcrição
LIMITE_CPS = 25  # Caracteres por segundo (acima é difícil ler)

# Lista de alucinações conhecidas do Whisper
ALUCINACOES_COMUNS = [
    "thank you for watching",
    "thanks for watching",
    "subscribe to our channel",
    "please subscribe",
    "see you next time",
    "stay tuned",
    "legendas por",
    "subtitles by",
    "amara.org",
    "transcribed by",
    "captioned by",
]

def eh_alucinacao_conhecida(texto):
    """Detecta frases comuns que o Whisper inventa em silêncios."""
    texto_lower = texto.lower().strip()
    return any(alu in texto_lower for alu in ALUCINACOES_COMUNS)

def quebrar_legenda_netflix(texto, max_chars=42, max_linhas=2):
    """Quebra texto seguindo padrão Netflix de legendagem (max 42 chars/linha, 2 linhas)."""
    texto = texto.replace('\n', ' ').strip()
    palavras = texto.split()
    linhas = []
    linha_atual = ""
    
    for palavra in palavras:
        teste = f"{linha_atual} {palavra}".strip()
        if len(teste) <= max_chars:
            linha_atual = teste
        else:
            if linha_atual:
                linhas.append(linha_atual)
            linha_atual = palavra
    
    if linha_atual:
        linhas.append(linha_atual)
    
    return "\n".join(linhas[:max_linhas])

def carregar_audio_via_pipe(video_path):
    """
    Usa FFmpeg para extrair, normalizar e enviar o áudio diretamente para a memória (Pipe).
    
    Aplica:
    - dynaudnorm: Normalização dinâmica (ótimo para picos/sussurros)
    - arnndn: Redução de ruído com IA (se disponível, senão usa afftdn)
    - highpass/lowpass: Remove frequências fora da voz humana
    - ar=16000: Taxa de amostragem nativa do Whisper
    - ac=1: Mono (Whisper não precisa de estéreo)
    - f=s16le: Formato PCM 16-bit raw
    
    Returns:
        numpy.array: Áudio em float32 normalizado, ou None se falhar
    """
    # Filtro otimizado com fallback
    # Tenta arnndn (melhor), se falhar usa afftdn
    filtro_principal = (
        "arnndn=m=models/rnn.rnnn,"  # Noise reduction com IA (pode não estar disponível)
        "dynaudnorm=f=150:g=15:p=0.9,"  # Normalização dinâmica
        "highpass=f=200,"  # Remove graves (não-voz)
        "lowpass=f=3000"   # Remove agudos (chiados)
    )
    
    # Filtro fallback (sem arnndn)
    filtro_fallback = (
        "afftdn=nr=20:nf=-30,"  # Noise reduction FFT
        "dynaudnorm=f=150:g=15:p=0.9,"
        "highpass=f=200,"
        "lowpass=f=3000"
    )
    
    comando = [
        "ffmpeg",
        "-i", video_path,
        "-af", filtro_fallback,  # Usar fallback por padrão (mais compatível)
        "-ar", "16000",
        "-ac", "1",
        "-f", "s16le",
        "-vn",
        "-"
    ]
    
    try:
        processo = subprocess.Popen(
            comando,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL
        )
        
        dados_raw, _ = processo.communicate(timeout=300)
        
        if processo.returncode != 0 or len(dados_raw) == 0:
            return None
        
        # Converte bytes para array NumPy float32 (formato esperado pelo Whisper)
        audio_array = np.frombuffer(dados_raw, np.int16).flatten().astype(np.float32) / 32768.0
        
        return audio_array
        
    except subprocess.TimeoutExpired:
        processo.kill()
        return None
    except Exception as e:
        print(f"    ⚠️ Erro no pipe: {str(e)[:50]}")
        return None

def format_timestamp(seconds):
    """Converte segundos para formato SRT HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def transcrever_audio_otimizado(audio_array, model):
    """
    Transcreve áudio com filtros de confiança integrados.
    
    Retorna apenas segmentos de alta qualidade:
    - Filtra por no_speech_prob (probabilidade de silêncio)
    - Filtra por avg_logprob (confiança da transcrição)
    - Detecta alucinações conhecidas
    - Verifica CPS (legibilidade)
    """
    try:
        vad_parameters = {
            "threshold": 0.5,
            "min_speech_duration_ms": 250,
            "min_silence_duration_ms": 500
        }
        
        segments, info = model.transcribe(
            audio_array,
            language="en",
            beam_size=5,
            without_timestamps=False,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=vad_parameters,
            no_speech_threshold=0.4,
            log_prob_threshold=-0.9,
            compression_ratio_threshold=2.4,
            word_timestamps=True,
        )
        
        # Filtrar segmentos por qualidade
        segmentos_filtrados = []
        stats = {
            'total': 0,
            'no_speech': 0,
            'low_prob': 0,
            'alucinacao': 0,
            'cps_alto': 0,
            'aprovados': 0
        }
        
        for segment in segments:
            stats['total'] += 1
            
            # Filtro 1: Probabilidade de Não-Fala
            if segment.no_speech_prob > LIMITE_NO_SPEECH:
                stats['no_speech'] += 1
                continue
            
            # Filtro 2: Confiança da transcrição
            if segment.avg_logprob < LIMITE_AVG_LOGPROB:
                stats['low_prob'] += 1
                continue
            
            # Filtro 3: Alucinações conhecidas
            texto = segment.text.strip()
            if eh_alucinacao_conhecida(texto):
                stats['alucinacao'] += 1
                continue
            
            # Filtro 4: CPS (apenas alerta, não bloqueia)
            duracao = segment.end - segment.start
            if duracao > 0:
                cps = len(texto) / duracao
                if cps > LIMITE_CPS:
                    stats['cps_alto'] += 1
            
            stats['aprovados'] += 1
            segmentos_filtrados.append({
                'start': segment.start,
                'end': segment.end,
                'text': texto,
                'no_speech_prob': segment.no_speech_prob,
                'avg_logprob': segment.avg_logprob
            })
        
        # Log de estatísticas
        if stats['total'] > 0:
            filtrados = stats['no_speech'] + stats['low_prob'] + stats['alucinacao']
            if filtrados > 0:
                print(f"(filtrou {filtrados}: {stats['no_speech']} silêncio, "
                      f"{stats['low_prob']} baixa conf., {stats['alucinacao']} aluc.)", 
                      end=" ", flush=True)
        
        return segmentos_filtrados
        
    except Exception as e:
        print(f"    ❌ Transcrição falhou: {str(e)[:60]}")
        return None

def salvar_srt(segments, output_path):
    """Salva segmentos em SRT com formatação Netflix"""
    contador = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for segment in segments:
            texto = quebrar_legenda_netflix(segment['text'], max_chars=42, max_linhas=2)
            
            contador += 1
            start = format_timestamp(segment['start'])
            end = format_timestamp(segment['end'])
            f.write(f"{contador}\n{start} --> {end}\n{texto}\n\n")
    
    return contador

def extrair_srt_otimizado(video_path, model):
    """Extrai SRT de um vídeo usando piping otimizado"""
    nome_video = Path(video_path).stem
    srt_saida = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
    
    # Pular se já existe
    if os.path.exists(srt_saida):
        print(f"  ✓ Já existe")
        return nome_video, True
    
    try:
        print(f"  1️⃣ Processando áudio (pipe+filtros)...", end=" ", flush=True)
        audio_array = carregar_audio_via_pipe(video_path)
        if audio_array is None:
            print("❌ FFmpeg falhou")
            return nome_video, False
        print("✓")
        
        print(f"  2️⃣ Transcrevendo com filtros...", end=" ", flush=True)
        segments = transcrever_audio_otimizado(audio_array, model)
        if segments is None or len(segments) == 0:
            print("❌ Whisper falhou ou nenhum segmento válido")
            return nome_video, False
        print("✓")
        
        print(f"  3️⃣ Salvando SRT...", end=" ", flush=True)
        contador = salvar_srt(segments, srt_saida)
        print(f"✓ ({contador} legendas)")
        
        return nome_video, True
        
    except Exception as e:
        print(f"❌ {str(e)[:60]}")
        return nome_video, False

# Carregar modelo uma única vez
print("⏳ Carregando modelo Whisper...")
model = WhisperModel(MODELO, device=DEVICE, compute_type=COMPUTE_TYPE, download_root=str(MODELS_DIR))
print("✅ Modelo carregado!\n")

def main():
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    # Listar todos os vídeos
    todos_videos = sorted([
        os.path.join(PASTA_ENTRADA, f) 
        for f in os.listdir(PASTA_ENTRADA) 
        if f.lower().endswith('.mp4')
    ])
    
    print(f"🎬 Encontrados {len(todos_videos)} vídeos na pasta\n")
    
    # Filtrar vídeos que já têm SRT existente
    videos = []
    ja_existentes = 0
    for video in todos_videos:
        nome_video = Path(video).stem
        srt_path = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
        if os.path.exists(srt_path):
            ja_existentes += 1
        else:
            videos.append(video)
    
    if ja_existentes > 0:
        print(f"✅ {ja_existentes} vídeo(s) já têm SRT - pulando")
    
    if len(videos) == 0:
        print(f"\n🎉 Todos os vídeos já têm SRT extraído!")
        return
    
    print(f"📋 {len(videos)} vídeo(s) para processar\n")
    print(f"🚀 OTIMIZAÇÕES ATIVAS:")
    print(f"   • FFmpeg Piping (sem arquivos temporários)")
    print(f"   • dynaudnorm (normalização dinâmica)")
    print(f"   • Filtros de Confiança (no_speech_prob, avg_logprob)")
    print(f"   • Detecção de alucinações conhecidas")
    print(f"   • Formatação Netflix (42 chars/linha)\n")
    
    print(f"🚀 Iniciando Pipeline Sequencial (Extrair -> Traduzir -> Embutir)\n")
    
    total_videos = len(videos)
    sucessos_finais = 0
    
    for i, video in enumerate(videos, 1):
        nome_completo = Path(video).name
        nome_video = Path(video).stem
        print(f"[{i}/{total_videos}] 🎬 Processando: {nome_completo}")
        
        # 1. Extrair com otimizações
        _, sucesso_extracao = extrair_srt_otimizado(video, model)
        if not sucesso_extracao:
            print(f"  ⏭️ Pulando etapas seguintes (Extração falhou)\n")
            continue
            
        srt_en_path = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
        
        # 2. Traduzir
        srt_pt_path = os.path.join(SUBTITLES_OUTPUT_DIR, f"{nome_video}_PT.srt")
        print(f"  🤖 Traduzindo (Gemini)...", end=" ", flush=True)
        sucesso_traducao = traduzir_srt_gemini(srt_en_path, srt_pt_path)
        if sucesso_traducao:
            print("✓")
        else:
            print("❌ Falha na tradução")
        
        # 3. Embutir (apenas se tradução foi bem-sucedida)
        if sucesso_traducao and os.path.exists(srt_pt_path):
            video_final_path = os.path.join(VIDEOS_OUTPUT_DIR, f"{nome_video}_PT.mp4")
            print(f"  📽️ Embutindo legenda...", end=" ", flush=True)
            sucesso_embed = embutir_legenda(video, srt_pt_path, video_final_path)
            if sucesso_embed:
                print("✓")
                print(f"  ✨ Vídeo finalizado: {video_final_path}")
                sucessos_finais += 1
            else:
                print("❌ Falha ao embutir")
        
        # 4. Cooldown
        if i < total_videos:
            print(f"  💤 Aguardando 30s para o próximo vídeo...\n")
            time.sleep(30)
    
    print("\n" + "="*70)
    print(f"🏁 Pipeline Finalizado: {sucessos_finais}/{total_videos} vídeos completados!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
