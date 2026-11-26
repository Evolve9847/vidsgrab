# Multi-platform local video downloader
A responsive downloader interface based on the general workflow of the reference page, with original branding and layout. Uses yt-dlp's supported extractors, so it can work with many public video links (YouTube, TikTok, Facebook, Instagram, Reddit, and other supported sites) depending on current extractor support.

## Windows
1. Install Python 3.10+ and FFmpeg (add FFmpeg to PATH).
2. Run `run_windows.bat`.
3. Open http://127.0.0.1:5000
4. Paste a supported public URL, click Get Video, choose video/audio and quality, then Start Download.

## Important limits
No downloader can guarantee every URL from every site. Private, deleted, age/region-restricted, DRM-protected, login-required, or platform-blocked media may not work. Supported formats and resolutions vary. YouTube and other services may change their systems, requiring yt-dlp updates. Use only content you own or have permission to download; follow platform terms. Intended for localhost only.


## Fix for FFmpeg `could not find codec parameters`

The downloader now prefers H.264 MP4 video plus M4A audio, then falls back to an MP4/best format. This avoids some video-only AV1/VP9 streams that can fail during FFmpeg post-processing. Update yt-dlp and FFmpeg if the error persists:

```bat
python -m pip install -U yt-dlp
ffmpeg -version
ffprobe -version
```

Make sure `ffmpeg.exe` and `ffprobe.exe` are from the same current FFmpeg build and are on PATH. Restart the app after updating. This is a compatibility fallback, not a guarantee for every source/site.
\n\nAudio output: choose MP3 128/192/256/320 kbps in Audio mode. MP3 conversion requires a current FFmpeg build. If FFmpeg reports `Error splitting the argument list: Option not found`, update FFmpeg (ffmpeg.exe and ffprobe.exe from the same full build), add its `bin` folder to PATH, open a new CMD, and verify `ffmpeg -version` and `ffprobe -version`.\n