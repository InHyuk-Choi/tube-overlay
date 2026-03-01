import time
import json
from flask import Flask, request, jsonify, Response

app = Flask(__name__)

# { userId: { title, artist, position, duration, playing, updated_at } }
sessions = {}

STALE_SECONDS = 5  # 5초 이상 업데이트 없으면 재생 중 아닌 것으로 처리


# ─── API ───────────────────────────────────────────────

@app.route("/update/<user_id>", methods=["POST"])
def update(user_id):
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"ok": False}), 400
    data["updated_at"] = time.time()
    sessions[user_id] = data
    return jsonify({"ok": True})


@app.route("/api/<user_id>")
def api(user_id):
    data = dict(sessions.get(user_id, {}))
    if not data:
        return jsonify({"title": "", "artist": "", "position": 0, "duration": 0, "playing": False})
    # 오래된 데이터면 재생 중지 처리
    if time.time() - data.get("updated_at", 0) > STALE_SECONDS:
        data["playing"] = False
        data["title"] = ""
    data.pop("updated_at", None)
    return jsonify(data)


# ─── 오버레이 ────────────────────────────────────────────

@app.route("/overlay/<user_id>")
def overlay(user_id):
    html = build_overlay(user_id)
    return Response(html, mimetype="text/html")


@app.route("/")
def index():
    return Response("<h2>Now Playing Overlay Server</h2><p>Use /overlay/YOUR_ID in OBS</p>", mimetype="text/html")


def build_overlay(user_id):
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  background: transparent;
  font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
  overflow: hidden;
}}
#container {{
  position: fixed;
  bottom: 20px;
  left: 20px;
  width: 360px;
  background: rgba(0,0,0,0.72);
  border-radius: 14px;
  padding: 13px 16px 11px;
  border-left: 4px solid #ff3b3b;
  backdrop-filter: blur(10px);
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.45s ease, transform 0.45s ease;
}}
#container.visible {{
  opacity: 1;
  transform: translateY(0);
}}
#top-row {{
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 5px;
}}
#icon {{ font-size: 13px; flex-shrink: 0; }}
#title-wrap {{ overflow: hidden; flex: 1; }}
#title {{
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  white-space: nowrap;
  display: inline-block;
}}
#title.scroll {{ animation: marquee 10s linear infinite; }}
@keyframes marquee {{
  0%,15%  {{ transform: translateX(0); }}
  85%,100%{{ transform: translateX(var(--d)); }}
}}
#artist {{
  color: #aaa;
  font-size: 11px;
  margin-bottom: 9px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
#bar-bg {{
  width: 100%;
  height: 3px;
  background: rgba(255,255,255,0.18);
  border-radius: 2px;
}}
#bar-fill {{
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #ff3b3b, #ff7c7c);
  border-radius: 2px;
  transition: width 0.4s linear;
}}
#times {{
  display: flex;
  justify-content: space-between;
  margin-top: 5px;
  color: #777;
  font-size: 10px;
}}
</style>
</head>
<body>
<div id="container">
  <div id="top-row">
    <span id="icon">&#127925;</span>
    <div id="title-wrap"><span id="title">-</span></div>
  </div>
  <div id="artist"></div>
  <div id="bar-bg"><div id="bar-fill"></div></div>
  <div id="times">
    <span id="cur">0:00</span>
    <span id="tot">0:00</span>
  </div>
</div>

<script>
const USER_ID = "{user_id}";
const API_URL = "/api/" + USER_ID;

const container = document.getElementById('container');
const titleEl   = document.getElementById('title');
const titleWrap = document.getElementById('title-wrap');
const artistEl  = document.getElementById('artist');
const barFill   = document.getElementById('bar-fill');
const curEl     = document.getElementById('cur');
const totEl     = document.getElementById('tot');

let lastTitle = '';
let srvPos = 0, srvTime = Date.now(), duration = 0, playing = false;

function fmt(s) {{
  s = Math.max(0, Math.floor(s));
  return Math.floor(s/60) + ':' + String(s%60).padStart(2,'0');
}}

function applyScroll() {{
  titleEl.classList.remove('scroll');
  void titleEl.offsetWidth;
  const over = titleEl.scrollWidth - titleWrap.clientWidth;
  if (over > 0) {{
    titleEl.style.setProperty('--d', -over - 16 + 'px');
    titleEl.classList.add('scroll');
  }}
}}

async function poll() {{
  try {{
    const r = await fetch(API_URL);
    const d = await r.json();
    if (d.title !== lastTitle) {{
      lastTitle = d.title;
      titleEl.textContent  = d.title  || '-';
      artistEl.textContent = d.artist || '';
      setTimeout(applyScroll, 80);
    }}
    duration = d.duration || 0;
    srvPos   = d.position || 0;
    srvTime  = Date.now();
    playing  = d.playing;
    container.classList.toggle('visible', !!d.title);
  }} catch(e) {{}}
}}

function tick() {{
  if (duration > 0) {{
    let pos = srvPos + (playing ? (Date.now()-srvTime)/1000 : 0);
    pos = Math.min(pos, duration);
    barFill.style.width = (pos/duration*100).toFixed(2) + '%';
    curEl.textContent   = fmt(pos);
    totEl.textContent   = fmt(duration);
  }}
}}

setInterval(poll, 1000);
setInterval(tick, 100);
poll();
</script>
</body>
</html>"""


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
