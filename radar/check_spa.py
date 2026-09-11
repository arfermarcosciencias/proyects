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
    ("CSV filename", r"radar-mas-oportunidades\.csv"),
    ("CSV mime", r"text/csv;charset=utf-8"),
    ("CSV named File", r"new File\(\[body\], name"),
    ("CSV data URI fallback", r'data:" \+ type \+ ","'),
    ("CSV revoke 4s", r", 4000\)"),
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
]

BANNED = [
    ("pendiente de importar", r"pendiente de importar"),
    ("Compra pendiente chip", r">Compra pendiente<"),
    ("esperando Mac", r"esperando Mac"),
    ("v1 GO favicon", r"icono_radar_rotacion_GO\.png"),
    ("CSV revoke 400ms", r"revokeObjectURL\([^)]*\),\s*400\)"),
]


def read(path: Path) -> str:
    if not path.is_file():
        raise SystemExit(f"missing {path}")
    return path.read_text(encoding="utf-8")


def static_snapshot(html: str) -> bool:
    articles = len(re.findall(r"<article\s+class=\"card\"", html))
    has_renderer = "function renderCard(" in html and "JSON_URL" in html
    return articles >= 3 and not has_renderer


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
    if errors:
        print("radar SPA guard FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("radar SPA guard OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
