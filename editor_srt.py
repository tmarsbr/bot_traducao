"""
Editor interativo de SRT - Traduz linha por linha no terminal
"""

import json
from pathlib import Path

class EditorSRT:
    def __init__(self):
        self.traducoes = {}
    
    def parser_srt(self, caminho_srt):
        """Extrai legendas do SRT"""
        with open(caminho_srt, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        blocos = conteudo.strip().split('\n\n')
        legendas = []
        
        for bloco in blocos:
            linhas = bloco.strip().split('\n')
            if len(linhas) >= 3:
                numero = linhas[0]
                timestamp = linhas[1]
                texto = '\n'.join(linhas[2:])
                legendas.append({
                    'numero': numero,
                    'timestamp': timestamp,
                    'texto_en': texto,
                    'texto_pt': ''
                })
        
        return legendas
    
    def editar_interativo(self, caminho_srt_entrada, caminho_srt_saida):
        """Editor interativo para traduzir legendas"""
        legendas = self.parser_srt(caminho_srt_entrada)
        total = len(legendas)
        
        print(f"\n{'='*70}")
        print(f"📝 EDITOR DE LEGENDAS - {total} linhas para traduzir")
        print(f"{'='*70}\n")
        print("💡 Dicas:")
        print("  - Digite a tradução em português")
        print("  - Digite '...' para pular (traduzir depois)")
        print("  - Digite 'sair' para salvar e terminar")
        print(f"\n{'='*70}\n")
        
        for idx, legenda in enumerate(legendas, 1):
            print(f"\n📌 Legenda {idx}/{total} [{legenda['timestamp']}]")
            print(f"🇬🇧 {legenda['texto_en']}")
            print("-" * 70)
            
            while True:
                traducao = input("🇧🇷 Tradução: ").strip()
                
                if traducao.lower() == 'sair':
                    print("\n✅ Salvando arquivo...")
                    self.salvar_srt(legendas, caminho_srt_saida)
                    return
                elif traducao == '...':
                    print("⏭️  Pulado - traduzir depois")
                    break
                elif traducao:
                    legenda['texto_pt'] = traducao
                    print("✓ Salvo")
                    break
                else:
                    print("❌ Digite algo ou '...' para pular")
        
        print("\n✅ Tradução concluída! Salvando...")
        self.salvar_srt(legendas, caminho_srt_saida)
    
    def salvar_srt(self, legendas, caminho_saida):
        """Salva legendas em formato SRT"""
        conteudo = ""
        
        for legenda in legendas:
            if legenda['texto_pt']:
                conteudo += f"{legenda['numero']}\n"
                conteudo += f"{legenda['timestamp']}\n"
                conteudo += f"{legenda['texto_pt']}\n\n"
        
        with open(caminho_saida, 'w', encoding='utf-8') as f:
            f.write(conteudo)
        
        print(f"✅ Arquivo salvo em: {caminho_saida}\n")
    
    def carregar_traducoes(self, arquivo_json):
        """Carrega traduções anteriores de um JSON"""
        if Path(arquivo_json).exists():
            with open(arquivo_json, 'r', encoding='utf-8') as f:
                self.traducoes = json.load(f)
    
    def salvar_traducoes(self, arquivo_json):
        """Salva traduções em JSON para reutilizar"""
        with open(arquivo_json, 'w', encoding='utf-8') as f:
            json.dump(self.traducoes, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    
    editor = EditorSRT()
    
    # Uso: python editor_srt.py <arquivo_entrada> <arquivo_saida>
    if len(sys.argv) >= 3:
        entrada = sys.argv[1]
        saida = sys.argv[2]
    else:
        entrada = "videos_input/elsa_transcribed.srt"
        saida = "videos_output/elsa_traduzido.srt"
    
    print(f"\n📂 Entrada: {entrada}")
    print(f"📂 Saída: {saida}\n")
    
    editor.editar_interativo(entrada, saida)
