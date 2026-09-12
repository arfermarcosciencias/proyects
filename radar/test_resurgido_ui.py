#!/usr/bin/env python3
"""FE UI contract for Resurgido: chip, Ya→Hoy max 3, no leftover hide."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "radar" / "index.html"
SNAPSHOT = ROOT / "radar" / "hoy_3_tarjetas.json"
HOY_MAX = 3


def _extract_spa_script(html: str) -> str:
    m = re.search(r"<script>([\s\S]*)</script>", html)
    if not m:
        return ""
    script = m.group(1)
    script = re.sub(r"\nload\(\);\s*$", "\n", script)
    return script


def run_js_resurge_cases() -> list[str]:
    """Hidden-via-localStorage + offer overlay, and 07BU001 landed $428 → RESURGIDO."""
    html = INDEX.read_text(encoding="utf-8")
    script = _extract_spa_script(html)
    if not script or "function refreshResurgidos(" not in script:
        return ["SPA script missing refreshResurgidos"]
    snap = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    cards = [c for c in (snap.get("cards") or []) if isinstance(c, dict)]
    hoy = next((c for c in cards if c.get("sku") == "01BX001"), cards[0] if cards else None)
    decided = snap.get("dismissed_or_paused") or snap.get("parked") or []
    bu = next((c for c in decided if isinstance(c, dict) and c.get("sku") == "07BU001"), None)
    if not hoy or not bu:
        return ["snapshot missing 01BX001 (Hoy) or 07BU001 (Ya)"]

    harness = r"""
const store = new Map();
globalThis.localStorage = {
  getItem(k) { return store.has(k) ? store.get(k) : null; },
  setItem(k, v) { store.set(String(k), String(v)); },
  removeItem(k) { store.delete(String(k)); },
  key(i) { return [...store.keys()][i]; },
  get length() { return store.size; }
};
function fakeEl() {
  return {
    innerHTML: "",
    textContent: "",
    hidden: false,
    classList: { toggle() {}, add() {}, remove() {} },
    addEventListener() {},
    querySelector() { return null; },
    querySelectorAll() { return []; },
    setAttribute() {},
    getAttribute() { return ""; }
  };
}
globalThis.window = { addEventListener() {}, location: { hash: "", pathname: "/", search: "" } };
globalThis.document = {
  getElementById() { return fakeEl(); },
  addEventListener() {},
  removeEventListener() {},
  title: "",
  body: fakeEl(),
  createElement() { return fakeEl(); }
};
globalThis.location = globalThis.window.location;
globalThis.history = { replaceState() {} };
"""
    cases = {
        "hoy": hoy,
        "bu": bu,
        "cards": cards,
        "queue": [c for c in (snap.get("queue") or []) if isinstance(c, dict)][:4],
    }
    runner = r"""
const hoy = CASES.hoy;
const bu = CASES.bu;
const tomorrow = new Date(Date.now() + 86400000).toISOString();
localStorage.setItem("radar-hoy:v1:" + hoy.done_id, JSON.stringify({
  done_id: hoy.done_id,
  sku: hoy.sku,
  outcome: "skip",
  hide_until: tomorrow,
  hide_days: 1
}));
localStorage.setItem("radar-hoy:external_offer:v1", JSON.stringify({
  schema: "arfershop.radar.external_offer.v1",
  updated_at: new Date().toISOString(),
  by_sku: {
    [hoy.sku]: { sku: hoy.sku, status: "OFERTA_ENCONTRADA", found_landed: 200, imported_at: new Date().toISOString() },
    [bu.sku]: { sku: bu.sku, status: "OFERTA_ENCONTRADA", found_landed: 428, imported_at: new Date().toISOString() }
  }
}));

const hiddenOnly = {
  cards: [JSON.parse(JSON.stringify(hoy))],
  queue: [],
  dismissed_or_paused: []
};
const hiddenItems = refreshResurgidos(hiddenOnly);
const hiddenHit = hiddenItems.find((x) => x.sku === hoy.sku);
const hiddenOk = !!(hiddenHit && hiddenHit.status === "RESURGIDO" && hiddenOnly.cards[0].resurgido);

