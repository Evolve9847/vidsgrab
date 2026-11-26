from flask import Flask,request,jsonify,render_template,send_file,abort
import yt_dlp,uuid,threading,os
from pathlib import Path
app=Flask(__name__); ROOT=Path(__file__).parent; OUT=ROOT/"downloads"; OUT.mkdir(exist_ok=True)
jobs={}; lock=threading.Lock()
def valid(u): return u.startswith(("https://","http://")) and len(u)<4096

def friendly_ytdlp_error(error):
    """Translate common YouTube server-side bot challenges into a clear user message."""
    raw = str(error)
    low = raw.lower()
    if ("sign in to confirm" in low or "not a bot" in low or
            "confirm you're not a bot" in low or "login required" in low or
            "use --cookies" in low):
        return (
            "YouTube is asking this hosting server to verify that it is not a bot. "
            "This is a YouTube-side restriction and cannot be reliably fixed by the website. "
            "Try again later, or download content you own through YouTube Studio. "
            "Do not upload personal Google cookies to this public website."
        )
    return raw[:450]
@app.get("/")
def home():
 site_url=os.environ.get("SITE_URL",request.url_root.rstrip("/"))
 return render_template("index.html",site_url=site_url)
@app.get("/privacy")
def privacy():
 return render_template("privacy.html",site_url=os.environ.get("SITE_URL",request.url_root.rstrip("/")))
@app.get("/terms")
def terms():
 return render_template("terms.html",site_url=os.environ.get("SITE_URL",request.url_root.rstrip("/")))
@app.get("/robots.txt")
def robots():
 base=os.environ.get("SITE_URL",request.url_root.rstrip("/"))
 body="User-agent: *\nAllow: /\nSitemap: "+base+"/sitemap.xml\n"
 return app.response_class(body,mimetype="text/plain")
@app.get("/sitemap.xml")
def sitemap():
 base=os.environ.get("SITE_URL",request.url_root.rstrip("/"))
 xml='<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+base+path+'</loc><changefreq>monthly</changefreq><priority>'+priority+'</priority></url>' for path,priority in [("/","1.0"),("/privacy","0.3"),("/terms","0.3")])+'</urlset>' 
 return app.response_class(xml,mimetype="application/xml")
@app.get("/healthz")
def healthz():
 return jsonify(ok=True)
@app.post("/api/info")
def info():
 u=(request.json or {}).get("url","").strip()
 if not valid(u): return jsonify(error="Enter a valid public video URL"),400
 try:
  with yt_dlp.YoutubeDL({
   "quiet":True,
   "skip_download":True,
   "noplaylist":True,
   "js_runtimes":{"deno":{}},
   "remote_components":{"ejs:github":{}},
  }) as y: m=y.extract_info(u,download=False)
  hs=sorted({f.get("height") for f in m.get("formats",[]) if f.get("height") and f.get("vcodec")!="none"})
  return jsonify(title=m.get("title","Video"),thumbnail=m.get("thumbnail"),duration=m.get("duration"),heights=hs)
 except Exception as e: return jsonify(error=friendly_ytdlp_error(e)),400
