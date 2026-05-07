#!/usr/bin/env python3
"""
GarakEye - Garak JSONL -> HTML Report Generator
Author  : crazywifi (LazyHacker) — https://github.com/crazywifi
Usage   : python garak_report.py <input.jsonl> [output.html]

If output.html is omitted, the report is saved as <input>_report.html
in the same directory.
"""

import json
import sys
import os
import html
from datetime import datetime
from collections import defaultdict


# ── helpers ─────────────────────────────────────────────────────────────────

def load_jsonl(filepath):
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def parse_entries(entries):
    data = {
        "config": None,
        "attempts": [],
        "run_id":     "N/A",
        "start_time": "N/A",
        "probe_spec": "N/A",
        "target_type":"N/A",
        "garak_version": "N/A",
    }
    for entry in entries:
        t = entry.get("entry_type", "")
        if t == "start_run setup":
            data["config"]      = entry
            data["run_id"]      = entry.get("transient.run_id", "N/A")
            data["start_time"]  = entry.get("transient.starttime_iso", "N/A")
            data["probe_spec"]  = entry.get("plugins.probe_spec", "N/A")
            data["target_type"] = entry.get("plugins.target_type", "N/A")
        elif t == "init":
            data["garak_version"] = entry.get("garak_version", "N/A")
        elif t == "attempt":
            data["attempts"].append(entry)
    return data


def esc(s):
    return html.escape(str(s) if s is not None else "")


def hit_stats(attempt):
    conversations    = attempt.get("conversations", [])
    detector_results = attempt.get("detector_results", {})
    total     = len(conversations)
    hit_count = 0
    for results in detector_results.values():
        if isinstance(results, list):
            hit_count = sum(1 for r in results if r == 1)
    return total, hit_count


# ── ring SVG ─────────────────────────────────────────────────────────────────

def score_ring(pct):
    r   = 40
    circ = 2 * 3.14159 * r
    filled = circ * pct / 100
    gap    = circ - filled
    color  = "#00e090" if pct >= 80 else ("#fbbf24" if pct >= 50 else "#ff3b6b")
    cls    = "good" if pct >= 80 else ("warn" if pct >= 50 else "bad")
    return f"""<div class="score-ring">
      <svg width="100" height="100" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="{r}" fill="none" stroke="#1e2128" stroke-width="10"/>
        <circle cx="50" cy="50" r="{r}" fill="none" stroke="{color}" stroke-width="10"
          stroke-dasharray="{filled:.1f} {gap:.1f}" stroke-linecap="round"
          transform="rotate(-90 50 50)"/>
      </svg>
      <div class="score-ring-text">
        <div class="score-pct {cls}">{pct:.0f}%</div>
        <div class="score-ring-label">BLOCKED</div>
      </div>
    </div>"""


# ── attempt card ──────────────────────────────────────────────────────────────

