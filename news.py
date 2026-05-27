import json
import requests
from model import ClassifiedNews, NewsSource
from database import query_news, insert_news
from huggingface_hub import InferenceClient
import os
from dotenv import load_dotenv
load_dotenv()
client = InferenceClient(api_key=os.getenv("HF_TOKEN"))
model = os.getenv("LLM_MODEL", "google/gemma-4-26B-A4B-it")
prompt = open("prompt.txt", "r").read()

def get_news(source: NewsSource, type: str | None = None):
    base_url = f"https://berita-indo-api-next.vercel.app/api/{source.value}"
    if type:
        base_url += f"/{type}"

    try:
        response = requests.get(base_url)
        response.raise_for_status()
        data = response.json()
        return data
    except Exception as e:
        print(e)
        return None
    
def classify_news(news: dict) -> dict:
    """
    Classify whether news will highly impact the stock market.
    """
    content_snippet = news["contentSnippet"].lower()
    global model
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "ClassifiedNews",
            "schema": ClassifiedNews.model_json_schema(),
            "strict": True
        },
    }
    messages=[
            {
                "role": "system",
                "content": prompt
            },
            {
                "role": "user",
                "content": "News snippet: " + content_snippet
            }
        ]
    max_retries = 3
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                messages=messages,
                response_format= response_format, # type: ignore
                model=model,
            ) # type: ignore
            structured_data = completion.choices[0].message.content
            return json.loads(structured_data)
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("All attempts failed.")
    return {
        "is_highly_impactful": False,
        "reasoning": "Failed to classify news after multiple attempts.",
        "confidence": 0.0
    }

if __name__ == "__main__":
    raw_data = get_news(NewsSource.CNBC)
    if not raw_data:
        print("No data found")
        exit()

    news = raw_data["data"]
    exists = 0
    classified = 0
    for item in news[:1]: 
        news_link = item["link"]
        if query_news(news_link):
            print(f"News with link '{news_link}' already exists in the database.")
            exists += 1
            continue
        classified_result = classify_news(item)
        classified += 1
        result = insert_news(item, source=NewsSource.CNBC.value, classified_data=classified_result)
    print(f"Classified : {classified} news, {exists} news already exists in the database.")
            
