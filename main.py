import os
import subprocess
import tempfile
import json
import requests
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response

WHISPER_MODEL = os.environ.get("WHISPER_MODEL", "/Users/lisalobster/.openclaw/whisper-models/ggml-base.en.bin")
WHISPER_CLI = os.environ.get("WHISPER_CLI", "whisper-cli")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "sk_628480121bf8663ad3f7c39811bda825579d543e79c1add0")
ELEVENLABS_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyAtvM0m1nqt6cl7qsZfCFyRspXvKUK62M4")
PORT = int(os.environ.get("PORT", "8080"))

LIBBY_SYSTEM_PROMPT = "You are Libby, a sharp, warm personal AI assistant for Andrew. Be concise, helpful, and natural — this is a voice conversation so keep responses short (2-4 sentences max). End every response with a lobster emoji 🦞."

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Libby Voice</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif;
    background: #f2f2f7;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 48px 24px 40px;
    color: #1c1c1e;
  }
  h1 {
    font-size: 28px;
    font-weight: 700;
    letter-spacing: -0.5px;
    margin-bottom: 8px;
    color: #1c1c1e;
  }
  .subtitle {
    font-size: 15px;
    color: #8e8e93;
    margin-bottom: 56px;
  }
  .mic-wrapper {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
    margin-bottom: 48px;
  }
  #mic-btn {
    width: 96px;
    height: 96px;
    border-radius: 50%;
    border: none;
    background: #007aff;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 20px rgba(0,122,255,0.35);
    transition: transform 0.1s ease, box-shadow 0.1s ease, background 0.15s ease;
    user-select: none;
    -webkit-user-select: none;
    touch-action: none;
    outline: none;
  }
  #mic-btn:active, #mic-btn.recording {
    transform: scale(0.93);
    background: #ff3b30;
    box-shadow: 0 4px 28px rgba(255,59,48,0.45);
  }
  #mic-btn svg { pointer-events: none; }
  #status {
    font-size: 16px;
    font-weight: 500;
    color: #3a3a3c;
    height: 22px;
  }
  .conversation {
    width: 100%;
    max-width: 520px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .bubble {
    border-radius: 18px;
    padding: 13px 17px;
    font-size: 15px;
    line-height: 1.5;
    max-width: 88%;
    word-break: break-word;
  }
  .bubble.user {
    background: #007aff;
    color: white;
    align-self: flex-end;
    border-bottom-right-radius: 4px;
  }
  .bubble.libby {
    background: white;
    color: #1c1c1e;
    align-self: flex-start;
    border-bottom-left-radius: 4px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.08);
  }
  .label {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #8e8e93;
    margin-bottom: 4px;
  }
  .bubble-wrap { display: flex; flex-direction: column; max-width: 88%; }
  .bubble-wrap.user { align-self: flex-end; align-items: flex-end; }
  .bubble-wrap.libby { align-self: flex-start; align-items: flex-start; }
  .error-msg {
    font-size: 13px;
    color: #ff3b30;
    background: #fff1f0;
    border-radius: 10px;
    padding: 10px 14px;
    align-self: center;
    max-width: 90%;
    text-align: center;
  }
  .ripple {
    position: absolute;
    border-radius: 50%;
    background: rgba(255,255,255,0.3);
    transform: scale(0);
    animation: ripple 0.5s linear;
    pointer-events: none;
  }
  @keyframes ripple {
    to { transform: scale(2.5); opacity: 0; }
  }
  #mic-btn { position: relative; overflow: hidden; }
  @keyframes pulse {
    0% { box-shadow: 0 4px 28px rgba(255,59,48,0.45); }
    50% { box-shadow: 0 4px 36px rgba(255,59,48,0.7), 0 0 0 12px rgba(255,59,48,0.1); }
    100% { box-shadow: 0 4px 28px rgba(255,59,48,0.45); }
  }
  #mic-btn.recording { animation: pulse 1.2s ease-in-out infinite; }
</style>
</head>
<body>
<h1>Libby Voice</h1>
<p class="subtitle">Your personal assistant</p>

<div class="mic-wrapper">
  <button id="mic-btn" aria-label="Hold to speak">
    <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
      <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
      <line x1="12" y1="19" x2="12" y2="23"/>
      <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>
  </button>
  <div id="status">Hold to speak</div>
</div>

<div class="conversation" id="conversation"></div>

<script>
const btn = document.getElementById('mic-btn');
const statusEl = document.getElementById('status');
const conv = document.getElementById('conversation');

let mediaRecorder = null;
let audioChunks = [];
let stream = null;
let isRecording = false;
let currentAudio = null;

function setStatus(text) { statusEl.textContent = text; }

function addBubble(text, role) {
  const wrap = document.createElement('div');
  wrap.className = `bubble-wrap ${role}`;
  const label = document.createElement('div');
  label.className = 'label';
  label.textContent = role === 'user' ? 'You' : 'Libby';
  const bubble = document.createElement('div');
  bubble.className = `bubble ${role}`;
  bubble.textContent = text;
  wrap.appendChild(label);
  wrap.appendChild(bubble);
  conv.appendChild(wrap);
  conv.scrollTop = conv.scrollHeight;
}

