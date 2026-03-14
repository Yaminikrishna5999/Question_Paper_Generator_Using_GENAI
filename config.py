import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # FREE Google Gemini API Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
    
    # AI Model Settings (FREE) - fallback list for quota exhaustion
    AI_MODEL = "models/gemini-1.5-flash"
    FALLBACK_MODELS = [
        "models/gemini-1.5-flash",
        "models/gemini-2.0-flash",
        "models/gemini-1.5-flash-8b",
        "models/gemini-1.5-pro"
    ]
    TEMPERATURE = 0.7
    
    # Question Paper Rules
    MIN_QUESTIONS = 1
    MAX_QUESTIONS = 50
    DEFAULT_QUESTIONS = 5
    
    # Difficulty Levels
    DIFFICULTY_LEVELS = ['Easy', 'Medium', 'Hard']
    DEFAULT_DIFFICULTY = {'Easy': 40, 'Medium': 40, 'Hard': 20}
    
    # Question Types
    QUESTION_TYPES = ['MCQ', 'Short Answer', 'Long Answer', 'True/False', 'Fill in the Blanks']
    
    # Marks Allocation
    MARKS_CONFIG = {
        'Easy': {'MCQ': 1, 'Short Answer': 2, 'True/False': 1, 'Fill in the Blanks': 1, 'Long Answer': 3},
        'Medium': {'MCQ': 2, 'Short Answer': 4, 'True/False': 2, 'Fill in the Blanks': 2, 'Long Answer': 5},
        'Hard': {'MCQ': 3, 'Short Answer': 6, 'True/False': 3, 'Fill in the Blanks': 3, 'Long Answer': 10}
    }
    
    # File Paths
    OUTPUT_DIR = 'data/generated_papers'
    QUESTION_BANK_FILE = 'data/question_bank.json'
    
    # Selection Options
    DEPARTMENTS = ["CSE", "ECE", "IT", "Mechanical", "Civil", "Mathematics", "Physics"]
    DESIGNATIONS = ["Assistant Professor", "Associate Professor", "Professor", "HOD", "Lecturer"]

    # Ensure directories exist
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs('data', exist_ok=True)