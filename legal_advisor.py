import os
import streamlit as st
from dotenv import load_dotenv

# 1. SQLite Fix (Zaroori hai taake Streamlit Cloud par ChromaDB crash na kare)
try:
    __import__('pysqlite3')
    import sys
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
    pass

api_key = st.secrets.get("GOOGLE_API_KEY")

# --- LangChain Imports ---
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

DB_PATH = "db/awaz_e_nisa_db"
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

try:
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5}) 
except Exception as e:
    print(f"Warning: Could not load vectorstore: {e}")
    class DummyRetriever:
        def invoke(self, *args, **kwargs): return []
    retriever = DummyRetriever()

# --- LLM CONFIGURATION ---
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.1, google_api_key=api_key)

# --- QUERY RELEVANCE CHECK FUNCTION ---
def is_legal_query(query: str) -> bool:
    """Check if query is related to Pakistani law/legal matters"""
    legal_keywords = [
        # Family Law - Urdu/Roman
        "shadi", "nikah", "talaq", "divorce", "khula", "haq mehr", "mehr",
        "husband", "wife", "shohar", "biwi", "second marriage", "dusri shadi",
        "child custody", "bachon ki parwarish", "guardian", "wali", "bachay",
        
        # Financial Rights
        "maintenance", "kharcha", "nan nafqa", "property", "jayedad", 
        "inheritance", "wirasat", "haq", "rights", "huqooq", "jahez",
        
        # Harassment & Violence
        "harassment", "harrasment", "abuse", "violence", "tashadud", 
        "domestic violence", "gharelu tashadud", "assault", "stalking", "mar peet",
        
        # Cyber Crime
        "cyber", "online", "blackmail", "bheek", "fia", "peca", "internet",
        "whatsapp", "facebook", "instagram", "digital", "privacy", "parcha",
        "fake id", "fake account",
        
        # Legal Terms
        "police", "pulis", "court", "adalat", "case", "muqadma", "law", "qanoon",
        "lawyer", "wakil", "petition", "draft", "notice", "complaint", "shikayat",
        "sentence", "saza", "fine", "jurmanah", "arrest", "giraftari", "jail",
        "appeal", "dafi", "section", "dafa",
        
        # Laws & Acts
        "mflo", "peca", "fcr", "ppc", "crpc", "qanoon-e-shahadat",
        "protection against harassment", "domestic violence act",
        
        # General Legal Questions
        "legal", "right", "huqooq", "act", "article", "constitution", "ain",
        "punjab", "sindh", "kpk", "pakistan", "islamabad",
        
        # Urdu/Roman Urdu common legal question starters
        "kya main", "kya mein", "kya mujhe", "can i", "can my",
        "is it legal", "kya yeh", "is this", "what should i", "mujhe kya",
        "kaise karein", "how to file", "where to report", "kis se rabta",
        "mujhe kya karna chahiye", "mera haq", "kya kar sakta hoon"
    ]
    
    query_lower = query.lower()
    
    # Check legal keywords
    for keyword in legal_keywords:
        if keyword in query_lower:
            return True
    
    # Reject very short queries (less than 3 words)
    words = query_lower.split()
    if len(words) < 3:
        return False
    
    return False

def retrieve_context(inputs):
    query = inputs if isinstance(inputs, str) else inputs.get("question", "")
    
    # Check if query is legal
    if not is_legal_query(query):
        print(f"\n⚠️ RELEVANCE CHECK: Non-legal query rejected: '{query}'")
        return "NON_LEGAL_QUERY"
    
    docs = retriever.invoke(query)
    
    print("\n" + "="*50)
    print(f"🔍 RAG DEBUG: Searching for: '{query}'")
    print(f"📚 DATABASE: Found {len(docs)} relevant snippets.")
    print("="*50 + "\n")
    
    if not docs:
        return "No specific legal context found for this exact query."
    return "\n\n".join(doc.page_content.strip() for doc in docs)

# --- 1. MAIN RAG CHAIN ---

main_prompt = ChatPromptTemplate.from_template("""
You are Awaz-e-Nisa, a highly accurate Legal AI Assistant for Pakistan. 
Your goal is to provide legally sound advice using ONLY the provided context.

CONTEXT FROM DATABASE:
{context}

USER QUERY: {question}
MODE: {mode}

⚠️ CRITICAL INSTRUCTION - READ FIRST:
If the context says "NON_LEGAL_QUERY", you MUST respond with EXACTLY this message and NOTHING ELSE:
"I am a legal AI assistant specialized ONLY in Pakistani law. I cannot answer non-legal questions. Please ask me a legal question about your rights under Pakistani law."

Do NOT add any additional information, examples, legal tips, helplines, or anything else. Just this exact message.

STRICT INSTRUCTIONS FOR LEGAL QUERIES:
1. LANGUAGE MATCH: Identify the language of the USER QUERY. If it is Roman Urdu, you MUST reply in Roman Urdu. If it is English, you MUST reply in English. Do not mix languages unless necessary for technical terms.
2. CITATION: You MUST mention specific Section numbers and Law names (e.g., Section 7 of MFLO 1961) if they are in the context.
3. GROUNDING & HALLUCINATION CONTROL: 
   - Answer ONLY based on the provided context. 
   - If the context does not contain a specific court decision or final verdict for a case mentioned, DO NOT make one up. 
   - Explicitly state: "The final court decision for this specific case is not available in the provided legal records."
4. ROMAN URDU GLOSSARY: 
   - 'Haq-e-Talaq-e-Tafweez' = Delegated right of divorce (MFLO Section 8).
   - 'Kharcha' / 'Nan-Nafqa' = Maintenance (MFLO Section 9).
   - 'Dusri Shadi' = Polygamy rules (MFLO Section 6).
   - 'Wirasat' = Succession/Inheritance (MFLO Section 4).
5. TONE:
   - 'GENERAL USER (Woman)': Empathetic + Simple Law explanation + MUST include Section numbers.
   - 'LEGAL PRO': Technical + Law Citations + No empathy.

ALWAYS end 'GENERAL USER' responses with this list:
* FIA Cybercrime: 1991
* Ministry of Human Rights: 1099
* Women Safety (Police): 15
* Digital Rights Foundation: 0800-39393
""")

