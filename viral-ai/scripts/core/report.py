"""Ghép số liệu (candidates.json) với phần phân tích (analysis.json) thành báo cáo HTML.

Dùng chung cho mọi nền tảng. Số liệu luôn lấy từ candidates.json theo ID, không lấy từ phần phân tích,
nên con số trên báo cáo không bao giờ là số do AI "nhớ lại". Cách gọi tên và bày số liệu của từng
nền tảng do module display của nền tảng đó cung cấp (platforms/<tên>/display.py).

Chạy qua CLI chung:  viral.py render <nền tảng> [--date YYYY-MM-DD]
Kết quả: reports/<nền tảng>/<ngày>.html và latest.html
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from html import escape as e

from .store import Store
from .util import age, num, short, times, when

TIER = {"mega": "Siêu viral", "viral": "Viral", "breakout": "Bứt phá", "rising": "Đang lên", "hot": "Đáng chú ý"}
PRIORITY = {"lam-ngay": "Làm ngay", "nen-lam": "Nên làm", "theo-doi": "Theo dõi"}
SLOT = {"chac-thang": "Chắc thắng", "di-truoc": "Đi trước", "bat-tin": "Bắt tin"}
CATEGORY = {"ra-mat": "Ra mắt sản phẩm", "demo": "Demo gây wow", "huong-dan": "Hướng dẫn, mẹo", "quan-diem": "Quan điểm, tranh luận",
            "so-lieu": "Số liệu, nghiên cứu", "hai-meme": "Hài, meme", "tin-nganh": "Tin ngành", "canh-bao": "Cảnh báo, rủi ro",
            "ke-chuyen": "Kể chuyện", "trend": "Bắt trend"}


def li(items) -> str:
    return "".join(f"<li>{e(str(x))}</li>" for x in items or [])


CSS = r"""
/* Bố cục: bản tin biên tập để quét nhanh — tóm tắt trước, thẻ bài sau; mỗi thẻ chia hai cột số liệu | kế hoạch đăng */
:root{
  --bg:#EEF1F4; --surface:#FFFFFF; --sunken:#E4E9EE; --ink:#16212B; --muted:#586876; --line:#D3DAE1;
  --accent:#1F4FD8; --accent-soft:#E3EAFD;
  --mega:#C2255C; --viral:#C9480F; --breakout:#6741D9; --rising:#087F5B; --hot:#586876;
  --warn:#9A5B00; --warn-soft:#FFF1D6;
  --font:"Be Vietnam Pro",system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;
  --mono:"JetBrains Mono",ui-monospace,"Cascadia Mono",Consolas,monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    color-scheme:dark;
    --bg:#0E141A; --surface:#161F29; --sunken:#1D2833; --ink:#E7EDF3; --muted:#94A4B3; --line:#2A3846;
    --accent:#8CAEFF; --accent-soft:#1B2A4D;
    --mega:#FF7AA8; --viral:#FF9A5C; --breakout:#B39DFF; --rising:#4FD1A5; --hot:#94A4B3;
    --warn:#FFC670; --warn-soft:#3A2C10;
  }
}
:root[data-theme="dark"]{
  color-scheme:dark;
  --bg:#0E141A; --surface:#161F29; --sunken:#1D2833; --ink:#E7EDF3; --muted:#94A4B3; --line:#2A3846;
  --accent:#8CAEFF; --accent-soft:#1B2A4D;
  --mega:#FF7AA8; --viral:#FF9A5C; --breakout:#B39DFF; --rising:#4FD1A5; --hot:#94A4B3;
  --warn:#FFC670; --warn-soft:#3A2C10;
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--font);font-size:15px;line-height:1.55}
a{color:var(--accent);text-decoration-thickness:1px;text-underline-offset:2px}
a:focus-visible,button:focus-visible,summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px}
.wrap{max-width:1120px;margin:0 auto;padding:28px 16px 64px;display:flex;flex-direction:column;gap:28px}
h1,h2,h3{margin:0;text-wrap:balance;line-height:1.2}
h1{font-size:clamp(26px,4vw,38px);font-weight:800;letter-spacing:-.02em}
h2{font-size:20px;font-weight:700}
h3{font-size:18px;font-weight:700}
p{margin:0}
.num{font-family:var(--mono);font-variant-numeric:tabular-nums}
.muted{color:var(--muted)}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted)}

