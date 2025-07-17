import os
import traceback
from dotenv import load_dotenv
from openai import OpenAI
from backend.tools.websearch_tool import search_web
from backend.tools.scrape_tool import scrape_urls, last_sources

load_dotenv()


client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

DEEPSEEK_MODEL = "deepseek/deepseek-r1:free"


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

    prompt = f"""You are a helpful assistant. Answer the following question based only on the content provided.\n\nQuestion: {question}\n\nWeb Content:\n{scraped}\n\nAnswer:"""

    try:
        print("== Calling DeepSeek model via OpenRouter...")
        response = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            extra_headers={
                "HTTP-Referer": "https://yourprojectname.streamlit.app",
                "X-Title": "SearchSage"
            }
        )
        answer = response.choices[0].message.content.strip()
        model_used = DEEPSEEK_MODEL

    except Exception as e:
        traceback.print_exc()
        return {
            "answer": "The DeepSeek model failed. Please try again later.",
            "sources": [],
            "log": str(e)
        }

    return {
        "answer": answer,
        "sources": last_sources.copy(),
        "log": f"Answer generated using: {model_used}"
    }
