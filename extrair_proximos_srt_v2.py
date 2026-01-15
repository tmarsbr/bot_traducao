#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Extrai SRT em inglês de todos os vídeos da pasta proximos_para_traducao

ANTI-ALUCINAÇÃO:
- VAD (Voice Activity Detection): remove silêncios antes de transcrever
- condition_on_previous_text=False: quebra loops de repetição
- Thresholds rigorosos para evitar transcrever ruído

PRÉ-PROCESSAMENTO de áudio:
- Highpass filter: 80Hz (remove ruídos graves)
- Lowpass filter: 3400Hz (remove chiados agudos)
- Resultado: Áudio MONO otimizado para Whisper

PÓS-PROCESSAMENTO:
- Filtro de alucinações internas (ex: "oh, oh, oh, oh...")
- Filtro de repetições consecutivas
"""

import os
import subprocess
import tempfile
from pathlib import Path
import time
from faster_whisper import WhisperModel
from config import SUBTITLES_EN_DIR, SUBTITLES_OUTPUT_DIR, VIDEOS_OUTPUT_DIR, WHISPER_MODEL, MODELS_DIR

# Importar ferramentas do pipeline
try:
    from traduzir_com_gemini import traduzir_srt_gemini
    from embutir_legendas_pt import embutir_legenda
except ImportError:
    print("⚠️ Módulos traduzir_com_gemini ou embutir_legendas_pt não encontrados!")
    # Criar stubs para não quebrar se faltar
    def traduzir_srt_gemini(*args): return False
    def embutir_legenda(*args): return False

# Configurações
PASTA_ENTRADA = "proximos_para_traducao"
PASTA_SAIDA = str(SUBTITLES_EN_DIR)
MODELO = WHISPER_MODEL
DEVICE = "cpu"
COMPUTE_TYPE = "int8"

# Carregar modelo uma única vez
print("⏳ Carregando modelo Whisper...")
model = WhisperModel(MODELO, device=DEVICE, compute_type=COMPUTE_TYPE, download_root=str(MODELS_DIR))
print("✅ Modelo carregado!\n")

def extrair_audio_bruto(video_path):
    """Extrai áudio bruto do vídeo (sem filtros)"""
    audio_tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_tmp.close()
    
    cmd = [
        'ffmpeg', '-i', video_path,
        '-acodec', 'pcm_s16le',
        '-ar', '44100',
        '-ac', '2',
        '-v', 'error',
        '-y',
        audio_tmp.name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode == 0:
        return audio_tmp.name
    else:
        if os.path.exists(audio_tmp.name):
            os.unlink(audio_tmp.name)
        return None

def limpar_audio_com_filtros(audio_bruto):
    """
    Limpa áudio aplicando filtros FFmpeg:
    1. Highpass filter 80Hz (remove ruídos graves)
    2. Lowpass filter 3400Hz (remove chiados agudos)
    Resultado: áudio MONO otimizado para transcrição
    """
    audio_limpo = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_limpo.close()
    
    # Filtro simples e robusto:
    # - highpass=f=80  : remove frequências abaixo de 80Hz (graves, humming)
    # - lowpass=f=3400 : remove frequências acima de 3400Hz (chiados, noise)
    # - aformat=channel_layouts=mono : converte para mono (compatível com qualquer entrada)
    
    filtro = (
        "afftdn=nr=20:nf=-30,"     # Reduce noise
        "highpass=f=200,"          # Voice isolation (stricter)
        "lowpass=f=3000,"
        "loudnorm,"                # Normalization
        "aformat=channel_layouts=mono"
    )
    
    cmd = [
        'ffmpeg', '-i', audio_bruto,
        '-af', filtro,
        '-acodec', 'pcm_s16le',
        '-ar', '44100',
        '-v', 'error',
        '-y',
        audio_limpo.name
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    
    # Verifica se arquivo foi criado e tem tamanho > 0
    if os.path.exists(audio_limpo.name) and os.path.getsize(audio_limpo.name) > 1000:
        return audio_limpo.name
    
    # Fallback: se filtro falhar, tenta sem filtro (apenas converte para mono)
    if os.path.exists(audio_limpo.name):
        os.unlink(audio_limpo.name)
    
    print("(fallback)", end=" ", flush=True)
    audio_limpo_fb = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_limpo_fb.close()
    
    cmd_fallback = [
        'ffmpeg', '-i', audio_bruto,
        '-acodec', 'pcm_s16le',
        '-ar', '44100',
        '-ac', '1',
        '-v', 'error',
        '-y',
        audio_limpo_fb.name
    ]
    
    result_fb = subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=300)
    
    if os.path.exists(audio_limpo_fb.name) and os.path.getsize(audio_limpo_fb.name) > 1000:
        return audio_limpo_fb.name
    else:
        if os.path.exists(audio_limpo_fb.name):
            os.unlink(audio_limpo_fb.name)
        return None

def transcrever_audio(audio_path, model):
    """
    Transcreve áudio com Whisper usando configurações ANTI-ALUCINAÇÃO:
    - VAD (Voice Activity Detection): remove silêncios antes de transcrever
    - condition_on_previous_text=False: quebra loops de repetição
    - Thresholds rigorosos para evitar transcrever ruído
    """
    try:
        # Parâmetros do VAD (Voice Activity Detection)
        vad_parameters = {
            "threshold": 0.5,              # Sensibilidade do VAD (0.5 é equilibrado)
            "min_speech_duration_ms": 250, # Ignora sons < 250ms (não são fala)
            "min_silence_duration_ms": 500 # Considera silêncio após 500ms sem fala
        }
        
        segments, info = model.transcribe(
            audio_path,
            language="en",
            beam_size=5,
            without_timestamps=False,
            
            # CRUCIAL: Desativa condicionamento no texto anterior
            # Isso QUEBRA os loops de repetição (ex: "You're fucking wrong" repetindo)
            condition_on_previous_text=False,
            
            # VAD (Voice Activity Detection) - Remove silêncios ANTES de transcrever
            # Principal causa de alucinações é o Whisper tentar preencher silêncios
            vad_filter=True,
            vad_parameters=vad_parameters,
            
            # Thresholds rigorosos e Otimizações de Guia Técnico
            no_speech_threshold=0.4,       # Mais sensível a sussurros (antes 0.6)
            log_prob_threshold=-0.9,       # Mais "corajoso" (antes -1.0)
            compression_ratio_threshold=2.4, # Detecta texto repetitivo
            word_timestamps=True,          # Melhora sincronia fina
            initial_prompt="Este é um vídeo com muitos sussurros e termos específicos." # Contexto
        )
        return list(segments)
    except Exception as e:
        print(f"    ❌ Transcrição falhou: {str(e)[:60]}")
        return None

def normalizar_texto(texto):
    """Normaliza texto para comparação (remove pontuação e espaços extras)"""
    import re
    texto = texto.lower().strip()
    texto = re.sub(r'[^\w\s]', '', texto)  # Remove pontuação
    texto = re.sub(r'\s+', ' ', texto)      # Normaliza espaços
    return texto

def eh_alucinacao_interna(texto, max_repeticoes=5):
    """
    Detecta alucinações DENTRO de um único segmento.
    Exemplo: "oh, oh, oh, oh, oh, oh..." ou "yeah yeah yeah yeah..."
    
    Returns:
        True se o segmento é uma alucinação, False se é legítimo
    """
    import re
    
    # Normalizar e dividir em palavras
    texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
    palavras = texto_limpo.split()
    
    if len(palavras) < 5:
        return False  # Muito curto para ser alucinação
    
    # Contar frequência de cada palavra
    from collections import Counter
    contagem = Counter(palavras)
    
    # Se uma palavra aparece mais de 50% das vezes, é alucinação
    palavra_mais_comum, qtd = contagem.most_common(1)[0]
    
    # Palavras comuns que podem repetir legitimamente
    palavras_ok = {'i', 'you', 'the', 'a', 'and', 'to', 'it', 'is', 'of', 'in', 'that', 'me', 'my', 'your'}
    
    if palavra_mais_comum in palavras_ok:
        threshold = 0.7  # 70% para palavras comuns
    else:
        threshold = 0.5  # 50% para outras palavras
    
    if qtd / len(palavras) >= threshold:
        return True
    
    # Verificar padrão repetitivo (mesma palavra ou frase curta repetindo)
    if len(palavras) >= 10:
        # Verificar se é só a mesma 1-3 palavras repetindo
        palavras_unicas = set(palavras)
        if len(palavras_unicas) <= 3 and len(palavras) >= 10:
            return True
    
    return False

def filtrar_alucinacoes(segments, max_repeticoes=2):
    """
    Remove alucinações do Whisper (frases repetidas consecutivamente).
    MAIS AGRESSIVO: remove se repetir mais de 2 vezes.
    Também detecta frases similares (não apenas idênticas).
    
    Args:
        segments: Lista de segmentos do Whisper
        max_repeticoes: Máximo de repetições permitidas (default: 2)
    
    Returns:
        Lista filtrada de segmentos
    """
    if not segments:
        return segments
    
    # Converter para lista de dicts para facilitar manipulação
    segs = []
    alucinacoes_internas = 0
    for s in segments:
        text = s.text.strip() if hasattr(s, 'text') else str(s).strip()
        if text:
            # Verificar se é alucinação interna (ex: "oh, oh, oh, oh...")
            if eh_alucinacao_interna(text):
                alucinacoes_internas += 1
                continue  # Pular este segmento
            
            segs.append({
                'start': s.start if hasattr(s, 'start') else 0,
                'end': s.end if hasattr(s, 'end') else 0,
                'text': text,
                'text_norm': normalizar_texto(text)
            })
    
    if alucinacoes_internas > 0:
        print(f"(removeu {alucinacoes_internas} repetições internas)", end=" ", flush=True)
    
    if not segs:
        return []
    
    # Detectar e remover sequências repetitivas
    filtrados = []
    i = 0
    total_removidos = 0
    
    while i < len(segs):
        texto_norm = segs[i]['text_norm']
        
        # Contar quantas vezes esse texto (ou similar) se repete consecutivamente
        repeticoes = 1
        j = i + 1
        while j < len(segs):
            outro_texto = segs[j]['text_norm']
            # Comparação: idêntico OU um contém o outro (para frases curtas repetidas)
            if texto_norm == outro_texto or (len(texto_norm) > 3 and (texto_norm in outro_texto or outro_texto in texto_norm)):
                repeticoes += 1
                j += 1
            else:
                break
        
        # Se repetiu mais que o máximo permitido, é alucinação
        if repeticoes > max_repeticoes:
            # Manter apenas 1 ocorrência
            filtrados.append(segs[i])
            total_removidos += repeticoes - 1
            i = j  # Pular todas as repetições
        else:
            # Manter todas as ocorrências (são legítimas)
            for k in range(i, j):
                filtrados.append(segs[k])
            i = j
    
    if total_removidos > 0:
        print(f"(filtrou {total_removidos} alucinações)", end=" ", flush=True)
    
    return filtrados

def salvar_srt(segments, output_path):
    """Salva transcrição em SRT com filtro anti-alucinação"""
    # Primeiro, filtrar alucinações (max 2 repetições)
    segments_filtrados = filtrar_alucinacoes(segments, max_repeticoes=2)
    
    contador = 0
    with open(output_path, 'w', encoding='utf-8') as f:
        for segment in segments_filtrados:
            text = segment['text'] if isinstance(segment, dict) else segment.text.strip()
            if text:
                contador += 1
                if isinstance(segment, dict):
                    start = format_timestamp(segment['start'])
                    end = format_timestamp(segment['end'])
                else:
                    start = format_timestamp(segment.start)
                    end = format_timestamp(segment.end)
                f.write(f"{contador}\n{start} --> {end}\n{text}\n\n")
    return contador

def format_timestamp(seconds):
    """Converte segundos para formato SRT HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def extrair_srt(video_path):
    """Extrai SRT de um vídeo com pré-processamento de áudio"""
    nome_video = Path(video_path).stem
    srt_saida = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
    
    # Pular se já existe
    if os.path.exists(srt_saida):
        print(f"  ✓ Já existe")
        return nome_video, True
    
    try:
        print(f"  1️⃣  Extraindo áudio...", end=" ", flush=True)
        audio_bruto = extrair_audio_bruto(video_path)
        if not audio_bruto:
            print("❌ FFmpeg falhou")
            return nome_video, False
        print("✓")
        
        print(f"  2️⃣  Limpando áudio (filtros)...", end=" ", flush=True)
        audio_limpo = limpar_audio_com_filtros(audio_bruto)
        if not audio_limpo:
            print("❌ Filtros falharam")
            if os.path.exists(audio_bruto):
                os.unlink(audio_bruto)
            return nome_video, False
        print("✓")
        
        print(f"  3️⃣  Transcrevendo...", end=" ", flush=True)
        segments = transcrever_audio(audio_limpo, model)
        if not segments:
            print("❌ Whisper falhou")
            if os.path.exists(audio_bruto):
                os.unlink(audio_bruto)
            if os.path.exists(audio_limpo):
                os.unlink(audio_limpo)
            return nome_video, False
        print("✓")
        
        print(f"  4️⃣  Salvando SRT...", end=" ", flush=True)
        contador = salvar_srt(segments, srt_saida)
        print(f"✓ ({contador} legendas)")
        
        # Limpeza
        if os.path.exists(audio_bruto):
            os.unlink(audio_bruto)
        if os.path.exists(audio_limpo):
            os.unlink(audio_limpo)
        
        return nome_video, True
        
    except Exception as e:
        print(f"❌ {str(e)[:60]}")
        return nome_video, False

