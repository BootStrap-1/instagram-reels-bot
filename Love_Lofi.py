import requests
import time
import os
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ================== CONFIG ==================

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
CLOUD_NAME = os.getenv("CLOUD_NAME")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

if not all([ACCESS_TOKEN, IG_USER_ID, CLOUD_NAME, API_KEY, API_SECRET]):
    raise Exception("❌ Missing environment variables. Check GitHub Secrets.")

CAPTION = "❤️ Follow for more #reels #love"

POST_TIMES = ["10:00", "18:00"]   # daily times (HH:MM)
UPLOAD_LOG = "uploaded.txt"

FORCE_MODE = False   # 👉 FIRST RUN = True, AFTER SUCCESS = False
# ============================================


def get_uploaded():
    if not os.path.exists(UPLOAD_LOG):
        return set()
    return set(open(UPLOAD_LOG).read().splitlines())


def mark_uploaded(pid):
    with open(UPLOAD_LOG, "a") as f:
        f.write(pid + "\n")


def list_cloudinary_videos():
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/video"
    params = {
        "type": "upload",
        "max_results": 500
    }
    r = requests.get(
        url,
        params=params,
        auth=HTTPBasicAuth(API_KEY, API_SECRET)
    )
    r.raise_for_status()
    return r.json()["resources"]


def is_time_to_post():
    if FORCE_MODE:
        return True

    now = datetime.now()
    for t in POST_TIMES:
        h, m = map(int, t.split(":"))
        scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if abs((now - scheduled).total_seconds()) <= 300:  # 5 min window
            return True
    return False


def post_reel(video_url):
    # STEP 1: Create container
    r = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
        data={
            "media_type": "REELS",
            "video_url": video_url,
            "caption": CAPTION,
            "access_token": ACCESS_TOKEN
        }
    ).json()

    if "id" not in r:
        print("❌ Create failed:", r)
        return False

    creation_id = r["id"]

    # STEP 2: Publish with retries
    for attempt in range(1, 6):
        print(f"⏳ Publish attempt {attempt} (waiting 30 sec)")
        time.sleep(30)

        p = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": ACCESS_TOKEN
            }
        ).json()

        if "id" in p:
            print("✅ Posted successfully:", video_url)
            return True

        # retry only if media not ready
        if "2207027" in str(p) or "not ready" in str(p):
            continue

        print("❌ Publish failed:", p)
        return False

    print("❌ Publish failed after retries")
    return False


print("🚀 Auto Instagram Reels Uploader STARTED")

while True:
    uploaded = get_uploaded()
    videos = list_cloudinary_videos()

    print("🎞 Total videos found:", len(videos))
    print("📂 Already uploaded:", len(uploaded))

    posted = 0

    for v in videos:
        public_id = v["public_id"]

        if public_id in uploaded:
            continue

        if not is_time_to_post():
            continue

        video_url = f"https://res.cloudinary.com/{CLOUD_NAME}/video/upload/{public_id}.mp4"
        print("⏫ Trying:", video_url)

        if post_reel(video_url):
            mark_uploaded(public_id)
            posted += 1
            time.sleep(120)

        if FORCE_MODE or posted == 2:
            break

    print("⏳ Waiting... next check in 60 sec")
    time.sleep(60)

