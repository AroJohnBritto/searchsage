from fastapi import FastAPI
from pydantic import BaseModel
from backend.search_agent import run_search_agent
import asyncio
from dotenv import load_dotenv

load_dotenv()
app = FastAPI()

class QueryRequest(BaseModel):
    question: str

@app.post("/query")
async def query(request: QueryRequest):
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_search_agent, request.question)
        return {"answer": result["answer"], "sources": result["sources"]}
    except Exception as e:
        return {"answer": "An error occurred while processing your request.", "sources": [], "error": str(e)}
