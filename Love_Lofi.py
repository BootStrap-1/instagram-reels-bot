import os
import requests
import time
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ========= ENV =========
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
CLOUD_NAME = os.getenv("CLOUD_NAME")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

if not all([ACCESS_TOKEN, IG_USER_ID, CLOUD_NAME, API_KEY, API_SECRET]):
    raise Exception("❌ Missing environment variables")

# ========= CONFIG =========
CAPTION = "❤️ Follow for more reels #lofi #love"
POST_TIMES = ["10:00", "18:00"]
UPLOAD_LOG = "uploaded.txt"
# ========================


def get_uploaded():
    if not os.path.exists(UPLOAD_LOG):
        return set()
    return set(open(UPLOAD_LOG).read().splitlines())


def mark_uploaded(pid):
    with open(UPLOAD_LOG, "a") as f:
        f.write(pid + "\n")


def list_cloudinary_videos():
    url = f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/video"
    r = requests.get(
        url,
        params={"type": "upload", "max_results": 500},
        auth=HTTPBasicAuth(API_KEY, API_SECRET)
    )
    r.raise_for_status()
    return r.json()["resources"]


def is_time_to_post():
    now = datetime.now()
    for t in POST_TIMES:
        h, m = map(int, t.split(":"))
        scheduled = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if abs((now - scheduled).total_seconds()) <= 300:
            return True
    return False


def post_reel(video_url):
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

    for i in range(1, 6):
        print(f"⏳ Publish attempt {i}")
        time.sleep(30)

        p = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": ACCESS_TOKEN
            }
        ).json()

        if "id" in p:
            print("✅ Posted successfully")
            return True

        if "2207027" in str(p):
            continue

        print("❌ Publish failed:", p)
        return False

    return False


print("🚀 Auto Instagram Reels Uploader STARTED")

uploaded = get_uploaded()
videos = list_cloudinary_videos()

print("🎞 Total videos:", len(videos))
print("📂 Already uploaded:", len(uploaded))

posted = 0

for v in videos:
    pid = v["public_id"]

    if pid in uploaded:
        continue

    if not is_time_to_post():
        break

    url = f"https://res.cloudinary.com/{CLOUD_NAME}/video/upload/{pid}.mp4"
    print("⏫ Trying:", url)

    if post_reel(url):
        mark_uploaded(pid)
        posted += 1

    if posted == 2:
        break

print("✅ Run finished cleanly")
