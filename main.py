import os
from pytube import YouTube, Playlist
from moviepy.editor import VideoFileClip
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = '7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo'
DOWNLOAD_PATH = 'downloads/'

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send me a YouTube link, and I will download the video for you.')

def choose_resolution(resolution):
    if resolution in ["low", "360", "360p"]:
        itag = 18
    elif resolution in ["medium", "720", "720p", "hd"]:
        itag = 22
    elif resolution in ["high", "1080", "1080p", "fullhd", "full_hd", "full hd"]:
        itag = 137
    elif resolution in ["very high", "2160", "2160p", "4K", "4k"]:
        itag = 313
    else:
        itag = 18
    return itag

def download_video(url, resolution):
    itag = choose_resolution(resolution)
    video = YouTube(url)
    stream = video.streams.get_by_itag(itag)
    stream.download(output_path=DOWNLOAD_PATH)
    return os.path.join(DOWNLOAD_PATH, stream.default_filename)

def download_playlist(url, resolution):
    playlist = Playlist(url)
    for video_url in playlist.video_urls:
        download_video(video_url, resolution)

def convert_to_mp3(filename):
    clip = VideoFileClip(filename)
    clip.audio.write_audiofile(filename[:-4] + ".mp3")
    clip.close()

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    choice = "1"  # فرض کنید همیشه انتخاب اول را انجام می‌دهیم
    resolution = "high"  # فرض کنید همیشه کیفیت بالا انتخاب می‌شود

    try:
        if 'playlist' in url:
            download_playlist(url, resolution)
            await update.message.reply_text("Playlist downloaded successfully!")
        else:
            video_path = download_video(url, resolution)
            await update.message.reply_text("Video downloaded successfully!")
            file_size = os.path.getsize(video_path) / (1024 * 1024)  # Get the file size in MB

            if file_size <= 50:  # Telegram can handle videos up to 50MB directly
                await update.message.reply_video(video=video_path)
            else:  # For larger files, send as document
                await update.message.reply_document(document=video_path)

            # Optional: Convert to MP3
            convert_to_mp3(video_path)
            await update.message.reply_text("Video converted to MP3 successfully!")

        os.remove(video_path)
    except Exception as e:
        await update.message.reply_text(f'Failed to process the link: {e}')

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(600).write_timeout(600).build()

    start_handler = CommandHandler('start', start)
    link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)

    application.add_handler(start_handler)
    application.add_handler(link_handler)

    print('Bot is running...')
    application.run_polling()
