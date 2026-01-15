#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Pipeline HÍBRIDO: Faster-Whisper + Stable-TS

AUTOMÁTICO:
- Vídeos < 20min  → Faster-Whisper V3 (rápido)
- Vídeos > 20min  → Stable-TS (evita time drift acumulativo)

OTIMIZAÇÕES:
- FFmpeg Piping (zero I/O)
- Filtros de confiança (no_speech_prob, avg_logprob)
- Detecção automática de duração
- Formatação Netflix (42 chars/linha)
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

# Verificar disponibilidade do Stable-TS
try:
    import stable_whisper
    STABLE_TS_AVAILABLE = True
except ImportError:
    STABLE_TS_AVAILABLE = False
    print("ℹ️ Stable-TS não instalado. Vídeos longos usarão Faster-Whisper.")
    print("   Para melhor qualidade em vídeos > 45min, instale: pip install stable-ts\n")

# Configurações
PASTA_ENTRADA = "proximos_para_traducao"
PASTA_SAIDA = str(SUBTITLES_EN_DIR)
MODELO = WHISPER_MODEL
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# Limites de duração (em segundos)
DURACAO_CURTA = 1200    # 20 minutos (threshold para Stable-TS)
DURACAO_LONGA = 1200    # 20 minutos (mesmo valor, mantém compatibilidade)

# Parâmetros de Qualidade
LIMITE_NO_SPEECH = 0.6
LIMITE_AVG_LOGPROB = -1.0
LIMITE_CPS = 25

