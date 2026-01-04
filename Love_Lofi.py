import os, time, random, subprocess
import requests
from datetime import datetime, timedelta, timezone
from requests.auth import HTTPBasicAuth

# ================= TIME =================
IST = timezone(timedelta(hours=5, minutes=30))
POST_WINDOWS = [("10:33", 10), ("18:00", 10)]

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

# ================= CLOUDINARY =================
def get_videos():
    r = requests.get(
        f"https://api.cloudinary.com/v1_1/{CLOUD_NAME}/resources/video",
        params={"type": "upload", "max_results": 100},
        auth=HTTPBasicAuth(API_KEY, API_SECRET),
        timeout=30
    )
    r.raise_for_status()
    return r.json().get("resources", [])

# ================= INSTAGRAM =================
def upload(video_url):
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
        return False

    creation_id = r["id"]
    time.sleep(30)

    pub = requests.post(
        f"https://graph.facebook.com/v19.0/{IG_USER_ID}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        }
    ).json()

    if "id" not in pub:
        print("❌ IG PUBLISH ERROR:", pub)
        return False

    print("✅ REEL PUBLISHED")
    return True

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

if not videos:
    print("❌ No videos found from Cloudinary")
    exit()

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