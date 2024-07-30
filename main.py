import os
from pytube import YouTube
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = '7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo'
DOWNLOAD_PATH = 'downloads/'

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send me a YouTube link, and I will download the video for you.')

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    await update.message.reply_text('Downloading video...')

    try:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        video_path = stream.download(output_path=DOWNLOAD_PATH)
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # Get the file size in MB

        if file_size <= 50:  # Telegram can handle videos up to 50MB directly
            await update.message.reply_video(video=video_path)
        else:  # For larger files, send as document
            await update.message.reply_document(document=video_path)

        os.remove(video_path)
    except Exception as e:
        await update.message.reply_text(f'Failed to download video: {e}')

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(600).write_timeout(600).build()

    start_handler = CommandHandler('start', start)
    download_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, download_video)

    application.add_handler(start_handler)
    application.add_handler(download_handler)

    print('Bot is running...')
    application.run_polling()
