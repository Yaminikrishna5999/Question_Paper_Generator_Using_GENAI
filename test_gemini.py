"""
Test script to verify Google Gemini API is working correctly
Compatible with NEW google.genai SDK
Run this before starting the main application
"""

import os
from dotenv import load_dotenv

print("=" * 60)
print("🧪 TESTING GOOGLE GEMINI API SETUP (NEW SDK)")
print("=" * 60)
print()

# Step 1: Check for .env file
print("Step 1: Checking for .env file...")
if os.path.exists(".env"):
    print("✅ .env file found")
else:
    print("❌ .env file NOT found")
    print("   Create .env file with: GEMINI_API_KEY=your_key")
    exit(1)

print()

# Step 2: Load environment variables
print("Step 2: Loading environment variables...")
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    print(f"✅ API key loaded: {api_key[:20]}...")
else:
    print("❌ GEMINI_API_KEY not found in .env")
    print("   Add to .env: GEMINI_API_KEY=your_actual_key")
    exit(1)

print()

# Step 3: Check google.genai package
print("Step 3: Checking google.genai package...")
try:
    from google import genai
    print("✅ google.genai package installed")
except ImportError:
    print("❌ google.genai NOT installed")
    print("   Install with: pip install -U google-genai")
    exit(1)

print()

# Step 4: Initialize Gemini client
print("Step 4: Initializing Gemini client...")
try:
    client = genai.Client(api_key=api_key)
    print("✅ Gemini client initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize Gemini client: {e}")
    exit(1)

print()

# Step 5: Test question generation
print("Step 5: Testing question generation...")
try:
    response = client.models.generate_content(
        model="models/gemini-flash-lite-latest",
        contents="Generate a simple MCQ question about Python programming with 4 options"
    )

    if response and response.text:
        print("✅ Question generated successfully!")
        print()
        print("Sample Output:")
        print("-" * 60)
        print(response.text[:300] + "...")
        print("-" * 60)
    else:
        print("❌ No response text returned from API")
        exit(1)

except Exception as e:
    print(f"❌ Question generation failed: {e}")
    print()
    print("Common issues:")
    print("- Invalid API key")
    print("- Using restricted model")
    print("- Free-tier quota exceeded")
    exit(1)

print()
print("=" * 60)
print("🎉 ALL TESTS PASSED!")
print("=" * 60)
print()
print("✅ Your Gemini API setup is working correctly!")
print("✅ You can now proceed with the main application")
print()
print("API Details:")
print("- Model: gemini-flash-lite-latest (FREE TIER)")
print("- SDK: google.genai (latest)")
print("- Cost: $0.00")
print()
print("=" * 60)
