
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ Erro: GEMINI_API_KEY não encontrada.")
else:
    genai.configure(api_key=api_key)
    print("🔍 Listando modelos disponíveis...")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"❌ Erro ao listar modelos: {e}")
