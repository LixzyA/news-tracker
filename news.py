import json
import requests
from model import ClassifiedNews, NewsSource
from database import query_news, insert_news
from huggingface_hub import InferenceClient
from logger import setup_logger
import resend
import time

import os
from dotenv import load_dotenv
load_dotenv()
client = InferenceClient(api_key=os.getenv("HF_TOKEN"))
model = os.getenv("LLM_MODEL", "google/gemma-4-26B-A4B-it")
prompt = open("prompt.txt", "r").read()
logger = setup_logger(__name__)

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
    if not news.get("contentSnippet"):
        logger.exception("content snippet / description is missing for news item with link: %s", news.get("link"))
        raise ValueError("content snippet / description is required for classification")
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
            print(f"Classification attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                logger.error("All classifications attempts failed.")
    return {
        "is_highly_impactful": False,
        "reasoning": "Failed to classify news after multiple attempts.",
        "confidence": 0.0
    }

# TODO: needs a dns verification to send email from custom domain
def send_email(subject: str, body: str, to: str | list[str]):
    resend_api_key = os.getenv("RESEND_API_KEY")
    try:
        result = resend.Emails.send({
            "from": "Felix <onboarding@mail.felix-antony.com>",
            "to": to,
            "subject": subject,
            "html": body
        })
        return result
    except Exception as e:
        logger.error(f"Failed to send email: {e}")

def main():
    important_news = []
    for source in NewsSource:
        logger.info(f"Fetching news from {source.value}...")
        raw_data = get_news(source)
        if not raw_data:
            logger.warning(f"No data found for {source.value}")
            continue

        news = raw_data["data"]
        if source == NewsSource.REPUBLIKA:
            for item in news:
                item['contentSnippet'] = item.pop('description')

        for item in news[:10]:  
            news_link = item["link"]
            if query_news(news_link):
                logger.info(f"News with link '{news_link}' already exists in the database.")
                continue
            classified_result = classify_news(item)
            if classified_result.get("is_highly_impactful"):
                important_news.append(item)
            insert_news(item, source=source.value, classified_data=classified_result)
    targets = ['felix.antony168@gmail.com']
    if important_news:
        send_email(
            subject="Daily Stock Market Impactful News",
            body = "<h1>Here are the news that are classified as highly impactful to the stock market:</h1>" + 
                "".join([f"<p><a href='{news['link']}'>{news['title']}</a></p>" for news in important_news]),
            to = targets
        )
    

if __name__ == "__main__":
    logger.info("Starting news tracker process...")
    while True:
        main()
        logger.info("News tracker process completed. Sleeping for 5 minutes...")
        time.sleep(300)
