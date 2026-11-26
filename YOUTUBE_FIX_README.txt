VidsGrab final YouTube compatibility patch

Extract this ZIP into your existing VidsGrab project folder and replace files when prompted.
Included:
- Dockerfile (installs FFmpeg and Deno)
- requirements.txt (updates yt-dlp with default EJS support)
- app.py (enables yt-dlp JS runtime and clearer YouTube bot-challenge errors; keeps Privacy/Terms routes)
- templates/index.html, templates/privacy.html, templates/terms.html

Then from your project folder run:
    git add Dockerfile requirements.txt app.py templates
    git commit -m "Update YouTube extractor runtime"
    git push

Render will rebuild after the push.

IMPORTANT:
This patch improves yt-dlp compatibility with YouTube's JavaScript player challenges.
It does NOT guarantee that YouTube will allow downloads from Render's shared/cloud IPs.
A server-side "Sign in to confirm you're not a bot" challenge may continue due to YouTube restrictions.
Do not upload personal Google cookies to GitHub or expose them through a public downloader.
