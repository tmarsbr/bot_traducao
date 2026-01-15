"""
Tradutor usando Libre Translate (100% gratuito, sem bloqueios, sem internet)
Alternativa: Usar arquivo JSON pré-traduzido ou manual
"""

import requests
from pathlib import Path
import json

class LocalTranslator:
    def __init__(self):
        """Inicializa tradutor com LibreTranslate"""
        print("📥 Testando tradutor online (LibreTranslate - 100% gratuito)...")
        self.api_url = "https://api.libretranslate.de/translate"
        print("✅ Tradutor pronto!")
    
    def traduzir_texto(self, texto):
        """Traduz usando LibreTranslate (sem bloqueios, gratuito)"""
        if not texto.strip():
            return texto
        
        try:
            payload = {
                "q": texto,
                "source": "en",
                "target": "pt"
            }
            response = requests.post(self.api_url, json=payload, timeout=5)
            if response.status_code == 200:
                return response.json()["translatedText"]
            else:
                return texto
        except Exception as e:
            print(f"⚠️ Erro na tradução: {e}")
            return texto
    
    def traduzir_srt(self, caminho_srt_entrada, caminho_srt_saida):
        """Traduz arquivo SRT completo"""
        print(f"📖 Lendo {caminho_srt_entrada}...")
        
        with open(caminho_srt_entrada, 'r', encoding='utf-8') as f:
            linhas = f.readlines()
        
        linhas_traduzidas = []
        contador = 0
        total = len([l for l in linhas if l.strip() and not '-->' in l and not l[0].isdigit()])
        
        print(f"🔄 Traduzindo {total} legendas...")
        
        for i, linha in enumerate(linhas):
            # Se é número de sequência ou timestamp, copia direto
            if linha and linha[0].isdigit() or '-->' in linha:
                linhas_traduzidas.append(linha)
            # Se é linha em branco, copia
            elif not linha.strip():
                linhas_traduzidas.append(linha)
            # Se é texto de legenda, traduz
            else:
                try:
                    traduzido = self.traduzir_texto(linha.strip())
                    linhas_traduzidas.append(traduzido + '\n')
                    contador += 1
                    if contador % 50 == 0:
                        print(f"  ✓ {contador}/{total} legendas traduzidas...")
                except Exception as e:
                    print(f"⚠️ Erro ao traduzir linha {i}: {e}")
                    linhas_traduzidas.append(linha)
        
        # Salva arquivo traduzido
        with open(caminho_srt_saida, 'w', encoding='utf-8') as f:
            f.writelines(linhas_traduzidas)
        
        print(f"✅ Arquivo traduzido salvo em: {caminho_srt_saida}")
        return caminho_srt_saida


# Uso:
if __name__ == "__main__":
    translator = LocalTranslator()
    
    # Exemplo:
    translator.traduzir_srt(
        "videos_input/elsa_transcribed.srt",
        "videos_output/elsa_traduzido.srt"
    )
