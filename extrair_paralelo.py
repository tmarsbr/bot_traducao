#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 EXTRAÇÃO PARALELA DE SRTs

Processa múltiplos vídeos simultaneamente usando multiprocessing.
Usa todos os núcleos do CPU para acelerar a extração.

ANTI-ALUCINAÇÃO:
- VAD (Voice Activity Detection): remove silêncios antes de transcrever
- condition_on_previous_text=False: quebra loops de repetição
- Thresholds rigorosos para evitar transcrever ruído

Uso:
    python extrair_paralelo.py          # Usa 4 processos (padrão)
    python extrair_paralelo.py --workers 8  # Usa 8 processos
"""

import os
import subprocess
import tempfile
import argparse
from pathlib import Path
from multiprocessing import Pool, cpu_count
from functools import partial

# Importar configurações
from config import SUBTITLES_EN_DIR, WHISPER_MODEL

# Configurações
PASTA_ENTRADA = "proximos_para_traducao"
PASTA_SAIDA = str(SUBTITLES_EN_DIR)
MODELO = WHISPER_MODEL
DEVICE = "cpu"
COMPUTE_TYPE = "int8"


def extrair_audio_bruto(video_path):
    """Extrai áudio bruto do vídeo"""
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
    """Aplica filtros de áudio para melhorar qualidade"""
    audio_limpo = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    audio_limpo.close()
    
    filtro = (
        "highpass=f=80,"
        "lowpass=f=3400,"
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
    
    if os.path.exists(audio_limpo.name) and os.path.getsize(audio_limpo.name) > 1000:
        return audio_limpo.name
    
    # Fallback
    if os.path.exists(audio_limpo.name):
        os.unlink(audio_limpo.name)
    
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
    
    subprocess.run(cmd_fallback, capture_output=True, text=True, timeout=300)
    
    if os.path.exists(audio_limpo_fb.name) and os.path.getsize(audio_limpo_fb.name) > 1000:
        return audio_limpo_fb.name
    else:
        if os.path.exists(audio_limpo_fb.name):
            os.unlink(audio_limpo_fb.name)
        return None


def format_timestamp(seconds):
    """Converte segundos para formato SRT"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def processar_video(video_path):
    """
    Processa um único vídeo (função executada em cada worker).
    Cada worker carrega seu próprio modelo Whisper.
    """
    from faster_whisper import WhisperModel
    import re
    from collections import Counter
    
    nome_video = Path(video_path).stem
    nome_curto = nome_video[:50]
    srt_saida = os.path.join(PASTA_SAIDA, f"{nome_video}_EN.srt")
    
    # Pular se já existe
    if os.path.exists(srt_saida):
        return (nome_video, "skip", "Já existe")
    
    try:
        # 1. Extrair áudio
        audio_bruto = extrair_audio_bruto(video_path)
        if not audio_bruto:
            return (nome_video, "error", "FFmpeg falhou")
        
        # 2. Limpar áudio
        audio_limpo = limpar_audio_com_filtros(audio_bruto)
        if not audio_limpo:
            if os.path.exists(audio_bruto):
                os.unlink(audio_bruto)
            return (nome_video, "error", "Filtros falharam")
        
        # 3. Carregar modelo (cada worker carrega o seu)
        model = WhisperModel(MODELO, device=DEVICE, compute_type=COMPUTE_TYPE)
        
        # 4. Transcrever com anti-alucinação
        vad_parameters = {
            "threshold": 0.5,
            "min_speech_duration_ms": 250,
            "min_silence_duration_ms": 500
        }
        
        segments, info = model.transcribe(
            audio_limpo,
            language="en",
            beam_size=5,
            without_timestamps=False,
            condition_on_previous_text=False,
            vad_filter=True,
            vad_parameters=vad_parameters,
            no_speech_threshold=0.6,
            log_prob_threshold=-1.0,
            compression_ratio_threshold=2.4
        )
        
        segments = list(segments)
        
        # Funções de filtro
        def normalizar_texto(texto):
            texto_norm = re.sub(r'[^\w\s]', '', texto.lower())
            return re.sub(r'\s+', ' ', texto_norm).strip()
        
        def eh_alucinacao_interna(texto):
            texto_limpo = re.sub(r'[^\w\s]', ' ', texto.lower())
            palavras = texto_limpo.split()
            if len(palavras) < 5:
                return False
            contagem = Counter(palavras)
            palavra_mais_comum, qtd = contagem.most_common(1)[0]
            palavras_ok = {'i', 'you', 'the', 'a', 'and', 'to', 'it', 'is', 'of', 'in', 'that', 'me', 'my', 'your'}
            threshold = 0.7 if palavra_mais_comum in palavras_ok else 0.5
            if qtd / len(palavras) >= threshold:
                return True
            if len(palavras) >= 10 and len(set(palavras)) <= 3:
                return True
            return False
        
        # 5. Primeiro filtro: alucinações internas
        segs_limpos = []
        for segment in segments:
            text = segment.text.strip()
            if text and not eh_alucinacao_interna(text):
                segs_limpos.append({
                    'start': segment.start,
                    'end': segment.end,
                    'text': text,
                    'text_norm': normalizar_texto(text)
                })
        
        # 6. Segundo filtro: repetições consecutivas (max 2)
        filtrados = []
        i = 0
        while i < len(segs_limpos):
            texto_norm = segs_limpos[i]['text_norm']
            repeticoes = 1
            j = i + 1
            while j < len(segs_limpos):
                outro = segs_limpos[j]['text_norm']
                if texto_norm == outro or (len(texto_norm) > 3 and (texto_norm in outro or outro in texto_norm)):
                    repeticoes += 1
                    j += 1
                else:
                    break
            
            if repeticoes > 2:
                # Manter só 1
                filtrados.append(segs_limpos[i])
                i = j
            else:
                for k in range(i, j):
                    filtrados.append(segs_limpos[k])
                i = j
        
        # 7. Salvar SRT
        contador = 0
        with open(srt_saida, 'w', encoding='utf-8') as f:
            for seg in filtrados:
                contador += 1
                start = format_timestamp(seg['start'])
                end = format_timestamp(seg['end'])
                f.write(f"{contador}\n{start} --> {end}\n{seg['text']}\n\n")
        
        # Limpeza
        if os.path.exists(audio_bruto):
            os.unlink(audio_bruto)
        if os.path.exists(audio_limpo):
            os.unlink(audio_limpo)
        
        return (nome_video, "success", f"{contador} legendas")
        
    except Exception as e:
        return (nome_video, "error", str(e)[:50])


