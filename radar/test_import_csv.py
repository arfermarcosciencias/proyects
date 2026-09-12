#!/usr/bin/env python3
"""Decision-table + SPA markers for Hallazgo/Hoy/Ya Importar CSV (GCX-165)."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "radar" / "index.html"

DECISIONS = ("RECOMPRAR", "PRECIO_BUENO", "ESPERAR", "NO", "MANUAL")
LOCKED_COLS = (
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


def parse_imported_estado(raw) -> str | None:
    key = re.sub(r"[\s-]+", "_", str(raw or "").strip().upper())
    if not key or key in ("OFERTA_ENCONTRADA", "RESURGIDO"):
        return None
    if key in ("PRECIOBUENO", "PRECIO_BUENO"):
        return "PRECIO_BUENO"
    if key in DECISIONS:
        return key
    return None


def merge_estado(existing: str | None, csv_estado: str, oferta_encontrada: str) -> str | None:
    """estado and oferta_encontrada stay separate — offer never writes RECOMPRAR."""
    parsed = parse_imported_estado(csv_estado)
    if parsed:
        return parsed
    flag = str(oferta_encontrada or "").strip().lower()
    if flag in ("true", "1", "oferta_encontrada") or str(oferta_encontrada).upper() == "OFERTA_ENCONTRADA":
        return existing
    return existing


def extract_fn(html: str, name: str) -> str:
    m = re.search(rf"function {name}\(", html)
    if not m:
        return ""
    nxt = re.search(r"\n(?:async )?function ", html[m.end():])
    return html[m.start(): m.end() + (nxt.start() if nxt else 4000)]


def check_spa(html: str, errors: list[str]) -> None:
    for label, pat in (
        ("importHallazgoCsv", r'id=["\']importHallazgoCsv["\']'),
        ("importHoyCsv", r'id=["\']importHoyCsv["\']'),
        ("importDecidedCsv", r'id=["\']importDecidedCsv["\']'),
        ("pasteHallazgoCsv", r'id=["\']pasteHallazgoCsv["\']'),
        ("pasteHoyCsv", r'id=["\']pasteHoyCsv["\']'),
        ("pasteDecidedCsv", r'id=["\']pasteDecidedCsv["\']'),
        ("Pegar CSV", r"Pegar CSV"),
        ("parseImportedEstado", r"function parseImportedEstado\("),
        ("importEstadoRows", r"function importEstadoRows\("),
        ("afterOfferImport hook", r"function afterOfferImport\("),
        ("writeImportResult", r"function writeImportResult\("),
        ("ESTADO_KEY", r"radar-hoy:hallazgo_estado:v1"),
        ("IMPORT_RESULT_KEY", r"radar-hoy:csv_import_result:v1"),
        ("queue importCsv stays", r'id=["\']importCsv["\']'),
        ("queue importOfferRows stays", r"function importOfferRows\("),
    ):
        if re.search(pat, html) is None:
            errors.append(f"SPA missing {label}")

    parse_fn = extract_fn(html, "parseImportedEstado")
    if "OFFER_FOUND" not in parse_fn and "OFERTA_ENCONTRADA" not in parse_fn:
        errors.append("parseImportedEstado must reject OFERTA_ENCONTRADA")
    if "return null" not in parse_fn:
        errors.append("parseImportedEstado must return null for offer/unknown")

    imp = extract_fn(html, "importEstadoRows")
    if 'parseImportedEstado(get("estado"))' not in imp and "parseImportedEstado(get('estado'))" not in imp:
        errors.append("importEstadoRows must read estado via parseImportedEstado")
    if "oferta_encontrada" not in imp:
        errors.append("importEstadoRows must keep oferta_encontrada as its own column")
    if re.search(r"parseImportedEstado\(get\([\"']oferta_encontrada[\"']\)\)", imp):
        errors.append("importEstadoRows must not parse oferta_encontrada as estado")
    if "afterOfferImport" not in imp:
        errors.append("importEstadoRows must reuse afterOfferImport → refreshResurgidos (#14)")
    if "mirrorLocal" in imp or "/api/" in imp:
        errors.append("importEstadoRows must not call Mac bridge or a new endpoint")
    if "writeImportResult" not in imp:
        errors.append("importEstadoRows must store csv_import_result locally (no Mac)")
    if re.search(r"estado\s*=\s*[\"']RECOMPRAR[\"']", imp):
        errors.append("importEstadoRows must never hardcode estado=RECOMPRAR from offer")

    offer_imp = extract_fn(html, "importOfferRows")
    if "function importOfferRows" not in offer_imp:
        errors.append("Más oportunidades importOfferRows must stay")
    if "afterOfferImport" not in offer_imp:
        errors.append("importOfferRows must reuse afterOfferImport → refreshResurgidos (#14)")
    if "DECISION_IDS.includes(statusNorm)" not in offer_imp:
        errors.append("importOfferRows must ignore the 5 estados as offer status")

    hook = extract_fn(html, "afterOfferImport")
    if "refreshResurgidos" not in hook:
        errors.append("afterOfferImport must call refreshResurgidos")
    if "setActiveTab(TAB_HOY)" not in hook:
        errors.append("afterOfferImport must setActiveTab(Hoy) when Import produces RESURGIDO")
    if "paint(" not in hook:
        errors.append("afterOfferImport must paint() so the resurgido card is visible")
    if "mirrorLocal" in hook or "fetch(" in hook:
        errors.append("afterOfferImport must not open a Mac/HTTP path")


def check_locked_cols(html: str, errors: list[str]) -> None:
    block = re.search(r"const HALLAZGO_CSV_COLS = \[(.*?)\]", html, re.S)
    if not block:
        errors.append("missing HALLAZGO_CSV_COLS")
        return
    headers = re.findall(r'header:\s*"([^"]+)"', block.group(1))
    if headers != list(LOCKED_COLS):
        errors.append(f"HALLAZGO_CSV_COLS must stay {list(LOCKED_COLS)}; got {headers}")


def main() -> int:
    errors: list[str] = []
    html = INDEX.read_text(encoding="utf-8")
    check_spa(html, errors)
    check_locked_cols(html, errors)

    cases = [
        ("OFERTA_ENCONTRADA", None, "offer token is not an estado"),
        ("Oferta encontrada", None, "spaced offer label"),
        ("RESURGIDO", None, "RESURGIDO is not an estado"),
        ("RECOMPRAR", "RECOMPRAR", "write RECOMPRAR"),
        ("PRECIO_BUENO", "PRECIO_BUENO", "write PRECIO_BUENO"),
        ("Precio bueno", "PRECIO_BUENO", "label PRECIO_BUENO"),
        ("ESPERAR", "ESPERAR", "write ESPERAR"),
        ("NO", "NO", "write NO"),
        ("MANUAL", "MANUAL", "write MANUAL"),
        ("", None, "empty"),
        ("wat", None, "unknown"),
    ]
    for raw, expect, why in cases:
        got = parse_imported_estado(raw)
        if got != expect:
            errors.append(f"parseImportedEstado({raw!r}) expected {expect} ({why}); got {got}")

    if merge_estado("ESPERAR", "OFERTA_ENCONTRADA", "true") != "ESPERAR":
        errors.append("offer flag must not move ESPERAR → RECOMPRAR")
    if merge_estado("NO", "", "true") != "NO":
        errors.append("oferta_encontrada=true must not write estado")
    if merge_estado("ESPERAR", "RECOMPRAR", "false") != "RECOMPRAR":
        errors.append("explicit estado RECOMPRAR must merge by sku")
    if merge_estado("MANUAL", "PRECIO_BUENO", "OFERTA_ENCONTRADA") != "PRECIO_BUENO":
        errors.append("estado and oferta_encontrada must apply independently")

    if errors:
        print("import CSV tests FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("import CSV tests OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