# Alucinações conhecidas
ALUCINACOES_COMUNS = [
    "thank you for watching", "thanks for watching",
    "subscribe to our channel", "please subscribe",
    "see you next time", "stay tuned",
    "legendas por", "subtitles by", "amara.org",
    "transcribed by", "captioned by",
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

def obter_duracao_video(video_path):
    """
    Obtém a duração do vídeo em segundos usando ffprobe.
    
    Returns:
        float: Duração em segundos, ou None se falhar
    """
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
        return None
        
    except Exception as e:
        print(f"    ⚠️ Erro ao obter duração: {e}")
        return None

def carregar_audio_via_pipe(video_path):
    """
    Usa FFmpeg para extrair, normalizar e enviar o áudio diretamente para a memória (Pipe).
    """
    filtro_reforçado = (
        "afftdn=nr=20:nf=-30,"
        "dynaudnorm=f=75:g=31:p=0.95:m=10,"
        "highpass=f=200,"
        "lowpass=f=3000"
    )
    
    comando = [
        "ffmpeg",
        "-i", video_path,
        "-af", filtro_reforçado,
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
            stderr=subprocess.DEVNULL,
            bufsize=10**7
        )
        
        dados_raw, _ = processo.communicate(timeout=300)
        
        if processo.returncode != 0 or len(dados_raw) == 0:
            return None
        
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

def transcrever_com_stable_ts(video_path, srt_output):
    """
    Transcreve usando Stable-TS para vídeos longos.
    ANTI-CHICLETE: VAD agressivo + limitação de duração máxima.
    TURBO RYZEN: Otimizado para Ryzen 7 3800X (12 threads).
    BLINDADO: Salva SRT imediatamente após transcrição (nunca perde trabalho).
    """
    if not STABLE_TS_AVAILABLE:
        return None
    
    try:
        import torch
        
        # --- DETECÇÃO DE HARDWARE ---
        tem_nvidia = torch.cuda.is_available()
        
        # Configuração para Ryzen 7 3800X (8 Cores / 16 Threads)
        # Usa 12 threads (75%) e deixa 4 para o SO
        THREADS_RYZEN = 12
        
        if tem_nvidia:
            device = "cuda"
            modelo_usar = MODELO  # Usa o configurado (large-v3)
            compute_type = "float16"
            threads = 4  # GPU não precisa de muitos threads CPU
            print("    🚀 GPU NVIDIA detectada! Modo Turbo Ativado.")
        else:
            device = "cpu"
            # Modelo 'medium' é ideal para CPU (rápido e preciso)
            # 'large-v3' seria 4x mais lento
            modelo_usar = "medium"
            compute_type = "int8"  # Obrigatório para velocidade em CPU
            threads = THREADS_RYZEN
            print(f"    🦁 Processador Ryzen detectado!")
            print(f"    🔥 MODO TURBO CPU: {threads} threads (Modelo: {modelo_usar} - int8)")
        
        # Carregar modelo usando Faster-Whisper como motor (MUITO mais rápido)
        print("    ⚙️ Carregando Stable-TS + Faster-Whisper...", end=" ", flush=True)
        model = stable_whisper.load_faster_whisper(
            modelo_usar,
            device=device,
            compute_type=compute_type,
            cpu_threads=threads,
            download_root=str(MODELS_DIR)
        )
        print("✓")
        
        # Obter áudio
        print("    🎙️ Extraindo áudio...", end=" ", flush=True)
        audio = carregar_audio_via_pipe(video_path)
        if audio is None:
            return None
        print("✓")
        
        # Transcrever com Stable-TS (VAD Agressivo)
        # CORREÇÃO: Usar .transcribe() em vez de .transcribe_stable() (deprecated)
        print("    🧠 Transcrevendo (ventoinhas vão acelerar!)...", end=" ", flush=True)
        result = model.transcribe(
            audio,
            language="en",
            vad=True,
            vad_threshold=0.3,  # ↓ Baixamos de 0.5 para 0.3 (Modo Sensível para sussurros)
            vad_parameters=dict(
                min_silence_duration_ms=500,  # Corta se houver 0.5s de silêncio
                speech_pad_ms=200             # Margem pequena nas pontas
            ),
            regroup=True,
            word_timestamps=True,
        )
        print("✓")
        
        # --- SALVAMENTO DE SEGURANÇA (CRÍTICO!) ---
        # Salva IMEDIATAMENTE antes de tentar qualquer otimização
        # Isso garante que nunca perdemos 45+ minutos de trabalho
        print("    💾 Salvando versão base...", end=" ", flush=True)
        result.to_srt_vtt(srt_output, word_level=False)
        print("✓")
        
        # --- PÓS-PROCESSAMENTO: "Travão de Mão" Anti-Chiclete (OPCIONAL) ---
        # Se falhar aqui, não tem problema - já salvamos o SRT base
        print("    ✂️ Refinando durações (Anti-Chiclete)...", end=" ", flush=True)
        try:
            # Verifica se os métodos existem antes de usar (defensive programming)
            if hasattr(result, 'clamp_max_duration'):
                result.clamp_max_duration(7.0)  # NENHUMA legenda > 7 segundos
            
            if hasattr(result, 'split_by_gap'):
                result.split_by_gap(0.5)  # Força quebra se houver buraco > 0.5s
                
            if hasattr(result, 'remove_all_empty'):
                result.remove_all_empty()  # Remove legendas vazias
            
            # Se conseguiu otimizar, sobrescreve com versão melhorada
            result.to_srt_vtt(srt_output, word_level=False)
            print("✓ (otimizado)")
            
        except Exception as e_opt:
            # Não falha - apenas avisa e mantém a versão base
            print(f"⚠️ (base salva, otimização ignorada)")
        
        return len(result.segments)
        
    except Exception as e:
        print(f"    ❌ Stable-TS falhou: {str(e)[:60]}")
        return None

def transcrever_audio_otimizado(audio_array, model):
    """
    Transcreve áudio com filtros de confiança integrados (Faster-Whisper).
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
        
        segmentos_filtrados = []
        stats = {
            'total': 0,
            'no_speech': 0,
            'low_prob': 0,
            'alucinacao': 0,
            'aprovados': 0
        }
        
        for segment in segments:
            stats['total'] += 1
            
            if segment.no_speech_prob > LIMITE_NO_SPEECH:
                stats['no_speech'] += 1
                continue
            
            if segment.avg_logprob < LIMITE_AVG_LOGPROB:
                stats['low_prob'] += 1
                continue
            
            texto = segment.text.strip()
            if eh_alucinacao_conhecida(texto):
                stats['alucinacao'] += 1
                continue
            
            stats['aprovados'] += 1
            segmentos_filtrados.append({
                'start': segment.start,
                'end': segment.end,
                'text': texto,
            })
        
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

def extrair_srt_hibrido(video_path, model_faster):
    """
    Extrai SRT usando método HÍBRIDO:
    - Detecta duração do vídeo
    - Escolhe Stable-TS (longo) ou Faster-Whisper (curto)
    """
    nome_video = Path(video_path).stem
    srt_saida = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
    
    if os.path.exists(srt_saida):
        print(f"  ✓ Já existe")
        return nome_video, True
    
    try:
        # 1. Detectar duração
        print(f"  🔍 Detectando duração...", end=" ", flush=True)
        duracao = obter_duracao_video(video_path)
        
        if duracao is None:
            print("⚠️ Usando Faster-Whisper (duração desconhecida)")
            metodo = "faster"
        elif duracao > DURACAO_LONGA and STABLE_TS_AVAILABLE:
            minutos = int(duracao / 60)
            print(f"✓ ({minutos}min)")
            print(f"  🎯 Vídeo longo: usando Stable-TS...", end=" ", flush=True)
            metodo = "stable"
        else:
            minutos = int(duracao / 60)
            print(f"✓ ({minutos}min)")
            print(f"  ⚡ Vídeo curto: usando Faster-Whisper...", end=" ", flush=True)
            metodo = "faster"
        
        # 2. Transcrever
        if metodo == "stable":
            num_legendas = transcrever_com_stable_ts(video_path, srt_saida)
            if num_legendas is None:
                print("❌ Stable-TS falhou, usando fallback (Faster-Whisper)")
                metodo = "faster"  # Fallback
            else:
                print(f"✓ ({num_legendas} legendas)")
                return nome_video, True
        
        if metodo == "faster":
            print(f"processando...", end=" ", flush=True)
            audio_array = carregar_audio_via_pipe(video_path)
            if audio_array is None:
                print("❌ FFmpeg falhou")
                return nome_video, False
            
            segments = transcrever_audio_otimizado(audio_array, model_faster)
            if segments is None or len(segments) == 0:
                print("❌ Whisper falhou")
                return nome_video, False
            
            contador = salvar_srt(segments, srt_saida)
            print(f"✓ ({contador} legendas)")
        
        return nome_video, True
        
    except Exception as e:
        print(f"❌ {str(e)[:60]}")
        return nome_video, False

# Carregar modelo Faster-Whisper uma única vez
print("⏳ Carregando modelo Faster-Whisper...")
model_faster = WhisperModel(MODELO, device=DEVICE, compute_type=COMPUTE_TYPE, download_root=str(MODELS_DIR))
print("✅ Modelo carregado!\n")

def main():
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    todos_videos = sorted([
        os.path.join(PASTA_ENTRADA, f) 
        for f in os.listdir(PASTA_ENTRADA) 
        if f.lower().endswith('.mp4')
    ])
    
    print(f"🎬 Encontrados {len(todos_videos)} vídeos na pasta\n")
    
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
    print(f"🤖 MODO HÍBRIDO ATIVO:")
    print(f"   • < 20min: Faster-Whisper V3 (rápido)")
    print(f"   • > 20min: Stable-TS (precisão máxima, previne drift)")
    if not STABLE_TS_AVAILABLE:
        print(f"   ⚠️ Stable-TS não instalado (todos usarão Faster-Whisper)")
    print(f"\n🚀 Iniciando Pipeline...\n")
    
    total_videos = len(videos)
    sucessos_finais = 0
    
    for i, video in enumerate(videos, 1):
        nome_completo = Path(video).name
        nome_video = Path(video).stem
        print(f"[{i}/{total_videos}] 🎬 {nome_completo}")
        
        # 1. Extrair com método híbrido
        _, sucesso_extracao = extrair_srt_hibrido(video, model_faster)
        if not sucesso_extracao:
            print(f"  ⏭️ Pulando etapas seguintes\n")
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
        
        # 3. Embutir
        if sucesso_traducao and os.path.exists(srt_pt_path):
            video_final_path = os.path.join(VIDEOS_OUTPUT_DIR, f"{nome_video}_PT.mp4")
            print(f"  📽️ Embutindo legenda...", end=" ", flush=True)
            sucesso_embed = embutir_legenda(video, srt_pt_path, video_final_path)
            if sucesso_embed:
                print("✓")
                print(f"  ✨ Finalizado: {video_final_path}")
                sucessos_finais += 1
            else:
                print("❌ Falha ao embutir")
        
        # 4. Cooldown
        if i < total_videos:
            print(f"  💤 Aguardando 30s...\n")
            time.sleep(30)
    
    print("\n" + "="*70)
    print(f"🏁 Pipeline: {sucessos_finais}/{total_videos} vídeos completados!")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
