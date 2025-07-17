import os
import traceback
from dotenv import load_dotenv
from huggingface_hub import InferenceClient
from backend.tools.websearch_tool import search_web
from backend.tools.scrape_tool import scrape_urls, last_sources

load_dotenv()

fireworks_client = InferenceClient(
    provider="fireworks-ai",
    api_key=os.getenv("HF_TOKEN")
)
FIREWORKS_MODEL = "deepseek-ai/DeepSeek-R1-0528"

# Fallback: standard inference client for flan
flan_client = InferenceClient(token=os.getenv("HF_TOKEN"))
FLAN_MODEL = "google/flan-t5-xl"

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

        try:
        print("== Trying DeepSeek model via Fireworks...")
        response = fireworks_client.chat.completions.create(
            model=FIREWORKS_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        answer = response.choices[0].message.content.strip()
        model_used = FIREWORKS_MODEL

    except HfHubHTTPError as e:
        if "402" in str(e) or "Payment Required" in str(e):
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