function addError(text) {
  const el = document.createElement('div');
  el.className = 'error-msg';
  el.textContent = text;
  conv.appendChild(el);
  conv.scrollTop = conv.scrollHeight;
}

async function startRecording() {
  if (isRecording) return;
  if (currentAudio) { currentAudio.pause(); currentAudio = null; }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioChunks = [];
    const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
      ? 'audio/webm;codecs=opus'
      : MediaRecorder.isTypeSupported('audio/webm')
      ? 'audio/webm'
      : 'audio/ogg;codecs=opus';
    mediaRecorder = new MediaRecorder(stream, { mimeType });
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
    mediaRecorder.start(100);
    isRecording = true;
    btn.classList.add('recording');
    setStatus('Listening...');
  } catch (err) {
    setStatus('Hold to speak');
    addError('Microphone access denied. Please allow mic access and try again.');
  }
}

async function stopRecording() {
  if (!isRecording || !mediaRecorder) return;
  isRecording = false;
  btn.classList.remove('recording');
  setStatus('Thinking...');

  await new Promise(resolve => {
    mediaRecorder.onstop = resolve;
    mediaRecorder.stop();
  });
  stream.getTracks().forEach(t => t.stop());

  const mimeType = mediaRecorder.mimeType || 'audio/webm';
  const blob = new Blob(audioChunks, { type: mimeType });
  const ext = mimeType.includes('ogg') ? 'ogg' : 'webm';

  const formData = new FormData();
  formData.append('audio', blob, `recording.${ext}`);

  try {
    const res = await fetch('/chat', { method: 'POST', body: formData });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }

    const transcript = res.headers.get('X-Transcript') || '';
    const libbyText = res.headers.get('X-Libby-Response') || '';

    if (transcript) addBubble(decodeURIComponent(transcript), 'user');
    if (libbyText) addBubble(decodeURIComponent(libbyText), 'libby');

    const audioBlob = await res.blob();
    const audioUrl = URL.createObjectURL(audioBlob);
    currentAudio = new Audio(audioUrl);
    currentAudio.onended = () => {
      setStatus('Hold to speak');
      URL.revokeObjectURL(audioUrl);
    };
    setStatus('Speaking...');
    await currentAudio.play();
  } catch (err) {
    setStatus('Hold to speak');
    addError(`Error: ${err.message}`);
  }
}

// Mouse events
btn.addEventListener('mousedown', e => { e.preventDefault(); startRecording(); });
btn.addEventListener('mouseup', () => { if (isRecording) stopRecording(); });
btn.addEventListener('mouseleave', () => { if (isRecording) stopRecording(); });

// Touch events
btn.addEventListener('touchstart', e => { e.preventDefault(); startRecording(); }, { passive: false });
btn.addEventListener('touchend', e => { e.preventDefault(); if (isRecording) stopRecording(); }, { passive: false });
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(audio: UploadFile = File(...)):
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save uploaded audio
        ext = "webm"
        if audio.filename:
            ext = audio.filename.rsplit(".", 1)[-1] if "." in audio.filename else "webm"
        input_path = os.path.join(tmpdir, f"input.{ext}")
        wav_path = os.path.join(tmpdir, "audio.wav")
        txt_path = os.path.join(tmpdir, "audio.txt")

        with open(input_path, "wb") as f:
            f.write(await audio.read())

        # Convert to wav with ffmpeg
        ffmpeg_ok = False
        try:
            result = subprocess.run(
                ["ffmpeg", "-y", "-i", input_path, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav_path],
                capture_output=True, timeout=30
            )
            ffmpeg_ok = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            ffmpeg_ok = False

        # Transcribe with whisper-cli
        transcript = None
        whisper_error = None
        if ffmpeg_ok:
            try:
                result = subprocess.run(
                    [WHISPER_CLI, "-m", WHISPER_MODEL, "-f", wav_path, "--output-txt", "-of", os.path.join(tmpdir, "audio")],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0 and os.path.exists(txt_path):
                    with open(txt_path) as f:
                        transcript = f.read().strip()
                else:
                    whisper_error = result.stderr or "whisper-cli failed"
            except (FileNotFoundError, subprocess.TimeoutExpired) as e:
                whisper_error = str(e)
        else:
            whisper_error = "ffmpeg not available"

        if not transcript:
            transcript = "[voice message received — transcription unavailable]"
            if whisper_error:
                transcript += f" ({whisper_error[:80]})"

        # Call Gemini
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}"
        gemini_payload = {
            "system_instruction": {"parts": [{"text": LIBBY_SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": transcript}]}]
        }
        try:
            gemini_res = requests.post(gemini_url, json=gemini_payload, timeout=30)
            gemini_res.raise_for_status()
            gemini_data = gemini_res.json()
            libby_text = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini error: {e}")

        # ElevenLabs TTS
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        tts_headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        tts_payload = {
            "text": libby_text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        }
        try:
            tts_res = requests.post(tts_url, json=tts_payload, headers=tts_headers, timeout=30)
            tts_res.raise_for_status()
            audio_bytes = tts_res.content
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"ElevenLabs error: {e}")

        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={
                "X-Transcript": requests.utils.quote(transcript),
                "X-Libby-Response": requests.utils.quote(libby_text),
                "Access-Control-Expose-Headers": "X-Transcript, X-Libby-Response",
            },
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