def attempt_card(idx, attempt):
    probe  = attempt.get("probe_classname", "Unknown")
    goal   = attempt.get("goal", "N/A")
    notes  = attempt.get("notes") or {}
    settings = notes.get("settings") or {}
    triggers = notes.get("triggers", [])
    conversations    = attempt.get("conversations", [])
    detector_results = attempt.get("detector_results", {})

    total, hits = hit_stats(attempt)
    pct = ((total - hits) / total * 100) if total else 100
    s_cls = "status-pass" if hits == 0 else "status-fail"
    s_lbl = f"&#10003; {total - hits}/{total} BLOCKED" if hits == 0 else f"&#10007; {hits}/{total} INJECTED"

    attack_label  = settings.get("attack_label", "N/A")
    attack_instr  = settings.get("attack_instruction", "N/A")
    rogue         = settings.get("attack_rogue_string", "N/A")
    delim         = settings.get("attack_settings_delimiter", "-")
    esc_times     = settings.get("attack_settings_escape_times", "N/A")

    triggers_html = "".join(f'<code class="chip">{esc(t)}</code>' for t in triggers) \
                    or '<span class="muted">None defined</span>'

    # conversations
    conv_items = ""
    for ci, conv in enumerate(conversations):
        user_text = asst_text = ""
        for turn in conv.get("turns", []):
            role    = turn.get("role", "")
            content = turn.get("content", {})
            text    = content.get("text", "") if isinstance(content, dict) else str(content)
            if role == "user":
                user_text = text
            elif role == "assistant":
                asst_text = text

        is_hit = any(
            isinstance(res, list) and ci < len(res) and res[ci] == 1
            for res in detector_results.values()
        )
        item_cls   = "conv-hit"  if is_hit else "conv-pass"
        res_cls    = "injected"  if is_hit else "blocked"
        res_lbl    = "&#9888; INJECTED" if is_hit else "&#10003; BLOCKED"

        safe_resp = esc(asst_text)
        for trig in triggers:
            safe_t    = esc(trig)
            safe_resp = safe_resp.replace(safe_t, f'<mark class="hl">{safe_t}</mark>')

        conv_items += f"""
        <div class="conv-item {item_cls}">
          <div class="conv-hdr">
            <span>Generation {ci + 1}</span>
            <span class="conv-res {res_cls}">{res_lbl}</span>
          </div>
          <div class="conv-body">
            <div class="msg-wrap user-wrap">
              <div class="msg-lbl">&#128228; Payload Sent</div>
              <pre class="msg-pre">{esc(user_text)}</pre>
            </div>
            <div class="msg-wrap asst-wrap">
              <div class="msg-lbl">&#128229; Model Response</div>
              <pre class="msg-pre">{safe_resp}</pre>
            </div>
          </div>
        </div>"""

    return f"""
  <div class="card">
    <div class="card-hdr" onclick="toggle({idx})">
      <div class="card-left">
        <span class="idx">#{idx + 1}</span>
        <div>
          <div class="probe-name">{esc(probe)}</div>
          <div class="goal-text">{esc(goal)}</div>
        </div>
      </div>
      <div class="card-right">
        <span class="status-badge {s_cls}">{s_lbl}</span>
        <span class="chev" id="chev-{idx}">&#9660;</span>
      </div>
    </div>
    <div class="card-body" id="body-{idx}">

      <div class="info-grid">
        <div class="info-blk">
          <div class="ib-label">Attack Type</div>
          <div class="ib-val">{esc(attack_label)}</div>
        </div>
        <div class="info-blk">
          <div class="ib-label">Target / Rogue String</div>
          <div class="ib-val red">{esc(rogue)}</div>
        </div>
        <div class="info-blk">
          <div class="ib-label">Delimiter</div>
          <div class="ib-val">{esc(delim)}</div>
        </div>
        <div class="info-blk">
          <div class="ib-label">Escape Repetitions</div>
          <div class="ib-val">{esc(esc_times)}</div>
        </div>
        <div class="info-blk span-all">
          <div class="ib-label">Injected Instruction</div>
          <div class="ib-val red">{esc(attack_instr)}</div>
        </div>
      </div>

      <div class="triggers-row">
        <div class="row-label">Detection Triggers</div>
        {triggers_html}
      </div>

      <div class="row-label" style="margin-bottom:10px">
        Conversations &mdash; {total} generation(s)
      </div>
      {conv_items}
    </div>
  </div>"""


# ── full document ─────────────────────────────────────────────────────────────

def build_html(data):
    attempts  = data["attempts"]
    run_id    = data["run_id"]
    start_time= data["start_time"]
    probe_spec= data["probe_spec"]
    target    = data["target_type"]
    version   = data["garak_version"]

    total_gens = sum(len(a.get("conversations", [])) for a in attempts)
    total_hits = sum(hit_stats(a)[1]                  for a in attempts)
    pct_overall = ((total_gens - total_hits) / total_gens * 100) if total_gens else 100

    # probe pills
    probe_counts = defaultdict(lambda: {"total": 0, "hits": 0})
    for a in attempts:
        p = a.get("probe_classname", "Unknown")
        t, h = hit_stats(a)
        probe_counts[p]["total"] += t
        probe_counts[p]["hits"]  += h

    probe_pills = ""
    for probe, c in probe_counts.items():
        t = c["total"]; h = c["hits"]
        r = ((t - h) / t * 100) if t else 100
        cls = "pill-pass" if h == 0 else "pill-fail"
        probe_pills += f"""<div class="probe-pill {cls}">
          <span class="pill-name">{esc(probe)}</span>
          <span class="pill-stat">{t - h}/{t} blocked &middot; {r:.0f}%</span>
        </div>"""

    cards = "".join(attempt_card(i, a) for i, a in enumerate(attempts))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>GarakEye &middot; {esc(run_id[:8])}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600;700&family=Syne:wght@400;600;800&display=swap" rel="stylesheet"/>
