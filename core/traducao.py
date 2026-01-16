import time
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL, BATCH_SIZE
from core.utils import logger

genai.configure(api_key=GEMINI_API_KEY)

def traduzir_srt_lotes(caminho_entrada, caminho_saida):
    """Traduz SRT em lotes usando Gemini, mantendo contexto para consistência."""
    logger.info(f"🤖 Iniciando tradução: {caminho_entrada.name}")
    
    try:
        with open(caminho_entrada, 'r', encoding='utf-8') as f:
            conteudo = f.read()
            
        import re
        blocos = re.split(r'\n\n+', conteudo.strip())
        if not blocos: return False
        
        model = genai.GenerativeModel(GEMINI_MODEL)
        legendas_traduzidas = []
        contexto = ""
        
        # Config de segurança para conteúdo adulto/sem censura
        safety_settings = [
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        for i in range(0, len(blocos), BATCH_SIZE):
            lote = blocos[i:i + BATCH_SIZE]
            texto_lote = "\n\n".join(lote)
            
            prompt = f"""Atue como tradutor profissional de legendas EN->PT(BR).
CONTEXTO ANTERIOR (consistência): {contexto[-500:] if contexto else "Início"}

REGRAS:
1. Mantenha formato SRT estrito (números e tempos).
2. Use gírias brasileiras naturais e sem censura.
3. Termos familiares: "Step-mom" = "Madrasta", "Step-bro" = "Meio-irmão".
4. NÃO adicione preâmbulos ou markdown tags.

ENTRADA:
{texto_lote}
"""
            
            sucesso_lote = False
            tentativas = 0
            while tentativas < 3 and not sucesso_lote:
                try:
                    res = model.generate_content(prompt, safety_settings=safety_settings)
                    if res.text:
                        traducao = res.text.replace("```srt", "").replace("```", "").strip()
                        legendas_traduzidas.append(traducao)
                        contexto = traducao # Atualiza contexto para próximo lote
                        sucesso_lote = True
                    else:
                        raise ValueError("Resposta da IA vazia")
                except Exception as e:
                    tentativas += 1
                    time.sleep(2 * tentativas)
            
            if not sucesso_lote:
                logger.warning(f"Falha no lote {i//BATCH_SIZE + 1}, mantendo original.")
                legendas_traduzidas.append(texto_lote)
                
            # Rate limit cooldown
            time.sleep(1)
            
        # Salvar Final
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write("\n\n".join(legendas_traduzidas))
            
        return True

    except Exception as e:
        logger.error(f"Erro na tradução: {e}")
        return False
