from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# 1. Database Path
DB_PATH = "db/awaz_e_nisa_db"

# 2. Embeddings model (same as before)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 3. Load the vector database
db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

# 4. Test Query
query = "What does the law say about khula or child custody?" 

print(f"\nSearching for: {query}")
docs = db.similarity_search(query, k=2) # Top 2 results

print("\n--- AI Ne Ye Dhoonda Hai ---")
for i, doc in enumerate(docs):
    print(f"\nResult {i+1} from {doc.metadata.get('source', 'Unknown')}:")
    print("-" * 30)
    print(doc.page_content[:500] + "...") # First 500 characters