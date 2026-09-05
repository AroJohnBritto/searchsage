import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from backend import db, logging_config, search_agent
from backend.auth import verify_api_key
from backend.ratelimit import query_rate_limiter

logging_config.setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="SearchSage", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = logging_config.new_request_id()
    token = logging_config.set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        logging_config.reset_request_id(token)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})


class QueryRequest(BaseModel):
    question: str
    session_id: str | None = None


class FeedbackRequest(BaseModel):
    answer_id: str
    vote: str


def _run_agent(question: str, session_id: str | None) -> dict:
    return search_agent.answer_question(question, session_id)


@app.post("/query", dependencies=[Depends(verify_api_key), Depends(query_rate_limiter)])
async def query(request: QueryRequest):
    if request.session_id and not db.session_exists(request.session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _run_agent, request.question, request.session_id)
    return result


@app.get("/query/stream", dependencies=[Depends(verify_api_key), Depends(query_rate_limiter)])
async def query_stream(question: str, session_id: str | None = None):
    if session_id and not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(None, _run_agent, question, session_id)

    async def event_generator():
        answer = result["answer"]
        chunk_size = 20
        for i in range(0, len(answer), chunk_size):
            chunk = answer[i : i + chunk_size]
            yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            await asyncio.sleep(0.03)

        final_payload = {
            "done": True,
            "sources": result["sources"],
            "mode": result["mode"],
            "answer_id": result["answer_id"],
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/session", dependencies=[Depends(verify_api_key)])
async def create_session():
    session_id = uuid.uuid4().hex
    db.create_session(session_id)
    return {"session_id": session_id}


@app.get("/session/{session_id}", dependencies=[Depends(verify_api_key)])
async def get_session_history(session_id: str):
    if not db.session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return {"session_id": session_id, "history": db.get_history(session_id)}


@app.get("/answer/{answer_id}")
async def get_answer(answer_id: str):
    answer = db.get_answer(answer_id)
    if answer is None:
        raise HTTPException(status_code=404, detail="Answer not found.")
    return answer


@app.post("/feedback", dependencies=[Depends(verify_api_key)])
async def feedback(request: FeedbackRequest):
    if request.vote not in ("up", "down"):
        raise HTTPException(status_code=400, detail="Vote must be 'up' or 'down'.")
    if db.get_answer(request.answer_id) is None:
        raise HTTPException(status_code=404, detail="Answer not found.")
    db.save_feedback(request.answer_id, request.vote)
    return {"status": "ok"}


@app.get("/status")
async def status():
    return {
        "tier1_configured": bool(os.getenv("GEMINI_API_KEY")),
        "tier2_configured": bool(os.getenv("NVIDIA_API_KEY")),
        "tier3_configured": bool(os.getenv("OPENROUTER_API_KEY")),
    }


@app.get("/health")
async def health():
    return {"status": "ok"}
