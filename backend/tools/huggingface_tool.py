# used for testing and playing with the LLM

# import os
# from huggingface_hub import InferenceClient
# from dotenv import load_dotenv

# load_dotenv()

# class HFInferenceLLM:
#     def __init__(self, repo_id: str):
#         token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
#         if not token:
#             raise ValueError("HUGGINGFACEHUB_API_TOKEN not set in environment.")
#         self.client = InferenceClient(token=token)
#         self.repo_id = repo_id


#     def invoke(self, input: str) -> str:
#         response = self.client.text_generation(
#             prompt=input,
#             max_new_tokens=200,
#             temperature=0.7,
#             top_p=0.95,
#             repetition_penalty=1.1,
#             do_sample=True,
#         )
#         return response.generated_text
