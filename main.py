
from fastapi import FastAPI, File, UploadFile, Form, Header, HTTPException
from pydantic import BaseModel
import httpx, io, os, base64, exifread, random, re
from typing import Optional, List, Dict, Any

app = FastAPI(title="SnapHistory API", description="Your Virtual Time-Guide — Every Picture Has a Soul. Created by Nuthan S Belandur.")

# ====== CONFIG ======
API_KEYS = {os.getenv("PLUGIN_API_KEY", "TEST_KEY_123")}
GOOGLE_VISION_KEY = os.getenv("GOOGLE_VISION_KEY", "YOUR_GOOGLE_VISION_KEY_HERE")

# ====== QUOTES ======
# Load quotes from quotes.json (bundled with app)
QUOTES = {
    "war": [
        "Where silence screams louder than war.",
        "Ruins remember what victors forget.",
        "Peace is carved from the scar of battle."
    ],
    "love": [
        "Even steel can feel love if kissed by light.",
        "Two hearts turned stone into legend.",
        "Love built this so it would never die."
    ],
    "spiritual": [
        "Here, stone breathes a prayer.",
        "Faith is the architecture of the unseen.",
        "Footsteps soften when the soul listens."
    ],
    "nature": [
        "Time drifts where the waves remember.",
        "Mountains teach the patience of the earth.",
        "The wind writes history on water and rock."
    ],
    "grand": [
        "Dreams forged in iron and ambition.",
        "Every arch is a heartbeat of an era.",
        "Greatness is geometry set to music."
    ],
    "neutral": [
        "Stone remembers; crowds forget.",
        "What survives of us is story.",
        "Every brick keeps a secret."
    ]
}

def load_quotes():
    global QUOTES
    try:
        import json, pathlib
        qpath = pathlib.Path(__file__).with_name("quotes.json")
        if qpath.exists():
            with open(qpath, "r", encoding="utf-8") as f:
                QUOTES = json.load(f)
    except Exception:
        pass

load_quotes()

# ====== HELPERS ======
def extract_exif_gps(image_bytes: bytes):
    try:
        f = io.BytesIO(image_bytes)
        tags = exifread.process_file(f, details=False)
        def dms_to_deg(dms):
            d = float(dms.values[0].num)/float(dms.values[0].den)
            m = float(dms.values[1].num)/float(dms.values[1].den)
            s = float(dms.values[2].num)/float(dms.values[2].den)
            return d + (m/60.0) + (s/3600.0)
        if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
            lat = dms_to_deg(tags["GPS GPSLatitude"])
            lon = dms_to_deg(tags["GPS GPSLongitude"])
            if str(tags.get("GPS GPSLatitudeRef")) in ("S","s"): lat = -lat
            if str(tags.get("GPS GPSLongitudeRef")) in ("W","w"): lon = -lon
            return {"lat": lat, "lon": lon}
    except Exception:
        pass
    return None

async def google_vision(image_bytes: bytes):
    if not GOOGLE_VISION_KEY or "YOUR_GOOGLE_VISION_KEY_HERE" in GOOGLE_VISION_KEY:
        # Return empty structure if key not configured
        return {"responses":[{}]}
    url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_VISION_KEY}"
    img64 = base64.b64encode(image_bytes).decode("utf-8")
    data = {
        "requests": [
            {
                "image": {"content": img64},
                "features": [
                    {"type": "LANDMARK_DETECTION", "maxResults": 3},
                    {"type": "LABEL_DETECTION", "maxResults": 5},
                    {"type": "WEB_DETECTION", "maxResults": 5}
                ]
            }
        ]
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=data)
        r.raise_for_status()
        return r.json()

async def reverse_geocode(lat, lon):
    url = "https://nominatim.openstreetmap.org/reverse"
    params = {"lat": lat, "lon": lon, "format": "jsonv2"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params, headers={"User-Agent": "SnapHistory/1.0 (support@example.com)"})
        r.raise_for_status()
        return r.json()

async def wikipedia_summary(title: str, lang="en"):
    safe = re.sub(r"\s", "_", title.strip())
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{safe}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        if r.status_code == 200:
            return r.json()
    return {}

