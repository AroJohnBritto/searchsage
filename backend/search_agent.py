# import os
# import traceback
# from dotenv import load_dotenv
# from backend.tools.websearch_tool import search_web
# from backend.tools.scrape_tool import scrape_urls, last_sources
# from huggingface_hub import InferenceClient

# load_dotenv()

# # Initialize InferenceClient directly
# client = InferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))
# REPO_ID = "gpt2"  # Or any other supported model

# def run_search_agent(question: str):
#     try:
#         print(f"== Running web search for: {question}")
#         urls = search_web(question)
#         scraped = scrape_urls(urls)

#         # Compose the full prompt
#         prompt = f"Question: {question}\n\nRelevant Content:\n{scraped}\n\nAnswer:"

#         print("== Sending prompt to Hugging Face...")
#         response = client.text_generation(
#             prompt=prompt,
#             model=REPO_ID,
#             max_new_tokens=200,
#             temperature=0.7,
#             top_p=0.95,
#             repetition_penalty=1.1,
#             do_sample=True
#         )

#         return {
#             "answer": response.generated_text.strip(),
#             "sources": last_sources.copy(),
#             "log": "Success"
#         }

#     except Exception as e:
#         traceback.print_exc()
#         return {
#             "answer": "An error occurred while processing your request.",
#             "sources": [],
#             "log": str(e)
#         }


# import os
# import traceback
# import logging
# from dotenv import load_dotenv
# from backend.tools.websearch_tool import search_web
# from backend.tools.scrape_tool import scrape_urls, last_sources
# from huggingface_hub import InferenceClient
# import requests

# # Set up logging
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)

# load_dotenv()

# # Initialize InferenceClient
# client = InferenceClient(token=os.getenv("HUGGINGFACEHUB_API_TOKEN"))
# REPO_ID = "gpt2"  # Model supporting text-generation task

# def run_search_agent(question: str) -> dict:
#     """
#     Run a search agent to answer a question using web search and Hugging Face model.
    
#     Args:
#         question (str): The user's question.
        
#     Returns:
#         dict: Contains answer, sources, and log.
#     """
#     if not question or not isinstance(question, str):
#         return {
#             "answer": "Invalid or empty question provided.",
#             "sources": [],
#             "log": "Input validation failed"
#         }

#     try:
#         logger.info(f"Running web search for: {question}")
#         urls = search_web(question)
#         if not urls:
#             return {
#                 "answer": "No relevant sources found.",
#                 "sources": [],
#                 "log": "Empty search results"
#             }

#         scraped = scrape_urls(urls)
#         if not scraped:
#             return {
#                 "answer": "Failed to scrape content from sources.",
#                 "sources": last_sources.copy(),
#                 "log": "Empty scraped content"
#             }

#         # Truncate scraped content to avoid exceeding context window
#         scraped = scraped[:1000] if len(scraped) > 1000 else scraped
#         prompt = f"Question: {question}\n\nRelevant Content:\n{scraped}\n\nAnswer:"

#         logger.info("Sending prompt to Hugging Face (text-generation task)...")
#         response = client.text_generation(
#             prompt=prompt,
#             model=REPO_ID,
#             max_new_tokens=200,
#             temperature=0.7,
#             top_p=0.95,
#             repetition_penalty=1.1,
#             do_sample=True
#         )

#         # Extract answer (response is a string)
#         answer = response.strip()
#         if answer.startswith(prompt):
#             answer = answer[len(prompt):].strip()

#         return {
#             "answer": answer,
#             "sources": last_sources.copy(),
#             "log": "Success"
#         }

#     except requests.exceptions.HTTPError as e:
#         if "Repository Not Found" in str(e) or "404" in str(e):
#             logger.error(f"Model repository not found or inaccessible: {REPO_ID}")
#             return {
#                 "answer": f"Error: Model '{REPO_ID}' not found or inaccessible.",
#                 "sources": last_sources.copy() if 'last_sources' in locals() else [],
#                 "log": f"Model repository error: {str(e)}"
#             }
#         logger.error(f"Hugging Face API error: {str(e)}")
#         return {
#             "answer": "An error occurred while processing your request.",
#             "sources": last_sources.copy() if 'last_sources' in locals() else [],
#             "log": f"Hugging Face API error: {str(e)}"
#         }
#     except ValueError as e:
#         if "not supported for task" in str(e):
#             logger.error(f"Model task error: {str(e)}")
#             return {
#                 "answer": f"Error: Model '{REPO_ID}' does not support the requested task.",
#                 "sources": last_sources.copy() if 'last_sources' in locals() else [],
#                 "log": f"Task error: {str(e)}"
#             }
#         logger.error(f"Value error: {str(e)}")
#         return {
#             "answer": "A value error occurred while processing your request.",
#             "sources": last_sources.copy() if 'last_sources' in locals() else [],
#             "log": f"Value error: {str(e)}"
#         }
#     except requests.exceptions.RequestException as e:
#         logger.error(f"Network error: {str(e)}")
#         return {
#             "answer": "A network error occurred while processing your request.",
#             "sources": last_sources.copy() if 'last_sources' in locals() else [],
#             "log": f"Network error: {str(e)}"
#         }
#     except StopIteration as e:
#         logger.error(f"No provider found for model: {REPO_ID}")
#         return {
#             "answer": f"Error: No provider available for model '{REPO_ID}'.",
#             "sources": last_sources.copy() if 'last_sources' in locals() else [],
#             "log": f"Provider error: {str(e)}"
#         }
#     except Exception as e:
#         logger.error(f"Unexpected error: {str(e)}", exc_info=True)
#         return {
#             "answer": "An unexpected error occurred.",
#             "sources": last_sources.copy() if 'last_sources' in locals() else [],
#             "log": str(e)
#         }

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
