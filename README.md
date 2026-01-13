# Agente de Tradução de Vídeos com Gemini e Google Cloud Translation

Um agente Python profissional para traduzir vídeos, extrair legendas, transcrever áudio e gerar arquivos SRT traduzidos usando Gemini e Google Cloud Translation.

## 🎯 Funcionalidades

✅ **Extração de Conteúdo**
- Extrai legendas existentes em formato SRT de vídeos
- Extrai áudio de vídeos para transcrição
- Suporta múltiplos formatos: MP4, AVI, MOV, MKV, WebM, FLV

✅ **Tradução Inteligente**
- Traduz legendas SRT mantendo timestamps
- Usa Gemini para transcrição e tradução de áudio
- Fallback para Google Cloud Translation API
- Suporta 10+ idiomas

✅ **Embutimento de Legendas**
- Embutir legendas traduzidas diretamente no vídeo
- Mantém qualidade do vídeo original

✅ **Processamento em Lote**
- Processa múltiplos vídeos em um diretório
- Loop automático com relatórios individuais

✅ **Logging e Relatórios**
- Logs detalhados por vídeo
- Relatórios JSON com métricas
- Rastreamento de erros e taxa de sucesso

✅ **Tratamento de Quotas**
- Retry automático com backoff exponencial
- Validação de limites de API
- Controle de tamanho de vídeo e duração

## 📋 Pré-requisitos

### Sistema Operacional
- Windows, macOS ou Linux
- Python 3.8+

### Dependências Externas
1. **FFmpeg** (essencial)
   - Windows: Baixe de https://ffmpeg.org/download.html
   - macOS: `brew install ffmpeg`
   - Linux: `sudo apt-get install ffmpeg`

