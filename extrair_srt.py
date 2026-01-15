"""
Extrair legendas de vídeos usando FFmpeg
"""

import subprocess
import os
from pathlib import Path

def extrair_srt_do_video(video_entrada, srt_saida):
    """
    Extrai SRT de um vídeo
    
    Args:
        video_entrada: caminho do vídeo (mp4, mkv, avi, etc)
        srt_saida: onde salvar o SRT
    """
    
    print(f"\n📹 Extraindo legendas do vídeo...")
    print(f"🎬 Vídeo: {video_entrada}")
    print(f"💾 Saída: {srt_saida}")
    
    # Verifica se vídeo existe
    if not os.path.exists(video_entrada):
        print(f"❌ Vídeo não encontrado: {video_entrada}")
        return False
    
    # Comando FFmpeg para extrair SRT
    cmd = [
        'ffmpeg',
        '-i', video_entrada,
        '-map', '0:s:0',  # Pega primeira stream de legenda
        srt_saida
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Verifica se foi criado
        if os.path.exists(srt_saida):
            tamanho = os.path.getsize(srt_saida)
            print(f"\n✅ Sucesso! SRT extraído: {srt_saida}")
            print(f"📊 Tamanho: {tamanho} bytes")
            return True
        else:
            print(f"\n⚠️ Nenhuma legenda encontrada no vídeo")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Erro ao extrair legendas: {e}")
        return False
    except FileNotFoundError:
        print("\n❌ FFmpeg não encontrado!")
        print("📥 Instale FFmpeg: https://ffmpeg.org/download.html")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        video_in = sys.argv[1]
        srt_out = sys.argv[2]
    else:
        # Padrão
        video_in = "videos_input/Nickey_h.mp4"
        srt_out = "videos_output/Nickey_h.srt"
    
    print(f"\n{'='*70}")
    print("🎬 EXTRAIR LEGENDAS DE VÍDEO")
    print(f"{'='*70}")
    
    if extrair_srt_do_video(video_in, srt_out):
        print(f"\n📝 Próximo passo: Traduzir o SRT em português")
        print(f"💾 Depois embutir no vídeo com: python embutir_legendas.py")
