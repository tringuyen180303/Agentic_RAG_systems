# rag_service/api.py
from datetime import datetime
import os, uuid
from typing import Optional, Dict, Any

from fastapi import FastAPI, APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from langfuse import Langfuse, observe, get_client
from .rag import qa_chain, agent   # ← your chain import
from collections import defaultdict
from .guardrails import guardrails, GuardrailViolationType
from prometheus_fastapi_instrumentator import Instrumentator
load_dotenv()

# ────────────────────────────────────────────────────────────────────────────
# Langfuse client
# ────────────────────────────────────────────────────────────────────────────
langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST", "http://langfuse-web:3000"),
)

# ────────────────────────────────────────────────────────────────────────────
# FastAPI objects
# ────────────────────────────────────────────────────────────────────────────
app    = FastAPI(title="RAG-as-a-Service")

Instrumentator(
    should_group_status_codes=True,      # e.g. 2xx, 4xx, 5xx
    should_ignore_untemplated=False,      # skip dynamic URLs
    should_respect_env_var=False,         # can disable via env var
).instrument(app).expose(app, include_in_schema=False, endpoint="/metrics")
router = APIRouter()
# ────────────────────────────────────────────────────────────────────────────
# Pydantic model
# ────────────────────────────────────────────────────────────────────────────
class RetrievalInput(BaseModel):
    query: str = Field(..., example="Explain the MN-vane code")
    user_id: Optional[str]    = Field(None, description="Unique user identifier")
    session_id: Optional[str] = Field(None, description="Conversation/session ID")
    metadata: Dict[str, Any]  = Field(default_factory=dict)

# ────────────────────────────────────────────────────────────────────────────
# Helper: generate safe defaults
# ────────────────────────────────────────────────────────────────────────────
def _default_ids(u: Optional[str], s: Optional[str]) -> tuple[str, str]:
    user_id    = u or f"anon_{uuid.uuid4().hex[:8]}"
    session_id = s or f"sess_{uuid.uuid4().hex[:8]}"
    return user_id, session_id

# ────────────────────────────────────────────────────────────────────────────
# Blocking RAG endpoint
# ────────────────────────────────────────────────────────────────────────────
@router.post("/rag", response_model=dict)
@observe(name="rag_blocking")   # Langfuse decorator
async def rag_block(
    req: RetrievalInput,
    x_user_id:    Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
):
    # 1️⃣  Resolve identifiers (body → header → generated)
    user_id, session_id = _default_ids(
        req.user_id or x_user_id,
        req.session_id or x_session_id,
    )
    langfuse = get_client()

    with langfuse.start_as_current_span(
        name="rag_request",
    ) as root_span:
        #root_span.update_current_trace(user_id=user_id, session_id=session_id)
        with root_span.start_as_current_generation(
            name="qa_chain.invoke",
            input={"query": req.query},
        ) as gen_span:
            gen_span.update(input={"query": req.query})
            out     = qa_chain.invoke({"query": req.query})
            answer  = out["result"]
            sources = [d.metadata.get("source_file") for d in out["source_documents"]]
            gen_span.update_trace(
                input=req.query,
                output=answer,
                user_id=user_id,
                session_id=session_id,
                metadata={"email": "tri@langfuse.com"},
                version="1.0.0"
                )
    return{"answer": answer, "sources": sources, "user_id": user_id, "session_id": session_id}


### ────────────────────────────────────────────────────────────────────────────
# RAG with gurardrails
# ────────────────────────────────────────────────────────────────────────────
@router.post("/rag_guarded", response_model=dict)
@observe(name="rag_guarded")
async def rag_guarded(
    req: RetrievalInput,
    x_user_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
):
    # 1️⃣ Resolve identifiers (body → header → generated)
    
    user_id, session_id = _default_ids(
        req.user_id or x_user_id,
        req.session_id or x_session_id,
    )
    langfuse_client = get_client()

    with langfuse_client.start_as_current_span(
        name="rag_guarded_request",
    ) as root_span:
        
        # 2️⃣ Query guardrail check
        with root_span.start_as_current_span(name="query_guardrail_check") as query_guard_span:
            should_block, query_violations = guardrails.scan_query(req.query, user_id)
            query_guard_span.update(
                input={"query": req.query, "query_length": len(req.query)},
                output={
                    "should_block": should_block, 
                    "violations_count": len(query_violations), 
                    "violation_types": [v.type.value for v in query_violations]
                }
            )
            
            if should_block:
                error_message = guardrails.get_safe_error_message(query_violations)
                query_guard_span.update_trace(
                    input=req.query,
                    output=error_message,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "email": "tri@langfuse.com"
                    }
                )
                return {
                    "answer": error_message

                }
                # raise HTTPException(
                #     status_code=400,
                #     detail={
                #         "error": "Guardrail Violation",
                #         "message": error_message,
                #         "status": "blocked",
                #     }
                # )
        
        # 3️⃣ RAG chain execution
        with root_span.start_as_current_generation(
            name="qa_chain.invoke",
            input={"query": req.query},
        ) as gen_span:
            out = qa_chain.invoke({"query": req.query})
            raw_answer = out["result"]
            sources = [d.metadata.get("source_file") for d in out["source_documents"]]
            
            gen_span.update(
                input={"query": req.query},
                output={"raw_answer_length": len(raw_answer), "sources_count": len(sources)}
            )
        
        # 4️⃣ Response guardrail check
        with root_span.start_as_current_span(name="response_guardrail_check") as resp_span:
            sanitized_answer, response_violations = guardrails.scan_response(
                raw_answer, sources, user_id
            )
            
            # Check if content was actually filtered
            content_was_filtered = raw_answer != sanitized_answer or len(response_violations) > 0
            all_violations = query_violations + response_violations
            
            # Generate warnings
            warnings = []
            if content_was_filtered:
                warnings.append("Content was filtered by guardrails for security and privacy.")
            
            resp_span.update(
                input={"raw_answer_length": len(raw_answer)},
                output={
                    "sanitized_answer_length": len(sanitized_answer),
                    "response_violations_found": len(response_violations),
                    "content_filtered": content_was_filtered,
                    "total_violations": len(all_violations)
                }
            )
        
        # 5️⃣ Update main generation trace
        gen_span.update_trace(
            input=req.query,
            output=sanitized_answer,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "email": "tri@langfuse.com",
                "version": "1.0.0",
                "guardrails_enabled": True,
                "total_violations_detected": len(all_violations),
                "content_filtered": content_was_filtered,
                "safety_status": "safe" if not all_violations else "filtered"
            }
        )
        
        # 6️⃣ Return response
        return {
            "answer": sanitized_answer,
            "sources": sources,
            "user_id": user_id,
            "session_id": session_id,
            "safety_status": "safe" if not all_violations else "filtered",
            "warnings": warnings if warnings else None,
            "filtered_content": content_was_filtered
        }
    
