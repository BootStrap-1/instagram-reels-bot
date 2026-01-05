import os, time, random, subprocess
import requests
from datetime import datetime, timedelta, timezone
from requests.auth import HTTPBasicAuth

# ================= TIME =================
IST = timezone(timedelta(hours=5, minutes=30))
POST_WINDOWS = [("10:15", 30), ("18:00", 30)]

# ================= ENV =================
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
CLOUD_NAME = os.getenv("CLOUD_NAME")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# ================= FILES =================
UPLOAD_LOG = "uploaded.txt"
DAILY_LOG = "daily_log.txt"

# ================= CAPTION =================
CAPTIONS = [
    "🎧 Lofi hits different at night",
    "🖤 Relatable vibes only",
    "🌙 Headphones on, world off",
]
HASHTAGS = ["#lofi", "#reels", "#sad", "#vibes", "#music"]

def caption():
    return f"{random.choice(CAPTIONS)}\n\n{' '.join(random.sample(HASHTAGS, 3))}"

# ================= HELPERS =================
def read_file(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as f:
        return set(f.read().splitlines())

def write_file(path, line):
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def today():
    return datetime.now(IST).strftime("%Y-%m-%d")

# ================= TIME CHECK =================
def check_window():
    now = datetime.now(IST)
    logs = read_file(DAILY_LOG)

    for t, w in POST_WINDOWS:
        h, m = map(int, t.split(":"))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        diff = abs((now - target).total_seconds()) / 60
        key = f"{today()}|{t}"

        if diff <= w:
            if key in logs:
                return False, None
            return True, t

    return False, None

# ================= CLOUDINARY (PAGINATION FIX) =================
def get_videos():
    all_videos = []
    cursor = None

    while True:
        params = {
            "type": "upload",
            "max_results": 100
        }
        if cursor:
            params["next_cursor"] = cursor

        r = requests.get(
            f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/video",
            params=params,
            auth=HTTPBasicAuth(API_KEY, API_SECRET),
            timeout=30
        )
        r.raise_for_status()

        data = r.json()
        all_videos.extend(data.get("resources", []))

        cursor = data.get("next_cursor")
        if not cursor:
            break

    return all_videos

# ================= INSTAGRAM (RETRY + STATUS FIX) =================
def upload(video_url):
    for attempt in range(3):  # 🔁 RETRY SYSTEM
        r = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media",
            data={
                "media_type": "REELS",
                "video_url": video_url,
                "caption": caption(),
                "access_token": ACCESS_TOKEN
            }
        ).json()

        if "id" not in r:
            print("❌ IG UPLOAD ERROR:", r)
            time.sleep(60)
            continue

        creation_id = r["id"]
        print("⏳ Processing media...")

        # ✅ STATUS POLLING
        status_url = f"https://graph.facebook.com/v19.0/{creation_id}"
        for _ in range(12):  # ~4 min
            s = requests.get(
                status_url,
                params={
                    "fields": "status_code",
                    "access_token": ACCESS_TOKEN
                }
            ).json()

            if s.get("status_code") == "FINISHED":
                break

            time.sleep(20)
        else:
            print("❌ Media processing timeout")
            return False

        pub = requests.post(
            f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
            data={
                "creation_id": creation_id,
                "access_token": ACCESS_TOKEN
            }
        ).json()

        if "id" in pub:
            print("✅ REEL PUBLISHED")
            return True

        print("❌ Publish failed, retrying...")
        time.sleep(90)

    print("❌ Final publish failed")
    return False

# ================= GIT COMMIT =================
def git_commit():
    subprocess.run(["git", "config", "user.name", "github-actions"])
    subprocess.run(["git", "config", "user.email", "actions@github.com"])
    subprocess.run(["git", "add", UPLOAD_LOG, DAILY_LOG])
    subprocess.run(["git", "commit", "-m", "update upload logs"], check=False)
    subprocess.run(["git", "push"], check=False)

# ================= MAIN =================
print("🚀 BOT STARTED")

allow, window = check_window()
if not allow:
    print("⏳ Not allowed now")
    exit()

uploaded = read_file(UPLOAD_LOG)
videos = get_videos()

print("📦 CLOUDINARY VIDEOS FOUND:", len(videos))

for v in videos:
    url = v.get("secure_url")
    if not url or url in uploaded:
        continue

    if upload(url):
        write_file(UPLOAD_LOG, url)
        write_file(DAILY_LOG, f"{today()}|{window}")
        git_commit()
    break

print("✅ DONE")
