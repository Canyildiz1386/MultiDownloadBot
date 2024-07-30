import os
from yt_dlp import YoutubeDL
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes


BOT_TOKEN = '7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo'
DOWNLOAD_PATH = 'downloads/'
FFMPEG_PATH = '/usr/bin/ffmpeg'

# Create the downloads directory if it does not exist
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send me a YouTube link, and I will download the video for you.')

async def ask_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['url'] = url

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'noplaylist': True,
        'quiet': True
    }
    formats = []

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=False)
            formats = info_dict.get('formats', [])
    except Exception as e:
        await update.message.reply_text(f'Failed to retrieve formats: {e}')
        return

    keyboard = []
    for fmt in formats:
        format_id = fmt.get('format_id')
        format_note = fmt.get('format_note') or 'unknown quality'
        ext = fmt.get('ext')
        resolution = fmt.get('resolution') or 'audio only'
        size = fmt.get('filesize') or 0
        size_mb = size / (1024 * 1024)

        if size > 0 and format_id and resolution and ext:
            button_text = f"{format_note} - {resolution} - {ext} - {size_mb:.2f}MB"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=format_id)])

    if not keyboard:
        await update.message.reply_text('No valid formats available for download.')
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose the quality:', reply_markup=reply_markup)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = query.data
    url = context.user_data['url']
    await query.edit_message_text(text=f'Downloading video in format {format_id}...')

    ydl_opts = {
        'format': format_id,
        'outtmpl': os.path.join(DOWNLOAD_PATH, '%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'socket_timeout': 600,
        'retries': 10,
        'ffmpeg_location': FFMPEG_PATH,
        'postprocessors': [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }]
    }

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_path = ydl.prepare_filename(info_dict)

        file_size = os.path.getsize(video_path) / (1024 * 1024)  # Get the file size in MB

        if file_size <= 50:  # Telegram can handle videos up to 50MB directly
            await query.message.reply_video(video=video_path)
        else:  # For larger files, send as document
            await query.message.reply_document(document=video_path)

        os.remove(video_path)
    except Exception as e:
        await query.message.reply_text(f'Failed to download video: {e}')

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(600).write_timeout(600).build()

    start_handler = CommandHandler('start', start)
    ask_quality_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, ask_quality)
    download_handler = CallbackQueryHandler(download_video)

    application.add_handler(start_handler)
    application.add_handler(ask_quality_handler)
    application.add_handler(download_handler)

    print('Bot is running...')
    application.run_polling()
