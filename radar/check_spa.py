#!/usr/bin/env python3
"""Fail if radar/index.html is a static 3-card snapshot instead of the interactive SPA."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "radar" / "index.html"
TWIN = ROOT / "radar" / "hoy_3_tarjetas.html"

MARKERS = [
    ("Ya lo hice button", r"data-act=[\"']done[\"']|>Ya lo hice<"),
    ("tab Hoy", r"Hoy \("),
    ("tab Más oportunidades", r"Más oportunidades"),
    ("tab Ya decididas", r"Ya decididas"),
    ("fetch hoy_3_tarjetas.json", r"hoy_3_tarjetas\.json"),
    ("JSON_URL", r"const JSON_URL"),
    ("renderCard", r"function renderCard\("),
    ("localStorage pending", r"purchases_pending"),
    ("Mac health", r"/api/health"),
    ("POST purchases_pending", r"/api/purchases_pending"),
    ("Exportar CSV", r"Exportar CSV"),
    ("Copiar CSV", r"Copiar CSV"),
    ("copyCsv button", r"id=[\"']copyCsv[\"']"),
    ("copyQueueCsv", r"function copyQueueCsv\("),
    ("blob object URL download", r"URL\.createObjectURL"),
    ("named File download", r"new File\(\[text\],"),
    ("showSaveFilePicker", r"showSaveFilePicker"),
    ("offscreen download anchor", r"left:-9999px"),
    ("blue toast", r"\.radar-toast\{[^}]*background:var\(--blue\)"),
    ("toast copy", r"CSV copiado — pégalo en ChatGPT"),
    ("Importar CSV", r"Importar CSV"),
    ("external_offer overlay", r"external_offer"),
    ("external_offers_active", r"external_offers_active"),
    ("OFERTA_ENCONTRADA", r"OFERTA_ENCONTRADA"),
    ("Oferta encontrada chip", r"Oferta encontrada"),
    ("ABRIR offer", r">ABRIR<"),
    ("found_landed label", r"Precio encontrado / landed"),
    ("big techo amount", r"techo-amount"),
    ("favicon.png", r"favicon\.png"),
    ("favicon.ico", r"favicon\.ico"),
    ("favicon GO_v2", r"icono_radar_rotacion_GO_v2\.png"),
    ("tab Hallazgo", r"Hallazgo"),
    ("fetch hallazgos_inventario.json", r"hallazgos_inventario\.json"),
    ("hallazgos schema", r"arfershop\.radar\.hallazgos_inventario\.v1"),
    ("decision RECOMPRAR", r"RECOMPRAR"),
    ("decision PRECIO_BUENO", r"PRECIO_BUENO"),
    ("decision ESPERAR", r"ESPERAR"),
    ("decision NO", r"\bNO\b"),
    ("decision MANUAL", r"MANUAL"),
    ("Hallazgo 404 copy", r"Codex todavía está emitiendo"),
    ("Hallazgo techo verb", r"Compra solo si no pasa de"),
    ("queue csv filename", r"radar-mas-oportunidades\.csv"),
    ("hallazgo csv filename", r"radar-hallazgo\.csv"),
    ("HALLAZGO_CSV_COLS", r"HALLAZGO_CSV_COLS"),
    ("hallazgoCsv", r"function hallazgoCsv\("),
    ("exportHallazgoCsv", r"function exportHallazgoCsv\("),
    ("copyHallazgoCsv", r"function copyHallazgoCsv\("),
    ("exportHallazgo button", r"id=[\"']exportHallazgoCsv[\"']"),
    ("copyHallazgo button", r"id=[\"']copyHallazgoCsv[\"']"),
    ("Hallazgo Solo filtro", r"Solo filtro"),
    ("Hallazgo CSV Todos", r"data-hallazgo-csv-scope=[\"']all[\"']"),
    ("oferta_encontrada column", r"oferta_encontrada"),
    ("queue Importar still present", r"id=[\"']importCsv[\"']"),
    ("queue importOfferRows", r"function importOfferRows\("),
    ("Hallazgo Importar CSV", r"id=[\"']importHallazgoCsv[\"']"),
    ("Hoy Importar CSV", r"id=[\"']importHoyCsv[\"']"),
    ("Ya Importar CSV", r"id=[\"']importDecidedCsv[\"']"),
    ("Pegar CSV", r"Pegar CSV"),
    ("parseImportedEstado", r"function parseImportedEstado\("),
    ("importEstadoRows", r"function importEstadoRows\("),
    ("estado overlay key", r"radar-hoy:hallazgo_estado:v1"),
    ("csv import result hook", r"radar-hoy:csv_import_result:v1"),
    ("import hook refreshResurgidos", r"writeImportResult"),
    ("hoy csv filename", r"radar-hoy\.csv"),
    ("decided csv filename", r"radar-ya-decididas\.csv"),
    ("exportHoyCsv", r"function exportHoyCsv\("),
    ("copyHoyCsv", r"function copyHoyCsv\("),
    ("exportDecidedCsv", r"function exportDecidedCsv\("),
    ("copyDecidedCsv", r"function copyDecidedCsv\("),
    ("exportHoy button", r"id=[\"']exportHoyCsv[\"']"),
    ("copyHoy button", r"id=[\"']copyHoyCsv[\"']"),
    ("exportDecided button", r"id=[\"']exportDecidedCsv[\"']"),
    ("copyDecided button", r"id=[\"']copyDecidedCsv[\"']"),
    ("RESURGIDO tag", r"RESURGIDO"),
    ("resurgidos[] artifact", r"resurgidos"),
    ("resucitar eval", r"function (?:canResucitar|refreshResurgidos)\("),
    ("nunca exclusion", r"function hasNuncaTag\("),
    ("descartado 30d block", r"DESCARTADO_BLOCK_DAYS"),
    ("resurrect_reason", r"resurrect_reason"),
    ("prev_state", r"prev_state"),
    ("cured_pause_reason", r"cured_pause_reason"),
    ("no auto-compra resurgido", r"el radar no compra solo"),
]

BANNED = [
    ("pendiente de importar", r"pendiente de importar"),
    ("Compra pendiente chip", r">Compra pendiente<"),
    ("esperando Mac", r"esperando Mac"),
    ("v1 GO favicon", r"icono_radar_rotacion_GO\.png"),
    ("small-file data URI CSV", r"text\.length\s*<\s*800000"),
    ("hidden download anchor display:none", r"a\.style\.display\s*=\s*['\"]none['\"]"),
    ("data URI href download", r"a\.href\s*=\s*['\"]data:"),
    ("Hallazgo CSV hidden until ok", r"if \(hallazgoStatus !== [\"']ok[\"'] \|\| !hallazgoDoc\) return [\"'][\"']"),
    ("offer mapped to RECOMPRAR", r"estado\s*=\s*[\"']RECOMPRAR[\"'].*oferta|oferta.*estado\s*=\s*[\"']RECOMPRAR[\"']"),
]


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    return path.read_text(encoding="utf-8")


def static_snapshot(html: str) -> bool:
    articles = len(re.findall(r"<article\s+class=\"card\"", html))
    has_renderer = "function renderCard(" in html and "JSON_URL" in html
    return articles >= 3 and not has_renderer


def check_download_text(path: Path, html: str, errors: list[str]) -> None:
    fn = re.search(r"function downloadText\([^)]*\)\s*\{", html)
    if not fn:
        errors.append(f"{path.name}: missing downloadText()")
        return
    start = fn.start()
    # Rough function body: next top-level function or end of script-ish block
    nxt = re.search(r"\n(?:async )?function ", html[fn.end():])
    body = html[start: fn.end() + (nxt.start() if nxt else 1600)]
    blob_at = body.find("createObjectURL")
    data_at = body.find('a.href = "data:"')
    if "new File([text]" not in body and "new File([text]," not in body:
        errors.append(f"{path.name}: downloadText must use named File([text], filename)")
    if "showSaveFilePicker" not in body:
        errors.append(f"{path.name}: downloadText must prefer window.showSaveFilePicker")
    if "suggestedName" not in body:
        errors.append(f"{path.name}: showSaveFilePicker must pass suggestedName")
    if "setAttribute(\"download\"" not in body and "setAttribute('download'" not in body:
        errors.append(f"{path.name}: downloadText must setAttribute('download', filename) before click")
    if "left:-9999px" not in body:
        errors.append(f"{path.name}: download anchor must be offscreen (left:-9999px), not display:none")
    if re.search(r"style\.display\s*=\s*['\"]none['\"]", body):
        errors.append(f"{path.name}: downloadText must not hide the anchor with display:none (Chrome drops filename)")
    if blob_at < 0:
        errors.append(f"{path.name}: downloadText must use URL.createObjectURL (named File fallback)")
    if data_at >= 0 or re.search(r"a\.href\s*=\s*['\"]data:", body):
        errors.append(f"{path.name}: downloadText must never use data: URI for CSV (Chrome UUID filename)")
    if "4000" not in body:
        errors.append(f"{path.name}: downloadText must revoke object URL after ≥4s")
    if "copyCsv" in html and "copyQueueCsv" not in html:
        errors.append(f"{path.name}: #copyCsv present but copyQueueCsv missing")
    if "copyHallazgoCsv" in html and "function copyHallazgoCsv(" not in html:
        errors.append(f"{path.name}: #copyHallazgoCsv present but copyHallazgoCsv missing")
    if "radar-mas-oportunidades.csv" not in html:
        errors.append(f"{path.name}: queue CSV filename radar-mas-oportunidades.csv must stay")


LOCKED_HALLAZGO_CSV = (
    "sku",
    "upc",
    "estado",
    "qty",
    "techo",
    "landed",
    "margen",
    "gate_ok",
    "why",
    "url_amazon",
    "url_ml",
    "url_oferta",
    "notas",
    "oferta_encontrada",
)


def check_hallazgo_csv_cols(path: Path, html: str, errors: list[str]) -> None:
    block = re.search(r"const HALLAZGO_CSV_COLS = \[(.*?)\]", html, re.S)
    if not block:
        errors.append(f"{path.name}: missing HALLAZGO_CSV_COLS")
        return
    headers = re.findall(r'header:\s*"([^"]+)"', block.group(1))
    missing = [h for h in LOCKED_HALLAZGO_CSV if h not in headers]
    if missing:
        errors.append(f"{path.name}: HALLAZGO_CSV_COLS missing locked column(s) {missing}")
    extra = [h for h in headers if h not in LOCKED_HALLAZGO_CSV]
    if extra:
        errors.append(f"{path.name}: HALLAZGO_CSV_COLS has extra column(s) {extra} (GCX-165 locked)")
    if headers != list(LOCKED_HALLAZGO_CSV):
        errors.append(f"{path.name}: HALLAZGO_CSV_COLS order must be {list(LOCKED_HALLAZGO_CSV)}")
    if "radar-hallazgo.csv" not in html:
        errors.append(f"{path.name}: Hallazgo export must use radar-hallazgo.csv")
    if "radar-hoy.csv" not in html:
        errors.append(f"{path.name}: Hoy export must use radar-hoy.csv")
    if "radar-ya-decididas.csv" not in html:
        errors.append(f"{path.name}: Ya decididas export must use radar-ya-decididas.csv")


def check(path: Path, html: str, errors: list[str]) -> None:
    if static_snapshot(html):
        errors.append(f"{path.name}: static 3-card snapshot (no SPA renderer)")
    for label, pat in MARKERS:
        if re.search(pat, html) is None:
            errors.append(f"{path.name}: missing interactive marker: {label}")
    for label, pat in BANNED:
        if re.search(pat, html):
            errors.append(f"{path.name}: banned copy still present: {label}")
    if "<script>" not in html:
        errors.append(f"{path.name}: missing <script> (not the ritual SPA)")
    check_download_text(path, html, errors)
    check_hallazgo_csv_cols(path, html, errors)


def main() -> int:
    errors: list[str] = []
    index = read(INDEX)
    twin = read(TWIN)
    check(INDEX, index, errors)
    check(TWIN, twin, errors)
    if index != twin:
        errors.append("radar/index.html and radar/hoy_3_tarjetas.html must stay identical")
    for asset in (
        ROOT / "radar" / "icono_radar_rotacion_GO_v2.png",
        ROOT / "radar" / "favicon.png",
        ROOT / "radar" / "favicon.ico",
    ):
        if not asset.is_file():
            errors.append(f"{asset.relative_to(ROOT)} missing")
    hallazgo = ROOT / "radar" / "hallazgos_inventario.json"
    if hallazgo.is_file():
        try:
            doc = json.loads(hallazgo.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"hallazgos_inventario.json: invalid JSON ({exc})")
        else:
            if doc.get("schema") != "arfershop.radar.hallazgos_inventario.v1":
                errors.append("hallazgos_inventario.json: schema must be arfershop.radar.hallazgos_inventario.v1")
            if not isinstance(doc.get("items"), list):
                errors.append("hallazgos_inventario.json: missing items[]")
            decisions = {"RECOMPRAR", "PRECIO_BUENO", "ESPERAR", "NO", "MANUAL"}
            seen = {str(it.get("decision")) for it in (doc.get("items") or []) if isinstance(it, dict)}
            extra = seen - decisions
            if extra:
                errors.append(f"hallazgos_inventario.json: unknown decision(s) {sorted(extra)}")
            counts = doc.get("counts") or {}
            for key in ("RECOMPRAR", "PRECIO_BUENO", "ESPERAR", "NO", "MANUAL", "total"):
                if key not in counts:
                    errors.append(f"hallazgos_inventario.json: counts missing {key}")
    try:
        from test_resucitar import main as resucitar_main
    except ImportError:
        sys.path.insert(0, str(ROOT / "radar"))
        from test_resucitar import main as resucitar_main
    if resucitar_main() != 0:
        errors.append("radar/test_resucitar.py failed")
    try:
        from test_import_csv import main as import_csv_main
    except ImportError:
        sys.path.insert(0, str(ROOT / "radar"))
        from test_import_csv import main as import_csv_main
    if import_csv_main() != 0:
        errors.append("radar/test_import_csv.py failed")
    if errors:
        print("radar SPA guard FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("radar SPA guard OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
