"""
Embutir legendas em vídeos usando FFmpeg
MELHORIA: Suporte a ASS com fundo opaco para melhor legibilidade
"""

import subprocess
import re
from pathlib import Path


def srt_para_ass(srt_path, ass_path):
    """
    Converte SRT para ASS com estilo profissional (fundo opaco como streaming).
    
    Args:
        srt_path: Caminho do arquivo SRT
        ass_path: Caminho de saída do arquivo ASS
    
    Returns:
        True se sucesso, False caso contrário
    """
    # Header ASS com estilo profissional
    # BackColour=&H80000000 = preto com 50% transparência
    # BorderStyle=3 = caixa opaca ao redor do texto
    # FontSize=22 adequado para 1080p
    header = """[Script Info]
Title: Legendas Traduzidas
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,32,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,3,2,0,2,10,10,30,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        # Parsear blocos SRT
        blocos = re.split(r'\n\n+', srt_content.strip())
        eventos = []
        
        for bloco in blocos:
            linhas = bloco.strip().split('\n')
            if len(linhas) >= 3:
                # Linha 2: timestamp
                timestamp_match = re.match(
                    r'(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})',
                    linhas[1]
                )
                if timestamp_match:
                    h1, m1, s1, ms1, h2, m2, s2, ms2 = timestamp_match.groups()
                    # Formato ASS: H:MM:SS.cc (centésimos)
                    start = f"{int(h1)}:{m1}:{s1}.{ms1[:2]}"
                    end = f"{int(h2)}:{m2}:{s2}.{ms2[:2]}"
                    
                    # Texto (linhas 3+)
                    texto = '\\N'.join(linhas[2:])  # \\N = quebra de linha no ASS
                    
                    eventos.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{texto}")
        
        # Escrever arquivo ASS
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(header)
            f.write('\n'.join(eventos))
        
        return True
        
    except Exception as e:
        print(f"⚠️ Erro ao converter SRT para ASS: {e}")
        return False


def embutir_legendas(video_entrada, srt_traduzido, video_saida):
    """
    Embutir SRT traduzido no vídeo usando FFmpeg.
    MELHORIA: Converte para ASS para melhor estilo visual.
    
    Args:
        video_entrada: caminho do vídeo original (mp4, avi, mkv, etc)
        srt_traduzido: caminho do SRT traduzido em português
        video_saida: caminho do vídeo final com legendas
    """
    
    print(f"\n📹 Embutindo legendas no vídeo...")
    print(f"🎬 Vídeo: {video_entrada}")
    print(f"📝 Legendas: {srt_traduzido}")
    print(f"💾 Saída: {video_saida}")
    
    # MELHORIA: Tentar converter para ASS primeiro
    srt_path = Path(srt_traduzido)
    ass_path = srt_path.with_suffix('.ass')
    usa_ass = False
    
    if srt_para_ass(str(srt_path), str(ass_path)):
        print(f"✨ Convertido para ASS com estilo profissional")
        legenda_a_usar = str(ass_path)
        usa_ass = True
    else:
        print(f"⚠️ Usando SRT original (falha na conversão ASS)")
        legenda_a_usar = srt_traduzido
    
    # Copiar legenda para pasta do vídeo (evita problemas de caminho Windows)
    video_dir = Path(video_entrada).parent
    temp_legenda = video_dir / f"_temp_legenda{'_ass' if usa_ass else ''}{'.ass' if usa_ass else '.srt'}"
    
    try:
        import shutil
        shutil.copy2(legenda_a_usar, temp_legenda)
        
        # Comando FFmpeg - hardcode subtitles no vídeo
        # Para ASS: usar filtro ass=
        # Para SRT: usar filtro subtitles=
        if usa_ass:
            filtro = f"ass={temp_legenda.name}"
        else:
            filtro = f"subtitles={temp_legenda.name}:force_style='FontSize=32,Outline=0,BackColour=&H80000000,BorderStyle=4,MarginV=25'"
        
        cmd = [
            'ffmpeg',
            '-i', str(Path(video_entrada).absolute()),
            '-vf', filtro,
            '-c:a', 'copy',
            '-y',
            str(Path(video_saida).absolute())
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(video_dir))
        
        # Limpar arquivos temporários
        if temp_legenda.exists():
            temp_legenda.unlink()
        if usa_ass and ass_path.exists():
            ass_path.unlink()
        
        if result.returncode == 0:
            print(f"\n✅ Sucesso! Legendas embutidas em: {video_saida}")
            return True
        else:
            print(f"\n❌ Erro ao embutir legendas: {result.stderr[:200]}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao embutir legendas: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        return False


def listar_videos_entrada():
    """Lista vídeos na pasta de entrada"""
    pasta = Path("videos_input")
    extensoes = ['*.mp4', '*.avi', '*.mkv', '*.mov', '*.webm']
    
    videos = []
    for ext in extensoes:
        videos.extend(pasta.glob(ext))
    
    return videos


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 4:
        video_in = sys.argv[1]
        srt_in = sys.argv[2]
        video_out = sys.argv[3]
    else:
        # Exemplo: procura vídeos na pasta
        videos = listar_videos_entrada()
        
        if not videos:
            print("\n❌ Nenhum vídeo encontrado em 'videos_input/'")
            print("📂 Coloque seus vídeos (mp4, avi, mkv, etc) em: videos_input/")
            sys.exit(1)
        
        print("\n📹 Vídeos encontrados:")
        for idx, video in enumerate(videos, 1):
            print(f"  {idx}. {video.name}")
        
        video_in = str(videos[0])
        srt_in = "videos_output/elsa_traduzido.srt"  # SRT que você vai traduzir
        video_out = f"videos_output/{Path(video_in).stem}_legendado.mp4"
    
    print(f"\n{'='*70}")
    print("🎬 EMBUTIR LEGENDAS EM VÍDEO")
    print(f"{'='*70}")
    
    embutir_legendas(video_in, srt_in, video_out)
