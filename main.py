
import os
import yt_dlp
import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# --- Config ---
LOG_FILE = "log.csv"
TOKEN = "7577926725:AAG2evwhjXmhbNzCMEnwFv7uR-ys4FGTIL0"  # ← Thay bằng token bot của bạn

# --- Logging ---
def save_log(user_id, username, format_choice, url):
    data = {'user_id': [user_id], 'username': [username], 'format': [format_choice], 'url': [url]}
    df = pd.DataFrame(data)
    if os.path.exists(LOG_FILE):
        df.to_csv(LOG_FILE, mode='a', index=False, header=False)
    else:
        df.to_csv(LOG_FILE, index=False)

# --- Download logic ---
def download(url, format_choice, cookie=None):
    format_map = {
        "480p": 'bestvideo[height<=480]+bestaudio/best',
        "720p": 'bestvideo[height<=720]+bestaudio/best'
    }

    if format_choice not in format_map:
        raise Exception("❌ Định dạng không hợp lệ.")

    ydl_opts = {
        'format': format_map[format_choice],
        'merge_output_format': 'mp4',
        'outtmpl': 'download.%(title).70s.%(ext)s',
        'noplaylist': True,
        'quiet': True,
        'socket_timeout': 60,
        'retries': 10,
        'fragment_retries': 10,
        'continuedl': True,
        'concurrent_fragment_downloads': 5,
        'nopart': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0',
        },
    }

    if cookie:
        ydl_opts['http_headers']['Cookie'] = cookie

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        ext = info.get("ext", "mp4")
        title = info.get("title", "video").replace("/", "_")[:70]
        file_path = f"download.{title}.{ext}"
        return file_path

# --- Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    lines = text.splitlines()
    url = lines[0].strip()
    cookie = None

    for line in lines[1:]:
        if line.lower().startswith("cookie:"):
            cookie = line[7:].strip()

    if cookie is None and os.path.exists("cookie.txt"):
        with open("cookie.txt", "r", encoding="utf-8") as f:
            cookie = f.read().strip()

    context.user_data['url'] = url
    context.user_data['cookie'] = cookie

    if "abcnews.go.com" in url and cookie is None:
        await update.message.reply_text("⚠️ Trang này yêu cầu cookie, vui lòng gửi kèm cookie hoặc để bot đọc từ file `cookie.txt`.")
        return

    supported_sites = ["youtube.com", "youtu.be", "facebook.com", "tiktok.com", "instagram.com", "twitter.com", "vimeo.com", "reddit.com"]
    if not any(site in url for site in supported_sites):
        await update.message.reply_text("⚠️ Trang web này không nằm trong danh sách hỗ trợ chính thức, sẽ vẫn thử tải nhé!")

    buttons = [
        [InlineKeyboardButton("📺 MP4 480p", callback_data='480p')],
        [InlineKeyboardButton("📺 MP4 720p", callback_data='720p')],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🔽 Chọn chất lượng video muốn tải:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_choice = query.data
    url = context.user_data.get('url')
    cookie = context.user_data.get('cookie')
    user = query.from_user

    await query.edit_message_text("⏳ Đang tải video...")

    try:
        file_path = download(url, format_choice, cookie)
        save_log(user.id, user.username, format_choice, url)
        await query.message.reply_video(video=open(file_path, 'rb'))
        os.remove(file_path)
    except Exception as e:
        await query.message.reply_text(f"⚠️ Lỗi khi tải video: {e}")

# --- App Entry ---
if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🚀 Bot đang chạy...")
    app.run_polling()
