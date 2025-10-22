
# SnapHistory — Your Virtual Time-Guide
**Every Picture Has a Soul.**  
*Created by Nuthan S Belandur*

SnapHistory lets anyone upload a photo and instantly get the **name, history, coordinates, and mood-based “Echo of Time” quote** about that place. 
It integrates **Google Vision** (landmark detection), **EXIF GPS**, **OpenStreetMap** reverse geocoding, and **Wikipedia** summaries.

---

## 1) Quick Start

### A. Local run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PLUGIN_API_KEY=TEST_KEY_123
export GOOGLE_VISION_KEY=YOUR_GOOGLE_VISION_KEY_HERE
uvicorn main:app --reload --port 8000
# test
curl http://localhost:8000/v1/health
```

### B. Deploy to Render (recommended)
1. Create a GitHub repo and upload all files.
2. Go to https://render.com → **New** → **Web Service** → Connect repo.
3. Environment Variables:
   - `PLUGIN_API_KEY=TEST_KEY_123`
   - `GOOGLE_VISION_KEY=YOUR_GOOGLE_VISION_KEY_HERE`
4. Use Dockerfile (auto-detected). After deploy, open:
   - `https://YOUR-RENDER-URL/v1/health` → returns `{"status":"ok"}`

> Replace `YOUR_GOOGLE_VISION_KEY_HERE` with your real key from Google Cloud Console (enable **Vision API** → **Credentials** → **Create API Key**).

---

## 2) Connect to ChatGPT (GPT Actions)

1. Open `openapi.yaml` and replace `https://REPLACE_WITH_YOUR_DEPLOY_URL` with your live URL.
2. In ChatGPT → **Explore GPTs → Create** → **Configure → Actions → Import from OpenAPI** → paste the YAML.
3. Auth: **API Key**, header: `x-api-key`, test value: `TEST_KEY_123`.
4. **Instructions** (paste into your GPT):
> When a user uploads a photo of a place, call `identifyPlace`. Then respond with:  
> - **🏛 Name:** {title}  
> - **📍 Location:** {country} ({coordinates})  
> - **🕰 Built/Architect:** {year_built or '—'}, {architect or '—'}  
> - **📖 Story:** {description}  
> - **✨ Echo of Time:** {echo_of_time}  
> - **🌐 Read More:** {wiki_url}  
> If confidence < 0.5, say “I’m not fully sure — here are my best guesses.”

---

## 3) How it works
- **Vision:** Landmark + label + web detection  
- **EXIF:** Reads GPS if present  
- **Reverse Geocode:** OpenStreetMap/Nominatim to get country  
- **History:** Wikipedia REST summary (in English)  
- **Mood Engine:** Keyword-based classifier (war/love/spiritual/nature/grand/neutral) → returns a short quote from `quotes.json`.

---

## 4) Security & Privacy
- This API accepts user images and may call third-party APIs.  
- Add logging, rate limits, and GDPR notices before large-scale public use.

---

## 5) Environment Variables
```
PLUGIN_API_KEY=TEST_KEY_123
GOOGLE_VISION_KEY=YOUR_GOOGLE_VISION_KEY_HERE
```

---

## 6) Test endpoints
- Health: `GET /v1/health`
- Identify: `POST /v1/identify` (multipart `image_file` OR JSON `image_url`)

**cURL example:**
```bash
curl -X POST "https://YOUR-RENDER-URL/v1/identify"   -H "x-api-key: TEST_KEY_123"   -F "image_file=@/path/to/photo.jpg"
```

---

## 7) Credits
- Google Cloud Vision API
- OpenStreetMap / Nominatim
- Wikimedia / Wikipedia
