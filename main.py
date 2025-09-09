from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from datetime import datetime, timedelta
import string, random

app = FastAPI()

# In-memory store
urls = {}

# Request model
class UrlRequest(BaseModel):
    url: str
    validity: int = 30
    shortcode: str = None

# Response model
class UrlResponse(BaseModel):
    shortLink: str
    expiry: str

# Generate shortcode if not given
def generate_shortcode(length=5):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.post("/shorturls", response_model=UrlResponse)
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

    host = str(request.base_url).rstrip("/")
    return UrlResponse(shortLink=f"{host}/{shortcode}", expiry=expiry.isoformat())

@app.get("/{shortcode}")
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

    return {"redirect_to": entry["url"]}

@app.get("/shorturls/{shortcode}")
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
