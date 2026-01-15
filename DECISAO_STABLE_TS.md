# 🎯 Decisão: Faster-Whisper vs Stable-TS

## 💡 Resumo Executivo (TL;DR)

**Para o seu caso (bot de tradução de vídeos):**

```
Vídeos < 30 min  →  Faster-Whisper (V3 otimizada)  ⚡
Vídeos > 45 min  →  Stable-TS                      🎯
Produção final   →  Stable-TS (se tempo permitir) ✨
```

---

## 🔄 Estratégia Híbrida Recomendada

### Configuração Ideal

```python
# Pseudocódigo para adicionar ao pipeline

if duracao_video < 30_minutos:
    usar_faster_whisper_v3()  # Rápido e bom
elif duracao_video < 60_minutos:
    if tem_tempo:
        usar_stable_ts()  # Melhor qualidade
    else:
        usar_faster_whisper_v3()  # Aceitável
else:  # > 1 hora
    usar_stable_ts()  # OBRIGATÓRIO (evita time drift)
```

---

## 📊 Análise de ROI (Retorno do Investimento de Tempo)

### Exemplo: Vídeo de 50 minutos

| Solução | Tempo | Qualidade | Reprocessar? |
|---------|-------|-----------|--------------|
| **Faster-Whisper V3** | 6 min | 85% boa | Talvez (+10 min) |
| **Stable-TS** | 18 min | 98% boa | Raramente |

**Conclusão:** Em vídeos longos, Stable-TS economiza tempo total (evita retrabalho).

---

## 🎬 Respostas às Suas Perguntas

### "Quer que eu explique como configurar o ficheiro .ASS gerado para ter aquele visual de 'fundo translúcido preto' igual ao da Netflix?"

**Resposta:** Isso já está implementado! 🎉

No `embutir_legendas.py` (que você usa), o ASS já tem:
```
BackColour=&H80000000  # Preto com 50% de transparência
BorderStyle=3          # Caixa ao redor do texto
FontSize=58            # Fonte grande (+81%)
```

Se quiser ajustar a transparência:
```
&H80000000  →  80 = transparência (00 = opaco, FF = transparente)
```

### "ou preferes focar primeiro em testar se a sincronia ficou perfeita?"

**Sugestão:** Teste PRIMEIRO com 1 vídeo problemático.

**Comando:**
```bash
pip install stable-ts
python transcritor_stable_ts.py "video_que_desincronizou.mp4"
```

Compare os 2 SRTs:
- `video_EN.srt` (Faster-Whisper)
- `video_STABLE.srt` (Stable-TS)

Abra ambos no VLC e veja qual sincroniza melhor no final do vídeo.

---

## 🛠️ Implementação Prática: Adicionar ao Pipeline

### Opção A: Script Separado (Mais Simples)

**Uso:** Rodar apenas quando Faster-Whisper falhar

```bash
# Pipeline normal
python extrair_proximos_srt_v3_otimizado.py

# Se algum vídeo descincronizar, reprocessar com:
python transcritor_stable_ts.py "video_problema.mp4"
```

✅ **Vantagens:** 
- Não quebra o pipeline existente
- Usa Stable-TS apenas quando necessário

### Opção B: Integração Automática (Mais Robusto)

Modificar `extrair_proximos_srt_v3_otimizado.py` para detectar duração:

```python
# No início do arquivo
try:
    from transcritor_stable_ts import transcrever_video_longo
    STABLE_TS_DISPONIVEL = True
except:
    STABLE_TS_DISPONIVEL = False

# Na função extrair_srt_otimizado
duracao = obter_duracao_video(video_path)

if duracao > 2700 and STABLE_TS_DISPONIVEL:  # 45 min
    print("  🎯 Vídeo longo detectado: usando Stable-TS...")
    srt_path = transcrever_video_longo(video_path)
else:
    # Lógica atual (Faster-Whisper)
    ...
```

---

## 📦 Instalação do Stable-TS

### Passo a Passo

```bash
# 1. Instalar
pip install stable-ts

# 2. Testar
python transcritor_stable_ts.py

# 3. Se der erro de CUDA (normal sem GPU NVIDIA)
# Edite o script e force CPU:
usar_gpu=False
```

**Tamanho do download:** ~4GB (PyTorch + modelos)

**Tempo da primeira execução:** ~10min (baixa modelos)

---

## 🎯 Recomendação Final

### Para o seu projeto:

1. **Curto prazo (agora):**
   - Continue usando `extrair_proximos_srt_v3_otimizado.py`
   - Instale Stable-TS como "plano B"
   - Teste em 1-2 vídeos longos para validar

2. **Médio prazo (próxima semana):**
   - Se Stable-TS funcionar bem, implemente **Opção A** (script separado)
   - Use para vídeos > 50 minutos

3. **Longo prazo (depois):**
   - Se processar muitos vídeos longos, implemente **Opção B** (automático)

---

## 🐛 Problemas Conhecidos e Soluções

### 1. "ModuleNotFoundError: No module named 'stable_whisper'"

```bash
pip install stable-ts
```

### 2. "CUDA out of memory" (GPU cheia)

Edite `transcritor_stable_ts.py`:
```python
usar_gpu=False  # Linha ~200
```

### 3. "FFmpeg not found"

Certifique-se que FFmpeg está no PATH:
```bash
ffmpeg -version
```

### 4. Muito lento mesmo em GPU

Normal. Stable-TS é 2-3x mais lento que Faster-Whisper.

**Alternativas:**
- Use modelo `medium` em vez de `large-v3`
- Processe durante a noite
- Use apenas para vídeos críticos

---

## ✅ Checklist de Decisão

Você PRECISA de Stable-TS se:

- [ ] Tem vídeos > 1 hora
- [ ] Legendas desincronizam no final do vídeo
- [ ] Muitas legendas falsas em momentos de música
- [ ] Precisão é crítica (cliente, produção)

Pode continuar com Faster-Whisper V3 se:

- [x] Maioria dos vídeos < 30 min
- [x] Velocidade é prioridade
- [x] Qualidade atual é aceitável
- [x] Processamento em lote grande

---

## 📞 Próximos Passos Sugeridos

**Pergunta para você:**

Quer que eu:

**A)** Crie uma versão híbrida automática do `extrair_proximos_srt_v3_otimizado.py` que detecta vídeos longos e usa Stable-TS?

**B)** Explique como configurar estilos ASS personalizados (cores, posições, karaoke)?

**C)** Foque em otimizar ainda mais o Faster-Whisper V3 para vídeos médios (30-45min)?

**D)** Deixe como está e você testa o Stable-TS manualmente quando precisar?

---

**Minha recomendação:** Opção **D** primeiro (testar), depois **A** se gostar dos resultados. 🚀