def main():
    parser = argparse.ArgumentParser(description='Extração paralela de SRTs')
    parser.add_argument('--workers', type=int, default=4, 
                        help=f'Número de workers paralelos (default: 4, max recomendado: {cpu_count()})')
    args = parser.parse_args()
    
    # Criar pasta de saída
    os.makedirs(PASTA_SAIDA, exist_ok=True)
    
    # Listar vídeos
    todos_videos = sorted([
        os.path.join(PASTA_ENTRADA, f)
        for f in os.listdir(PASTA_ENTRADA)
        if f.lower().endswith('.mp4')
    ])
    
    # Filtrar já existentes
    videos = []
    ja_existentes = 0
    for video in todos_videos:
        nome = Path(video).stem
        if os.path.exists(os.path.join(PASTA_SAIDA, f"{nome}_EN.srt")):
            ja_existentes += 1
        else:
            videos.append(video)
    
    print(f"""
╔══════════════════════════════════════════════════════════════════════╗
║              🚀 EXTRAÇÃO PARALELA DE SRTs                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  Workers: {args.workers} processos paralelos                                    ║
║  CPU: {cpu_count()} núcleos disponíveis                                         ║
║  Vídeos: {len(todos_videos)} total, {len(videos)} para processar, {ja_existentes} já prontos              ║
╚══════════════════════════════════════════════════════════════════════╝
""")
    
    if not videos:
        print("✨ Todos os vídeos já têm SRT!")
        return
    
    print(f"📊 Configurações anti-alucinação:")
    print(f"   • VAD (Voice Activity Detection) ativado")
    print(f"   • condition_on_previous_text = False")
    print(f"   • Thresholds rigorosos\n")
    print(f"🚀 Iniciando processamento paralelo...\n")
    
    # Processar em paralelo
    with Pool(args.workers) as pool:
        resultados = pool.map(processar_video, videos)
    
    # Resumo
    sucesso = sum(1 for r in resultados if r[1] == "success")
    erros = sum(1 for r in resultados if r[1] == "error")
    
    print(f"\n{'='*70}")
    print(f"✅ Concluído: {sucesso}/{len(videos)} vídeos processados")
    if erros > 0:
        print(f"⚠️  {erros} vídeo(s) falharam:")
        for nome, status, msg in resultados:
            if status == "error":
                print(f"   • {nome[:40]}... → {msg}")
    print("="*70)
    
    # Limpeza final de todos os SRTs (igual ao script sequencial)
    print("\n" + "="*70)
    print("🔍 VERIFICAÇÃO FINAL: Limpando alucinações de todos os SRTs...")
    print("="*70 + "\n")
    
    import subprocess
    import sys
    subprocess.run([sys.executable, "limpar_alucinacoes_srt.py"], cwd=os.path.dirname(os.path.abspath(__file__)))


if __name__ == "__main__":
    main()
