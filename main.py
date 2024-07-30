import os
from pytube import YouTube
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = '7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo'
DOWNLOAD_PATH = 'downloads/'

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send me a YouTube link, and I will download the video for you.')

async def ask_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    context.user_data['url'] = url

    try:
        yt = YouTube(url)
        streams = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc()
    except Exception as e:
        await update.message.reply_text(f'Failed to retrieve formats: {e}')
        return

    keyboard = []
    for stream in streams:
        resolution = stream.resolution
        size = stream.filesize or 0
        size_mb = size / (1024 * 1024)
        format_id = stream.itag

        if size > 0 and resolution:
            button_text = f"{resolution} - {size_mb:.2f}MB"
            keyboard.append([InlineKeyboardButton(button_text, callback_data=str(format_id))])

    if not keyboard:
        await update.message.reply_text('No valid formats available for download.')
        return

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Choose the quality:', reply_markup=reply_markup)

async def download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_id = int(query.data)
    url = context.user_data['url']
    await query.edit_message_text(text=f'Downloading video in format {format_id}...')

    try:
        yt = YouTube(url)
        stream = yt.streams.get_by_itag(format_id)
        video_path = stream.download(output_path=DOWNLOAD_PATH)
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
