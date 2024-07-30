import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
import subprocess
from yt_dlp import YoutubeDL
import sqlite3
import os

logging.basicConfig(level=logging.CRITICAL)
yt_dlp_logger = logging.getLogger('yt_dlp')
yt_dlp_logger.setLevel(logging.CRITICAL)

user_data = {}

conn = sqlite3.connect('downloads.db')
c = conn.cursor()
c.execute('''
    CREATE TABLE IF NOT EXISTS downloads (
        user_id INTEGER PRIMARY KEY,
        downloads INTEGER
    )
''')
conn.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("🇮🇷 فارسی", callback_data='fa'),
            InlineKeyboardButton("🇬🇧 English", callback_data='en'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('لطفا زبان خود را انتخاب کنید / Please choose your language:', reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {'language': query.data}
    
    if query.data == 'fa':
        await query.edit_message_text(text="🌐 زبان شما فارسی انتخاب شد.")
    else:
        await query.edit_message_text(text="🌐 Your language is set to English.")

    await query.message.reply_text('📎 لطفا لینک ویدیو یوتیوب را ارسال کنید / Please send the YouTube video link:')

def list_formats(url):
    ydl_opts = {
        'listformats': True,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        formats = info_dict.get('formats', [])
    return formats

def download_video_audio_separately(url, video_output_path, audio_output_path, video_format, audio_format):
    ydl_opts_video = {
        'format': video_format,
        'outtmpl': video_output_path,
        'quiet': True,
        'no_warnings': True,
    }
    ydl_opts_audio = {
        'format': audio_format,
        'outtmpl': audio_output_path,
        'quiet': True,
        'no_warnings': True,
    }
    with YoutubeDL(ydl_opts_video) as ydl:
        ydl.download([url])
    with YoutubeDL(ydl_opts_audio) as ydl:
        ydl.download([url])

def merge_video_audio(video_path, audio_path, output_path):
    command = [
        'ffmpeg',
        '-i', video_path,
        '-i', audio_path,
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-strict', 'experimental',
        output_path
    ]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

def update_download_count(user_id):
    c.execute('SELECT downloads FROM downloads WHERE user_id = ?', (user_id,))
    row = c.fetchone()
    if row:
        downloads = row[0] + 1
        c.execute('UPDATE downloads SET downloads = ? WHERE user_id = ?', (downloads, user_id))
    else:
        downloads = 1
        c.execute('INSERT INTO downloads (user_id, downloads) VALUES (?, ?)', (user_id, downloads))
    conn.commit()

async def get_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_data:
        await update.message.reply_text('لطفا ابتدا زبان خود را انتخاب کنید / Please choose your language first:')
        return

    user_data[user_id]['link'] = update.message.text
    formats = list_formats(update.message.text)
    
    keyboard = [
        [InlineKeyboardButton(f"{f['format_id']} - {f['ext']} - {f['resolution'] if 'resolution' in f else ''}", callback_data=f"video_{f['format_id']}")] 
        for f in formats if 'vcodec' in f and f['vcodec'] != 'none'
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if user_data[user_id]['language'] == 'fa':
        await update.message.reply_text('🎥 لطفا فرمت ویدیو را انتخاب کنید:', reply_markup=reply_markup)
    else:
        await update.message.reply_text('🎥 Please choose the video format:', reply_markup=reply_markup)

async def video_format_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    format_id = query.data.split("_")[1]
    user_data[user_id]['video_format'] = format_id

    formats = list_formats(user_data[user_id]['link'])
    keyboard = [
        [InlineKeyboardButton(f"{f['format_id']} - {f['ext']} - {f['abr'] if 'abr' in f else ''}", callback_data=f"audio_{f['format_id']}")] 
        for f in formats if 'acodec' in f and f['acodec'] != 'none'
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    new_text = '🎵 لطفا فرمت صدا را انتخاب کنید:' if user_data[user_id]['language'] == 'fa' else '🎵 Please choose the audio format:'

    if query.message.text != new_text or query.message.reply_markup != reply_markup:
        await query.edit_message_text(new_text, reply_markup=reply_markup)

async def audio_format_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    format_id = query.data.split("_")[1]
    user_data[user_id]['audio_format'] = format_id

    link = user_data[user_id]['link']
    video_format = user_data[user_id]['video_format']
    audio_format = user_data[user_id]['audio_format']
    video_output_path = f'{user_id}_video.mp4'
    audio_output_path = f'{user_id}_audio.m4a'
    final_output_path = f'{user_id}_final_video.mp4'

    if user_data[user_id]['language'] == 'fa':
        await query.message.edit_text('⏳ لطفا منتظر بمانید، ویدیو در حال دانلود و ترکیب است...')
    else:
        await query.message.edit_text('⏳ Please wait, the video is being downloaded and merged...')

    download_video_audio_separately(link, video_output_path, audio_output_path, video_format, audio_format)
    merge_video_audio(video_output_path, audio_output_path, final_output_path)
    update_download_count(user_id)
    
    with open(final_output_path, 'rb') as video_file:
        if os.path.getsize(final_output_path) > 50 * 1024 * 1024:
            print(222222)
            await query.message.reply_document(document=video_file)
        else:
            print(3333333333)
            await query.message.reply_video(video=video_file)

    os.remove(video_output_path)
    os.remove(audio_output_path)
    os.remove(final_output_path)

    if user_data[user_id]['language'] == 'fa':
        await query.message.reply_text('✅ ویدیو با موفقیت دانلود و ترکیب شد!')
    else:
        await query.message.reply_text('✅ The video has been successfully downloaded and merged!')

def main() -> None:
    application = ApplicationBuilder().token("7325149894:AAGTxEjEVB5pFuV-kGN_4dEOCdX5GRfsVzo").build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button, pattern='^(fa|en)$'))
    application.add_handler(CallbackQueryHandler(video_format_button, pattern='^video_'))
    application.add_handler(CallbackQueryHandler(audio_format_button, pattern='^audio_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_link))

    application.run_polling()

if __name__ == '__main__':
    main()
