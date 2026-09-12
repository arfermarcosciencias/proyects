#!/usr/bin/env python3
"""FE UI contract for Resurgido: chip, Ya→Hoy max 3, no leftover hide."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "radar" / "index.html"
HOY_MAX = 3


def slots_for_resurgidos(hoy_visible: int, n_resurgidos: int, hoy_max: int = HOY_MAX) -> tuple[int, int]:
    """How many resurgidos go to Hoy vs Más oportunidades when Hoy already has hoy_visible cards."""
    room = max(0, hoy_max - max(0, hoy_visible))
    to_hoy = min(room, n_resurgidos)
    to_queue = n_resurgidos - to_hoy
    return to_hoy, to_queue


def main() -> int:
    errors: list[str] = []
    html = INDEX.read_text(encoding="utf-8")

    for label, pat in (
        ("chip Resurgido", r'<span class="resurge-chip">Resurgido</span>'),
        ("status es-MX", r"Resurgido · el radar no compra solo"),
        ("data-resurgido attr", r'data-resurgido="\$\{resurgido \? "true" : ""\}"'),
        ("card.resurgido detect", r"truthyFlag\(card\.resurgido\)"),
        ("status RESURGIDO detect", r'normTag\(card\.status\) === "resurgido"'),
        ("root resurgidos[]", r"function rootResurgidos\("),
        ("promote from Ya", r"function promoteResurgidosFromDecided\("),
        ("HOY_MAX", r"const HOY_MAX = 3"),
        ("clear hide_until", r"function clearHideForResurgido\("),
        ("isHidden skips stale", r"function hideIsStaleForResurgido\("),
        ("lang es-MX", r'<html lang="es-MX">'),
        ("tap 44px", r"--tap:44px"),
        ("chip min-height tap", r"\.resurge-chip\{[^}]*min-height:var\(--tap\)"),
        ("oferta chip stays", r">Oferta encontrada<"),
        ("ABRIR stays", r">ABRIR<"),
        ("purchases_pending stays", r"purchases_pending"),
        ("export Hoy stays", r"function exportHoyCsv\("),
        ("export Decided stays", r"function exportDecidedCsv\("),
        ("export Hallazgo stays", r"function exportHallazgoCsv\("),
        ("no auto-buy", r"el radar no compra solo"),
        ("RESURGIDO canComprar", r"canComprar = !hideBuy && \(resurgido \|\| showComprarCta"),
        ("Ya Registré compra", r"Registré compra"),
    ):
        if re.search(pat, html) is None:
            errors.append(f"missing {label}")

    if re.search(r"\.resurge-chip\{[^}]*#6d28d9", html):
        errors.append("Resurgido chip must be distinct from BUSCAR purple")
    if re.search(r"\.resurge-chip\{[^}]*#166534", html):
        errors.append("Resurgido chip must be distinct from COMPRAR green")
    if re.search(r'<span class="resurge-chip">RESURGIDO</span>', html):
        errors.append("chip copy must be es-MX «Resurgido», not RESURGIDO")

    start = html.find("function refreshResurgidos")
    nxt = html.find("\nfunction ", start + 10) if start >= 0 else -1
    body = html[start:nxt] if start >= 0 and nxt > start else ""
    if "upsertPurchase" in body or "lockCard" in body:
        errors.append("refreshResurgidos must not auto-buy")

    cases = [
        (3, 2, 0, 2, "Hoy full → overflow to Más oportunidades"),
        (0, 2, 2, 0, "Hoy empty → fill Hoy"),
        (2, 4, 1, 3, "Hoy has 1 slot → 1 Hoy + 3 queue"),
        (3, 0, 0, 0, "no resurgidos"),
    ]
    for hoy_visible, n, expect_hoy, expect_queue, why in cases:
        got_hoy, got_queue = slots_for_resurgidos(hoy_visible, n)
        if (got_hoy, got_queue) != (expect_hoy, expect_queue):
            errors.append(f"{why}: expected Hoy {expect_hoy}/queue {expect_queue}, got {got_hoy}/{got_queue}")

    if errors:
        print("resurgido UI tests FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("resurgido UI tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