rag_chain = (
    {
        "context": RunnableLambda(retrieve_context),
        "question": lambda x: x["question"],
        "mode": lambda x: x["mode"]
    }
    | main_prompt 
    | llm 
    | StrOutputParser()
)

# --- ANALYSIS CHAINS ---

# 1. Case Merits
merits_prompt = ChatPromptTemplate.from_template("""
Analyze the legal strength (merits) and weaknesses (demerits) based on Pakistani law.

USER QUERY: {question}
CONTEXT: {context}

⚠️ IMPORTANT: If the context says "NON_LEGAL_QUERY", respond with EXACTLY: "SKIP_ANALYSIS"

INSTRUCTIONS FOR LEGAL QUERIES:
1. LANGUAGE: Identify the language of the USER QUERY. Reply ONLY in that same language (Roman Urdu or English).
2. YOU MUST CITE SPECIFIC SECTIONS.
3. Section 1: **Legal Merits (Strengths)**
4. Section 2: **Potential Demerits (Weaknesses)**
""")

def merits_wrapper(query):
    if not is_legal_query(query):
        return "SKIP_ANALYSIS"
    context = retrieve_context(query)
    if context == "NON_LEGAL_QUERY":
        return "SKIP_ANALYSIS"
    return (merits_prompt | llm | StrOutputParser()).invoke({"question": query, "context": context})

merits_chain = RunnableLambda(merits_wrapper)

# 2. Opposition Arguments
opp_prompt = ChatPromptTemplate.from_template("""
Predict arguments the opposing party will raise in this Pakistani legal scenario.

USER QUERY: {question}
CONTEXT FROM DATABASE: {context}

⚠️ IMPORTANT: If the context says "NON_LEGAL_QUERY", respond with EXACTLY: "SKIP_ANALYSIS"

INSTRUCTIONS FOR LEGAL QUERIES:
- LANGUAGE: Reply ONLY in the SAME language as the user query (Roman Urdu or English).
- Use the context to find potential legal loopholes they might use.
""")

def opposition_wrapper(query):
    if not is_legal_query(query):
        return "SKIP_ANALYSIS"
    context = retrieve_context(query)
    if context == "NON_LEGAL_QUERY":
        return "SKIP_ANALYSIS"
    return (opp_prompt | llm | StrOutputParser()).invoke({"question": query, "context": context})

opposition_chain = RunnableLambda(opposition_wrapper)

# 3. Timeline
time_prompt = ChatPromptTemplate.from_template("""
Provide an estimated timeline for this case based on Pakistani court procedures.

USER QUERY: {question}
CONTEXT FROM DATABASE: {context}

⚠️ IMPORTANT: If the context says "NON_LEGAL_QUERY", respond with EXACTLY: "SKIP_ANALYSIS"

INSTRUCTIONS FOR LEGAL QUERIES:
- LANGUAGE: Reply ONLY in the SAME language as the user query (Roman Urdu or English).
- Mention stages like Summoning, Evidence, and Final Arguments.
""")

def timeline_wrapper(query):
    if not is_legal_query(query):
        return "SKIP_ANALYSIS"
    context = retrieve_context(query)
    if context == "NON_LEGAL_QUERY":
        return "SKIP_ANALYSIS"
    return (time_prompt | llm | StrOutputParser()).invoke({"question": query, "context": context})

timeline_chain = RunnableLambda(timeline_wrapper)

# 4. Legal Draft
draft_prompt = ChatPromptTemplate.from_template("""
Create a formal legal notice or petition draft for this issue.

USER QUERY: {question}
CONTEXT FROM DATABASE: {context}

⚠️ IMPORTANT: If the context says "NON_LEGAL_QUERY", respond with EXACTLY: "SKIP_ANALYSIS"

INSTRUCTIONS FOR LEGAL QUERIES:
1. LEGAL DRAFT: Always write the actual draft in FORMAL ENGLISH (Standard for Pakistan Courts).
2. BRIEF SUMMARY: Provide a 2-line explanation in the SAME LANGUAGE as the user query (Roman Urdu or English).
""")

def draft_wrapper(query):
    if not is_legal_query(query):
        return "SKIP_ANALYSIS"
    context = retrieve_context(query)
    if context == "NON_LEGAL_QUERY":
        return "SKIP_ANALYSIS"
    return (draft_prompt | llm | StrOutputParser()).invoke({"question": query, "context": context})

draft_chain = RunnableLambda(draft_wrapper)


is_legal_query = is_legal_query