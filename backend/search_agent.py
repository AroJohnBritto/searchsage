import os
import traceback
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from huggingface_hub.utils import HfHubHTTPError
from backend.tools.websearch_tool import search_web
from backend.tools.scrape_tool import scrape_urls, last_sources

load_dotenv()

# Primary: Fireworks (DeepSeek)
fireworks_client = InferenceClient(
    provider="fireworks-ai",
    api_key=os.getenv("HF_TOKEN")
)
FIREWORKS_MODEL = "deepseek-ai/DeepSeek-R1-0528"

# Fallback: Free-tier Flan
flan_client = InferenceClient(token=os.getenv("HF_TOKEN"), provider = None)
FLAN_MODEL = "google/flan-t5-xl"

def run_search_agent(question: str):
    print(f"== Searching web for: {question}")
    urls = search_web(question)
    scraped = scrape_urls(urls)

    if not scraped.strip():
        return {
            "answer": "I couldn’t find enough relevant content to answer this question from the web.",
            "sources": [],
            "log": "No content scraped."
        }

    prompt = f"""You are a helpful assistant. Answer the following question based only on the content provided.

Question: {question}

Web Content:
{scraped}

Answer:"""

    try:
        print("== Trying DeepSeek model via Fireworks...")
        response = fireworks_client.chat.completions.create(
            model=FIREWORKS_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()
        model_used = FIREWORKS_MODEL

    except HfHubHTTPError as e:
        if hasattr(e, "response") and getattr(e.response, "status_code", None) == 402:
            print("== Fireworks usage limit exceeded, falling back to Flan-T5...")
            try:
                response = flan_client.text_generation(
                    model=FLAN_MODEL,
                    prompt=prompt,
                    max_new_tokens=300,
                    temperature=0.7
                )
                answer = response.generated_text.strip()
                model_used = FLAN_MODEL
            except Exception as fallback_error:
                traceback.print_exc()
                return {
                    "answer": "Both primary and fallback models failed. Please try again later.",
                    "sources": [],
                    "log": str(fallback_error)
                }
        else:
            traceback.print_exc()
            return {
                "answer": "Fireworks AI model failed unexpectedly.",
                "sources": [],
                "log": str(e)
            }

    except Exception as e:
        traceback.print_exc()
        return {
            "answer": "An error occurred while processing your request.",
            "sources": [],
            "log": str(e)
        }

    return {
        "answer": answer,
        "sources": last_sources.copy(),
        "log": f"Answer generated using: {model_used}"
    }
