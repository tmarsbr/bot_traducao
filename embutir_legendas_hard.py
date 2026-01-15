"""
Embutir legendas RENDERIZADAS no vídeo (hard subtitles)
As legendas ficam visíveis sempre, sem opção de desativar
"""

import subprocess
from pathlib import Path

def embutir_legendas_hard(video_entrada, srt_traduzido, video_saida):
    """
    Embutir SRT como hard subtitles (renderizado no vídeo)
    Isso garante que as legendas apareçam em qualquer player
    """
    
    print(f"\n📹 Embutindo legendas RENDERIZADAS no vídeo...")
    print(f"🎬 Vídeo: {video_entrada}")
    print(f"📝 Legendas: {srt_traduzido}")
    print(f"💾 Saída: {video_saida}")
    
    # Comando FFmpeg com subtitles filter (renderiza legendas)
    cmd = [
        'ffmpeg',
        '-i', video_entrada,
        '-vf', f"subtitles={srt_traduzido}",  # Renderiza legendas no vídeo
        '-c:a', 'copy',  # Copia áudio sem re-codificar
        '-y',  # Sobrescreve arquivo existente
        video_saida
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print(f"\n✅ Sucesso! Legendas renderizadas em: {video_saida}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao embutir legendas: {e}")
        return False
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 4:
        video_in = sys.argv[1]
        srt_in = sys.argv[2]
        video_out = sys.argv[3]
    else:
        video_in = "videos_input/Nickey_h.mp4"
        srt_in = "videos_output/Nickey_h_pt.srt"
        video_out = "videos_output/Nickey_h_legendado_hard.mp4"
    
    print(f"\n{'='*70}")
    print("🎬 EMBUTIR LEGENDAS (RENDERIZADAS)")
    print(f"{'='*70}")
    
    embutir_legendas_hard(video_in, srt_in, video_out)