const parked = {
  cards: [],
  queue: [],
  dismissed_or_paused: [JSON.parse(JSON.stringify(bu))]
};
const buItems = refreshResurgidos(parked);
const buHit = buItems.find((x) => x.sku === "07BU001");
const eco = resurgeEconomics(parked.dismissed_or_paused[0], cardExternalOffer(parked.dismissed_or_paused[0]));
const buOk = !!(buHit && buHit.status === "RESURGIDO" && parked.dismissed_or_paused[0].resurgido
  && eco.from_landed && eco.util >= 120 && eco.roi >= 30 && eco.margen > 0);

cachedData = {
  cards: JSON.parse(JSON.stringify(CASES.cards || [])).slice(0, 3),
  queue: JSON.parse(JSON.stringify(CASES.queue || [])),
  dismissed_or_paused: [JSON.parse(JSON.stringify(bu))]
};
activeTab = TAB_QUEUE;
const afterItems = afterOfferImport();
const afterHit = afterItems.find((x) => x.sku === "07BU001");
const lists = tabLists(cachedData);
const hoySkus = (lists.cards || []).map((c) => c.sku);
const onHoy = (lists.cards || []).some((c) => c.sku === "07BU001" && isResurgido(c));
const seedSkus = (CASES.cards || []).slice(0, 3).map((c) => c.sku);
const displaced = (lists.queue || []).some((c) => seedSkus.includes(c.sku));
const promoteOk = !!(afterHit && onHoy && activeTab === TAB_HOY && displaced && hoySkus.length <= HOY_MAX);

const out = { hiddenOk, buOk, promoteOk, onHoy, activeTab, hoySkus, displaced, hiddenItems, buItems, eco };
if (!hiddenOk || !buOk || !promoteOk) {
  console.error(JSON.stringify(out));
  process.exit(1);
}
console.log(JSON.stringify({ hiddenOk, buOk, promoteOk, buUtil: eco.util, buRoi: eco.roi, onHoy, hoySkus }));
"""
    node_src = (
        harness
        + script
        + "\nconst CASES = "
        + json.dumps(cases)
        + ";\n"
        + runner
    )
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".cjs", delete=False, encoding="utf-8") as fh:
            fh.write(node_src)
            tmp_path = Path(fh.name)
        proc = subprocess.run(
            ["node", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=20,
            cwd=str(ROOT),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return [f"node resurgido harness failed to run: {exc}"]
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return [f"hidden+overlay / 07BU001 promote-Hoy JS case failed: {detail[:800]}"]
    return []


def slots_for_resurgidos(hoy_visible: int, n_resurgidos: int, hoy_max: int = HOY_MAX) -> tuple[int, int]:
    """Resurgidos take Hoy slots first (displace executables). Overflow only past HOY_MAX."""
    del hoy_visible  # existing Hoy cards yield slots; not a cap on resurgidos
    to_hoy = min(max(0, n_resurgidos), hoy_max)
    to_queue = max(0, n_resurgidos - to_hoy)
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
        ("resurgidoCandidates", r"function resurgidoCandidates\("),
        ("hasLocalDecision", r"function hasLocalDecision\("),
        ("resurgeEconomics", r"function resurgeEconomics\("),
        ("stampResurgidoCard", r"function stampResurgidoCard\("),
        ("afterOfferImport setActiveTab Hoy", r"function afterOfferImport\([^)]*\)\s*\{[\s\S]{0,240}setActiveTab\(TAB_HOY\)"),
        ("afterOfferImport paints", r"function afterOfferImport\([^)]*\)\s*\{[\s\S]{0,280}paint\("),
        ("promote takes resurgidos first", r"promoted\.forEach\(take\)"),
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
    if "resurgidoCandidates" not in html:
        errors.append("refreshResurgidos must evaluate localStorage-hidden Ya cards")

    js_errors = run_js_resurge_cases()
    errors.extend(js_errors)

    cases = [
        (3, 2, 2, 0, "Hoy full → resurgidos still take Hoy slots"),
        (0, 2, 2, 0, "Hoy empty → fill Hoy"),
        (2, 4, 3, 1, "4 resurgidos → 3 Hoy + 1 queue"),
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
