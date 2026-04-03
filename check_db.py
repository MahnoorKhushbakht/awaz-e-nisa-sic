from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

DB_PATH = "db/awaz_e_nisa_db"
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)


collection = vectorstore.get()
total_chunks = len(collection['ids'])

print(f"✅ Total Chunks in Database: {total_chunks}")
if total_chunks > 0:
    print("🚀 Data successfully loaded from 164 files!")
else:
    print("❌ Database is empty!")