<style>
:root {{
  --bg:       #0a0c10;
  --surf:     #111318;
  --surf2:    #1a1d24;
  --border:   #252930;
  --accent:   #00e5ff;
  --red:      #ff3b6b;
  --green:    #00e090;
  --yellow:   #fbbf24;
  --text:     #e2e8f0;
  --muted:    #64748b;
  --code:     #0d1117;
  --r:        10px;
  --fh:       'Syne', sans-serif;
  --fm:       'JetBrains Mono', monospace;
}}
*,*::before,*::after {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:var(--bg); color:var(--text); font-family:var(--fm); font-size:13px; padding-bottom:60px; }}

/* header */
.hdr {{ background:linear-gradient(135deg,#0d1117,#111827,#0a0f1a);
  border-bottom:1px solid var(--border); padding:32px 48px 26px; position:relative; overflow:hidden; }}
.hdr::before {{ content:''; position:absolute; inset:0;
  background:radial-gradient(ellipse 60% 80% at 80% 50%,rgba(0,229,255,.07) 0%,transparent 70%); pointer-events:none; }}
.hdr-row {{ display:flex; align-items:flex-start; justify-content:space-between; gap:24px; }}
.hdr-title {{ font-family:var(--fh); font-size:28px; font-weight:800; color:#fff; }}
.hdr-title span {{ color:var(--accent); }}
.hdr-sub {{ font-size:11px; color:var(--muted); margin-top:6px; letter-spacing:.5px; }}
.ver-tag {{ background:rgba(0,229,255,.1); border:1px solid rgba(0,229,255,.25); color:var(--accent);
  padding:4px 10px; border-radius:4px; font-size:11px; font-weight:700; letter-spacing:1px; white-space:nowrap; }}

/* meta */
.meta {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr));
  gap:10px; padding:20px 48px; background:var(--surf); border-bottom:1px solid var(--border); }}
.meta-card {{ background:var(--surf2); border:1px solid var(--border); border-radius:var(--r); padding:12px 14px; }}
.mc-label {{ color:var(--muted); font-size:10px; letter-spacing:1px; text-transform:uppercase; margin-bottom:5px; }}
.mc-val {{ font-size:13px; font-weight:600; word-break:break-all; }}

/* score */
.score-wrap {{ display:flex; align-items:center; gap:28px; padding:26px 48px;
  border-bottom:1px solid var(--border); background:var(--surf); flex-wrap:wrap; }}
.score-ring {{ position:relative; width:100px; height:100px; flex-shrink:0; }}
.score-ring-text {{ position:absolute; inset:0; display:flex; flex-direction:column;
  align-items:center; justify-content:center; }}
.score-pct {{ font-family:var(--fh); font-size:22px; font-weight:800; line-height:1; }}
.score-pct.good {{ color:var(--green); }} .score-pct.warn {{ color:var(--yellow); }} .score-pct.bad {{ color:var(--red); }}
.score-ring-label {{ font-size:9px; color:var(--muted); letter-spacing:.5px; margin-top:2px; }}
.score-stats {{ display:flex; flex-direction:column; gap:7px; }}
.srow {{ display:flex; align-items:center; gap:10px; }}
.sdot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
.sdot.g {{ background:var(--green); }} .sdot.r {{ background:var(--red); }}

/* probes */
.probes {{ padding:18px 48px; border-bottom:1px solid var(--border); }}
.sec-label {{ font-family:var(--fh); font-size:10px; font-weight:700; letter-spacing:2px;
  text-transform:uppercase; color:var(--muted); margin-bottom:10px; }}
.pills {{ display:flex; flex-wrap:wrap; gap:8px; }}
.probe-pill {{ display:flex; align-items:center; gap:10px; border-radius:6px;
  padding:8px 14px; border:1px solid; }}
