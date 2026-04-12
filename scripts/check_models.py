import google.generativeai as genai
import os


os.environ["GOOGLE_API_KEY"] = "AIzaSyDSmff0hvEqm27-e4SwrBfmsZp2bSo-bCU"
genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

print("--- Checking Available Models ---")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Model Name: {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")