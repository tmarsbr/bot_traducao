"""
Teste rápido de tradução com MarianMT
"""

from local_translator import LocalTranslator

# Cria tradutor
translator = LocalTranslator()

# Testa com algumas linhas
teste_en = """What the fuck is this?
This is a test phrase.
Another line here."""

print("\n📋 Texto original:\n", teste_en)

# Traduz cada linha
for linha in teste_en.split('\n'):
    if linha.strip():
        traduzida = translator.traduzir_texto(linha)
        print(f"🇬🇧 {linha}")
        print(f"🇧🇷 {traduzida}\n")
