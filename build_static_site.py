"""Prepare the optimized static Nuova FLORA bundle for ChatGPT Sites."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd


SITE_ROOT = Path(__file__).resolve().parent
REPO_ROOT = SITE_ROOT.parent
SOURCE_ROOT = REPO_ROOT / "nuova_flora" / "work" / "eu27_full"
SOURCE_DASHBOARD = SOURCE_ROOT / "dashboard"
SOURCE_OUTPUT = SOURCE_ROOT / "output"
DIST = SITE_ROOT / "dist"

CASE_COLUMNS = [
    "period",
    "country",
    "flow",
    "partner",
    "product",
    "euro",
    "var_yoy",
    "alert_type",
    "series_direction",
    "alert_grade",
    "refined_score",
    "is_any_alert",
    "hormuz_selected",
    "hormuz_relevance",
    "hormuz_anticipatory",
]


def json_records(csv_path: Path) -> str:
    frame = pd.read_csv(csv_path, dtype={"period": str, "product": str, "flow": str}, low_memory=False)
    frame = frame[[column for column in CASE_COLUMNS if column in frame.columns]]
    return frame.to_json(orient="records", force_ascii=False)


def compact_series(source_root: Path, target_root: Path) -> None:
    """Write lossless column-oriented JSON to stay within Sites asset limits."""
    for source in source_root.rglob("*.json"):
        relative = source.relative_to(source_root)
        target = target_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        records = json.loads(source.read_text(encoding="utf-8"))
        if not records:
            payload = {"c": [], "d": []}
        else:
            columns = list(records[0])
            payload = {
                "c": columns,
                "d": [[record.get(column) for column in columns] for record in records],
            }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def externalize_data(page: str) -> str:
    start = page.index("const rows=")
    types_start = page.index("types=['cambio livello'", start)
    page = page[:start] + "let rows=[],hormuzRows=[];const " + page[types_start:]
    page = page.replace(";let filtered=rows.slice(),activeType=", ";let filtered=[],activeType=", 1)
    page = page.replace(
        "function url(r){return`data/series/${encodeURIComponent(r.country)}/${r.flow}/${encodeURIComponent(r.partner)}.json`}async function seriesFor(r){const u=url(r);if(!cache.has(u))cache.set(u,fetch(u).then(x=>{if(!x.ok)throw Error('Serie non disponibile');return x.json()}));return(await cache.get(u)).filter(x=>String(x.product)===String(r.product)).sort((a,b)=>String(a.period).localeCompare(String(b.period)))}",
        "function unpackSeries(payload){if(Array.isArray(payload))return payload;const c=payload?.c,d=payload?.d;if(!Array.isArray(c)||!Array.isArray(d))throw Error('Formato serie non valido');return d.map(values=>Object.fromEntries(c.map((name,i)=>[name,values[i]])))}function url(r){return`data/series/${encodeURIComponent(r.country)}/${r.flow}/${encodeURIComponent(r.partner)}.json`}async function seriesFor(r){const u=url(r);if(!cache.has(u))cache.set(u,fetch(u).then(async x=>{if(!x.ok)throw Error('Serie non disponibile');return unpackSeries(await x.json())}));return(await cache.get(u)).filter(x=>String(x.product)===String(r.product)).sort((a,b)=>String(a.period).localeCompare(String(b.period)))}",
        1,
    )

    options_start = page.index("function opts(")
    options_end = page.index("function selected()", options_start)
    options_code = r'''function opts(id,values,label){const el=document.getElementById(id),current=el.value;el.innerHTML=`<option value="">${label}</option>`+values.map(v=>`<option value="${v}">${v}</option>`).join('');if(values.map(String).includes(String(current)))el.value=current}
function refreshOptions(source){opts('fCountry',[...new Set(source.map(r=>r.country))].sort(),'Tutti');opts('fPeriod',[...new Set(source.map(r=>r.period))].sort().reverse(),'Tutti');opts('fProduct',[...new Set(source.map(r=>r.product))].sort(),'Tutte');opts('fPartner',[...new Set(source.map(r=>r.partner))].sort(),'Tutti')}
'''
    page = page[:options_start] + options_code + page[options_end:]

    apply_start = page.index("function apply(){")
    script_end = page.index("</script>", apply_start)
    bootstrap = r'''let alertsLoaded=false,alertsPromise=null;
function setStatus(message,isError=false){dataStatus.hidden=!message;dataStatus.textContent=message;dataStatus.classList.toggle('error',isError)}
async function fetchDataset(url){const response=await fetch(url);if(!response.ok)throw Error(`Impossibile caricare ${url}`);return response.json()}
async function ensureAlerts(){if(alertsLoaded)return;if(alertsPromise)return alertsPromise;setStatus('Caricamento degli alert UE27…');alertsPromise=fetchDataset('data/alerts.json').then(data=>{rows=data;filtered=rows.slice();alertsLoaded=true;refreshOptions([...hormuzRows,...rows]);setStatus('')}).catch(error=>{setStatus('Gli alert generali non sono disponibili. Riprova aggiornando la pagina.',true);throw error}).finally(()=>{alertsPromise=null});return alertsPromise}
function apply(){if(alertsLoaded){filtered=filterSet(rows);renderTop();renderAll();renderProduct()}renderHormuz()}
applyFilters.onclick=apply;
resetFilters.onclick=()=>{document.querySelectorAll('.filters select').forEach(x=>x.value='');activeType='';hormuzMode='all';hormuzType='';typeButtons.querySelectorAll('button').forEach((x,i)=>x.classList.toggle('active',i===0));hormuzControls.querySelectorAll('button').forEach((x,i)=>x.classList.toggle('active',i===0));hormuzTypeControls.querySelectorAll('button').forEach((x,i)=>x.classList.toggle('active',i===0));apply()};
document.querySelectorAll('.tab').forEach(button=>button.onclick=async()=>{document.querySelectorAll('.tab,.page').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.tab').forEach(x=>x.setAttribute('aria-selected','false'));button.classList.add('active');button.setAttribute('aria-selected','true');document.getElementById(button.dataset.page).classList.add('active');if(button.dataset.page!=='hormuz'){try{await ensureAlerts();apply()}catch(_){}}});
async function bootstrap(){setStatus('Caricamento dei casi Hormuz…');try{hormuzRows=await fetchDataset('data/hormuz.json');refreshOptions(hormuzRows);renderHormuz();setStatus('')}catch(error){setStatus('I dati Hormuz non sono disponibili. Riprova aggiornando la pagina.',true)}}
bootstrap();
'''
    page = page[:apply_start] + bootstrap + page[script_end:]
    return page


def improve_shell(page: str) -> str:
    page = page.replace(
        "<title>Nuova FLORA UE27</title>",
        '<title>Nuova FLORA UE27</title><meta name="description" content="Alert sui flussi commerciali UE27 e analisi della crisi dello Stretto di Hormuz"><link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' viewBox=\'0 0 64 64\'%3E%3Crect width=\'64\' height=\'64\' rx=\'14\' fill=\'%23080d13\'/%3E%3Cpath d=\'M16 46V18h34v8H25v5h21v8H25v7z\' fill=\'%235aafff\'/%3E%3C/svg%3E">',
    )
    page = page.replace(
        "Early warning su import ed export in euro · top 20 partner per paese e flusso · CPA a 2 digit · dati consolidati fino a maggio 2026",
        "Fonte: TERRA/Eurostat COMEXT. Elaborazioni Nuova FLORA. Dati consolidati fino a maggio 2026.<br><span class=\"header-scope\">Import ed export in euro · top 20 partner per paese e flusso · CPA a 2 digit</span>",
    )
    page = page.replace("<main>", '<main><div id="dataStatus" class="data-status" role="status" aria-live="polite" hidden></div>', 1)
    page = page.replace('<nav class="tabs">', '<nav class="tabs" role="tablist" aria-label="Sezioni della dashboard">', 1)
    page = page.replace('<button class="tab active" data-page="hormuz">', '<button class="tab active" role="tab" aria-selected="true" data-page="hormuz">', 1)
    page = page.replace('<button class="tab" data-page="top">', '<button class="tab" role="tab" aria-selected="false" data-page="top">', 1)
    page = page.replace('<button class="tab" data-page="all">', '<button class="tab" role="tab" aria-selected="false" data-page="all">', 1)
    page = page.replace('<button class="tab" data-page="product">', '<button class="tab" role="tab" aria-selected="false" data-page="product">', 1)
    extra_css = r'''
body{font-size:16px;line-height:1.45}header{background:#0b121b;padding:22px clamp(16px,3vw,34px)}header p{line-height:1.55}.header-scope{font-size:.9rem;color:#849db3}main{padding-inline:clamp(10px,2vw,28px);max-width:1920px;margin:auto}.panel{box-shadow:0 10px 28px rgba(0,0,0,.16)}.tab,.btn,.type-button,.card{transition:background-color .16s ease,border-color .16s ease,color .16s ease,transform .16s ease}.tab:hover,.type-button:hover,.btn:hover{border-color:#5aafff}.tab.active{background:#162638}.type-button.active{box-shadow:0 0 0 2px rgba(90,175,255,.18)}.card:hover{transform:translateY(-1px)}.filters label{font-size:.88rem}.filters select,.btn,.type-button{min-height:42px;font-size:.95rem}.data-status{position:sticky;top:0;z-index:20;margin:12px 0;padding:12px 16px;border:1px solid #37668f;border-radius:9px;background:#10263a;color:#c9e7ff;font-weight:650}.data-status.error{border-color:#a94b47;background:#351b1b;color:#ffd0cd}.table-wrap{scrollbar-color:#61788e #101923}th{font-size:.84rem}td{font-size:.86rem}.clickable:focus,.sortable:focus,.tab:focus-visible,.btn:focus-visible,.type-button:focus-visible,summary:focus-visible,select:focus-visible{outline:3px solid rgba(90,175,255,.75);outline-offset:2px}.notice{border-radius:8px}.kpi{min-height:88px}.kpi b{font-variant-numeric:tabular-nums}.chart{height:235px;padding:8px}.chart svg{max-width:100%;overflow:visible}.analysis-page a:not(.btn){color:#79c2ff}.analysis-page a:not(.btn):hover{text-decoration-thickness:2px}@media(max-width:850px){.head{align-items:flex-start;flex-direction:column}.body{padding:14px}.table-wrap{max-height:540px}.chart{height:220px}}@media(max-width:650px){body{font-size:15px}h1{font-size:1.45rem}.filters{grid-template-columns:1fr}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.type-button{flex:1 1 auto}.split{display:block}.detail{margin-top:14px}.classification-list{columns:1}}
'''
    page = page.replace("</style>", extra_css + "</style>", 1)
    return page


def build() -> dict:
    DIST.mkdir(parents=True, exist_ok=True)
    data_dir = DIST / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    page = (SOURCE_DASHBOARD / "index.html").read_text(encoding="utf-8")
    page = improve_shell(externalize_data(page))
    (DIST / "index.html").write_text(page, encoding="utf-8")
    (data_dir / "hormuz.json").write_text(
        json_records(SOURCE_OUTPUT / "dashboard_hormuz_cases.csv"), encoding="utf-8"
    )
    (data_dir / "alerts.json").write_text(
        json_records(SOURCE_OUTPUT / "dashboard_cases.csv"), encoding="utf-8"
    )

    source_series = SOURCE_DASHBOARD / "data" / "series"
    target_series = data_dir / "series"
    compact_series(source_series, target_series)
    shutil.copy2(SOURCE_DASHBOARD / "analisi_hormuz_nuova_flora.docx", DIST)

    file_count = sum(1 for path in DIST.rglob("*") if path.is_file())
    total_bytes = sum(path.stat().st_size for path in DIST.rglob("*") if path.is_file())
    return {"files": file_count, "bytes": total_bytes}


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
