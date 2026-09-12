#!/usr/bin/env python3
"""Smoke: Ya decididas can register a purchase; RESURGIDO keeps COMPRAR."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "radar" / "index.html"


def _fn_body(html: str, name: str) -> str:
    start = html.find(f"function {name}(")
    if start < 0:
        return ""
    nxt = html.find("\nfunction ", start + 10)
    return html[start:nxt] if nxt > start else html[start:]


def main() -> int:
    errors: list[str] = []
    html = INDEX.read_text(encoding="utf-8")

    for label, pat in (
        ("Registré compra CTA", r">Registré compra<"),
        ("RESURGIDO or gate COMPRAR", r"canComprar = !hideBuy && \(resurgido \|\| showComprarCta\(card\)\)"),
        ("promote stays", r"function promoteResurgidosFromDecided\("),
        ("HOY_MAX stays", r"const HOY_MAX = 3"),
        ("purchases_pending POST", r"/api/purchases_pending"),
        ("openPurchaseModal", r"function openPurchaseModal\("),
        ("upsertPurchase", r"function upsertPurchase\("),
        ("no auto-buy copy", r"el radar no compra solo"),
        ("COMPRAR button", r">COMPRAR<"),
        ("Hoy RESURGIDO Ya lo compré", r">Ya lo compré<"),
        ("qty+precio modal", r'id="buy-qty"'),
        ("tienda modal", r'id="buy-store"'),
        ("tap 44px", r"--tap:44px"),
    ):
        if re.search(pat, html) is None:
            errors.append(f"missing {label}")

    render = _fn_body(html, "renderCard")
    decided = re.search(r"else if \(decided\) \{\s*actionsHtml", render)
    if not decided:
        errors.append("renderCard missing decided actions branch")
    else:
        chunk = render[decided.start():decided.start() + 700]
        if "Registré compra" not in chunk:
            errors.append("Ya decididas must render Registré compra")
        if "COMPRAR" not in chunk or "canComprar" not in chunk:
            errors.append("Ya decididas RESURGIDO must be able to render COMPRAR")
        if 'data-act="comprar"' not in chunk:
            errors.append("Ya decididas purchase CTAs must reuse data-act=comprar")

    modal = _fn_body(html, "openPurchaseModal")
    guard = re.search(r"if\s*\((.{0,120}?)\)\s*return", modal)
    if not guard:
        errors.append("openPurchaseModal missing guard")
    elif "showComprarCta" in guard.group(1):
        errors.append("openPurchaseModal must not require showComprarCta (Ya parked Registré compra)")
    if "livePurchaseForCard" not in modal:
        errors.append("openPurchaseModal must still skip live purchases")
    if "upsertPurchase" not in modal:
        errors.append("openPurchaseModal must still upsertPurchase")
    if "syncPurchaseToMac" not in modal:
        errors.append("openPurchaseModal must still syncPurchaseToMac")

    wire = _fn_body(html, "wire")
    buy = wire.find("button[data-act='comprar']")
    parked = wire.find('data-tab-kind") === "decided"')
    if buy < 0 or parked < 0 or buy > parked:
        errors.append("wire() must handle comprar before decided early-return")

    promote = _fn_body(html, "promoteResurgidosFromDecided")
    if "HOY_MAX" not in promote:
        errors.append("promoteResurgidosFromDecided must still use HOY_MAX")
    if "upsertPurchase" in promote or "lockCard" in promote:
        errors.append("promote must not auto-buy")

    if errors:
        print("ya compra tests FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("ya compra tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
