import pandas as pd
import time
import google.generativeai as genai
from legal_advisor import rag_chain, retriever 

# --- 1. API KEY ROTATION SETUP ---


current_key_index = 0

def configure_gemini():
    """Gemini ko current active key se configure karne ke liye"""
    active_key = API_KEYS[current_key_index]
    genai.configure(api_key=active_key)
   
    print(f"🔄 Using API Key Index: {current_key_index} (Key starts with: {active_key[:8]}...)")

def rotate_api_key():
    """Key badalne ke liye jab quota khatam ho jaye"""
    global current_key_index
    current_key_index = (current_key_index + 1) % len(API_KEYS)
    configure_gemini()
    print(f"✅ Key Rotated! Retrying with new key...")

# --- 2. TEST DATASET (30 QUESTIONS) ---
test_dataset = [
    # --- FAMILY LAW & MFLO 1961 ---
    {"question": "What is the legal procedure for a second marriage under Pakistani law?", "expected_sections": ["Section 6", "Polygamy", "Arbitration Council"], "mode": "LEGAL PRO"},
    {"question": "Shohar ne talaq de di hai, notice kahan dena hai aur iddat kab shuru hogi?", "expected_sections": ["Section 7", "Chairman", "Union Council"], "mode": "GENERAL USER (Woman)"},
    {"question": "My husband is not providing maintenance, where can I file a complaint?", "expected_sections": ["Section 9", "Maintenance", "Arbitration Council"], "mode": "GENERAL USER (Woman)"},
    {"question": "Nikah nama mein 'Haq-e-Talaq-e-Tafweez' ka kya matlab hai?", "expected_sections": ["Section 8", "Dissolution", "Delegated"], "mode": "GENERAL USER (Woman)"},
    {"question": "Do orphaned grandchildren have a share in their grandfather's property?", "expected_sections": ["Section 4", "Succession", "Grandchildren"], "mode": "LEGAL PRO"},
    {"question": "What is the minimum age for marriage for a girl in Punjab?", "expected_sections": ["Child Marriage", "Restraint", "16", "18"], "mode": "GENERAL USER (Woman)"},
    {"question": "Agar nikah register na ho toh kya ye kanoonan jurm hai?", "expected_sections": ["Section 5", "Registration", "Penalty"], "mode": "LEGAL PRO"},
    {"question": "Can a woman claim her Haq Mehr at the time of Rukhsati?", "expected_sections": ["Dower", "Prompt", "Deferred", "Mehr"], "mode": "GENERAL USER (Woman)"},
    {"question": "What happens if a husband divorces his wife without informing the Union Council?", "expected_sections": ["Section 7", "Invalid", "Notice", "Fine"], "mode": "LEGAL PRO"},
    {"question": "Shohar ne doosri shadi ki ijazat nahi li, kya main court ja sakti hoon?", "expected_sections": ["Section 6", "Permission", "Arbitration", "Criminal"], "mode": "GENERAL USER (Woman)"},

    # --- KHULA, DISSOLUTION & CUSTODY ---
    {"question": "What is the procedure for a woman to obtain Khula through court?", "expected_sections": ["Family Courts Act", "Khula", "Dissolution"], "mode": "GENERAL USER (Woman)"},
    {"question": "Bachon ki custody (Hizanat) ke liye maa ka kya haq hai?", "expected_sections": ["Guardians", "Wards", "Custody", "Hizanat"], "mode": "GENERAL USER (Woman)"},
    {"question": "Can a father stop paying maintenance if the mother remarries?", "expected_sections": ["Maintenance", "Father", "Responsibility", "Minor"], "mode": "LEGAL PRO"},
    {"question": "What is the difference between Khula and Talaq-e-Tafweez?", "expected_sections": ["Dissolution", "Delegated", "Court", "Agreement"], "mode": "LEGAL PRO"},
    {"question": "Court mein Khula ka case kitne arsay mein finalize hota hai?", "expected_sections": ["Family Courts", "Procedure", "Timeline"], "mode": "GENERAL USER (Woman)"},

    # --- INHERITANCE (WIRASAT) ---
    {"question": "How much share does a widow get if she has children?", "expected_sections": ["Inheritance", "Widow", "1/8th", "Share"], "mode": "LEGAL PRO"},
    {"question": "Kya beti ka hissa bete se aadha hota hai Islamic law mein?", "expected_sections": ["Inheritance", "Daughter", "Half", "Succession"], "mode": "GENERAL USER (Woman)"},
    {"question": "If a person dies without any children, who inherits the property?", "expected_sections": ["Residuaries", "Parents", "Spouse", "Succession"], "mode": "LEGAL PRO"},
    {"question": "Can a father disinherit (Aaq) his daughter from his legal property?", "expected_sections": ["Shariah", "Legal", "Heirs", "Invalid"], "mode": "GENERAL USER (Woman)"},
    {"question": "Maa ki property mein bachon ka kitna hissa hota hai?", "expected_sections": ["Mother", "Property", "Heirs", "Succession"], "mode": "GENERAL USER (Woman)"},

    # --- CYBERCRIME (FIA / PECA) ---
    {"question": "Someone is blackmailing me with my pictures on social media, what should I do?", "expected_sections": ["FIA", "Cybercrime", "PECA", "1991"], "mode": "GENERAL USER (Woman)"},
    {"question": "Fake identity bana kar koi tang kar raha hai, kya ye jurm hai?", "expected_sections": ["PECA", "Spoofing", "Identity", "Forgery"], "mode": "GENERAL USER (Woman)"},
    {"question": "What is the punishment for online harassment under PECA 2016?", "expected_sections": ["Section 21", "Imprisonment", "Fine", "Privacy"], "mode": "LEGAL PRO"},
    {"question": "How to file a complaint in FIA Cybercrime wing online?", "expected_sections": ["NR3C", "Portal", "Complaint", "Evidence"], "mode": "GENERAL USER (Woman)"},

    # --- WORKPLACE HARASSMENT (2010 Act) ---
    {"question": "Office mein boss ghalat tareeqay se touch karta hai, kya ye harassment hai?", "expected_sections": ["Section 2", "Harassment", "Workplace"], "mode": "GENERAL USER (Woman)"},
    {"question": "If the office committee is not listening to my harassment complaint, where can I appeal?", "expected_sections": ["Section 8", "Ombudsman", "Mohtasib"], "mode": "GENERAL USER (Woman)"},
    {"question": "What are the major penalties for a harasser under the 2010 Act?", "expected_sections": ["Section 4", "Penalties", "Dismissal"], "mode": "LEGAL PRO"},
    {"question": "Can a domestic worker file a harassment complaint under the 2010 Act?", "expected_sections": ["Workplace", "Definition", "Domestic", "Employee"], "mode": "LEGAL PRO"},
    {"question": "What is the timeline for the Inquiry Committee to decide a case?", "expected_sections": ["30 days", "Procedure", "Inquiry"], "mode": "LEGAL PRO"},
    {"question": "Agar company harassment policy display na kare toh kya fine hai?", "expected_sections": ["Display", "Code of Conduct", "Penalty"], "mode": "LEGAL PRO"}
]

