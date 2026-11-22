
import os, hashlib, json, mimetypes
from datetime import datetime, timezone
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from werkzeug.utils import secure_filename
from PIL import Image
import cv2
from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED = {"png", "jpg", "jpeg", "webp", "mp4", "mov", "avi", "wav", "mp3", "m4a"}
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "change-this-secret-before-production")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def get_records():
    p = BASE_DIR / "evidence.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_record(record):
    records = get_records()
    records.insert(0, record)
    (BASE_DIR / "evidence.json").write_text(json.dumps(records, indent=2), encoding="utf-8")

detector = None

def analyze_image(path):
    global detector

    if detector is None:
        detector = YOLO("yolo11n.pt")

    with Image.open(path) as im:
        image_format = im.format or "Unknown"
        width, height = im.size

    results = detector(str(path), verbose=False)
    result = results[0]

    detections = []

    if result.boxes is not None:
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])

            detections.append({
                "name": result.names[class_id],
                "confidence": round(confidence * 100, 2)
            })

    output_name = path.stem + "_detected.jpg"
    output_path = UPLOAD_DIR / output_name

    annotated_image = result.plot()
    cv2.imwrite(str(output_path), annotated_image)

    return {
        "type": "Image",
        "details": f"Format: {image_format} · Size: {width} × {height} pixels",
        "detections": detections,
        "annotated_image": output_name
    }
def analyze_video(path):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"type": "Video", "details": "Video file could not be decoded on this server."}
    fps = cap.get(cv2.CAP_PROP_FPS) or 0
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    duration = count / fps if fps else 0
    saved_frames = []
    for i, fraction in enumerate((0.10, 0.35, 0.60, 0.85), start=1):
        if count <= 0: break
        cap.set(cv2.CAP_PROP_POS_FRAMES, min(int(count * fraction), max(int(count)-1, 0)))
        ok, frame = cap.read()
        if ok:
            name = f"{path.stem}_frame_{i}.jpg"
            cv2.imwrite(str(UPLOAD_DIR / name), frame)
            saved_frames.append(name)
    cap.release()
    return {"type": "Video", "details": f"Resolution: {width} × {height} · FPS: {fps:.2f} · Duration: {duration:.1f} seconds · Frames extracted: {len(saved_frames)}", "frames": saved_frames}

def transcribe_audio(path):
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return {"type": "Audio", "details": "Audio uploaded successfully. Add GROQ_API_KEY in Render Environment to enable automatic transcription."}
    try:
        import requests
        with open(path, "rb") as audio:
            response = requests.post(
                "https://api.groq.com/openai/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {api_key}"},
                files={"file": (path.name, audio)},
                data={"model": "whisper-large-v3-turbo"},
                timeout=120
            )
        response.raise_for_status()
        transcript = response.json().get("text", "")
        return {"type": "Audio", "details": "Transcription completed.", "transcript": transcript}
    except Exception as exc:
        return {"type": "Audio", "details": f"Audio saved, but transcription failed: {str(exc)[:180]}"}

@app.route("/")
def index():
    records = get_records()
    return render_template("index.html", records=records, total=len(records))

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("evidence")
    if not file or not file.filename:
        flash("Please select an evidence file first.")
        return redirect(url_for("index"))
    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED:
        flash("Unsupported format. Use JPG, PNG, WEBP, MP4, MOV, AVI, WAV, MP3 or M4A.")
        return redirect(url_for("index"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stored_name = f"{stamp}_{original}"
    path = UPLOAD_DIR / stored_name
    file.save(path)
    try:
        if ext in {"png", "jpg", "jpeg", "webp"}:
            result = analyze_image(path)
        elif ext in {"mp4", "mov", "avi"}:
            result = analyze_video(path)
        else:
            result = transcribe_audio(path)
        record = {
            "id": stamp + "_" + str(len(get_records()) + 1),
            "filename": original,
            "stored_name": stored_name,
            "uploaded_at": datetime.now().strftime("%d %b %Y, %I:%M %p"),
            "sha256": sha256_file(path),
            "analysis": result
        }
        save_record(record)
        flash("Evidence uploaded and processed.")
    except Exception as exc:
        flash(f"Could not analyze this file: {str(exc)[:180]}")
    return redirect(url_for("index"))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.route("/health")
def health():
    return {"status": "ok", "service": "CrimeVision AI"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)
