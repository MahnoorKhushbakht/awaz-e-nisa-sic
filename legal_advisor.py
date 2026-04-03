import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_chroma import Chroma
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

llm = ChatGoogleGenerativeAI(model="gemini-3-flash-preview", temperature=0.2)

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
You are Awaz-e-Nisa, an expert legal AI assistant for Pakistan.

CONTEXT FROM DATABASE:
{context}

USER QUERY: {question}
MODE: {mode}

INSTRUCTIONS:
1. Primary Goal: Use the CONTEXT to provide specific legal advice according to Pakistani Law.
2. If the context is empty or doesn't fully cover the query, use your general knowledge of Pakistani Law (Constitution, PPC, Family Laws) to help the user. Do NOT say 'outside knowledge base' unless the query is completely unrelated to Law (e.g., cooking, sports).
3. LANGUAGE: Match the user's language. If they use Roman Urdu, reply in Roman Urdu only.
4. TONE:
   - 'GENERAL USER (Woman)': Start with a very kind, empathetic acknowledgement of their situation. Explain legal rights in simple terms.
   - 'LEGAL PRO': Be technical, use Section numbers, and skip empathy.

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

# --- ANALYSIS CHAINS (Slightly relaxed for better results) ---

merits_prompt = ChatPromptTemplate.from_template("Analyze the legal strength (merits) of this situation based on Pakistani law: {question}\nContext: {context}")
merits_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | merits_prompt | llm | StrOutputParser())

opp_prompt = ChatPromptTemplate.from_template("What arguments could the opposing party raise in this Pakistani legal scenario: {question}\nContext: {context}")
opposition_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | opp_prompt | llm | StrOutputParser())

time_prompt = ChatPromptTemplate.from_template("Based on typical Pakistani court procedures, what is the estimated timeline for: {question}\nContext: {context}")
timeline_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | time_prompt | llm | StrOutputParser())

draft_prompt = ChatPromptTemplate.from_template("Create a formal legal notice or petition draft in English for this issue: {question}\nContext: {context}. Also provide a brief explanation in the user's language.")
draft_chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} | draft_prompt | llm | StrOutputParser())