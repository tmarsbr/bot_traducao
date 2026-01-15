import sys
from pathlib import Path
from video_translator import VideoTranslationAgent
from config import VIDEOS_INPUT_DIR

def process_single_video(video_name: str, target_lang: str = 'pt'):
    """
    Função simplificada para processar um vídeo pelo nome.
    Procura o vídeo na pasta videos_input se não for um caminho absoluto.
    """
    print(f"🔄 Iniciando processamento para: {video_name}")
    
    # Resolver o caminho do vídeo
    video_path = Path(video_name)
    if not video_path.exists():
        # Tentar encontrar na pasta de inputs padrão
        possible_path = VIDEOS_INPUT_DIR / video_name
        
        # Tentar encontrar na pasta de tradução atual
        possible_path_2 = Path("proximos_para_traducao") / video_name
        
        if possible_path.exists():
            video_path = possible_path
        elif possible_path_2.exists():
            video_path = possible_path_2
        else:
            print(f"❌ Erro: Vídeo não encontrado: {video_name}")
            print(f"   Procurei em: {video_path.absolute()}")
            print(f"   E em: {possible_path.absolute()}")
            print(f"   E em: {possible_path_2.absolute()}")
            return

    agent = VideoTranslationAgent()
    
    # Executar pipeline completo
    result = agent.translate_video(
        video_path=str(video_path),
        target_language=target_lang,
        embed_subs=True,      # Padrão: fundir legenda
        use_gemini=True,      # Padrão: usar Gemini
        auto_transcribe=True  # Padrão: se não tiver legenda, transcrever
    )

    if result:
        print(f"\n✅ Sucesso! Arquivo gerado: {result}")
    else:
        print("\n❌ Falha no processamento. Verifique os logs para mais detalhes.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python main.py <nome_do_video.mp4> [idioma_alvo]")
        print("Exemplo: python main.py aula_01.mp4 pt")
    else:
        video_name = sys.argv[1]
        lang = sys.argv[2] if len(sys.argv) > 2 else 'pt'
        process_single_video(video_name, lang)
