"""
Extrair SRT do vídeo Nickey_h.mp4
"""

import subprocess
import os
from pathlib import Path

def extract_srt_ffmpeg(video_path, output_srt):
    """Tenta extrair SRT embutido no vídeo"""
    print(f"\n🎬 Tentando extrair legendas do vídeo...")
    print(f"📁 Vídeo: {video_path}")
    print(f"💾 Saída: {output_srt}")
    
    if not os.path.exists(video_path):
        print(f"❌ Vídeo não encontrado: {video_path}")
        return False
    
    try:
        # Extrai primeira stream de legenda
        cmd = [
            'ffmpeg', '-i', video_path,
            '-map', '0:s:0', '-c', 'copy',
            output_srt, '-y'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if os.path.exists(output_srt) and os.path.getsize(output_srt) > 0:
            print(f"\n✅ SRT extraído com sucesso!")
            return True
        else:
            print(f"⚠️ Nenhuma legenda encontrada no vídeo")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ Timeout ao extrair")
        return False
    except FileNotFoundError:
        print("⚠️ FFmpeg não instalado")
        return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False


def transcribe_with_whisper(video_path, output_srt, language='en'):
    """Transcreve usando Whisper se não tiver legendas embutidas"""
    print(f"\n🎙️  Transcrevendo vídeo com Whisper...")
    
    try:
        from faster_whisper import WhisperModel
        from utils import format_timestamp
        
        print("📥 Carregando modelo Whisper (primeira vez = lento)...")
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        
        print("🔄 Transcrevendo...")
        segments, info = model.transcribe(video_path, language=language, beam_size=5)
        
        print(f"✅ Transcrição concluída")
        print(f"   Idioma: {info.language}")
        print(f"   Duração: {info.duration:.1f}s")
        
        # Salvar como SRT
        with open(output_srt, "w", encoding="utf-8") as f:
            for i, segment in enumerate(segments, start=1):
                start = format_timestamp(segment.start)
                end = format_timestamp(segment.end)
                text = segment.text.strip()
                
                f.write(f"{i}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        
        print(f"✅ SRT salvo em: {output_srt}")
        return True
        
    except ImportError:
        print("❌ Faster-Whisper não instalado")
        print("   Instale com: pip install faster-whisper")
        return False
    except Exception as e:
        print(f"❌ Erro na transcrição: {e}")
        return False


if __name__ == "__main__":
    video = "videos_input/Nickey_h.mp4"
    output = "videos_output/Nickey_h_EN.srt"
    
    print(f"\n{'='*70}")
    print("📹 EXTRAIR SRT DO VÍDEO")
    print(f"{'='*70}")
    
    # Tenta extrair com FFmpeg primeiro
    if extract_srt_ffmpeg(video, output):
        print("\n✅ Pronto! SRT disponível para traduzir")
    else:
        print("\n🔄 Sem legendas embutidas, tentando transcrever...")
        if transcribe_with_whisper(video, output, language='en'):
            print("\n✅ Pronto! SRT disponível para traduzir")
        else:
            print("\n❌ Não foi possível extrair SRT")