.pill-pass {{ background:rgba(0,224,144,.06); border-color:rgba(0,224,144,.25); }}
.pill-fail {{ background:rgba(255,59,107,.06); border-color:rgba(255,59,107,.3); }}
.pill-name {{ font-size:12px; font-weight:700; }}
.pill-pass .pill-name {{ color:var(--green); }} .pill-fail .pill-name {{ color:var(--red); }}
.pill-stat {{ font-size:11px; color:var(--muted); }}

/* attempts */
.attempts {{ padding:22px 48px; }}

/* card */
.card {{ background:var(--surf); border:1px solid var(--border); border-radius:var(--r);
  margin-bottom:14px; overflow:hidden; transition:border-color .2s; }}
.card:hover {{ border-color:#333; }}
.card-hdr {{ display:flex; align-items:center; justify-content:space-between;
  padding:15px 18px; cursor:pointer; user-select:none; background:var(--surf2); gap:14px; }}
.card-hdr:hover {{ background:#1e2128; }}
.card-left {{ display:flex; align-items:center; gap:12px; flex:1; min-width:0; }}
.idx {{ font-family:var(--fh); font-size:11px; font-weight:800; color:var(--muted);
  letter-spacing:1px; white-space:nowrap; }}
.probe-name {{ font-size:13px; font-weight:700; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.goal-text {{ font-size:11px; color:var(--muted); margin-top:2px; }}
.card-right {{ display:flex; align-items:center; gap:10px; flex-shrink:0; }}
.status-badge {{ font-size:11px; font-weight:700; padding:4px 10px;
  border-radius:4px; letter-spacing:.5px; white-space:nowrap; border:1px solid; }}
.status-pass {{ background:rgba(0,224,144,.1); color:var(--green); border-color:rgba(0,224,144,.3); }}
.status-fail {{ background:rgba(255,59,107,.1); color:var(--red); border-color:rgba(255,59,107,.3); }}
.chev {{ color:var(--muted); font-size:13px; transition:transform .22s; flex-shrink:0; }}
.chev.open {{ transform:rotate(180deg); }}
.card-body {{ display:none; padding:18px; }}
.card-body.open {{ display:block; }}

/* info grid */
.info-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
  gap:10px; margin-bottom:18px; }}
.info-blk {{ background:var(--code); border:1px solid var(--border); border-radius:7px; padding:11px 13px; }}
.span-all {{ grid-column:1/-1; }}
.ib-label {{ font-size:10px; color:var(--muted); letter-spacing:1px; text-transform:uppercase; margin-bottom:5px; }}
.ib-val {{ font-size:12px; color:var(--accent); word-break:break-word; }}
.ib-val.red {{ color:var(--red); }}

/* triggers */
.triggers-row {{ margin-bottom:18px; }}
.row-label {{ font-size:10px; color:var(--muted); letter-spacing:1px; text-transform:uppercase; margin-bottom:7px; }}
.chip {{ display:inline-block; background:rgba(255,59,107,.12); border:1px solid rgba(255,59,107,.3);
  color:var(--red); border-radius:4px; padding:3px 8px; font-size:12px; margin:2px; }}

/* convs */
.conv-item {{ border:1px solid var(--border); border-radius:7px; margin-bottom:10px; overflow:hidden; }}
.conv-hit {{ border-color:rgba(255,59,107,.4); }}
.conv-pass {{ border-color:rgba(0,224,144,.2); }}
.conv-hdr {{ display:flex; align-items:center; justify-content:space-between;
  padding:7px 13px; background:var(--surf2); font-size:11px; color:var(--muted); }}
.conv-res {{ font-size:11px; font-weight:700; padding:2px 8px; border-radius:3px; }}
.injected {{ background:rgba(255,59,107,.15); color:var(--red); }}
.blocked  {{ background:rgba(0,224,144,.1);  color:var(--green); }}
.conv-body {{ padding:12px; display:grid; gap:10px; }}
.msg-wrap {{ border-radius:5px; overflow:hidden; }}
.msg-lbl {{ font-size:10px; letter-spacing:1px; text-transform:uppercase;
  padding:5px 11px; font-weight:700; }}
.user-wrap .msg-lbl {{ background:rgba(0,229,255,.08); color:var(--accent); }}
.asst-wrap .msg-lbl {{ background:rgba(0,224,144,.06); color:var(--green); }}
pre.msg-pre {{ background:var(--code); border:1px solid var(--border); border-top:none;
  padding:11px; font-family:var(--fm); font-size:12px; white-space:pre-wrap;
  word-break:break-word; color:#c9d1d9; line-height:1.6; max-height:260px; overflow-y:auto; }}
mark.hl {{ background:rgba(255,59,107,.3); color:var(--red); border-radius:2px; padding:0 2px; }}

/* footer */
footer {{ text-align:center; padding:26px; color:var(--muted); font-size:11px;
  letter-spacing:.5px; border-top:1px solid var(--border); margin-top:18px; }}
.muted {{ color:var(--muted); }}

@media(max-width:680px) {{
  .hdr,.meta,.score-wrap,.probes,.attempts {{ padding-left:14px; padding-right:14px; }}
}}
</style>
</head>
<body>

<header class="hdr">
  <div class="hdr-row">
    <div>
      <div class="hdr-title">&#9889; <span>GarakEye</span> Scan Report</div>
      <div class="hdr-sub">LLM Vulnerability Analysis &middot; {esc(start_time)}</div>
    </div>
    <div class="ver-tag">v{esc(version)}</div>
  </div>
</header>

<div class="meta">
  <div class="meta-card"><div class="mc-label">Run ID</div><div class="mc-val" style="font-size:11px;color:var(--muted)">{esc(run_id)}</div></div>
  <div class="meta-card"><div class="mc-label">Probe Spec</div><div class="mc-val">{esc(probe_spec)}</div></div>
  <div class="meta-card"><div class="mc-label">Target Type</div><div class="mc-val">{esc(target)}</div></div>
  <div class="meta-card"><div class="mc-label">Total Attempts</div><div class="mc-val">{len(attempts)}</div></div>
  <div class="meta-card"><div class="mc-label">Total Generations</div><div class="mc-val">{total_gens}</div></div>
</div>

<div class="score-wrap">
  {score_ring(pct_overall)}
  <div class="score-stats">
    <div class="srow"><div class="sdot g"></div><span><strong>{total_gens - total_hits}</strong> generations blocked (safe)</span></div>
    <div class="srow"><div class="sdot r"></div><span><strong>{total_hits}</strong> injections succeeded</span></div>
    <div class="srow" style="color:var(--muted);font-size:11px;margin-top:4px">Overall robustness across {len(attempts)} probe(s)</div>
  </div>
</div>

<div class="probes">
  <div class="sec-label">Probes Executed</div>
  <div class="pills">{probe_pills}</div>
</div>

<div class="attempts">
  <div class="sec-label">Attempt Details &mdash; click to expand</div>
  {cards}
</div>

<footer>Generated by <strong>GarakEye</strong> &middot; {esc(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))} &middot; Built by <a href="https://github.com/crazywifi" target="_blank" style="color:var(--accent);text-decoration:none;">crazywifi (LazyHacker)</a></footer>

<script>
function toggle(idx) {{
  document.getElementById('body-' + idx).classList.toggle('open');
  document.getElementById('chev-' + idx).classList.toggle('open');
}}
</script>
</body>
</html>"""


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("GarakEye — Garak Report Generator")
        print("Author : crazywifi (LazyHacker) | https://github.com/crazywifi")
        print("Usage  : python garak_report.py <input.jsonl> [output.html]")
        print("Example: python garak_report.py my_scan.jsonl report.html")
        sys.exit(0)

    input_file  = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) >= 3 else None

    if not os.path.isfile(input_file):
        print(f"[!] File not found: {input_file}")
        sys.exit(1)

    if output_file is None:
        base        = os.path.splitext(os.path.basename(input_file))[0]
        output_file = base + "_report.html"

    print(f"[*] Reading  : {input_file}")
    entries = load_jsonl(input_file)
    data    = parse_entries(entries)

    print(f"[*] Attempts : {len(data['attempts'])}")
    print(f"[*] Version  : {data['garak_version']}")

    html_out = build_html(data)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[✓] Report   : {output_file}")
    print(f"    Open in browser: file://{os.path.abspath(output_file)}")


if __name__ == "__main__":
    main()
