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
  opacity: 0;
  animation: float-whale linear infinite;
  pointer-events: none;
}}
@keyframes float-whale {{
  0%   {{ transform: translateX(-60px) translateY(0px) scaleX(1); opacity:0; }}
  5%   {{ opacity: 0.45; }}
  48%  {{ transform: translateX(var(--dist)) translateY(-14px) scaleX(1); }}
  50%  {{ transform: translateX(var(--dist)) translateY(-14px) scaleX(-1); }}
  95%  {{ opacity: 0.45; }}
  100% {{ transform: translateX(4px) translateY(0px) scaleX(-1); opacity:0; }}
}}

/* 메인 카드 */
#container {{
  position: fixed;
  bottom: 24px;
  left: 24px;
  width: 400px;
  background: rgba(225, 240, 248, 0.92);
  border-radius: 20px;
  padding: 18px 20px 14px;
  box-shadow: 0 8px 32px rgba(30,90,140,0.18);
  backdrop-filter: blur(20px);
  opacity: 0;
  transform: translateY(14px);
  transition: opacity 0.5s ease, transform 0.5s ease;
}}
#container.visible {{
  opacity: 1;
  transform: translateY(0);
}}

/* 상단: 텍스트 왼쪽 + 앨범아트 오른쪽 */
#top-row {{
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 14px;
}}
#text-col {{ flex: 1; min-width: 0; padding-right: 12px; }}
#title-wrap {{ overflow: hidden; margin-bottom: 5px; }}
#title {{
  color: #1a1a2e;
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
  display: inline-block;
  letter-spacing: -0.3px;
}}
#title.scroll {{ animation: marquee 10s linear infinite; }}
@keyframes marquee {{
  0%,15%  {{ transform: translateX(0); }}
  85%,100%{{ transform: translateX(var(--d)); }}
}}
#artist {{
  color: #5a7a8a;
  font-size: 13px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}}
#art {{
  width: 58px;
  height: 58px;
  border-radius: 14px;
  background: linear-gradient(135deg, #b8dff0, #d4eef8);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 30px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(30,90,140,0.12);
}}

/* 진행바 */
#bar-wrap {{
  position: relative;
  margin-bottom: 6px;
  padding: 6px 0;
}}
#bar-bg {{
  width: 100%;
  height: 4px;
  background: rgba(30,90,140,0.15);
  border-radius: 2px;
  overflow: visible;
  position: relative;
}}
#bar-fill {{
  height: 100%;
  width: 0%;
  background: #3a9dc8;
  border-radius: 2px;
  transition: width 0.4s linear;
  position: relative;
}}
#bar-dot {{
  position: absolute;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 13px;
  height: 13px;
  background: #3a9dc8;
  border-radius: 50%;
  left: 0%;
  transition: left 0.4s linear;
  box-shadow: 0 0 0 3px rgba(58,157,200,0.2);
}}
#times {{
  display: flex;
  justify-content: space-between;
  color: #7a9aaa;
  font-size: 11px;
}}

/* 컨트롤 버튼 */
#controls {{
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 24px;
  margin-top: 12px;
  color: #3a6070;
  font-size: 18px;
}}
#controls .btn {{ cursor: default; opacity: 0.7; user-select:none; }}
#controls .btn-play {{
  width: 38px;
  height: 38px;
  background: #3a9dc8;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 10px rgba(58,157,200,0.4);
  position: relative;
}}
#controls .btn-play .triangle {{
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 6px 0 6px 11px;
  border-color: transparent transparent transparent white;
  margin-left: 2px;
}}
#controls .btn-play .pause {{
  display: flex;
  gap: 3px;
  align-items: center;
}}
#controls .btn-play .pause span {{
  width: 3px;
  height: 13px;
  background: white;
  border-radius: 1px;
  display: block;
}}
</style>
</head>
<body>

<!-- 떠다니는 고래 4마리 -->
<div class="whale" style="top:12%; --dist:440px; animation-duration:20s; animation-delay:0s;   font-size:30px;">&#x1F433;</div>
<div class="whale" style="top:52%; --dist:400px; animation-duration:26s; animation-delay:7s;   font-size:20px;">&#x1F433;</div>
<div class="whale" style="top:78%; --dist:460px; animation-duration:22s; animation-delay:13s;  font-size:24px;">&#x1F433;</div>
<div class="whale" style="top:33%; --dist:380px; animation-duration:30s; animation-delay:4s;   font-size:16px;">&#x1F433;</div>

<div id="container">
  <div id="top-row">
    <div id="text-col">
      <div id="title-wrap"><span id="title">-</span></div>
      <div id="artist"></div>
    </div>
    <div id="art">&#x1F433;</div>
  </div>

  <div id="bar-wrap">
    <div id="bar-bg">
      <div id="bar-fill"></div>
      <div id="bar-dot"></div>
    </div>
  </div>
  <div id="times">
    <span id="cur">0:00</span>
    <span id="tot">0:00</span>
  </div>

  <div id="controls">
    <span class="btn">&#x21C5;</span>
    <span class="btn">&#x23EE;</span>
    <span class="btn-play" id="play-btn"><span class="triangle"></span></span>
    <span class="btn">&#x23ED;</span>
    <span class="btn">&#x22EE;</span>
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
const barDot    = document.getElementById('bar-dot');
const playBtn   = document.getElementById('play-btn');
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
    playBtn.innerHTML = playing
      ? '<span class="pause"><span></span><span></span></span>'
      : '<span class="triangle"></span>';
    container.classList.toggle('visible', !!d.title);
  }} catch(e) {{}}
}}

function tick() {{
  if (duration > 0) {{
    let pos = srvPos + (playing ? (Date.now()-srvTime)/1000 : 0);
    pos = Math.min(pos, duration);
    const pct = (pos/duration*100).toFixed(2);
    barFill.style.width = pct + '%';
    barDot.style.left   = pct + '%';
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
