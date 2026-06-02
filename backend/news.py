from contextlib import asynccontextmanager
import json
from fastapi import FastAPI
import requests
from model import ClassifiedNews, NewsSource
from database import query_news, insert_news, get_active_subscribers
from huggingface_hub import InferenceClient
from logger import setup_logger
import resend
import asyncio

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
        "is_high_impact": False,
        "sentiment": "neutral",
        "impact_category": "none",
        "affected_sectors": [],
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

def build_email_body(important_news: list[tuple[dict, dict]], unsubscribe_url: str = "") -> str:
    """Build a beautiful HTML email body from classified important news items."""
    cards_list: list[str] = []
    for item, classified in important_news:
        confidence_pct = round(classified["confidence"] * 100)
        # Prefer canonical 'reason' but accept legacy 'reasoning'
        reasoning = classified.get("reason") or classified.get("reasoning", "")
        sentiment = classified.get("sentiment", "neutral")
        impact_category = classified.get("impact_category", "none")
        affected_sectors = classified.get("affected_sectors", [])
        content_snippet = item.get("contentSnippet", "")
        # Truncate snippet for email preview
        if len(content_snippet) > 200:
            content_snippet = content_snippet[:200] + "…"
        image_url = item.get("image", {}).get("small", "")
        date_str = item.get("isoDate", "").split("T")[0]

        cards_list.append(f"""
        <div style="background:#fff;border-radius:12px;border:1px solid #e5e7eb;padding:20px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,0.06);">
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
                <tr>
                    <td style="width:80px;vertical-align:top;padding-right:16px;">
                        <img src="{image_url}" alt="" width="80" height="80" style="border-radius:8px;width:80px;height:80px;object-fit:cover;" />
                    </td>
                    <td style="vertical-align:top;">
                        <div style="display:inline-block;background:#dbeafe;color:#1d4ed8;font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px;margin-bottom:6px;">{item.get("source", "")}</div>
                        <div style="display:inline-block;background:{'#dcfce7' if confidence_pct >= 70 else '#fef9c3'};color:{'#15803d' if confidence_pct >= 70 else '#a16207'};font-size:11px;font-weight:600;padding:2px 8px;border-radius:4px;margin-bottom:6px;margin-left:4px;">{confidence_pct}% confidence</div>
                        <h3 style="margin:0 0 4px;font-size:16px;line-height:1.4;"><a href="{item['link']}" style="color:#111827;text-decoration:none;">{item['title']}</a></h3>
                        <p style="margin:0 0 4px;font-size:13px;color:#6b7280;line-height:1.5;">{content_snippet}</p>
                        <p style="margin:0;font-size:12px;color:#9ca3af;">{date_str}</p>
                    </td>
                </tr>
            </table>
            <div style="margin-top:12px;padding-top:12px;border-top:1px solid #f3f4f6;">
                <p style="margin:0;font-size:13px;color:#4b5563;line-height:1.5;"><strong style="color:#374151;">Why it matters:</strong> {reasoning}</p>
                <p style="margin:8px 0 0;font-size:12px;color:#6b7280;line-height:1.4;"><strong>Sentiment:</strong> {sentiment} &nbsp;|&nbsp; <strong>Impact:</strong> {impact_category}</p>
                {f'<p style="margin:6px 0 0;font-size:12px;color:#6b7280;">Affected sectors: {", ".join(affected_sectors)}</p>' if affected_sectors else ''}
            </div>
        </div>""")
    cards = "\n".join(cards_list)

    return f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"/></head>
<body style="margin:0;padding:0;background-color:#f3f4f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;">
    <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f3f4f6;padding:24px 0;">
        <tr><td align="center">
            <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">
                <tr>
                    <td style="background:linear-gradient(135deg,#1e3a5f,#2563eb);border-radius:16px 16px 0 0;padding:28px 24px;text-align:center;">
                        <h1 style="margin:0 0 4px;font-size:22px;color:#ffffff;font-weight:700;">📈 Daily Market Impact</h1>
                        <p style="margin:0;font-size:14px;color:#bfdbfe;">AI-classified news likely to impact the stock market</p>
                    </td>
                </tr>
                <tr>
                    <td style="background:#ffffff;padding:24px;">
                        <p style="margin:0 0 16px;font-size:14px;color:#374151;">Found <strong>{len(important_news)}</strong> highly impactful news article{'s' if len(important_news) > 1 else ''} today:</p>
                        {cards}
                    </td>
                </tr>
                <tr>
                    <td style="background:#f9fafb;border-radius:0 0 16px 16px;padding:16px 24px;text-align:center;border-top:1px solid #e5e7eb;">
                        <p style="margin:0;font-size:12px;color:#9ca3af;">This email was generated automatically by News Tracker — AI-classified market impact analysis.</p>
                        {f'<p style="margin:8px 0 0;font-size:12px;"><a href="{unsubscribe_url}" style="color:#9ca3af;text-decoration:underline;">Unsubscribe</a></p>' if unsubscribe_url else ''}
                    </td>
                </tr>
            </table>
        </td></tr>
    </table>
</body>
</html>"""


def main():
    important_news: list[tuple[dict, dict]] = []
    for source in NewsSource:
        logger.info(f"Fetching news from {source.value}...")
        raw_data = get_news(source)
        if not raw_data:
            logger.warning(f"No data found for {source.value}")
            continue

        news = raw_data["data"]
        logger.debug(f"Fetched {len(news)} news items from {source.value}")
        if source == NewsSource.REPUBLIKA:
            for item in news:
                item['contentSnippet'] = item.pop('description')

        for item in news[:10]:  
            news_link = item["link"]
            if query_news(news_link):
                logger.info(f"News with link '{news_link}' already exists in the database.")
                continue
            classified_result = classify_news(item)
            if classified_result.get("is_high_impact"):
                important_news.append((item, classified_result))
            insert_news(item, source=source.value, classified_data=classified_result)
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    subscribers = get_active_subscribers()
    if not subscribers:
        logger.info("No active subscribers — skipping email dispatch.")
        return
    if important_news:
        logger.debug(f"Found {len(important_news)} highly impactful news articles.")
        for news in important_news:
            logger.debug(f"Important news: {news[0]['title']} with classification {news[1]}, link: {news[0]['link']}, snippet: {news[0].get('contentSnippet', '')[:100]}..., image: {news[0].get('image', {}).get('small', '')}, sector: {news[1].get('affected_sectors', [])}")
        for subscriber in subscribers:
            unsubscribe_url = f"{base_url}/unsubscribe?token={subscriber['token']}"
            email_body = build_email_body(important_news, unsubscribe_url=unsubscribe_url)
            send_email(
                subject=f"Daily Stock Market Impactful News — {len(important_news)} article{'s' if len(important_news) > 1 else ''}",
                body=email_body,
                to=subscriber["email"],
            )
    


async def news_polling_loop():
    """Run the news tracker polling loop as an async background task."""
    logger.info("Starting news tracker polling loop...")
    while True:
        await asyncio.to_thread(main)
        logger.info("News tracker process completed. Sleeping for 5 minutes...")
        await asyncio.sleep(300)

@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = asyncio.create_task(news_polling_loop())
    try:
        yield
    finally:
        polling_task.cancel()



