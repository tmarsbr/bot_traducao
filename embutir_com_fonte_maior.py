#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Embute legendas PT nos vídeos com FONTE MAIOR (81% maior que o padrão)
- FontSize original: 32
- FontSize novo: 58 (32 * 1.81 = 58)
- Aumento total: +81%
"""

import subprocess
import re
import os
from pathlib import Path

def srt_para_ass_fonte_maior(srt_path, ass_path, font_size=58):
    """
    Converte SRT para ASS com fonte MAIOR e estilo profissional.
    
    Args:
        srt_path: Caminho do arquivo SRT
        ass_path: Caminho de saída do arquivo ASS
        font_size: Tamanho da fonte (padrão: 51 para +60%)
    """
    # Header ASS com fonte GRANDE
    header = f"""[Script Info]
Title: Legendas Traduzidas (Fonte Grande)
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,3,3,0,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        blocos = re.split(r'\n\n+', srt_content.strip())
        eventos = []
        
        for bloco in blocos:
            linhas = bloco.strip().split('\n')
            if len(linhas) >= 3:
                timestamp_match = re.match(
                    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                    linhas[1]
                )
                if timestamp_match:
                    h1, m1, s1, ms1, h2, m2, s2, ms2 = timestamp_match.groups()
                    start = f"{int(h1)}:{m1}:{s1}.{ms1[:2]}"
                    end = f"{int(h2)}:{m2}:{s2}.{ms2[:2]}"
                    texto = '\\N'.join(linhas[2:])
                    eventos.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{texto}")
        
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write('\n'.join(eventos))
        
        return True
        
    except Exception as e:
        print(f"⚠️ Erro ao converter SRT para ASS: {e}")
        return False


def embutir_legendas_fonte_maior(video_entrada, srt_traduzido, video_saida, font_size=58):
    """
    Embutir SRT traduzido no vídeo com FONTE GRANDE.
    
    Args:
        video_entrada: vídeo original
        srt_traduzido: SRT em português
        video_saida: vídeo final com legendas
        font_size: tamanho da fonte (51 = +60%)
    """
    print(f"\n📹 Embutindo legendas GRANDES no vídeo...")
    print(f"🎬 Vídeo: {video_entrada}")
    print(f"📝 Legendas: {srt_traduzido}")
    print(f"🔤 Tamanho da fonte: {font_size} (+81%)")
    print(f"💾 Saída: {video_saida}")
    
    srt_path = Path(srt_traduzido)
    ass_path = srt_path.with_suffix('.ass')
    
    if not srt_para_ass_fonte_maior(str(srt_path), str(ass_path), font_size):
        print(f"❌ Falha ao converter para ASS")
        return False
    
    print(f"✨ Convertido para ASS com fonte {font_size}")
    
    # Copiar legenda para pasta do vídeo
    video_dir = Path(video_entrada).parent
    temp_legenda = video_dir / f"_temp_legenda_grande.ass"
    
    try:
        import shutil
        shutil.copy2(str(ass_path), str(temp_legenda))
        
        # Comando FFmpeg
        filtro = f"ass={temp_legenda.name}"
        
        cmd = [
            'ffmpeg',
            '-i', str(Path(video_entrada).absolute()),
            '-vf', filtro,
            '-c:a', 'copy',
            '-y',
            str(Path(video_saida).absolute())
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(video_dir))
        
        # Limpar temporários
        if temp_legenda.exists():
            temp_legenda.unlink()
        if ass_path.exists():
            ass_path.unlink()
        
        if result.returncode == 0:
            print(f"\n✅ Sucesso! Legendas embutidas com fonte GRANDE em: {video_saida}")
            return True
        else:
            print(f"\n❌ Erro ao embutir legendas: {result.stderr[:200]}")
            return False
            
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    # Lista de vídeos para processar
    videos_para_processar = [
        {
            'video': 'proximos_para_traducao/Almost Identical Twin Stepdaughters Joey White Sami White Dad Crush.mp4',
            'srt': 'videos_output/subtitles_pt/Almost Identical Twin Stepdaughters Joey White Sami White Dad Crush_PT.srt',
            'saida': 'videos_output/videos_translated/Almost Identical Twin Stepdaughters Joey White Sami White Dad Crush_PT_LEGENDA_GRANDE.mp4'
        },
        {
            'video': 'proximos_para_traducao/Beyond Brother And Sister Daisy Stone Sis Loves Me.mp4',
            'srt': 'videos_output/subtitles_pt/Beyond Brother And Sister Daisy Stone Sis Loves Me_PT.srt',
            'saida': 'videos_output/videos_translated/Beyond Brother And Sister Daisy Stone Sis Loves Me_PT_LEGENDA_GRANDE.mp4'
        }
    ]
    
    print("="*70)
    print("🎬 EMBUTIR LEGENDAS COM FONTE GRANDE (+81%)")
    print("="*70)
    print(f"📏 FontSize: 58 (era 32, aumentou 81%)")
    print(f"📋 Vídeos para processar: {len(videos_para_processar)}\n")
    
    sucessos = 0
    
    for i, item in enumerate(videos_para_processar, 1):
        print(f"\n[{i}/{len(videos_para_processar)}] Processando...")
        
        if not os.path.exists(item['video']):
            print(f"❌ Vídeo não encontrado: {item['video']}")
            continue
        
        if not os.path.exists(item['srt']):
            print(f"❌ SRT não encontrado: {item['srt']}")
            continue
        
        sucesso = embutir_legendas_fonte_maior(
            item['video'], 
            item['srt'], 
            item['saida'],
            font_size=58  # +81% (tamanho perfeito)
        )
        
        if sucesso:
            sucessos += 1
    
    print("\n" + "="*70)
    print(f"✅ Concluído! {sucessos}/{len(videos_para_processar)} vídeos processados")
    print("="*70)
