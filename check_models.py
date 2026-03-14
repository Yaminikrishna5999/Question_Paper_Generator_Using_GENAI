from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
if not api_key:
    api_key = "PASTE_YOUR_KEY_HERE"
    
print(f"Using Key: {api_key[:8]}...")

client = genai.Client(api_key=api_key)

print("\n--- Available Models ---")
try:
    for m in client.models.list():
        print(f"Name: {m.name} | Supported: {m.supported_generation_methods}")
except Exception as e:
    print(f"Error: {e}")

print(f"\nSDK: google-genai (Modern)")
