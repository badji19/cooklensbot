import os
import tempfile
import subprocess
import yt_dlp
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from openai import OpenAI

# Load environment variables
BOT_TOKEN = os.getenv("8547641969:AAFZfNiVEhpX7KaYCxFKHAaxfLpVj7OtG2E")
OPENAI_API_KEY = os.getenv("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")

client = OpenAI(api_key=OPENAI_API_KEY)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "CookLens is online.\nSend me any short cooking video link (TikTok, Instagram, YouTube), and I will extract the full recipe."
    )


# -----------------------------
# Helper: Download video
# -----------------------------
def download_video(url):
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, "video.mp4")

    ydl_opts = {
        "format": "mp4",
        "outtmpl": video_path
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    return video_path


# -----------------------------
# Helper: Extract audio
# -----------------------------
def extract_audio(video_path):
    audio_path = video_path.replace(".mp4", ".mp3")

    command = [
        "ffmpeg", "-i", video_path,
        "-vn", "-acodec", "mp3",
        audio_path
    ]

    subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    return audio_path


# -----------------------------
# Helper: Whisper speech-to-text
# -----------------------------
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="gpt-4o-mini-tts",
            file=f,
        )
    return transcript.text


# -----------------------------
# Helper: Convert raw text → Recipe
# -----------------------------
def generate_recipe(text):
    prompt = f"""
You are CookLens AI. Convert the following cooking instructions into a clean, structured recipe.

Include:
- Title
- Ingredients (bullet list with quantities)
- Step-by-step instructions
- Notes or tips
- Language: choose English, Arabic, or French based on what makes most sense.

Here is the extracted transcript:
{text}
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content


# -----------------------------
# MAIN logic: User sends video link
# -----------------------------
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    await update.message.reply_text("Downloading video...")

    try:
        video_path = download_video(url)
    except Exception:
        await update.message.reply_text("Error: Could not download video.")
        return

    await update.message.reply_text("Extracting audio...")

    audio_path = extract_audio(video_path)

    await update.message.reply_text("Transcribing speech...")

    transcript = transcribe_audio(audio_path)

    await update.message.reply_text("Generating recipe...")

    recipe = generate_recipe(transcript)

    await update.message.reply_text(recipe)


# -----------------------------
# LAUNCH BOT
# -----------------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    app.run_polling()
