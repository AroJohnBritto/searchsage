import os
import traceback
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from backend.tools.websearch_tool import search_web
from backend.tools.scrape_tool import scrape_urls, last_sources

load_dotenv()

client = InferenceClient(
    provider="fireworks-ai",
    api_key=os.getenv("HF_TOKEN")
)

MODEL_ID = "deepseek-ai/DeepSeek-R1-0528"

def run_search_agent(question: str):
    try:
        print(f"== Searching web for: {question}")
        urls = search_web(question)

        scraped = scrape_urls(urls)

        if not scraped.strip() or "could not extract" in scraped.lower():
            return {
                "answer": "I couldn’t find relevant information online to answer this query.",
                "sources": [],
                "log": "No content scraped."
            }

        prompt = f"""You are a helpful assistant. Only answer based on the following web content. Do not use prior knowledge.

Question: {question}

Web Content:
{scraped}

Answer:"""

        print("== Calling model with scraped content only...")

        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[{"role": "user", "content": prompt}]
        )

        answer = response.choices[0].message.content.strip()

        return {
            "answer": answer,
            "sources": last_sources.copy(),
            "log": "Answer generated strictly from scraped content."
        }

    except Exception as e:
        traceback.print_exc()
        return {
            "answer": "An error occurred while processing your request.",
            "sources": [],
            "log": str(e)
        }