# Agents with guardrails
@router.post("/rag_agent", response_model=dict)
@observe(name="rag_agent")
async def rag_agent(
    req: RetrievalInput,
    x_user_id: Optional[str] = Header(None),
    x_session_id: Optional[str] = Header(None),
):
    # 1️⃣ Resolve identifiers (body → header → generated)
    user_id, session_id = _default_ids(
        req.user_id or x_user_id,
        req.session_id or x_session_id,
    )
    langfuse_client = get_client()

    with langfuse_client.start_as_current_span(
        name="rag_guarded_request",
    ) as root_span:
        
        # 2️⃣ Query guardrail check
        with root_span.start_as_current_span(name="query_guardrail_check") as query_guard_span:
            should_block, query_violations = guardrails.scan_query(req.query, user_id)
            query_guard_span.update(
                input={"query": req.query, "query_length": len(req.query)},
                output={
                    "should_block": should_block, 
                    "violations_count": len(query_violations), 
                    "violation_types": [v.type.value for v in query_violations]
                }
            )
            
            if should_block:
                error_message = guardrails.get_safe_error_message(query_violations)
                query_guard_span.update_trace(
                    input=req.query,
                    output=error_message,
                    user_id=user_id,
                    session_id=session_id,
                    metadata={
                        "email": "tri@langfuse.com"
                    }
                )
                return {
                    "answer": error_message

                }
                # raise HTTPException(
                #     status_code=400,
                #     detail={
                #         "error": "Guardrail Violation",
                #         "message": error_message,
                #         "status": "blocked",
                #     }
                # )
        
        # 3️⃣ RAG chain execution
        with root_span.start_as_current_generation(
            name="agentic invoke",
            input={"query": req.query},
        ) as gen_span:
            out = agent.invoke({"input": req.query})
            print("Agent output:", out)
            raw_answer = out["output"]
            #sources = [d.metadata.get("source_file") for d in out["source_documents"]]
            docs       = out.get("source_documents", []) or out.get("sources", [])
            sources    = [d.metadata.get("source_file") for d in docs]
            
            gen_span.update(
                input={"query": req.query},
                output={"raw_answer_length": len(raw_answer)}
            )
        
        # 4️⃣ Response guardrail check
        with root_span.start_as_current_span(name="response_guardrail_check") as resp_span:
            sanitized_answer, response_violations = guardrails.scan_response(
                raw_answer, sources, user_id
            )
            
            # Check if content was actually filtered
            content_was_filtered = raw_answer != sanitized_answer or len(response_violations) > 0
            all_violations = query_violations + response_violations
            
            # Generate warnings
            warnings = []
            if content_was_filtered:
                warnings.append("Content was filtered by guardrails for security and privacy.")
            
            resp_span.update(
                input={"raw_answer_length": len(raw_answer)},
                output={
                    "sanitized_answer_length": len(sanitized_answer),
                    "response_violations_found": len(response_violations),
                    "content_filtered": content_was_filtered,
                    "total_violations": len(all_violations)
                }
            )
        
        # 5️⃣ Update main generation trace
        gen_span.update_trace(
            input=req.query,
            output=sanitized_answer,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "email": "tri@langfuse.com",
                "version": "1.0.0",
                "guardrails_enabled": True,
                "total_violations_detected": len(all_violations),
                "content_filtered": content_was_filtered,
                "safety_status": "safe" if not all_violations else "filtered"
            }
        )
        
        # 6️⃣ Return response
        return {
            "answer": sanitized_answer,
            "sources": sources,
            "user_id": user_id,
            "session_id": session_id,
            "safety_status": "safe" if not all_violations else "filtered",
            "warnings": warnings if warnings else None,
            "filtered_content": content_was_filtered
        }
# ────────────────────────────────────────────────────────────────────────────
# Attach router & health check
# ────────────────────────────────────────────────────────────────────────────


app.include_router(router)

@app.get("/health")
async def health():
    return {"ok": True}

# ────────────────────────────────────────────────────────────────────────────
# Optional warm-up on startup
# ────────────────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def warm_chain():
    # warm up the chain once so the first user isn’t slow
    qa_chain.invoke({"query": "ping"})