def main():
    # Criar pasta de saída se não existir
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
    print(f"📊 Com PRÉ-PROCESSAMENTO de áudio:")
    print(f"   • Extrai canal central (5.1 surround)")
    print(f"   • Highpass filter: 80Hz (remove ruídos graves)")
    print(f"   • Lowpass filter: 3400Hz (remove chiados agudos)")
    print(f"   → Resultado: Áudio MONO otimizado para Whisper\n")
    
    # Processar sequencialmente
    resultados = {}
    # Processar sequencialmente COMPLETO por vídeo
    print(f"\n🚀 Iniciando Pipeline Sequencial (Extrair -> Limpar -> Traduzir -> Embutir)\n")
    
    total_videos = len(videos)
    sucessos_finais = 0
    
    for i, video in enumerate(videos, 1):
        nome_completo = Path(video).name
        nome_video = Path(video).stem
        print(f"[{i}/{total_videos}] 🎬 Processando: {nome_completo}")
        
        # 1. Extrair
        _, sucesso_extracao = extrair_srt(video)
        if not sucesso_extracao:
            print(f"  ⏭️ Pulando etapas seguintes (Extração falhou)\n")
            continue
            
        srt_en_path = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
        
        # 2. Limpar
        print(f"  🧹 Limpando alucinações...", end=" ", flush=True)
        limpar_srt_unico(srt_en_path)
        print("✓")
        
        # 3. Traduzir
        srt_pt_path = os.path.join(SUBTITLES_OUTPUT_DIR, f"{nome_video}_PT.srt")
        print(f"  🤖 Traduzindo (Gemini)...", end=" ", flush=True)
        sucesso_traducao = traduzir_srt_gemini(srt_en_path, srt_pt_path)
        if sucesso_traducao:
            print("✓")
        else:
            print("❌ Falha na tradução")
        
        # 4. Embutir (apenas se tradução existiu)
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
        
        # 5. Sleep (Cooldown)
        if i < total_videos:
            print(f"  💤 Aguardando 30s para o próximo vídeo...\n")
            time.sleep(30)
    
    print("\n" + "="*70)
    print(f"🏁 Pipeline Finalizado: {sucessos_finais}/{total_videos} vídeos completados com sucesso!")
    print("="*70 + "\n")

