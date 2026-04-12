import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv

load_dotenv()

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
llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.1)

def retrieve_context(inputs):
    query = inputs if isinstance(inputs, str) else inputs.get("question", "")
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

STRICT INSTRUCTIONS:
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

INSTRUCTIONS:
1. LANGUAGE: Identify the language of the USER QUERY. Reply ONLY in that same language (Roman Urdu or English).
2. YOU MUST CITE SPECIFIC SECTIONS.
3. Section 1: **Legal Merits (Strengths)**
4. Section 2: **Potential Demerits (Weaknesses)**
""")
merits_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | merits_prompt | llm | StrOutputParser())

# 2. Opposition Arguments
opp_prompt = ChatPromptTemplate.from_template("""
Predict arguments the opposing party will raise in this Pakistani legal scenario.
USER QUERY: {question}
CONTEXT FROM DATABASE: {context}

INSTRUCTIONS:
- LANGUAGE: Reply ONLY in the SAME language as the user query (Roman Urdu or English).
- Use the context to find potential legal loopholes they might use.
""")
opposition_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | opp_prompt | llm | StrOutputParser())

# 3. Timeline
time_prompt = ChatPromptTemplate.from_template("""
Provide an estimated timeline for this case based on Pakistani court procedures.
USER QUERY: {question}
CONTEXT FROM DATABASE: {context}

INSTRUCTIONS:
- LANGUAGE: Reply ONLY in the SAME language as the user query (Roman Urdu or English).
- Mention stages like Summoning, Evidence, and Final Arguments.
""")
timeline_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | time_prompt | llm | StrOutputParser())

# 4. Legal Draft
draft_prompt = ChatPromptTemplate.from_template("""
Create a formal legal notice or petition draft for this issue.
USER QUERY: {question}
CONTEXT FROM DATABASE: {context}

INSTRUCTIONS:
1. LEGAL DRAFT: Always write the actual draft in FORMAL ENGLISH (Standard for Pakistan Courts).
2. BRIEF SUMMARY: Provide a 2-line explanation in the SAME LANGUAGE as the user query (Roman Urdu or English).
""")
draft_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | draft_prompt | llm | StrOutputParser())