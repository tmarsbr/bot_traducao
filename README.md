# Bot de Tradução e Dublagem de Vídeos (Whisper + Gemini)

Este projeto automatiza o processo de extração de legendas, tradução e embutimento ("queima") de legendas em vídeos, utilizando IA de ponta.

## 🚀 Funcionalidades

1.  **Transcrição de Áudio (Speech-to-Text)**:
    *   Usa **Faster-Whisper** com modelo `large-v3` para máxima precisão.
    *   Filtros de áudio FFmpeg (Noise Reduction, Isolamento de Voz, Normalização).
    *   **Anti-Alucinação**: Filtros customizados para remover repetições e loops comuns do Whisper.

2.  **Tradução Inteligente (LLM)**:
    *   Usa **Google Gemini** para traduzir do Inglês para Português (PT-BR).
    *   Preserva timestamps e adapta gírias/expressões para contexto natural.

3.  **Processamento de Vídeo**:
    *   Embuti legendas (hardsub) automaticamente.
    *   Pipeline 100% automatizado: `Extrair -> Limpar -> Traduzir -> Embutir`.

## 🛠️ Instalação

1.  **Pré-requisitos**:
    *   Python 3.8+
    *   [FFmpeg](https://ffmpeg.org/download.html) instalado e no PATH do sistema.

2.  **Instalar dependências**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configuração (.env)**:
    Crie um arquivo `.env` na raiz com sua chave API do Gemini:
    ```env
    GEMINI_API_KEY=sua_chave_aqui_AIzaSy...
    WHISPER_MODEL=large-v3
    ```

## ▶️ Como Usar

### Modo Automático (Pipeline Completo)
Para processar **todos** os vídeos da pasta `proximos_para_traducao`:

```bash
python extrair_proximos_srt_v2.py
```

O script vai:
1. Pegar um vídeo.
2. Extrair e limpar a legenda (Whisper).
3. Traduzir (Gemini).
4. Embutir a legenda PT-BR (FFmpeg).
5. Aguardar 30s (resfriamento).
6. Repetir para o próximo vídeo.

### Modo Manual (Vídeo Único)
Para traduzir um vídeo específico:

```bash
python main.py "Nome do Video.mp4" pt
```

## 📁 Estrutura de Pastas

*   `proximos_para_traducao/`: Jogue seus vídeos aqui.
*   `videos_output/`:
    *   `subtitles_en/`: Legendas originais extraídas.
    *   `subtitles_pt/`: Legendas traduzidas pelo Gemini.
    *   `videos_translated/`: Vídeos finais com legenda embutida.
*   `models/`: Onde o modelo Whisper (3GB) é baixado localmente.

## 📝 Scripts Principais

*   `extrair_proximos_srt_v2.py`: Pipeline principal (Sequencial).
*   `traduzir_com_gemini.py`: Módulo de tradução.
*   `embutir_legendas_pt.py`: Módulo de queima de legendas.
*   `config.py`: Configurações centrais.

## ⚠️ Notas
*   O modelo `large-v3` requer cerca de 2GB-4GB de RAM e processamento razoável. No CPU pode levar ~10-20min para vídeo de 40min.
*   A primeira execução irá baixar o modelo (~3GB).
