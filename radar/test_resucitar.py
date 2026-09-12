#!/usr/bin/env python3
"""Decision-table checks for Radar Rotación resucitar (RESURGIDO)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "radar" / "index.html"
SNAPSHOT = ROOT / "radar" / "hoy_3_tarjetas.json"

UTIL_MIN = 120
ROI_MIN = 30


def parse_context_money(card: dict) -> tuple[float | None, float | None, float | None]:
    ctx = str(card.get("contexto_prompt") or "")
    um = re.search(r"Utilidad est\.\s*/\s*u:\s*\$?\s*([\d.]+)", ctx, re.I)
    roi = re.search(r"ROI:\s*([\d.]+)\s*%", ctx, re.I)
    mg = re.search(r"margen u:\s*\$?\s*([\d.]+)", ctx, re.I)
    return (
        float(um.group(1)) if um else None,
        float(roi.group(1)) if roi else None,
        float(mg.group(1)) if mg else None,
    )


def estimated_gain(card: dict) -> float | None:
    for key in ("ganancia_estimada_mxn", "unit_margin"):
        v = card.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    ev = card.get("evidence") or {}
    if ev.get("unit_margin") is not None:
        return float(ev["unit_margin"])
    gain, _, _ = parse_context_money(card)
    return gain


def estimated_roi(card: dict) -> float | None:
    v = card.get("roi_pct")
    if v is not None:
        try:
            return float(v)
        except (TypeError, ValueError):
            pass
    _, roi, _ = parse_context_money(card)
    return roi


def estimated_margin(card: dict) -> float | None:
    for key in ("unit_margin", "margen_u", "margen"):
        v = card.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                pass
    ev = card.get("evidence") or {}
    if ev.get("unit_margin") is not None:
        return float(ev["unit_margin"])
    _, _, mg = parse_context_money(card)
    return mg if mg is not None else estimated_gain(card)


def tags_of(card: dict) -> set[str]:
    raw = [card.get("tag"), card.get("status"), card.get("reason"), card.get("outcome")]
    extra = card.get("tags")
    if isinstance(extra, list):
        raw.extend(extra)
    out = set()
    for v in raw:
        if v is None:
            continue
        out.add(str(v).strip().lower().replace(" ", "_").replace("-", "_"))
    return out


def passes_numbers(card: dict) -> bool:
    util = estimated_gain(card)
    roi = estimated_roi(card)
    margen = estimated_margin(card)
    if util is not None and roi is not None and margen is not None:
        if util >= UTIL_MIN and roi >= ROI_MIN and margen > 0:
            return True
    if card.get("gate_ok") is True:
        if util is not None and util < UTIL_MIN:
            return False
        if roi is not None and roi < ROI_MIN:
            return False
        if margen is not None and not (margen > 0):
            return False
        return True
    return False


def offer_cures(card: dict, offer: dict | None) -> bool:
    if not offer or str(offer.get("status") or "").upper() != "OFERTA_ENCONTRADA":
        return False
    landed = offer.get("found_landed")
    cap = card.get("max_landed_cost")
    if landed is not None and cap is not None and float(landed) > float(cap):
        return False
    return True


def can_resucitar(card: dict, offer: dict | None) -> bool:
    tags = tags_of(card)
    if "nunca" in tags or "never" in tags:
        return False
    if str(card.get("outcome") or "").lower() == "descartado":
        return False
    if not passes_numbers(card):
        return False
    if not offer_cures(card, offer):
        return False
    return True


def check_spa_markers(html: str, errors: list[str]) -> None:
    for label, pat in (
        ("canResucitar", r"function canResucitar\("),
        ("refreshResurgidos", r"function refreshResurgidos\("),
        ("hasNuncaTag", r"function hasNuncaTag\("),
        ("descartadoWithin30d", r"function descartadoWithin30d\("),
        ("offerCuresPause", r"function offerCuresPause\("),
        ("resurgidos[] write", r"resurgidos"),
        ("RESURGIDO const", r'const RESURGIDO = "RESURGIDO"'),
        ("no snapshot write", r"RESURGIDOS_KEY"),
        ("resurrect_reason", r'gate_ok_post_import'),
        ("prev_state paused|dismissed", r'prev_state'),
        ("cured_pause_reason", r"cured_pause_reason"),
        ("util field", r"\butil\b"),
        ("found_landed optional", r"found_landed"),
    ):
        if re.search(pat, html) is None:
            errors.append(f"SPA missing {label}")
    if re.search(r"localStorage\.setItem\(\s*JSON_URL", html):
        errors.append("SPA must not write hoy_3_tarjetas.json")
    if "upsertPurchase" in html and "function refreshResurgidos" in html:
        start = html.find("function refreshResurgidos")
        nxt = html.find("\nfunction ", start + 10)
        body = html[start:nxt]
        if "upsertPurchase" in body or "lockCard" in body:
            errors.append("refreshResurgidos must not auto-buy")
    # Export multi-tab (PR #13) must stay
    for label, pat in (
        ("exportHallazgoCsv", r"function exportHallazgoCsv\("),
        ("exportHoyCsv", r"function exportHoyCsv\("),
        ("exportDecidedCsv", r"function exportDecidedCsv\("),
        ("renderActiveTabCsvBar", r"function renderActiveTabCsvBar\("),
        ("radar-hallazgo.csv", r"radar-hallazgo\.csv"),
        ("radar-ya-decididas.csv", r"radar-ya-decididas\.csv"),
    ):
        if re.search(pat, html) is None:
            errors.append(f"SPA must keep FE#13 export: {label}")


def main() -> int:
    errors: list[str] = []
    html = INDEX.read_text(encoding="utf-8")
    check_spa_markers(html, errors)

    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    decided = snap.get("dismissed_or_paused") or snap.get("parked") or []
    by_sku = {c.get("sku"): c for c in decided if isinstance(c, dict)}

    cases = [
        ("NIJU004", {"status": "OFERTA_ENCONTRADA", "found_landed": 200}, True, "piso+oferta bajo techo"),
        ("NICX002", {"status": "OFERTA_ENCONTRADA", "found_landed": 800}, True, "piso+oferta bajo techo"),
        ("10LU001", {"status": "OFERTA_ENCONTRADA", "found_landed": 50}, False, "util < 120"),
        ("07BU001", {"status": "OFERTA_ENCONTRADA", "found_landed": 400}, False, "util/ROI bajo piso"),
        ("NIFU011", {"status": "OFERTA_ENCONTRADA", "found_landed": 400}, False, "landed > techo no cura"),
        ("NIFU011", {"status": "OFERTA_ENCONTRADA", "found_landed": 250}, True, "oferta cura techo"),
    ]
    for sku, offer, expect, why in cases:
        card = by_sku.get(sku)
        if not card:
            errors.append(f"snapshot missing dismissed sku {sku}")
            continue
        got = can_resucitar(card, offer)
        if got != expect:
            errors.append(f"{sku} expected {expect} ({why}); got {got} util={estimated_gain(card)} roi={estimated_roi(card)}")

    nunca = dict(by_sku["NIJU004"], tag="nunca")
    if can_resucitar(nunca, {"status": "OFERTA_ENCONTRADA", "found_landed": 200}):
        errors.append("tag nunca must never resurrect")
    desc = dict(by_sku["NICX002"], outcome="descartado")
    if can_resucitar(desc, {"status": "OFERTA_ENCONTRADA", "found_landed": 800}):
        errors.append("descartado must never resurrect")

    if errors:
        print("resucitar tests FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("resucitar tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
