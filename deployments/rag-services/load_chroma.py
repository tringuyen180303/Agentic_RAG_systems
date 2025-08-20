#!/usr/bin/env python3
# 
import os, time, chromadb
from dotenv import load_dotenv
import os
import time
import requests
import chromadb
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# load CHROMA_HOST, CHROMA_PORT from env
host = os.getenv("CHROMA_HOST", "chroma-svc")
port = int(os.getenv("CHROMA_PORT", "8000"))

# wait for the HTTP server
while True:
    try:
        import requests
        r = requests.get(f"http://{host}:{port}/health", timeout=2)
        if r.status_code == 200:
            break
    except:
        pass
    print("Waiting for Chroma to become healthy…")
    time.sleep(2)



# ────────────────────────────────────────────────────────────────────
# Config
# ────────────────────────────────────────────────────────────────────
load_dotenv()  # if you mount a .env; otherwise defaults below
CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma-svc")
CHROMA_PORT = int(os.getenv("CHROMA_PORT", "8000"))
DOCS_DIR    = os.getenv("DOCS_DIR", "/docs")
COLLECTION  = os.getenv("COLLECTION_NAME", "docs")

# ────────────────────────────────────────────────────────────────────
# 1) wait for Chroma HTTP to be healthy
# ────────────────────────────────────────────────────────────────────
health_url = f"http://{CHROMA_HOST}:{CHROMA_PORT}/health"
print(f"[loader] waiting for Chroma at {health_url} …", end="", flush=True)
while True:
    try:
        r = requests.get(health_url, timeout=2)
        if r.status_code == 200:
            print(" OK")
            break
    except requests.RequestException:
        pass
    print(".", end="", flush=True)
    time.sleep(2)

# ────────────────────────────────────────────────────────────────────
# 2) load all documents from DOCS_DIR
# ────────────────────────────────────────────────────────────────────
print(f"[loader] loading documents from {DOCS_DIR}")
documents = []
for fn in os.listdir(DOCS_DIR):
    path = os.path.join(DOCS_DIR, fn)
    if fn.lower().endswith(".pdf"):
        pages = PyPDFLoader(path).load()
    elif fn.lower().endswith(".txt"):
        pages = TextLoader(path, encoding="utf-8").load()
    else:
        continue
    for p in pages:
        p.metadata["source_file"] = fn
    documents.extend(pages)
print(f"[loader] found {len(documents)} pages")

# ────────────────────────────────────────────────────────────────────
# 3) split into chunks
# ────────────────────────────────────────────────────────────────────
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks   = splitter.split_documents(documents)
print(f"[loader] split into {len(chunks)} chunks")

# ────────────────────────────────────────────────────────────────────
# 4) set up embeddings + chroma HTTP client
# ────────────────────────────────────────────────────────────────────
embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
client   = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# ────────────────────────────────────────────────────────────────────
# 5) ensure collection exists
# ────────────────────────────────────────────────────────────────────
try:
    client.get_collection(COLLECTION)
    print(f"[loader] collection “{COLLECTION}” already exists")
except chromadb.errors.NotFoundError:
    client.create_collection(COLLECTION)
    print(f"[loader] created collection “{COLLECTION}”")

# ────────────────────────────────────────────────────────────────────
# 6) wrap in LangChain + upsert
# ────────────────────────────────────────────────────────────────────
vectorstore = Chroma(
    client=client,
    collection_name=COLLECTION,
    embedding_function=embedder,
)

texts     = [c.page_content for c in chunks]
ids       = [f"{c.metadata['source_file']}-{i}" for i, c in enumerate(chunks)]
metas     = [c.metadata for c in chunks]

print(f"[loader] upserting {len(texts)} chunks …")
vectorstore.add_texts(texts=texts, ids=ids, metadatas=metas)

# ────────────────────────────────────────────────────────────────────
# 7) done
# ────────────────────────────────────────────────────────────────────
count = client.get_collection(COLLECTION).count()
print(f"[loader] done, collection “{COLLECTION}” now has {count} items")

