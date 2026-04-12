import pandas as pd
import time
import google.generativeai as genai
import re
import os
from legal_advisor import rag_chain, retriever 

# --- 1. API KEY ROTATION SETUP ---
API_KEYS = ["AIzaSyCsjo9b7SyVO1l_vGzRwH00oxx1yQ4OOVE", "AIzaSyDeA1RDWbtS41duiYZZ6KKIaQjJQTz1dwI"] 
current_key_index = 0

def configure_gemini():
    active_key = API_KEYS[current_key_index]
    genai.configure(api_key=active_key)
    print(f"🔄 Switched to API Key Index: {current_key_index}")

def rotate_api_key():
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    configure_gemini()
    print("⏳ Rate Limit Hit! Cooldown for 30 seconds...")
    time.sleep(30) 

# --- 2. OPTIMIZED TEST DATASET (20 TOPIC-BASED QUERIES) ---
test_dataset = [
    # Marriage & Polygamy
    {"question": "What is the legal procedure for a second marriage in Pakistan?", "expected_sections": ["Section 6", "Polygamy", "Arbitration Council"], "mode": "LEGAL PRO"},
    {"question": "Shohar ne doosri shadi ki ijazat nahi li, kya ye jurm hai?", "expected_sections": ["Section 6", "Permission", "Fine"], "mode": "GENERAL USER (Woman)"},
    {"question": "Nikah register na ho toh kya saza ho sakti hai?", "expected_sections": ["Section 5", "Registration", "Penalty"], "mode": "LEGAL PRO"},
    {"question": "What is the minimum age for marriage in Punjab for girls?", "expected_sections": ["Child Marriage", "16", "18"], "mode": "GENERAL USER (Woman)"},

    # Divorce & Iddat
    {"question": "Shohar ne talaq di hai, notice Chairman ko kab dena hota hai?", "expected_sections": ["Section 7", "Notice", "Chairman"], "mode": "GENERAL USER (Woman)"},
    {"question": "Explain 'Haq-e-Talaq-e-Tafweez' in Nikahnama.", "expected_sections": ["Section 8", "Delegated", "Divorce"], "mode": "LEGAL PRO"},
    {"question": "Khula lene ka sahi kanooni tariqa kya hai?", "expected_sections": ["Family Courts", "Khula", "Dissolution"], "mode": "GENERAL USER (Woman)"},
    {"question": "Does a divorce become effective immediately without Union Council notice?", "expected_sections": ["Section 7", "Invalid", "90 days"], "mode": "LEGAL PRO"},

    # Maintenance & Custody
    {"question": "My husband is not giving me money (Kharcha), where to complain?", "expected_sections": ["Section 9", "Maintenance", "Arbitration Council"], "mode": "GENERAL USER (Woman)"},
    {"question": "Bachon ki custody (Hizanat) ka faisla kaise hota hai?", "expected_sections": ["Guardians", "Custody", "Welfare"], "mode": "GENERAL USER (Woman)"},
    {"question": "Can a wife claim maintenance after divorce during Iddat?", "expected_sections": ["Iddat", "Maintenance", "Kharcha"], "mode": "LEGAL PRO"},

    # Inheritance
    {"question": "Do orphaned grandchildren inherit from their grandfather?", "expected_sections": ["Section 4", "Succession", "Grandchildren"], "mode": "LEGAL PRO"},
    {"question": "Beti ka hissa bete se kitna hota hai kanoon ki nazar mein?", "expected_sections": ["Inheritance", "Daughter", "Half"], "mode": "GENERAL USER (Woman)"},
    {"question": "How much share does a widow get if the deceased has children?", "expected_sections": ["Inheritance", "Widow", "1/8th"], "mode": "LEGAL PRO"},
    {"question": "Kya walid apni beti ko wirasat se aaq (disinherit) kar sakta hai?", "expected_sections": ["Invalid", "Heirs", "Shariah"], "mode": "GENERAL USER (Woman)"},

    # Cybercrime
    {"question": "Someone is blackmailing me with my photos, what should I do?", "expected_sections": ["FIA", "Cybercrime", "PECA"], "mode": "GENERAL USER (Woman)"},
    {"question": "What is the punishment for online harassment under PECA?", "expected_sections": ["Section 21", "Harassment", "Fine"], "mode": "LEGAL PRO"},
    {"question": "Fake account bana kar koi tang kare toh kahan report karein?", "expected_sections": ["Identity", "Spoofing", "Complaint"], "mode": "GENERAL USER (Woman)"},

    # Workplace Harassment
    {"question": "Office boss is harassing me, where to file an appeal?", "expected_sections": ["Ombudsman", "Mohtasib", "Committee"], "mode": "GENERAL USER (Woman)"},
    {"question": "What are the major penalties for workplace harassment?", "expected_sections": ["Section 4", "Dismissal", "Removal"], "mode": "LEGAL PRO"}
]

def run_accuracy_test():
    configure_gemini()
    results = []
    total_score = 0
    print(f"🚀 Starting System Validation on {len(test_dataset)} Queries...")

    for i, test in enumerate(test_dataset):
        print(f"\n[{i+1}/{len(test_dataset)}] Analyzing: {test['question'][:50]}...")
        
        success = False
        attempts = 0
        
        while not success and attempts < (len(API_KEYS) * 2):
            try:
                start_time = time.time()
                
                # A. Retrieval Test
                docs = retriever.invoke(test["question"])
                ret_status = "✅ OK" if len(docs) > 0 else "❌ FAIL"

                # B. Generation Test
                response = rag_chain.invoke({"question": test["question"], "mode": test["mode"]})
                
                # C. Scoring
                clean_resp = re.sub(r'[^a-zA-Z0-9\s]', ' ', response.lower())
                matched = [kw for kw in test["expected_sections"] if kw.lower() in clean_resp]
                
                score = len(matched) / len(test["expected_sections"])
                duration = round(time.time() - start_time, 2)

                results.append({
                    "No": i+1,
                    "Retrieved": ret_status,
                    "Acc %": round(score * 100, 2),
                    "Time(s)": duration
                })
                
                total_score += score
                success = True
                print(f"   ↳ Result: {round(score * 100, 2)}% Accuracy in {duration}s")
                
                # SET TO 20 SECONDS FOR API STABILITY
                time.sleep(20) 

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    rotate_api_key()
                    attempts += 1
                else:
                    print(f"❌ Error: {e}")
                    results.append({"No": i+1, "Retrieved": "❌ ERR", "Acc %": 0.0, "Time(s)": 0})
                    success = True

    # --- RESULTS REPORT ---
    if results:
        df = pd.DataFrame(results)
        final_acc = (total_score / len(test_dataset)) * 100
        print("\n" + "="*60)
        print("📊 FINAL AWAZ-E-NISA SYSTEM REPORT (20 QUERIES)")
        print("="*60)
        print(df.to_string(index=False))
        print("\n" + "="*60)
        print(f"🏆 OVERALL ACCURACY: {round(final_acc, 2)}%")
        print(f"⏱️ AVG RESPONSE TIME: {round(df['Time(s)'].mean(), 2)}s")
        print("="*60)

if __name__ == "__main__":
    run_accuracy_test()