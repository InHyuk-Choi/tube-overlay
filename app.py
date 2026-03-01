import time
import json
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

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
  font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', Arial, sans-serif;
  overflow: hidden;
}}

/* 떠다니는 고래들 */
.whale {{
  position: fixed;
  font-size: 28px;
  opacity: 0;
  animation: float-whale linear infinite;
  pointer-events: none;
  filter: drop-shadow(0 0 6px rgba(78,201,225,0.4));
}}
@keyframes float-whale {{
  0%   {{ transform: translateX(-60px) translateY(0px) scaleX(1); opacity:0; }}
  5%   {{ opacity: 0.55; }}
  48%  {{ transform: translateX(var(--dist)) translateY(-18px) scaleX(1); }}
  50%  {{ transform: translateX(var(--dist)) translateY(-18px) scaleX(-1); }}
  95%  {{ opacity: 0.55; }}
  100% {{ transform: translateX(0px) translateY(0px) scaleX(-1); opacity:0; }}
}}

/* 메인 카드 */
#container {{
  position: fixed;
  bottom: 24px;
  left: 24px;
  width: 380px;
  background: linear-gradient(135deg, rgba(8,28,58,0.88) 0%, rgba(10,42,80,0.88) 100%);
  border-radius: 18px;
  padding: 16px 18px 14px;
  border: 1px solid rgba(78,201,225,0.25);
  box-shadow: 0 8px 32px rgba(0,20,60,0.5), inset 0 1px 0 rgba(78,201,225,0.15);
  backdrop-filter: blur(16px);
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 0.5s ease, transform 0.5s ease;
  overflow: hidden;
}}
#container.visible {{
  opacity: 1;
  transform: translateY(0);
}}

/* 카드 내부 배경 고래 */
#bg-whale {{
  position: absolute;
  right: -10px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 90px;
  opacity: 0.06;
  pointer-events: none;
  user-select: none;
}}

/* 상단: 앨범아트 + 텍스트 */
#top-row {{
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 14px;
  position: relative;
}}
#art {{
  width: 52px;
  height: 52px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0e4d6e, #1a8fa8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.35);
  animation: art-pulse 3s ease-in-out infinite;
}}
@keyframes art-pulse {{
  0%,100% {{ box-shadow: 0 4px 12px rgba(0,0,0,0.35); }}
  50%      {{ box-shadow: 0 4px 20px rgba(78,201,225,0.3); }}
}}
#text-col {{ flex: 1; min-width: 0; }}
#title-wrap {{ overflow: hidden; margin-bottom: 4px; }}
#title {{
  color: #ffffff;
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  display: inline-block;
  letter-spacing: -0.2px;
}}
#title.scroll {{ animation: marquee 10s linear infinite; }}
@keyframes marquee {{
  0%,15%  {{ transform: translateX(0); }}
  85%,100%{{ transform: translateX(var(--d)); }}
}}
#artist {{
  color: #7ab8cc;
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}

/* 진행바 */
#bar-wrap {{
  position: relative;
  margin-bottom: 7px;
}}
#bar-bg {{
  width: 100%;
  height: 4px;
  background: rgba(255,255,255,0.12);
  border-radius: 2px;
  overflow: visible;
}}
#bar-fill {{
  height: 100%;
  width: 0%;
  background: linear-gradient(90deg, #1a8fa8, #4ec9e1);
  border-radius: 2px;
  transition: width 0.4s linear;
  position: relative;
}}
#bar-fill::after {{
  content: '';
  position: absolute;
  right: -5px;
  top: 50%;
  transform: translateY(-50%);
  width: 10px;
  height: 10px;
  background: #4ec9e1;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(78,201,225,0.8);
}}
#times {{
  display: flex;
  justify-content: space-between;
  color: #4a7a8a;
  font-size: 10px;
  letter-spacing: 0.3px;
}}
</style>
</head>
<body>

<!-- 떠다니는 고래 4마리 -->
<div class="whale" style="top:15%; --dist:420px; animation-duration:18s; animation-delay:0s;">&#x1F433;</div>
<div class="whale" style="top:55%; --dist:380px; animation-duration:24s; animation-delay:6s; font-size:18px;">&#x1F433;</div>
<div class="whale" style="top:75%; --dist:460px; animation-duration:20s; animation-delay:11s; font-size:22px;">&#x1F433;</div>
<div class="whale" style="top:35%; --dist:400px; animation-duration:28s; animation-delay:3s; font-size:16px;">&#x1F433;</div>

<div id="container">
  <div id="bg-whale">&#x1F433;</div>
  <div id="top-row">
    <div id="art">&#x1F3B5;</div>
    <div id="text-col">
      <div id="title-wrap"><span id="title">-</span></div>
      <div id="artist"></div>
    </div>
  </div>
  <div id="bar-wrap">
    <div id="bar-bg"><div id="bar-fill"></div></div>
  </div>
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
