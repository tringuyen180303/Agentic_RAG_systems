from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain.chains import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain.chat_models import ChatOpenAI
import httpx, os
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain.chains import RetrievalQA
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from langchain_tavily import TavilySearch
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain.tools import Tool
from langchain.agents import initialize_agent, AgentType
from langchain.memory import ConversationBufferMemory
from .rule_book import rulebook_tool


from .settings import get_settings
from dotenv import load_dotenv
import os
load_dotenv()  # load environment variables from .env file
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["HUGGINGFACE_API_KEY"] = os.getenv("HUGGINGFACE_API_KEY")
S = get_settings()

# --------------------------------------------------------------------- #
#  Initialise once per worker                                           #
# --------------------------------------------------------------------- #

# 1) vector store client (points at the Chroma container)

#embeddings = HuggingFaceEmbeddings(model_name=S.embed_model)
embeddings = HuggingFaceEmbeddings(model_name="models/all-MiniLM-L6-v2")  # local model
import chromadb
# client = chromadb.HttpClient(host="localhost", port=8000)   # service name in compose

CHROMA_HOST = os.getenv("CHROMA_HOST", "chroma")   # <- service name in docker-compose.yml
CHROMA_PORT = int(os.getenv("CHROMA_PORT", 8000))
client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
collection = client.get_collection("docs")

vectordb = Chroma(
    client=client,
    collection_name="docs",
    embedding_function=embeddings,
)


http_client = httpx.Client(base_url=S.ollama_url, timeout=30.0,
                           headers={"Connection": "keep-alive"})
base_retriever = vectordb.as_retriever(search_kwargs={"k": 5})
#cross_encoder = HuggingFaceCrossEncoder(model_name= "BAAI/bge-reranker-large")
#cross_encoder = HuggingFaceCrossEncoder(model_name="models/bge-reranker-large")# local model
cross_encoder = HuggingFaceCrossEncoder(model_name="models/bge-reranker-large")  # remote model
compressor = CrossEncoderReranker(model=cross_encoder, top_n=4)
compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=base_retriever,
)

SYSTEM_PROMPT = """
    You are a flow-meter configuration assistant.

┌─  Tool rules ────────────────────────────────────────────┐
│ 1. **Spec questions** → call **LocalDocs** first.        │
│    • If LocalDocs returns data, answer immediately and   │
│      cite the source files.                              │
│ 2. **Model-code validation** → call **RuleBook**.        │
│    • If RuleBook returns {"valid": true}                 │
│        → Final Answer: ✅ The model code is VALID.        │
│    • If it returns {"valid": false, "errors": [...],     │
│      "suggestions": [...]}                               │
│        → Final Answer: ❌ INVALID.                       │
│          Reason(s): <errors>.                            │
│          Suggested fix: <suggestions>.                   │
│ 3. If neither tool can answer, call **WebSearch**.       │
└──────────────────────────────────────────────────────────┘

After you output the line that starts with “Final Answer:” you must not call
any more tools.
"""


llm = ChatOllama(
    model=S.model_name,
    temperature=0.1,
    max_tokens=1024,          # cap response
    streaming=True,
    http_client=http_client, # NEW in langchain 0.1.20
    base_url=S.ollama_url,   # pass through for clarity
)

def ask_local_rag(question: str) -> str:
        """RAG over local PDFs. Returns the answer plus sources."""
        out = qa_chain.invoke({"query": question})
        answer = out["result"]
        sources = "\n".join(f"- {d.metadata['source_file']}" for d in out["source_documents"])
        return f"{answer}\n\nSOURCES:\n{sources}"

search_api = TavilySearch(top_k=5)

def ask_web(question: str) -> str:
    """1-shot web search + LLM summarisation."""
    model_generated_tool_call = {
        "args": {"query": question},
        "id": "5",
        "name": "tavily",
        "type": "tool_call",
    }
    tool_msg = search_api.invoke(model_generated_tool_call)
    return tool_msg.content 
tools = [
    Tool(
    name="LocalDocs",
    func=ask_local_rag,
    description="Use this for questions answerable from the company's PDFs."
),
rulebook_tool, # Custom rulebook tool

Tool(
    name="WebSearch",
    func=ask_web,
    description="Use this only when LocalDocs is insufficient."
)
    
]

memory = ConversationBufferMemory(return_messages=True)
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    max_iterations=3,
    early_stopping_method="generate",
    # memory=memory,
)


# OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
# llm = ChatOpenAI(
#     model_name="gpt-4o-mini",                    # switch to GPT-4
#      temperature=0.1,
#      max_tokens=512,
#      streaming=True,                        # or False if you want the full response at once
# )

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=compression_retriever,
    return_source_documents=True,
)