### Credenciais
- Chave da API Gemini (obtém em https://makersuite.google.com/app/apikeys)
- (Opcional) Projeto Google Cloud com habilitação da Translation API

## 🚀 Instalação

### 1. Clone ou baixe o projeto
```bash
cd seu_projeto
```

### 2. Crie um ambiente virtual
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instale as dependências
```bash
pip install -r requirements.txt
```

### 4. Configure as credenciais
```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite .env com suas credenciais
# GEMINI_API_KEY=sua_chave_aqui
# GOOGLE_CLOUD_PROJECT=seu_projeto
```

### 5. Verifique FFmpeg
```bash
ffmpeg -version
ffprobe -version
```

## 📖 Uso

### Traduzir um único vídeo

```bash
python video_translator.py \
    --input_video videos/meu_video.mp4 \
    --target_language en \
    --embed_subs
```

### Traduzir e gerar apenas SRT

```bash
python video_translator.py \
    --input_video videos/meu_video.mp4 \
    --target_language es
```

### Processar múltiplos vídeos em um diretório

```bash
python video_translator.py \
    --input_dir videos/ \
    --target_language pt \
    --embed_subs
```

### Usar Google Cloud Translation em vez de Gemini

```bash
python video_translator.py \
    --input_video videos/meu_video.mp4 \
    --target_language fr \
    --use_gemini False
```

## 📚 Argumentos de Linha de Comando

| Argumento | Tipo | Descrição | Obrigatório |
|-----------|------|-----------|------------|
| `--input_video` | string | Caminho do vídeo | Sim (sem `--input_dir`) |
| `--target_language` | string | Código do idioma: pt, en, es, fr, de, it, ja, ko, zh, ru | Sim |
| `--output_subtitle` | string | Caminho custom para SRT de saída | Não |
| `--embed_subs` | flag | Embutir legendas no vídeo final | Não |
| `--auto_transcribe` | flag | Tentar transcrição automática para vídeos sem legendas (requer Whisper) | Não |
| `--use_gemini` | flag | Usar Gemini para transcrição (padrão: True) | Não |
| `--input_dir` | string | Processar diretório com múltiplos vídeos | Não |

## 🎬 Vídeos SEM Legendas?

Se seu vídeo **não tem legendas embutidas**, você tem 3 opções:

### Opção 1: Usar arquivo SRT externo (⭐ Recomendado)

Coloque o arquivo `.srt` no mesmo diretório com o mesmo nome:

```
videos_input/
├── tutorial.mp4
└── tutorial.srt    ← Coloque aqui
```

O agente detectará automaticamente!

### Opção 2: Transcrição automática com Whisper

```bash
# Instalar Whisper (uma vez)
pip install openai-whisper

# Transcrever video + traduzir
python video_translator.py \
    --input_video videos_input/tutorial.mp4 \
    --target_language pt \
    --auto_transcribe
```

### Opção 3: Guia Completo

Leia **`GUIA_SEM_LEGENDA.md`** para:
- ✅ Como gerar SRT com Whisper
- ✅ Estratégias automáticas e manuais  
- ✅ Comparação de métodos
- ✅ Exemplos completos

## 📁 Estrutura do Projeto

```
bot_tradução/
├── video_translator.py       # Módulo principal (CLI + pipeline)
├── video_processor.py        # Extração de áudio/legendas com ffmpeg
├── transcriber.py            # Transcrição de áudio com Whisper
├── translation_api.py        # Integrações Gemini e Google Cloud
├── config.py                 # Configuração centralizada
├── logger_config.py          # Sistema de logging
├── utils.py                  # Utilitários e métricas
├── requirements.txt          # Dependências Python
├── .env.example              # Template de variáveis de ambiente
├── .env                      # Variáveis de ambiente (gitignore)
├── README.md                 # Documentação principal
├── GUIA_SEM_LEGENDA.md       # Guia para vídeos sem legendas
├── videos_input/             # Vídeos de entrada (criar)
├── videos_output/            # Vídeos/legendas de saída
└── logs/                     # Logs e relatórios JSON
```

## 🔑 Configuração das APIs

### Gemini API

1. Acesse https://makersuite.google.com/app/apikeys
2. Crie uma chave de API
3. Copie e cole em `.env`:
   ```
   GEMINI_API_KEY=sk-...
   ```

### Google Cloud Translation

1. Crie um projeto em https://console.cloud.google.com
2. Ative a API Translation
3. Crie credenciais de serviço (JSON)
4. Configure em `.env`:
   ```
   GOOGLE_CLOUD_PROJECT=seu-projeto-id
   GOOGLE_APPLICATION_CREDENTIALS=/caminho/para/credentials.json
   ```

## 📊 Saídas

### Legendas Traduzidas (SRT)
```
videos_output/
└── meu_video_en.srt          # Legendas em inglês
```

### Vídeo com Legendas Embutidas
```
videos_output/
└── meu_video_with_subtitles.mp4
```

### Relatórios
```
logs/
└── report_meu_video_20251027_143022.json
```

Exemplo de relatório:
```json
{
  "video_name": "meu_video",
  "target_language": "en",
  "duration_seconds": 125.43,
  "api_requests": 3,
  "tokens_used": 1250,
  "stages_completed": {
    "extract": true,
    "transcribe": false,
    "translate": true,
    "embed": true
  },
  "errors": [],
  "status": "success"
}
```

## ⚠️ Limitações Importantes

### Tamanho de Vídeo
- Máximo: **100 MB** (configurável em `config.py`)
- Motivo: Limite de upload da API Gemini

### Duração de Vídeo
- Máximo: **25 minutos** (configurável)
- Motivo: Limite de tokens da API

### Formatos Suportados
- Vídeo: MP4, AVI, MOV, MKV, WebM, FLV
- Áudio: WAV, MP3, AAC
- Legendas: SRT

### Idiomas Suportados
- Português (pt), Inglês (en), Espanhol (es)
- Francês (fr), Alemão (de), Italiano (it)
- Japonês (ja), Coreano (ko), Chinês (zh), Russo (ru)

## 🐛 Troubleshooting

### "ffmpeg não encontrado"
```bash
# Windows
# Baixe de https://ffmpeg.org/download.html
# Adicione à PATH ou instale via Chocolatey:
choco install ffmpeg

# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

### "GEMINI_API_KEY não configurada"
```bash
# Verifique se .env existe e tem a chave:
cat .env

# Ou defina a variável de ambiente:
# Windows PowerShell
$env:GEMINI_API_KEY = "sua_chave"

# Linux/macOS
export GEMINI_API_KEY="sua_chave"
```

### "Nenhuma legenda encontrada"
Se o vídeo não tem legendas embutidas, o sistema extrai áudio automaticamente. A transcrição ocorre via Gemini.

### "Erro de Quota/Rate Limit"
O sistema implementa retry automático com espera. Se persistir:
1. Verifique sua quota na console do Gemini
2. Reduza tamanho do vídeo
3. Processe em horários diferentes

## 🔄 Pipeline Detalhado

```
[Vídeo Input]
    ↓
[Validar: Formato, Tamanho, Duração]
    ↓
[Tentar Extrair Legendas SRT]
    ├─→ Se SIM:
    │   ├─ Traduzir SRT (Google Cloud ou Gemini)
    │   ├─ Salvar SRT traduzido
    │   └─ (Opcional) Embutir com ffmpeg
    │
    └─→ Se NÃO:
        ├─ Extrair Áudio
        ├─ Enviar para Gemini
        ├─ Obter Transcrição + Tradução
        ├─ Gerar SRT
        └─ (Opcional) Embutir com ffmpeg
    
    ↓
[Salvar Relatório JSON]
    ↓
[Resultado Final: SRT ou MP4]
```

## 📝 Logs

Logs são salvos automaticamente em `logs/video_translator.log`:

```
2025-10-27 14:30:22 - video_translator - INFO - Validando vídeo: videos/meu_video.mp4
2025-10-27 14:30:23 - video_translator - INFO - Tamanho do arquivo: 45.32MB
2025-10-27 14:30:24 - video_translator - INFO - ✓ Vídeo validado com sucesso
2025-10-27 14:30:25 - video_processor - INFO - Extraindo legendas existentes...
2025-10-27 14:30:26 - video_processor - INFO - ✓ Legendas encontradas no vídeo
```

## 🚀 Exemplos Práticos

### Exemplo 1: Traduzir vídeo de PT para EN
```bash
python video_translator.py \
    --input_video videos/palestra.mp4 \
    --target_language en \
    --embed_subs
```

### Exemplo 2: Processar pasta inteira
```bash
python video_translator.py \
    --input_dir videos/ \
    --target_language es
```

### Exemplo 3: Apenas extrair SRT sem embutir
```bash
python video_translator.py \
    --input_video videos/curso.mp4 \
    --target_language fr
# Resultado: videos_output/curso_fr.srt
```

## 🛡️ Boas Práticas

1. **Backup de Originals**: Sempre mantenha cópia dos vídeos originais
2. **Teste com Vídeos Pequenos**: Comece com vídeos < 5 minutos
3. **Revisão Manual**: Transcrições automáticas podem ter erros
4. **Monitorar Quota**: Verifique limites diários da API
5. **Usar .env**: Nunca commit das credenciais no Git

## 📄 Licença

Projeto criado para fins educacionais. Respeite direitos autorais dos vídeos.

## 📞 Suporte

Para questões ou bugs, verifique:
- Logs em `logs/video_translator.log`
- Relatórios em `logs/report_*.json`
- Documentação oficial: https://ai.google.dev/

---

**Desenvolvido com ❤️ usando Gemini e Google Cloud Translation**