def run_accuracy_test():
    configure_gemini()
    print(f"🚀 Starting Awaz-e-Nisa Extended Accuracy Test ({len(test_dataset)} Queries)...\n")
    results = []
    total_score = 0

    for i, test in enumerate(test_dataset):
        print(f"Testing Query {i+1}/{len(test_dataset)}: {test['question'][:50]}...")
        
        success = False
        attempts = 0
        
        while not success and attempts < len(API_KEYS):
            try:
                start_time = time.time()
                
                # A. Test Retrieval (ChromaDB check)
                docs = retriever.invoke(test["question"])
                retrieval_success = len(docs) > 0

                # B. Test Generation (Gemini check)
                response = rag_chain.invoke({"question": test["question"], "mode": test["mode"]})
                
                end_time = time.time()

                # C. Scoring Logic
                matched_keywords = [word for word in test["expected_sections"] if word.lower() in response.lower()]
                accuracy_score = len(matched_keywords) / len(test["expected_sections"])
                
                results.append({
                    "No": i+1,
                    "Question": test["question"][:40] + "...",
                    "Retrieval": "✅ OK" if retrieval_success else "❌ FAIL",
                    "Accuracy %": round(accuracy_score * 100, 2),
                    "Time (s)": round(end_time - start_time, 2)
                })
                
                total_score += accuracy_score
                success = True # Mark as successful to move to next query
                print(f"   ↳ Result: {round(accuracy_score * 100, 2)}% Accuracy")
                
                # Wait to stay within Rate Limits (Requests Per Minute)
                time.sleep(5) 

            except Exception as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    print(f"⚠️ Quota Exhausted for Key {current_key_index}. Rotating...")
                    rotate_api_key()
                    attempts += 1
                else:
                    print(f"❌ Unexpected Error: {e}")
                    # Error record karke aage barhein
                    results.append({"No": i+1, "Question": test["question"][:40], "Retrieval": "❌ ERR", "Accuracy %": 0.0, "Time (s)": 0})
                    success = True 

    # --- FINAL REPORT GENERATION ---
    df = pd.DataFrame(results)
    print("\n" + "="*70)
    print("📊 FINAL SYSTEM PERFORMANCE REPORT (30 QUERIES)")
    print("="*70)
    print(df.to_string(index=False))
    
    final_avg = (total_score / len(test_dataset)) * 100
    avg_time = sum([r["Time (s)"] for r in results if r["Time (s)"] > 0]) / len(results)

    print("\n" + "="*70)
    print(f"🏆 OVERALL SYSTEM ACCURACY: {round(final_avg, 2)}%")
    print(f"⏱️ AVERAGE RESPONSE TIME: {round(avg_time, 2)} seconds")
    print("="*70)

if __name__ == "__main__":
    run_accuracy_test()