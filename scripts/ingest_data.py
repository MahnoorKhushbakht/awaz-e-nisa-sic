import os
import shutil
from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Paths - Absolute paths for stability
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(BASE_DIR, "db", "awaz_e_nisa_db")

def build_vector_db():
    print(f"--- Starting Ingestion Pipeline (Deep Scan Mode) ---")
    
    # 1. Validation
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: '{DATA_PATH}' folder not found!")
        return

    # Deep scan for validation print
    all_pdfs = []
    for root, dirs, files in os.walk(DATA_PATH):
        for file in files:
            if file.lower().endswith(".pdf"):
                all_pdfs.append(os.path.join(root, file))

    if not all_pdfs:
        print(f"⚠️ Warning: No PDF files found in {DATA_PATH} or its sub-folders!")
        return
    else:
        print(f"📂 Found {len(all_pdfs)} PDFs across all nested folders.")

    # 2. Loading PDFs Recursively
    print("Step 1: Loading & Pre-processing documents (Recursive)...")
    try:
        # glob="**/*.pdf" + recursive=True is the key for nested folders
        loader = DirectoryLoader(
            DATA_PATH, 
            glob="**/*.pdf", 
            loader_cls=PyPDFLoader,
            recursive=True,
            show_progress=True
        )
        documents = loader.load()
    except Exception as e:
        print(f"❌ Error during loading: {e}")
        return

    if not documents:
        print("❌ Error: Could not extract text. Check if PDFs are scanned images.")
        return

    # Metadata Enrichment
    for doc in documents:
        source_path = doc.metadata.get("source", "Unknown")
        doc.metadata["file_name"] = os.path.basename(source_path)
        doc.page_content = " ".join(doc.page_content.split())

    print(f"✅ Total Pages Processed: {len(documents)}")

    # 3. Strategic Chunking
    print("Step 2: Strategic Chunking (Recursive Splitting)...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, 
        chunk_overlap=150,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    splits = text_splitter.split_documents(documents)
    print(f"✅ Created {len(splits)} optimized chunks.")

    # 4. Neural Embeddings
    print("Step 3: Generating Neural Embeddings (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

    # 5. Saving to ChromaDB
    print("Step 4: Saving to ChromaDB...")
    
    if os.path.exists(DB_PATH):
        print("🧹 Cleaning old database for fresh start...")
        shutil.rmtree(DB_PATH)

    try:
        vector_db = Chroma.from_documents(
            documents=splits, 
            embedding=embeddings, 
            persist_directory=DB_PATH
        )
        print(f"🚀 SUCCESS: Database saved at {DB_PATH}")
    except Exception as e:
        print(f"❌ Error saving to ChromaDB: {e}")

if __name__ == "__main__":
    build_vector_db()