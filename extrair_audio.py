"""
Extrair e converter vídeo para SRT usando ferramentas Python
"""

import os
from pathlib import Path

def extrair_audio_e_transcrever(video_path, srt_output):
    """
    Extrai áudio do vídeo e transcreve para SRT
    """
    
    print(f"\n📹 Processando vídeo...")
    print(f"🎬 Vídeo: {video_path}")
    
    # Verifica se arquivo existe
    if not os.path.exists(video_path):
        print(f"❌ Vídeo não encontrado: {video_path}")
        return False
    
    try:
        # Tenta com moviepy
        print("🔧 Usando moviepy para extrair informações...")
        from moviepy.editor import VideoFileClip
        
        video = VideoFileClip(video_path)
        
        print(f"\n📊 Informações do vídeo:")
        print(f"  ⏱️  Duração: {video.duration:.0f}s ({video.duration/60:.1f} min)")
        print(f"  🎬 Resolução: {video.size}")
        print(f"  ⏪ FPS: {video.fps}")
        
        # Extrai áudio
        audio_path = "temp_audio.wav"
        if video.audio is not None:
            print(f"\n🔊 Extraindo áudio...")
            video.audio.write_audiofile(audio_path, verbose=False, logger=None)
            print(f"✅ Áudio extraído: {audio_path}")
        else:
            print("⚠️ Nenhum áudio encontrado no vídeo")
            video.close()
            return False
        
        video.close()
        
        print(f"\n✅ Vídeo processado!")
        print(f"💾 Áudio salvo em: {audio_path}")
        print(f"\n📝 Próximo passo: Transcrever áudio para SRT")
        print(f"   Use um serviço como:")
        print(f"   - Google Speech-to-Text")
        print(f"   - OpenAI Whisper")
        print(f"   - AssemblyAI")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 2:
        video_in = sys.argv[1]
        srt_out = sys.argv[2] if len(sys.argv) > 2 else "videos_output/extracted.srt"
    else:
        video_in = "videos_input/Nickey_h.mp4"
        srt_out = "videos_output/Nickey_h.srt"
    
    print(f"\n{'='*70}")
    print("🎬 EXTRAIR ÁUDIO DE VÍDEO")
    print(f"{'='*70}")
    
    extrair_audio_e_transcrever(video_in, srt_out)
