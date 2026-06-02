"""FastAPI application exposing subscribe / unsubscribe endpoints for News Tracker."""

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse

from database import add_subscriber, remove_subscriber
from logger import setup_logger
from model import SubscribeRequest, MessageResponse
from news import lifespan

logger = setup_logger(__name__)

app = FastAPI(
    title="News Tracker Subscription API",
    description="Subscribe or unsubscribe from the daily market-impact email digest.",
    version="1.0.0",
    lifespan=lifespan,
)

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=MessageResponse, tags=["Health"])
def health_check():
    """Liveness probe — returns 200 OK when the API is running."""
    return {"status": "ok", "message": "News Tracker API is running."}


@app.post("/subscribe", response_model=MessageResponse, tags=["Subscriptions"])
def subscribe(body: SubscribeRequest):
    """
    Subscribe an email address to the daily market-impact digest.

    - Returns **400** if the email is already actively subscribed.
    - Returns **200** on success (new subscription or re-activation).
    """
    result = add_subscriber(body.email)
    if result["status"] == "error":
        logger.warning(f"Subscribe endpoint returned error for {body.email}: {result['message']}")
        return JSONResponse(status_code=400, content=result)
    return result


@app.get("/unsubscribe", response_class=HTMLResponse, tags=["Subscriptions"])
def unsubscribe(token: str = Query(..., description="Unsubscribe token included in every digest email")):
    """
    Unsubscribe via a token link.  Renders a simple HTML confirmation page
    so the user gets a human-readable response when clicking the email footer link.
    """
    result = remove_subscriber(token)

    if result["status"] == "error":
        logger.warning(f"Unsubscribe failed for token {token}: {result['message']}")
        # TODO: return a raw json
        return HTMLResponse(
            content=_render_html(
                title="Unsubscribe failed",
                heading="❌ Something went wrong",
                body=result["message"],
                color="#dc2626",
            ),
            status_code=400,
        )

    email = result.get("email", "your address")
    # TODO: return a raw json
    return HTMLResponse(
        content=_render_html(
            title="Unsubscribed",
            heading="✅ You've been unsubscribed",
            body=f"<strong>{email}</strong> has been removed from the News Tracker digest. "
                 "You won't receive any more emails from us.",
            color="#16a34a",
        ),
        status_code=200,
    )


# ---------------------------------------------------------------------------
# HTML helper
# ---------------------------------------------------------------------------

def _render_html(title: str, heading: str, body: str, color: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{title} — News Tracker</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f3f4f6;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
    }}
    .card {{
      background: #ffffff;
      border-radius: 16px;
      padding: 48px 40px;
      max-width: 480px;
      width: 100%;
      text-align: center;
      box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }}
    .badge {{
      display: inline-block;
      background: {color}1a;
      color: {color};
      font-size: 13px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 999px;
      margin-bottom: 20px;
    }}
    h1 {{ font-size: 22px; color: #111827; margin-bottom: 12px; }}
    p {{ font-size: 15px; color: #6b7280; line-height: 1.6; }}
    .footer {{ margin-top: 32px; font-size: 12px; color: #9ca3af; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="badge">News Tracker</div>
    <h1>{heading}</h1>
    <p>{body}</p>
    <div class="footer">📈 Daily Market Impact — AI-classified news digest</div>
  </div>
</body>
</html>"""
