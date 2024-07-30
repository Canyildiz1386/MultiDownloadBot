const ytdl = require('ytdl-core');
const fs = require('fs');
const ffmpeg = require('fluent-ffmpeg');
const ffmpegPath = require('@ffmpeg-installer/ffmpeg').path;

ffmpeg.setFfmpegPath(ffmpegPath);

// URL ویدئوی یوتیوبی که می‌خواهید دانلود کنید
const videoURL = 'https://www.youtube.com/watch?v=Isf8_mNcinQ';

// مسیری که می‌خواهید ویدئو در آن ذخیره شود
const outputPath = 'video.mp4';

// دانلود ویدئو
const videoStream = ytdl(videoURL, {
  quality: 'highestvideo',
  filter: format => format.container === 'mp4'
});

// ایجاد جریان ffmpeg برای ذخیره ویدئو
ffmpeg(videoStream)
  .audioCodec('copy')
  .videoCodec('copy')
  .save(outputPath)
  .on('end', () => {
    console.log('دانلود ویدئو به پایان رسید.');
  })
  .on('error', (error) => {
    console.error('خطا در دانلود ویدئو:', error);
  });
