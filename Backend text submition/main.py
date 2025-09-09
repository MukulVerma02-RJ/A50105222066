from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
import string, random, logging, webbrowser
import threading, time


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


app = FastAPI(
    title="URL Shortener API",
    description="A simple URL Shortener API with expiry, stats, and logging",
    version="1.0.0",
    contact={
        "name": "Mukul Rajput",
        "email": "your-email@example.com"
    },
    openapi_tags=[
        {"name": "URL Shortener", "description": "Operations for creating and managing short URLs"},
        {"name": "Redirect", "description": "Redirect shortened URLs to original links"},
        {"name": "Statistics", "description": "Get usage stats for short URLs"}
    ]
)


urls = {}


class UrlRequest(BaseModel):
    url: str
    validity: int = 30
    shortcode: str | None = None

class UrlResponse(BaseModel):
    shortLink: str
    expiry: str


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info(f"Incoming request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response status: {response.status_code}")
    return response


def generate_shortcode(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


@app.post(
    "/shorturls",
    response_model=UrlResponse,
    tags=["URL Shortener"],
    summary="Create a new short URL",
    description="Create a shortened URL with an optional custom shortcode and expiry time."
)
def create_short_url(data: UrlRequest, request: Request):
    shortcode = data.shortcode or generate_shortcode()
    if shortcode in urls:
        raise HTTPException(status_code=400, detail="Shortcode already exists")

    expiry = datetime.utcnow() + timedelta(minutes=data.validity)
    urls[shortcode] = {
        "url": data.url,
        "expiry": expiry,
        "clicks": []
    }

    base_url = str(request.base_url).rstrip("/")
    logger.info(f"Short URL created: {shortcode} -> {data.url}")
    return UrlResponse(shortLink=f"{base_url}/{shortcode}", expiry=expiry.isoformat())


@app.get(
    "/{shortcode}",
    tags=["Redirect"],
    summary="Redirect to the original URL",
    description="Redirect the user to the original URL if the shortcode is valid and not expired."
)
def redirect_url(shortcode: str, request: Request):
    if shortcode not in urls:
        raise HTTPException(status_code=404, detail="Shortcode not found")

    entry = urls[shortcode]
    if datetime.utcnow() > entry["expiry"]:
        raise HTTPException(status_code=410, detail="Link expired")

    entry["clicks"].append({
        "timestamp": datetime.utcnow().isoformat(),
        "referrer": request.headers.get("referer", "unknown"),
        "ip": request.client.host
    })

    logger.info(f"Redirect requested: {shortcode} -> {entry['url']}")
    return {"redirect_to": entry["url"]}


@app.get(
    "/shorturls/{shortcode}",
    tags=["Statistics"],
    summary="Get statistics for a short URL",
    description="Retrieve total clicks, IP addresses, and timestamps for a specific short URL."
)
def stats(shortcode: str):
    if shortcode not in urls:
        raise HTTPException(status_code=404, detail="Shortcode not found")

    entry = urls[shortcode]
    return {
        "url": entry["url"],
        "expiry": entry["expiry"].isoformat(),
        "total_clicks": len(entry["clicks"]),
        "click_data": entry["clicks"]
    }

# -------------------
# Auto-open Swagger UI on startup
# -------------------
def open_swagger():
    time.sleep(1)  # wait for server to start
    webbrowser.open("http://127.0.0.1:8000/docs")

# -------------------
# Run Directly
# -------------------
if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=open_swagger).start()
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
