import os
import shutil
import requests
import zipfile
import tempfile
from yt_dlp import YoutubeDL
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

BOT_TOKEN = '7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo'
DOWNLOAD_PATH = 'downloads/'

youtubedl_location = os.path.expanduser('~/Documents/site-packages/')
youtubedl_dir = 'yt_dlp'
backup_location = './backup/yt_dlp/'
youtubedl_downloadurl = 'https://github.com/yt-dlp/yt-dlp/archive/master.zip'
youtubedl_unarchive_location = './yt-dlp-master/'

files_to_change = [
    ('utils.py','import ctypes','#import ctypes'),
    ('utils.py','import pipes','#import pipes'),
    ('YoutubeDL.py','self._err_file.isatty() and ',''),
    ('downloader/common.py','(\'\r\x1b[K\' if sys.stderr.isatty() else \'\r\')','\'r\''),
    ('downloader/common.py','(\'\r\x1b[K\' if sys.stderr.isatty() else \'\r\')','\r'),
    ('extractor/common.py',' and sys.stderr.isatty()','')
]

# ایجاد پوشه دانلود در صورت عدم وجود
if not os.path.exists(DOWNLOAD_PATH):
    os.makedirs(DOWNLOAD_PATH)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Send me a YouTube link, and I will download the video for you.')

def backup_youtubedl():
    if os.path.isdir(youtubedl_location + youtubedl_dir):
        if not os.path.exists(backup_location):
            os.makedirs(backup_location)
        shutil.move(youtubedl_location + youtubedl_dir, backup_location + youtubedl_dir + time.strftime('%Y%m%d%H%M%S'))

def restore_youtubedl_backup():
    if not os.path.isdir(backup_location) or not os.listdir(backup_location):
        return 'No backups found to restore'
    else:
        folders = os.listdir(backup_location)
        folder = folders[len(folders) - 1]
        shutil.move(backup_location + folder, youtubedl_location + youtubedl_dir)
        return f'Successfully restored {folder}'

def downloadfile(url):
    localFilename = url.split('/')[-1] or 'download'
    with open(localFilename, 'wb') as f:
        r = requests.get(url, stream=True)
        total_length = r.headers.get('content-length')
        if total_length:
            dl = 0
            total_length = float(total_length)
            for chunk in r.iter_content(1024):
                dl += len(chunk)
                f.write(chunk)
        else:
            f.write(r.content)
    return localFilename

def process_file(path):
    if zipfile.is_zipfile(path):
        zipfile.ZipFile(path).extractall()

def update_youtubedl():
    if os.path.exists(youtubedl_location + youtubedl_dir):
        return 'yt-dlp exists in site-packages and will be overwritten'
    file = downloadfile(youtubedl_downloadurl)
    process_file(file)
    if os.path.exists(youtubedl_location + youtubedl_dir):
        shutil.rmtree(youtubedl_location + youtubedl_dir)
    shutil.move(youtubedl_unarchive_location + youtubedl_dir, youtubedl_location + youtubedl_dir)
    shutil.rmtree(youtubedl_unarchive_location)
    os.remove(file)
    process_youtubedl_for_pythonista()
    return 'yt-dlp updated successfully'

def process_youtubedl_for_pythonista():
    for patch in files_to_change:
        filename, old_str, new_str = patch
        replace_in_file(youtubedl_location + youtubedl_dir + '/' + filename, old_str, new_str)

def replace_in_file(file_path, old_str, new_str):
    with open(file_path, encoding='utf-8') as old_file:
        fh, abs_path = tempfile.mkstemp()
        os.close(fh)
        with open(abs_path, encoding='utf-8', mode='w') as new_file:
            for line in old_file:
                new_file.write(line.replace(old_str, new_str))
    os.remove(file_path)
    shutil.move(abs_path, file_path)

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    choice = "1"
    resolution = "high"

    try:
        if 'playlist' in url:
            download_playlist(url, resolution)
            await update.message.reply_text("Playlist downloaded successfully!")
        else:
            video_path = download_video(url, resolution)
            await update.message.reply_text("Video downloaded successfully!")
            file_size = os.path.getsize(video_path) / (1024 * 1024)

            if file_size <= 50:
                await update.message.reply_video(video=video_path)
            else:
                await update.message.reply_document(document=video_path)

            convert_to_mp3(video_path)
            await update.message.reply_text("Video converted to MP3 successfully!")

        os.remove(video_path)
    except Exception as e:
        await update.message.reply_text(f'Failed to process the link: {e}')

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
    video = YoutubeDL().extract_info(url, download=False)
    stream = video['formats'][itag]
    file_path = os.path.join(DOWNLOAD_PATH, f"{video['id']}.mp4")
    with YoutubeDL({'outtmpl': file_path}) as ydl:
        ydl.download([url])
    return file_path

def download_playlist(url, resolution):
    playlist = Playlist(url)
    for video_url in playlist.video_urls:
        download_video(video_url, resolution)

def convert_to_mp3(filename):
    clip = VideoFileClip(filename)
    clip.audio.write_audiofile(filename[:-4] + ".mp3")
    clip.close()

async def backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    backup_youtubedl()
    await update.message.reply_text('Backup completed successfully!')

async def restore(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = restore_youtubedl_backup()
    await update.message.reply_text(result)

async def update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update_youtubedl()
    await update.message.reply_text(result)

if __name__ == '__main__':
    application = ApplicationBuilder().token(BOT_TOKEN).read_timeout(600).write_timeout(600).build()

    start_handler = CommandHandler('start', start)
    link_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link)
    backup_handler = CommandHandler('backup', backup)
    restore_handler = CommandHandler('restore', restore)
    update_handler = CommandHandler('update', update)

    application.add_handler(start_handler)
    application.add_handler(link_handler)
    application.add_handler(backup_handler)
    application.add_handler(restore_handler)
    application.add_handler(update_handler)

    print('Bot is running...')
    application.run_polling()
