import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings  # <— new import path
from langchain_community.chat_models import ChatOllama   # <— local LLM
from langchain.chains import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_tavily import TavilySearch
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
print("Loading PDFs and text files from docs directory...")
docs_dir = "docs"
documents = []


for filename in os.listdir(docs_dir):
    fpath = os.path.join(docs_dir, filename)

    if filename.lower().endswith(".pdf"):
        pages = PyPDFLoader(fpath).load()          # binary PDF parser
    elif filename.lower().endswith(".txt"):
        pages = TextLoader(fpath, encoding="utf-8").load()  # plain text
    else:
        continue                                   # ignore other files

    for p in pages:
        p.metadata["source_file"] = filename
    documents.extend(pages)
print(f"Loaded {len(documents)} pages\n")

# Split into overlapping chunks
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks   = splitter.split_documents(documents)
print(f"Created {len(chunks)} text chunks\n")

# Vector DB (FAISS‑backed Chroma) with local HF embeddings
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
# if os.path.exists("vectorstore"):
#     print("Loading existing Chroma vector store …")
#     vectorstore = Chroma(persist_directory="vectorstore", embedding_function=embeddings)
# else:
print("Building / loading Chroma vector store …")
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="vectorstore"
)
# `.persist()` is automatic for Chroma ≥ 0.4, but harmless:
vectorstore.persist()
import chromadb
from langchain_chroma import Chroma
from langchain.embeddings import HuggingFaceEmbeddings

# 1) Embedder
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

# 2) Raw HTTP Chroma client
client = chromadb.HttpClient(host="localhost", port=8000)

# 3) (Re)create the collection
try:
    client.get_collection("docs")
except chromadb.errors.NotFoundError:
    client.create_collection("docs")

# 4) LangChain wrapper
vectorstore = Chroma(
    client=client,
    collection_name="docs",
    embedding_function=embeddings,
)

# 5) Prepare your chunks
texts     = [c.page_content for c in chunks]
ids       = [f"{c.metadata['source_file']}-{i}" for i, c in enumerate(chunks)]
metadatas = [c.metadata       for c in chunks]

# 6) Upsert into Chroma
vectorstore.add_texts(
    texts=texts,
    ids=ids,
    metadatas=metadatas,
)

# 7) (Optional) verify
stats = client.heartbeat()  # or client.get_collection("docs").count()
print(f"Pushed {len(texts)} chunks into Chroma.")



import chromadb

# 1) connect to your running Chroma server
client = chromadb.HttpClient(host="localhost", port=8000)

# 2) pull back the list of collections
#    as of chromadb v0.4+, this is `list_collections()`
collections = client.list_collections()

# 3) print them out
if not collections:
    print("🚫 no collections found")
else:
    print("📚 collections:")
    for col in collections:
        # each item is a dict with at least a 'name' key
        print(col)


