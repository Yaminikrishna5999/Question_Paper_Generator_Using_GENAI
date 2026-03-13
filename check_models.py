import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
print(f"Using Key: {api_key[:8]}...")

genai.configure(api_key=api_key)

print("\n--- Available Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Name: {m.name}")
except Exception as e:
    print(f"Error: {e}")

import google.generativeai
print(f"\nSDK Version: {google.generativeai.__version__}")
