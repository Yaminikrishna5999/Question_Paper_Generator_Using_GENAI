from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

client = genai.Client(api_key=api_key)

with open('available_models.txt', 'w') as f:
    try:
        for m in client.models.list():
            f.write(f"{m.name}\n")
    except Exception as e:
        f.write(f"Error: {e}\n")
