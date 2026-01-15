# 🚀 Guia Rápido - Testar V3 Otimizada

## ⚡ Início Rápido (5 minutos)

### 1. Instalar dependência adicional
```bash
pip install numpy
```

### 2. Testar em um único vídeo

**Opção A:** Processar apenas 1 vídeo para testar
```bash
# Edite o script e adicione esta linha após a linha 273 (antes do loop):
# videos = videos[:1]  # Processa apenas o primeiro

python extrair_proximos_srt_v3_otimizado.py
```

**Opção B:** Criar pasta de teste
```bash
# Criar pasta temporária
mkdir proximos_teste
copy proximos_para_traducao\*.mp4 proximos_teste\ /Y

# Editar PASTA_ENTRADA no script para "proximos_teste"
python extrair_proximos_srt_v3_otimizado.py
```

### 3. Comparar resultados

```bash
# Ver legendas geradas
dir videos_output\subtitles_en\*_EN.srt

# Abrir e comparar qualidade
notepad videos_output\subtitles_en\[nome_video]_EN.srt
```

---

## 📋 Checklist de Verificação

Após rodar a V3, verifique:

- [ ] **Velocidade**: Levou menos tempo que a V2?
- [ ] **Alucinações**: Menos "Thank you for watching" falsos?
- [ ] **Silêncios**: Menos legendas em momentos de música/pausa?
- [ ] **Qualidade de Áudio**: Sussurros foram transcritos corretamente?
- [ ] **Legendas**: Estão quebradas em linhas de ~42 caracteres?

---

## 🔍 Exemplo de Saída Esperada

```
⏳ Carregando modelo Whisper...
✅ Modelo carregado!

🎬 Encontrados 55 vídeos na pasta

📋 3 vídeo(s) para processar

🚀 OTIMIZAÇÕES ATIVAS:
   • FFmpeg Piping (sem arquivos temporários)
   • dynaudnorm (normalização dinâmica)
   • Filtros de Confiança (no_speech_prob, avg_logprob)
   • Detecção de alucinações conhecidas
   • Formatação Netflix (42 chars/linha)

[1/3] 🎬 Processando: video_teste.mp4
  1️⃣ Processando áudio (pipe+filtros)... ✓
  2️⃣ Transcrevendo com filtros... (filtrou 5: 3 silêncio, 1 baixa conf., 1 aluc.) ✓
  3️⃣ Salvando SRT... ✓ (142 legendas)
  🤖 Traduzindo (Gemini)... ✓
  📽️ Embutindo legenda... ✓
  ✨ Vídeo finalizado: videos_output/videos_translated/video_teste_PT.mp4
```

---

## ⚙️ Configurações Recomendadas por Cenário

### Vídeos com Muito Ruído de Fundo
```python
# Mais agressivo na filtragem
LIMITE_NO_SPEECH = 0.5  # Padrão: 0.6
LIMITE_AVG_LOGPROB = -0.8  # Padrão: -1.0
```

### Vídeos com Falas Rápidas (Podcasts/Debates)
```python
# Aceitar CPS mais alto
LIMITE_CPS = 30  # Padrão: 25
```

### Vídeos com Áudio Limpo (Estúdio)
```python
# Menos filtragem (captura tudo)
LIMITE_NO_SPEECH = 0.7  # Padrão: 0.6
LIMITE_AVG_LOGPROB = -1.2  # Padrão: -1.0
```

---

## 🐛 Problemas Comuns

### Erro: "module 'numpy' has no attribute..."
**Solução:**
```bash
pip install --upgrade numpy
```

### Erro: ffmpeg não encontrado
**Solução:** Certifique-se que ffmpeg está no PATH
```bash
ffmpeg -version
```

### Muitas legendas sendo filtradas
**Ajuste:** Reduza o rigor dos filtros (veja seção acima)

### Pipeline muito lento
**Diagnóstico:** A V3 deve ser ~30% mais rápida. Se não for:
- Verifique se `numpy` está instalado
- Confirme que não está salvando arquivos temp (não deve haver WAV na pasta)

---

## 📊 Benchmark Rápido

Para medir o ganho real no seu hardware:

```bash
# Medir tempo da V2
time python extrair_proximos_srt_v2.py

# Medir tempo da V3
time python extrair_proximos_srt_v3_otimizado.py

# Comparar
```

---

## ✅ Próximo Passo Após Validação

Se a V3 funcionar bem, você pode:

1. **Substituir a V2** (backup primeiro!)
```bash
mv extrair_proximos_srt_v2.py extrair_proximos_srt_v2_backup.py
mv extrair_proximos_srt_v3_otimizado.py extrair_proximos_srt_v2.py
```

2. **Processar lote grande** com confiança
```bash
python extrair_proximos_srt_v2.py  # Agora é a V3!
```

---

## 💡 Dica Pro

Para ver estatísticas detalhadas de cada vídeo, adicione esta linha após `stats['aprovados'] += 1` (linha ~192):

```python
print(f"\n    📊 Stats: {stats['aprovados']}/{stats['total']} aprovados "
      f"({stats['no_speech']} silêncios, {stats['alucinacao']} aluc.)")
```

Isso mostrará quantas legendas foram filtradas em tempo real!

---

**Boa sorte! 🚀**  
Em caso de dúvida, ajuste os parâmetros no topo do script e teste novamente.