def detect_mood(text: str) -> str:
    t = (text or "").lower()
    # keyword buckets
    if any(k in t for k in ["war", "battle", "memorial", "bomb", "massacre", "genocide", "army", "trench"]):
        return "war"
    if any(k in t for k in ["love", "romance", "honeymoon", "valentine", "wedding", "heart"]):
        return "love"
    if any(k in t for k in ["temple", "mosque", "church", "cathedral", "basilica", "shrine", "pilgrim", "spiritual"]):
        return "spiritual"
    if any(k in t for k in ["mountain", "sea", "lake", "river", "forest", "desert", "beach", "cliff", "island", "canyon"]):
        return "nature"
    if any(k in t for k in ["tower", "palace", "castle", "bridge", "fort", "skyscraper", "cathedral", "museum", "opera", "theatre"]):
        return "grand"
    return "neutral"

def echo_of_time(mood: str) -> str:
    arr = QUOTES.get(mood) or QUOTES["neutral"]
    return random.choice(arr)

# ====== MODELS ======
class PlaceInfo(BaseModel):
    title: Optional[str]
    country: Optional[str]
    description: Optional[str]
    coordinates: Optional[Dict[str, float]]
    confidence: Optional[float]
    wiki_url: Optional[str]
    image_credit: Optional[str]
    year_built: Optional[str]
    architect: Optional[str]
    mood: Optional[str]
    echo_of_time: Optional[str]
    sources: Optional[List[str]]

# ====== ROUTES ======
@app.get("/v1/health")
async def health(): 
    return {"status": "ok"}

@app.post("/v1/identify", response_model=PlaceInfo)
async def identify_place(
    image_file: Optional[UploadFile] = File(None),
    image_url: Optional[str] = Form(None),
    x_api_key: Optional[str] = Header(None)
):
    if x_api_key not in API_KEYS:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if not image_file and not image_url:
        raise HTTPException(status_code=400, detail="Provide image_file or image_url")

    # Load image bytes
    if image_file:
        img_bytes = await image_file.read()
    else:
        async with httpx.AsyncClient() as c:
            r = await c.get(image_url)
            r.raise_for_status()
            img_bytes = r.content

    gps = extract_exif_gps(img_bytes)
    vision = await google_vision(img_bytes)
    resp = vision.get("responses", [{}])[0] if isinstance(vision.get("responses"), list) else {}

    # --- Landmark detection first ---
    title = None
    confidence = 0.0
    coords = gps
    sources = []

    for lm in resp.get("landmarkAnnotations", []):
        title = lm.get("description")
        if lm.get("locations"):
            coords = {
                "lat": lm["locations"][0]["latLng"]["latitude"],
                "lon": lm["locations"][0]["latLng"]["longitude"]
            }
        confidence = max(confidence, lm.get("score", 0.0))
        break

    # Web entities as fallback
    if not title:
        webs = resp.get("webDetection", {}).get("webEntities", [])
        for e in webs or []:
            if e.get("description"):
                title = e["description"]
                confidence = max(confidence, e.get("score", 0.4))
                break

    # Labels as a last hint
    if not title:
        labels = resp.get("labelAnnotations", [])
        if labels:
            title = labels[0].get("description")

    # Reverse geocode if we have GPS
    country = None
    if coords:
        try:
            rev = await reverse_geocode(coords["lat"], coords["lon"])
            address = rev.get("address", {})
            country = address.get("country")
            if not title:
                title = rev.get("name") or rev.get("display_name", "").split(",")[0]
        except Exception:
            pass

    # Wikipedia fetch
    wiki = {}
    if title:
        wiki = await wikipedia_summary(title)
        # try again with country appended if first attempt fails
        if not wiki.get("extract") and country:
            wiki = await wikipedia_summary(f"{title} {country}")

    description = wiki.get("extract") if wiki else None

    # Extract heuristics for year/architect from description
    year_built = None
    architect = None
    if description:
        m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", description)
        if m:
            year_built = m.group(1)
        m2 = re.search(r"by ([A-Z][A-Za-z\s\.-]{2,40})", description)
        if m2:
            architect = m2.group(1).strip()

    # Mood & echo
    mood = detect_mood(f"{title or ''} {description or ''}")
    echo = echo_of_time(mood)

    wiki_url = wiki.get("content_urls", {}).get("desktop", {}).get("page") if wiki else None
    img_credit = wiki.get("originalimage", {}).get("source") if wiki.get("originalimage") else None

    out = {
        "title": title,
        "country": country,
        "description": description or "I found this place, but couldn't locate a detailed history.",
        "coordinates": coords,
        "confidence": round(confidence, 3) if confidence else None,
        "wiki_url": wiki_url,
        "image_credit": img_credit,
        "year_built": year_built,
        "architect": architect,
        "mood": mood,
        "echo_of_time": echo,
        "sources": [wiki_url] if wiki_url else []
    }
    return out