.mast{display:flex;flex-direction:column;gap:10px;border-bottom:2px solid var(--ink);padding-bottom:20px}
.mast .lede{font-size:17px;max-width:68ch}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);border-radius:10px;overflow:hidden}
.stat{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:2px}
.stat b{font-family:var(--mono);font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}
.stat span{font-size:13px;color:var(--muted)}

.section{display:flex;flex-direction:column;gap:12px}
.themes{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.theme{background:var(--surface);border:1px solid var(--line);border-left:4px solid var(--accent);border-radius:8px;padding:12px 14px;display:flex;flex-direction:column;gap:6px}
.theme b{font-size:15px}
.theme p{font-size:14px;color:var(--muted)}
.theme .refs{display:flex;flex-wrap:wrap;gap:6px;font-size:13px}

.tablebox{overflow-x:auto;background:var(--surface);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:720px}
th,td{padding:9px 12px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{font-size:12px;font-weight:600;letter-spacing:.05em;text-transform:uppercase;color:var(--muted);background:var(--sunken);white-space:nowrap}
tr:last-child td{border-bottom:0}
td.r,th.r{text-align:right;white-space:nowrap}

.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:2px 9px;border-radius:999px;border:1px solid currentColor;white-space:nowrap}
.pill::before{content:"";width:7px;height:7px;border-radius:50%;background:currentColor}
.t-mega{color:var(--mega)} .t-viral{color:var(--viral)} .t-breakout{color:var(--breakout)} .t-rising{color:var(--rising)} .t-hot{color:var(--hot)}
.prio{font-size:12px;font-weight:700;padding:3px 10px;border-radius:4px;white-space:nowrap}
.p-lam-ngay{background:var(--ink);color:var(--bg)}
.p-nen-lam{background:var(--accent-soft);color:var(--accent)}
.p-theo-doi{background:var(--sunken);color:var(--muted)}
.chip{font-size:12px;padding:2px 8px;border-radius:4px;background:var(--sunken);color:var(--muted);white-space:nowrap}
.chip.warn{background:var(--warn-soft);color:var(--warn);font-weight:600}

.toolbar{display:flex;flex-wrap:wrap;gap:8px;align-items:center;position:sticky;top:0;z-index:5;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line)}
.toolbar button{font:inherit;font-size:14px;font-weight:600;padding:7px 14px;border-radius:999px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer}
.toolbar button[aria-pressed="true"]{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.toolbar .count{margin-left:auto;font-size:13px;color:var(--muted)}

.cards{display:flex;flex-direction:column;gap:18px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:12px;overflow:hidden;scroll-margin-top:64px}
.card.picked{border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
.card-head{display:flex;gap:14px;padding:16px 18px;border-bottom:1px solid var(--line);align-items:flex-start}
.rank{font-family:var(--mono);font-size:28px;font-weight:700;line-height:1;min-width:44px;color:var(--muted)}
.card-head .ttl{display:flex;flex-direction:column;gap:8px;flex:1;min-width:0}
.tags{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.byline{font-size:14px;color:var(--muted);overflow-wrap:anywhere}
.byline a{font-weight:600}
.card-body{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,6fr);gap:0}
.col{padding:16px 18px;display:flex;flex-direction:column;gap:14px;min-width:0}
.col + .col{border-left:1px solid var(--line);background:color-mix(in srgb,var(--sunken) 45%,var(--surface))}
.block{display:flex;flex-direction:column;gap:6px}
.block ul,.block ol{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:4px}
.quote{font-size:14px;color:var(--muted);border-left:3px solid var(--line);padding-left:10px;overflow-wrap:anywhere}
.metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:1px;background:var(--line);border:1px solid var(--line);border-radius:8px;overflow:hidden}
.m{background:var(--surface);padding:8px 10px;display:flex;flex-direction:column}
.m b{font-family:var(--mono);font-size:16px;font-variant-numeric:tabular-nums}
.m span{font-size:12px;color:var(--muted)}
.m.key b{color:var(--accent)}
.score{display:flex;flex-direction:column;gap:5px}
.score-top{display:flex;justify-content:space-between;align-items:baseline;font-size:13px;color:var(--muted)}
.score-top b{font-family:var(--mono);font-size:20px;color:var(--ink)}
.bar-row{display:grid;grid-template-columns:118px 1fr 34px;gap:8px;align-items:center;font-size:12px;color:var(--muted)}
.bar{height:6px;background:var(--sunken);border-radius:3px;overflow:hidden}
.bar i{display:block;height:100%;background:var(--accent);border-radius:3px}
.why li b{font-weight:600}
.plan{border:1px solid var(--line);border-radius:8px;background:var(--surface);padding:12px 14px;display:flex;flex-direction:column;gap:8px}
.plan h4{margin:0;font-size:13px;font-weight:700;letter-spacing:.05em;text-transform:uppercase;display:flex;justify-content:space-between;gap:8px;flex-wrap:wrap}
.plan h4 span{font-weight:500;text-transform:none;letter-spacing:0;color:var(--muted)}
.hook{font-size:16px;font-weight:600;border-left:3px solid var(--accent);padding-left:10px}
.kv{font-size:14px}
.kv b{font-weight:600}
.caption{font-size:14px;background:var(--sunken);border-radius:6px;padding:8px 10px;overflow-wrap:anywhere}
.actions{display:flex;flex-wrap:wrap;gap:8px;padding:12px 18px;border-top:1px solid var(--line);align-items:center}
.btn{font:inherit;font-size:14px;font-weight:600;padding:7px 14px;border-radius:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink);cursor:pointer;text-decoration:none;display:inline-flex;align-items:center}
.btn.primary{background:var(--accent);border-color:var(--accent);color:var(--surface)}
.btn[aria-pressed="true"]{background:var(--accent-soft);border-color:var(--accent);color:var(--accent)}
.meta-line{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:13px;color:var(--muted)}
.meta-line b{color:var(--ink);font-weight:600}
details{background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:0 16px}
details summary{cursor:pointer;font-weight:700;padding:14px 0;font-size:16px}
details .inner{padding:0 0 16px;display:flex;flex-direction:column;gap:12px;max-width:78ch}
details .inner ul{margin:0;padding-left:20px;display:flex;flex-direction:column;gap:4px}
.foot{font-size:13px;color:var(--muted)}
[hidden]{display:none!important}
@media (max-width:760px){
  .card-body{grid-template-columns:1fr}
  .col + .col{border-left:0;border-top:1px solid var(--line)}
  .rank{font-size:22px;min-width:32px}
  .bar-row{grid-template-columns:96px 1fr 30px}
}
@media (prefers-reduced-motion:no-preference){html{scroll-behavior:smooth}}
"""

JS = r"""
(function(){
  var KEY='viral-ai-picked-'+document.body.dataset.date, picked={};
  try{picked=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
  var cards=[].slice.call(document.querySelectorAll('.card')), filter='all', chan='', onlyPicked=false;
  function save(){try{localStorage.setItem(KEY,JSON.stringify(picked))}catch(e){}}
  function apply(){
    var shown=0;
    cards.forEach(function(c){
      var ok=(filter==='all'||c.dataset.prio===filter)&&(!chan||c.dataset.channel===chan)&&(!onlyPicked||picked[c.id]);
      c.hidden=!ok; if(ok)shown++;
      c.classList.toggle('picked',!!picked[c.id]);
      var b=c.querySelector('[data-act=pick]');
      b.setAttribute('aria-pressed',picked[c.id]?'true':'false');
      b.textContent=picked[c.id]?'Đã chọn làm':'Chọn làm __NOUN__ này';
    });
    document.getElementById('shown').textContent='Đang hiện '+shown+'/'+cards.length+' __NOUN__, đã chọn '+Object.keys(picked).filter(function(k){return picked[k]}).length;
  }
  document.querySelectorAll('[data-filter]').forEach(function(b){
    b.addEventListener('click',function(){
      filter=b.dataset.filter;
      document.querySelectorAll('[data-filter]').forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});
      apply();
    });
  });
  document.querySelectorAll('button[data-channel]').forEach(function(b){
    b.addEventListener('click',function(){
      chan=(chan===b.dataset.channel)?'':b.dataset.channel;
      document.querySelectorAll('button[data-channel]').forEach(function(x){x.setAttribute('aria-pressed',x.dataset.channel===chan?'true':'false')});
      apply();
    });
  });
  var op=document.getElementById('only-picked');
  op.addEventListener('click',function(){onlyPicked=!onlyPicked;op.setAttribute('aria-pressed',onlyPicked?'true':'false');apply()});
  cards.forEach(function(c){
    c.querySelector('[data-act=pick]').addEventListener('click',function(){picked[c.id]=!picked[c.id];save();apply()});
    var cp=c.querySelector('[data-act=copy]');
    cp.addEventListener('click',function(){
      var t=c.querySelector('template').content.textContent.trim();
      function done(ok){cp.textContent=ok?'Đã chép':'Không chép được, hãy bôi đen thủ công';setTimeout(function(){cp.textContent='Chép brief'},1800)}
      try{navigator.clipboard.writeText(t).then(function(){done(true)},function(){done(false)})}catch(e){done(false)}
    });
  });
  apply();
})();
"""


def render_card(rank: int, pk: dict, p: dict, D) -> str:
    """D là module display của nền tảng."""
    tk, vd = pk.get("tiktok") or {}, pk.get("video") or {}
    prio = pk.get("priority", "nen-lam")
    sig_chips = "".join(f'<span class="chip{" warn" if s in D.WARN_SIGNALS else ""}">{e(D.SIGNAL.get(s, s))}</span>' for s in p["signals"])
    amp = ""
    if p.get("amplifiers"):
        amp = '<span class="chip">Chia sẻ lại bởi ' + ", ".join("@" + e(a) for a in p["amplifiers"][:4]) + "</span>"
    media = D.media_note(p)
    metric_cells = "".join(f'<div class="m{" key" if key else ""}"><b>{e(val)}</b><span>{e(lab)}</span></div>' for val, lab, key in D.metrics(p))
    sp = p["score_parts"]
    bars = "".join(
        f'<div class="bar-row"><span>{lab}</span><div class="bar"><i style="width:{max(sp[k], 2)}%"></i></div><span class="num">{sp[k]}</span></div>'
        for lab, k in D.SCORE_BARS if k in sp)
    why = "".join(f"<li><b>{e(w.get('factor', ''))}.</b> {e(w.get('evidence', ''))}</li>" for w in pk.get("why_viral", []))
    growth = ""
    if p.get("views_gain_since_last_run"):
        growth = f'<span>Từ lần quét trước: <b class="num">+{short(p["views_gain_since_last_run"])}</b> lượt xem</span>'
    brief = "\n".join(filter(None, [
        f"BRIEF: {pk.get('title_vi', '')}",
        f"Kênh: {pk['channel']}" if pk.get("channel") else "",
        f"Nguồn: {D.brief_source(p)}",
        f"Tóm tắt: {pk.get('summary_vi', '')}",
        f"Góc Việt hoá: {pk.get('vn_angle', '')}",
        "",
        f"TIKTOK ({tk.get('format', '')}, {tk.get('length', '')})",
        f"Hook: {tk.get('hook', '')}",
        *[f"  {i}. {b}" for i, b in enumerate(tk.get("beats", []), 1)],
        f"Caption: {tk.get('caption', '')} {' '.join(tk.get('hashtags', []))}",
        "",
        f"VIDEO DÀI ({vd.get('fit', '')}, {vd.get('length', '')})",
        f"Tiêu đề: {vd.get('title', '')}",
        *[f"  {i}. {b}" for i, b in enumerate(vd.get("outline", []), 1)],
        "",
        f"Lưu ý: {pk.get('risk', '')}",
    ]))
    quote = D.extra_html(p)
    lesson = ""
    if pk.get("format_lesson"):
        lesson = f'<div class="block"><span class="eyebrow">Công thức đáng học</span><p>{e(pk["format_lesson"])}</p></div>'
    video_block = ""
    if vd:
        video_block = f"""
        <div class="plan">
          <h4>Video dài <span>{e(vd.get('fit', ''))}{' · ' + e(vd.get('length', '')) if vd.get('length') else ''}</span></h4>
          {f'<p class="kv"><b>Tiêu đề gợi ý:</b> {e(vd.get("title", ""))}</p>' if vd.get('title') else ''}
          {f'<div class="block"><ol>{li(vd.get("outline"))}</ol></div>' if vd.get('outline') else ''}
          {f'<p class="kv muted">{e(vd.get("note", ""))}</p>' if vd.get('note') else ''}
        </div>"""
    return f"""
  <article class="card" id="p{rank}" data-prio="{e(prio)}" data-channel="{e(pk.get('channel', ''))}">
    <div class="card-head">
      <div class="rank">{rank:02d}</div>
      <div class="ttl">
        <div class="tags">
          {f'<span class="prio p-lam-ngay">{e(pk["channel"])}</span>' if pk.get('channel') else ''}
          {f'<span class="chip">{e(SLOT.get(pk["slot"], pk["slot"]))}</span>' if pk.get('slot') else ''}
          <span class="prio p-{e(prio)}">{e(PRIORITY.get(prio, prio))}</span>
          <span class="pill t-{e(p['tier'])}">{e(TIER.get(p['tier'], p['tier']))}</span>
          <span class="chip">{e(CATEGORY.get(pk.get('category', ''), pk.get('category', '')))}</span>
          <span class="chip">{e(D.ORIGIN.get(p['origin'], ''))}</span>
        </div>
        <h3>{e(pk.get('title_vi', ''))}</h3>
        <p class="byline"><a href="{e(p['url'])}" target="_blank" rel="noopener">@{e(p['author'])}</a> · {e(p['author_name'])} · {num(p['followers'])} follower · đăng {when(p['created_utc'])} (giờ VN), {age(p['age_hours'])}{' · ' + ', '.join(media) if media else ''}</p>
      </div>
    </div>
    <div class="card-body">
      <div class="col">
        <p>{e(pk.get('summary_vi', ''))}</p>
        {quote}
        <div class="metrics">{metric_cells}</div>
        <div class="score">
          <div class="score-top"><span>Điểm viral</span><b>{p['score']:.0f}<span class="muted" style="font-size:13px">/100</span></b></div>
          {bars}
        </div>
        <div class="tags">{sig_chips}{amp}</div>
        <div class="block why"><span class="eyebrow">Vì sao viral</span><ul>{why}</ul></div>
      </div>
      <div class="col">
        <div class="block"><span class="eyebrow">Góc Việt hoá</span><p>{e(pk.get('vn_angle', ''))}</p></div>
        {lesson}
        <div class="plan">
          <h4>TikTok <span>{e(tk.get('format', ''))}{' · ' + e(tk.get('length', '')) if tk.get('length') else ''}</span></h4>
          <p class="hook">{e(tk.get('hook', ''))}</p>
          <div class="block"><ol>{li(tk.get('beats'))}</ol></div>
          <p class="caption"><b>Caption:</b> {e(tk.get('caption', ''))} <span class="muted">{e(' '.join(tk.get('hashtags', [])))}</span></p>
        </div>{video_block}
        <div class="meta-line">
          <span>Công sức: <b>{e(pk.get('effort', '–'))}</b></span>
          <span>Nên đăng: <b>{e(pk.get('deadline', '–'))}</b></span>
          <span>Hợp kênh: <b>{e(str(pk.get('fit', '–')))}/5</b></span>
          {growth}
        </div>
        {f'<p class="kv"><b>Lưu ý:</b> {e(pk.get("risk", ""))}</p>' if pk.get('risk') else ''}
      </div>
    </div>
    <div class="actions">
      <a class="btn primary" href="{e(p['url'])}" target="_blank" rel="noopener">{e(D.OPEN_LABEL)}</a>
      <button class="btn" type="button" data-act="pick" aria-pressed="false">Chọn làm {e(D.NOUN)} này</button>
      <button class="btn" type="button" data-act="copy">Chép brief</button>
      <template>{e(brief)}</template>
    </div>
  </article>"""


def render(platform: str, D, date: str = "") -> int:
    """platform: tên nền tảng; D: module display của nền tảng; date: YYYY-MM-DD hoặc rỗng (ngày mới nhất)."""
    store = Store(platform)
    day = store.day_dir(date)
    if not day or not (day / "candidates.json").exists():
        print(f"Chưa có dữ liệu cho {platform}. Hãy chạy: viral.py collect {platform}", file=sys.stderr)
        return 1
    cand = json.loads((day / "candidates.json").read_text(encoding="utf-8"))
    an_path = day / "analysis.json"
    if not an_path.exists():
        print(f"Thiếu {an_path}. Bước phân tích chưa chạy.", file=sys.stderr)
        return 1
    an = json.loads(an_path.read_text(encoding="utf-8"))
    meta = cand["meta"]
    by_id = {p["id"]: p for p in cand["posts"]}

    picks, missing = [], []
    for pk in an.get("picks", []):
        p = by_id.get(str(pk.get("id")))
        (picks.append((pk, p)) if p else missing.append(str(pk.get("id"))))
    order = {"lam-ngay": 0, "nen-lam": 1, "theo-doi": 2}
    channels = list(dict.fromkeys(pk.get("channel") for pk, _ in picks if pk.get("channel")))
    ch_order = {c: i for i, c in enumerate(channels)}
    picks.sort(key=lambda x: (ch_order.get(x[0].get("channel"), 99), order.get(x[0].get("priority"), 9), -x[1]["score"]))
    rank_of = {pk["id"]: i for i, (pk, _) in enumerate(picks, 1)}

    d = datetime.strptime(meta["date"], "%Y-%m-%d")
    date_vi = d.strftime("%d/%m/%Y")
    cards = "".join(render_card(i, pk, p, D) for i, (pk, p) in enumerate(picks, 1))
    ch_buttons = "".join(f'<button type="button" data-channel="{e(c)}" aria-pressed="false">{e(c)}</button>' for c in channels)
    qlabel, qfn = D.QUICK_COL
    N = D.NOUN

    quick = "".join(
        f'<tr><td class="num">{i:02d}</td><td><a href="#p{i}">{e(pk.get("title_vi", ""))}</a><br><span class="muted">@{e(p["author"])}</span></td>'
        f'<td>{e(pk.get("channel", ""))}<br><span class="muted">{e(SLOT.get(pk.get("slot"), ""))}</span></td>'
        f'<td><span class="prio p-{e(pk.get("priority", ""))}">{e(PRIORITY.get(pk.get("priority"), ""))}</span></td>'
        f'<td><span class="pill t-{e(p["tier"])}">{e(TIER[p["tier"]])}</span></td>'
        f'<td class="r num">{short(p["views"])}</td><td class="r num">{qfn(p)}</td>'
        f'<td class="r num">{times(p["outlier_ratio"]) if p["baseline_posts"] else "–"}</td>'
        f'<td>{e((pk.get("tiktok") or {}).get("format", ""))}</td><td>{e((pk.get("video") or {}).get("fit", ""))}</td></tr>'
        for i, (pk, p) in enumerate(picks, 1))

    themes = ""
    for t in an.get("themes", []):
        refs = "".join(f'<a href="#p{rank_of[i]}">{N.capitalize()} {rank_of[i]:02d}</a>' for i in map(str, t.get("post_ids", [])) if i in rank_of)
        themes += f'<div class="theme"><b>{e(t.get("name", ""))}</b><p>{e(t.get("summary", ""))}</p><div class="refs">{refs}</div></div>'

    skipped = {str(s["id"]): s.get("reason", "") for s in an.get("skipped", [])}
    rest_rows = "".join(
        f'<tr><td><a href="{e(p["url"])}" target="_blank" rel="noopener">@{e(p["author"])}</a></td>'
        f'<td>{e(re.sub(chr(10), " ", p["text"])[:110])}…</td><td><span class="pill t-{e(p["tier"])}">{e(TIER[p["tier"]])}</span></td>'
        f'<td class="r num">{short(p["views"])}</td><td class="r num">{qfn(p)}</td><td class="r num">{p["score"]:.0f}</td>'
        f'<td class="muted">{e(skipped.get(p["id"], "Không chọn"))}</td></tr>'
        for p in cand["posts"] if p["id"] not in rank_of)

    hn = "".join(f'<li><a href="{e(h["hn"])}" target="_blank" rel="noopener">{e(h["title"])}</a> <span class="muted num">{h["points"]} điểm, {h["comments"]} bình luận</span></li>'
                 for h in cand.get("context", {}).get("hackernews", [])[:10])
    n_now = sum(1 for pk, _ in picks if pk.get("priority") == "lam-ngay")
    tiles = "".join(f'<div class="stat"><b>{e(v)}</b><span>{e(lab)}</span></div>' for v, lab in D.stat_tiles(meta, len(picks), n_now))
    extra_sections = "".join(f'<details><summary>{e(title)}</summary><div class="inner">{body}</div></details>'
                             for title, body in D.context_sections(cand))

    html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(D.PAGE_TITLE)} {d.strftime('%d-%m-%Y')}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body data-date="{e(platform)}-{e(meta['date'])}">
<div class="wrap">
  <header class="mast">
    <span class="eyebrow">Bản tin ý tưởng nội dung · {e(D.NAME)} · {date_vi} · {meta['window_hours']} giờ gần nhất</span>
    <h1>{e(D.TITLE)}</h1>
    <p class="lede">{e(an.get('headline', ''))}</p>
    <p class="foot">Quét lúc {e(meta['generated_local'][:16])} giờ máy. {e(D.FRESHNESS_NOTE)}</p>
  </header>

  <div class="stats">{tiles}</div>

  <section class="section">
    <h2>Chủ đề nóng</h2>
    <div class="themes">{themes}</div>
  </section>

  <section class="section">
    <h2>Nhìn nhanh {len(picks)} {N}</h2>
    <div class="tablebox"><table>
      <thead><tr><th>#</th><th>Ý tưởng</th><th>Kênh</th><th>Ưu tiên</th><th>Hạng</th><th class="r">Xem</th><th class="r">{e(qlabel)}</th><th class="r">So mức thường</th><th>TikTok</th><th>Video dài</th></tr></thead>
      <tbody>{quick}</tbody>
    </table></div>
  </section>

  <section class="section">
    <h2>Chi tiết từng {N}</h2>
    <div class="toolbar" role="group" aria-label="Lọc {N}">
      <button type="button" data-filter="all" aria-pressed="true">Tất cả</button>
      <button type="button" data-filter="lam-ngay" aria-pressed="false">Làm ngay</button>
      <button type="button" data-filter="nen-lam" aria-pressed="false">Nên làm</button>
      <button type="button" data-filter="theo-doi" aria-pressed="false">Theo dõi</button>
      {ch_buttons}
      <button type="button" id="only-picked" aria-pressed="false">Chỉ {N} tôi đã chọn</button>
      <span class="count" id="shown"></span>
    </div>
    <div class="cards">{cards}</div>
  </section>

  <section class="section">
    <details>
      <summary>Ứng viên còn lại ({len(cand['posts']) - len(picks)} {N} lọt vòng chấm điểm nhưng không chọn)</summary>
      <div class="inner" style="max-width:none"><div class="tablebox"><table>
        <thead><tr><th>Tác giả</th><th>Nội dung</th><th>Hạng</th><th class="r">Xem</th><th class="r">{e(qlabel)}</th><th class="r">Điểm</th><th>Lý do không chọn</th></tr></thead>
        <tbody>{rest_rows}</tbody></table></div></div>
    </details>
    {extra_sections}
    <details>
      <summary>Giới công nghệ đang bàn gì (Hacker News)</summary>
      <div class="inner"><ul>{hn or '<li>Không có dữ liệu.</li>'}</ul></div>
    </details>
    <details>
      <summary>Thế nào là viral trên {e(D.NAME)}, và điểm số tính ra sao</summary>
      <div class="inner">{D.method_html(meta)}
      </div>
    </details>
  </section>
  <p class="foot">Phần đánh dấu chọn chỉ lưu trên trình duyệt này. Khi dùng video hay hình của người khác, hãy ghi nguồn và thêm phần bình luận của riêng bạn thay vì đăng lại nguyên bản.</p>
</div>
<script>{JS.replace('__NOUN__', N)}</script>
</body>
</html>
"""
    store.report_dir.mkdir(parents=True, exist_ok=True)
    out = store.report_dir / f"{meta['date']}.html"
    out.write_text(html, encoding="utf-8")
    (store.report_dir / "latest.html").write_text(html, encoding="utf-8")
    # đánh dấu đã chọn vào lịch sử để lần quét sau không gợi ý lại
    try:
        store.mark_picked([pk["id"] for pk, _ in picks], meta["date"])
    except Exception as ex:
        print(f"Không cập nhật được history.json: {ex}", file=sys.stderr)
    print(f"ĐÃ LƯU: {out}")
    if missing:
        print("CẢNH BÁO: các ID trong analysis.json không có trong candidates.json (bị bỏ qua):", ", ".join(missing))
    print(f"{len(picks)} {N} trong báo cáo.")
    return 0