def limpar_srt_unico(srt_path):
    """Limpa alucinações de um único arquivo SRT (baseado na lógica antiga)"""
    import re
    
    if not os.path.exists(srt_path):
        return

    # Ler SRT
    segments = []
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        blocos = re.split(r'\n\n+', content.strip())
        for bloco in blocos:
            linhas = bloco.strip().split('\n')
            if len(linhas) >= 3:
                timestamp = linhas[1]
                texto = '\n'.join(linhas[2:])
                match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})', timestamp)
                if match:
                    segments.append({
                        'start': match.group(1),
                        'end': match.group(2),
                        'text': texto.strip(),
                        'text_norm': normalizar_texto(texto.strip())
                    })
    except Exception as e:
        print(f"Erro ao ler SRT para limpeza: {e}")
        return

    if not segments:
        return

    # Primeiro: remover alucinações internas
    segments_sem_internas = []
    for seg in segments:
        if not eh_alucinacao_interna(seg['text']):
            segments_sem_internas.append(seg)
    segments = segments_sem_internas

    if not segments: # Ficou vazio
        with open(srt_path, 'w', encoding='utf-8') as f: f.write("")
        return

    # Segundo: filtrar alucinações consecutivas
    filtrados = []
    i = 0
    while i < len(segments):
        texto_norm = segments[i]['text_norm']
        repeticoes = 1
        j = i + 1
        while j < len(segments):
            outro = segments[j]['text_norm']
            if texto_norm == outro or (len(texto_norm) > 3 and (texto_norm in outro or outro in texto_norm)):
                repeticoes += 1
                j += 1
            else:
                break
        
        if repeticoes > 2: # Max repetições
            filtrados.append(segments[i])
            i = j
        else:
            for k in range(i, j):
                filtrados.append(segments[k])
            i = j

    # Salvar SRT corrigido
    with open(srt_path, 'w', encoding='utf-8') as f:
        for idx, seg in enumerate(filtrados, 1):
            f.write(f"{idx}\n{seg['start']} --> {seg['end']}\n{seg['text']}\n\n")



if __name__ == "__main__":
    main()
