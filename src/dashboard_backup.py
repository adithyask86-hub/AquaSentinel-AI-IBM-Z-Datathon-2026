import csv
import json
from collections import Counter
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "outputs" / "decision_support_queue.csv"
SUMMARY = ROOT / "outputs" / "analysis_summary.json"


def load_data():
    with REPORT.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    summary = {}
    if SUMMARY.exists():
        with SUMMARY.open(encoding="utf-8") as f:
            summary = json.load(f)
    return rows, summary


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>AquaSentinel AI | Water Intelligence</title>
<style>
:root{font-family:Inter,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
color:#e8f2ff;background:#071522}
*{box-sizing:border-box}body{margin:0}
header{padding:30px max(22px,5vw);background:linear-gradient(120deg,#0c3444,#10233d);
border-bottom:1px solid #24485a}
.brand{color:#66e0cb;font-size:12px;letter-spacing:3px;font-weight:800}
h1{margin:10px 0 7px;font-size:clamp(28px,4vw,43px)}
.sub{color:#a9c4d7;max-width:720px;line-height:1.6}
main{max-width:1400px;margin:auto;padding:25px max(16px,4vw) 50px}
.notice{background:#172c3b;border:1px solid #315064;border-radius:12px;
padding:13px 16px;color:#c4d8e8;font-size:13px;line-height:1.6}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(165px,1fr));
gap:13px;margin:20px 0}
.card{background:#102334;border:1px solid #203d50;border-radius:14px;padding:19px}
.label{font-size:12px;color:#9bb6c9}
.number{font-size:30px;font-weight:750;margin-top:8px}
.mint{color:#66e0cb}.red{color:#ff9d9d}.amber{color:#ffd28b}
.panel{background:#102334;border:1px solid #203d50;border-radius:14px;
padding:20px;margin-top:17px}
h2{font-size:17px;margin:0 0 16px}
.controls{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:15px}
input,select{background:#081a29;border:1px solid #315064;border-radius:8px;
padding:11px;color:#e8f2ff;font:inherit;min-width:170px}
input{flex:1}
table{width:100%;border-collapse:collapse;font-size:13px}
th{text-align:left;color:#9bb6c9;font-weight:600;background:#0b1c2a}
td,th{padding:12px 10px;border-bottom:1px solid #20394b;vertical-align:top}
tr:hover{background:#142b3d}
.tablewrap{overflow-x:auto}
.tag{display:inline-block;border-radius:20px;padding:5px 8px;font-size:11px;
font-weight:750;white-space:nowrap}
.HIGH_REVIEW{background:#542b35;color:#ffb7bc}
.MEDIUM_REVIEW{background:#594524;color:#ffdb91}
.ROUTINE_REVIEW{background:#1b443e;color:#8fe3c8}
.DATA_QUALITY{background:#253c54;color:#b9d7ff}
.INSUFFICIENT_EVIDENCE{background:#3b3157;color:#d8c7ff}
.barrow{display:grid;grid-template-columns:155px 1fr 45px;gap:10px;
align-items:center;margin:13px 0;font-size:12px;color:#b6cbd9}
.track{height:10px;background:#203a4b;border-radius:9px;overflow:hidden}
.fill{height:100%;background:#66e0cb;border-radius:9px}
footer{color:#829daf;font-size:12px;line-height:1.7;margin-top:20px}
@media(max-width:600px){header{padding:23px 18px}.barrow{grid-template-columns:115px 1fr 35px}
.panel{padding:13px}td,th{padding:9px 7px}}
</style>
</head>
<body>
<header>
<div class="brand">AQUASENTINEL AI</div>
<h1>Water Intelligence Dashboard</h1>
<div class="sub">Explainable conductivity anomaly screening and
decision support for water-quality data.</div>
</header>
<main>
<div class="notice"><strong>Historical-data mode:</strong> This prototype
analyses historical measurements. Flags indicate records for review, not
confirmed pollution, and conductivity alone cannot establish water safety.</div>
<section class="metrics" id="metrics"></section>
<section class="panel">
<h2>Review queue distribution</h2>
<div id="bars"></div>
</section>
<section class="panel">
<h2>Station review explorer</h2>
<div class="controls">
<input id="search" placeholder="Search station or district…">
<select id="priority"><option value="">All priorities</option></select>
<select id="status"><option value="">All screening statuses</option></select>
</div>
<div class="tablewrap">
<table><thead><tr><th>Station / District</th><th>Timestamp</th>
<th>Conductivity</th><th>Robust score</th><th>Priority</th>
<th>Reason / recommended action</th></tr></thead>
<tbody id="records"></tbody></table>
</div>
<div id="count" class="label" style="margin-top:14px"></div>
</section>
<footer>Method: station-specific median absolute deviation (MAD), with
rule-based review prioritisation. The 5,000 µS/cm cutoff is exploratory,
not a regulatory limit. Missing data and insufficient station history are
tracked separately. Human verification is required before action.</footer>
</main>
<script>
const DATA = __DATA__;
const SUMMARY = __SUMMARY__;
const priorities = ["HIGH_REVIEW","MEDIUM_REVIEW","ROUTINE_REVIEW",
"DATA_QUALITY","INSUFFICIENT_EVIDENCE"];
const counts = Object.fromEntries(priorities.map(p =>
[p, DATA.filter(r=>r.review_priority===p).length]));
const fmt = v => Number(v||0).toLocaleString("en-IN");
const el = id => document.getElementById(id);
const metrics = [
["Source records",SUMMARY.source_records ?? DATA.length,"mint"],
["Valid conductivity readings",SUMMARY.valid_numeric_readings ?? "—","mint"],
["Candidate anomalies",SUMMARY.CANDIDATE_ANOMALY ?? counts.HIGH_REVIEW+counts.MEDIUM_REVIEW,"red"],
["Missing / invalid readings",SUMMARY.invalid_or_missing_readings ?? counts.DATA_QUALITY,"amber"]
];
el("metrics").innerHTML=metrics.map(m=>`<div class="card">
<div class="label">${m[0]}</div><div class="number ${m[2]}">${fmt(m[1])}</div>
</div>`).join("");
const total=DATA.length;
el("bars").innerHTML=priorities.map(p=>`<div class="barrow">
<span>${p.replaceAll("_"," ")}</span><div class="track"><div class="fill"
style="width:${total?counts[p]/total*100:0}%"></div></div><b>${counts[p]}</b>
</div>`).join("");
priorities.forEach(p=>el("priority").insertAdjacentHTML("beforeend",
`<option value="${p}">${p.replaceAll("_"," ")}</option>`));
[...new Set(DATA.map(r=>r.status).filter(Boolean))].sort().forEach(s=>
el("status").insertAdjacentHTML("beforeend",`<option value="${s}">${s}</option>`));
function esc(s){return String(s??"").replace(/[&<>"']/g,c=>({
"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"
}[c]));}
function render(){
const q=el("search").value.toLowerCase();
const p=el("priority").value,s=el("status").value;
const filtered=DATA.filter(r=>
(!q||[r.station,r.district].some(v=>(v||"").toLowerCase().includes(q)))&&
(!p||r.review_priority===p)&&(!s||r.status===s));
el("records").innerHTML=filtered.slice(0,250).map(r=>`<tr>
<td><strong>${esc(r.station)}</strong><br><span class="label">${esc(r.district)}</span></td>
<td>${esc(r.timestamp)}</td><td>${esc(r.conductivity_us_cm||"Missing")}</td>
<td>${esc(r.robust_score||"—")}</td>
<td><span class="tag ${esc(r.review_priority)}">${esc(r.review_priority)}</span></td>
<td>${esc(r.review_reason)}<br><br><span class="label">${esc(r.recommended_action)}</span></td>
</tr>`).join("");
el("count").textContent=`Showing ${Math.min(filtered.length,250)} of ${filtered.length} matching records (maximum 250 displayed).`;
}
["search","priority","status"].forEach(id=>el(id).addEventListener(
id==="search"?"input":"change",render));
render();
</script>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if urlparse(self.path).path not in ("/", "/index.html"):
            self.send_error(404)
            return
        try:
            rows, summary = load_data()
            page = PAGE.replace("__DATA__", json.dumps(rows, ensure_ascii=False))
            page = page.replace("__SUMMARY__", json.dumps(summary, ensure_ascii=False))
            body = page.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as exc:
            body = f"Dashboard error: {exc}".encode()
            self.send_error(500, body.decode())

    def log_message(self, fmt, *args):
        print("%s - %s" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    print("AquaSentinel AI dashboard: http://127.0.0.1:8501")
    print("Press Ctrl+C to stop.")
    HTTPServer(("127.0.0.1", 8501), Handler).serve_forever()
