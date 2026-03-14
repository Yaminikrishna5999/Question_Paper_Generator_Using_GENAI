from modules.question_generator import QuestionGenerator
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

print(f"Testing with key: {api_key[:8]}...")
# Try forcing v1 to see if it avoids the 404 v1beta issue
client = genai.Client(api_key=api_key, http_options={'api_version': 'v1'})

print("\n--- Listing ALL available models ---")
try:
    for m in client.models.list():
        print(f"ID: {m.name} | Methods: {m.supported_generation_methods}")
except Exception as e:
    print(f"List failed: {e}")

qgen = QuestionGenerator(api_key=api_key)
# Force discovery
qgen._discover_available_models()
print(f"\nDiscovered fallbacks: {qgen.fallback_preference}")

mock_cfg = {
    "exam_name": "Test Exam",
    "course_name": "Test Course",
    "total_questions": 2,
    "question_types": ["MCQ"],
    "counts_per_type": {"MCQ": 2},
    "marks_per_type": {"MCQ": 2},
    "topics": ["Python"],
    "difficulty": "Medium",
    "num_sets": 1
}

prompt = qgen.build_academic_prompt(mock_cfg, "A")
print("\n--- Testing Generation ---")
result = qgen.generate_batch(prompt)

if result:
    print("\nSUCCESS: Received text starting with:", result[:50])
else:
    print("\nFAILURE: Check Generator Errors")
    for err in qgen.errors:
        print(f"Error: {err}")
