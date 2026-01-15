"""
Embutir legendas em vídeos usando FFmpeg
"""

import subprocess
from pathlib import Path

def embutir_legendas(video_entrada, srt_traduzido, video_saida):
    """
    Embutir SRT traduzido no vídeo usando FFmpeg
    
    Args:
        video_entrada: caminho do vídeo original (mp4, avi, mkv, etc)
        srt_traduzido: caminho do SRT traduzido em português
        video_saida: caminho do vídeo final com legendas
    """
    
    print(f"\n📹 Embutindo legendas no vídeo...")
    print(f"🎬 Vídeo: {video_entrada}")
    print(f"📝 Legendas: {srt_traduzido}")
    print(f"💾 Saída: {video_saida}")
    
    # Comando FFmpeg para embutir legendas
    # Opção 1: Soft subtitle (pode ativar/desativar)
    cmd = [
        'ffmpeg',
        '-i', video_entrada,
        '-i', srt_traduzido,
        '-c:v', 'copy',  # Copia vídeo sem re-codificar (rápido)
        '-c:a', 'copy',  # Copia áudio sem re-codificar
        '-c:s', 'mov_text',  # Codec para legendas
        '-metadata:s:s:0', 'language=por',  # Marca como português
        video_saida
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ Sucesso! Legendas embutidas em: {video_saida}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao embutir legendas: {e}")
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