@app.post("/api/download")
def start():
 d=request.json or {}; u=d.get("url","").strip(); mode=d.get("mode","video"); quality=str(d.get("quality","best")); audio_quality=str(d.get("audio_quality","192")); selected_audio_quality=audio_quality if audio_quality in {"128","192","256","320"} else "192"
 if not valid(u): return jsonify(error="Enter a valid URL"),400
 jid=uuid.uuid4().hex; jobs[jid]={"status":"queued","progress":0,"error":"","path":None,"name":""}
 def hook(x):
  with lock:
   j=jobs[jid]
   if x["status"]=="downloading":
    total=x.get("total_bytes") or x.get("total_bytes_estimate") or 0
    pct=int(100*x.get("downloaded_bytes",0)/total) if total else j["progress"]
    j.update(status="downloading",progress=max(j["progress"],min(98,pct)))
   else:j.update(status="processing",progress=99)
 def work():
  try:
   # Prefer broadly compatible H.264 video + AAC/M4A audio for MP4.
   # Avoid selecting AV1/VP9-only streams (e.g. YouTube itag 398) as the first choice.
   if mode == "audio":
    fmt = "bestaudio[ext=m4a]/bestaudio/best"
   elif quality == "best":
    fmt = "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/best[ext=mp4]/best"
   else:
    fmt = f"bestvideo[ext=mp4][vcodec^=avc1][height<={quality}]+bestaudio[ext=m4a]/best[ext=mp4][height<={quality}]/best[height<={quality}]/best"
   opts={"format":fmt,"outtmpl":str(OUT/(jid+"_%(title).100B.%(ext)s")),"noplaylist":True,"quiet":True,"progress_hooks":[hook],"merge_output_format":"mp4","restrictfilenames":True,
          "js_runtimes":{"deno":{}},
          "remote_components":{"ejs:github":{}}}
   if mode=="audio":
    # The validated bitrate is captured before the worker thread starts.
    opts["postprocessors"]=[{"key":"FFmpegExtractAudio","preferredcodec":"mp3","preferredquality":selected_audio_quality}]
   with yt_dlp.YoutubeDL(opts) as y:
    y.download([u])

   # yt-dlp writes: <jobid>_<title>.<ext>; the previous glob
   # (<jobid>_.*) incorrectly expected a dot immediately after the underscore.
   # Find the final output for this job, excluding partial/temp files.
   candidates = [
    p for p in OUT.glob(jid + "_*")
    if p.is_file()
    and not p.name.endswith((".part", ".ytdl", ".temp"))
    and ".part-" not in p.name
   ]

   # If post-processing changed the extension, the final file is still
   # prefixed by this job ID. Pick the newest non-empty final artifact.
   candidates = [p for p in candidates if p.stat().st_size > 0]
   if not candidates:
    raise Exception("Download finished, but final output file was not found. Check FFmpeg/yt-dlp post-processing.")

   p = max(candidates, key=lambda x: x.stat().st_mtime)
   with lock:
    jobs[jid].update(status="done", progress=100, path=str(p), name=p.name)
  except Exception as e:
   err=friendly_ytdlp_error(e)
   # If MP3 extraction fails in FFmpeg, keep the downloaded source audio
   # (typically M4A) and still deliver it rather than losing the whole job.
   if mode=="audio":
    fallback = [
     p for p in OUT.glob(jid + "_*")
     if p.is_file()
     and p.suffix.lower() in {".m4a", ".aac", ".opus", ".webm", ".mp3"}
     and p.stat().st_size > 0
     and not p.name.endswith((".part", ".ytdl", ".temp"))
     and ".part-" not in p.name
    ]
    if fallback:
     p=max(fallback,key=lambda x:x.stat().st_mtime)
     with lock:
      jobs[jid].update(status="done",progress=100,path=str(p),name=p.name,
       error="MP3 conversion failed; delivering original audio as " + p.suffix.upper() + ". Update/fix FFmpeg to enable MP3 quality conversion.")
    else:
     with lock: jobs[jid].update(status="error",error=err[:450])
   else:
    with lock: jobs[jid].update(status="error",error=err[:450])
 threading.Thread(target=work,daemon=True).start(); return jsonify(job=jid)
@app.get("/api/progress/<jid>")
def progress(jid):
 j=jobs.get(jid)
 if not j:return jsonify(error="Unknown job"),404
 return jsonify(status=j["status"],progress=j["progress"],error=j["error"],name=j["name"])
@app.get("/api/file/<jid>")
def file(jid):
 j=jobs.get(jid)
 if not j or j["status"]!="done" or not j["path"]:abort(404)
 return send_file(j["path"],as_attachment=True,download_name=j["name"])
if __name__=="__main__":app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")))
