# CrimeVision AI – Multimodal Forensic Analysis Platform

A student-friendly Flask prototype for organizing digital evidence. It accepts image, video and audio files, records SHA-256 hashes, extracts basic image/video metadata, samples video frames, and can transcribe audio through the Groq Whisper API when a key is configured.

## Run locally
1. Install Python 3.10 or 3.11.
2. Open this folder in VS Code / terminal.
3. Run:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # macOS/Linux:
   source .venv/bin/activate
   pip install -r requirements.txt
   python app.py
   ```
4. Open http://127.0.0.1:5000

## Optional audio transcription
Create a Groq API key and set `GROQ_API_KEY` as an environment variable. Never paste the key into source code or upload it to GitHub.

Windows PowerShell:
```powershell
$env:GROQ_API_KEY="your_key"
python app.py
```

## Deploy on Render
1. Create a GitHub repository and upload these project files.
2. In Render, choose **New + → Web Service → Build and deploy from a Git repository**.
3. Select your repository. Render can read `render.yaml`; otherwise use:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
4. Deploy. Add `GROQ_API_KEY` under Render → Environment only if you want audio transcription.

## Important limitations
This is an educational prototype, not a certified forensic tool. It does not identify suspects, prove guilt, detect deepfakes, or guarantee evidence authenticity. Keep original evidence unchanged and work on copies. The default Render filesystem may be temporary; uploaded files and the JSON evidence log can disappear after redeploy/restart unless persistent storage or a database is configured. Do not upload real, sensitive case evidence to a public demo.
