# Radar Rotación (Pages)

Ritual URL: `/radar/` — SPA that reads `hoy_3_tarjetas.json`.

Tabs: **Hoy** · **Más oportunidades** · **Ya decididas** · **Hallazgo**.

**Hallazgo** reads `hallazgos_inventario.json` (`arfershop.radar.hallazgos_inventario.v1`) and renders the 5-decision catalog: Recomprar · Precio bueno · Esperar · No · Manual. A 404 while Codex is still emitting the JSON does not break the other tabs. Deep-link: `/radar/#hallazgo`.

**Exportar CSV / Copiar CSV:** `radar-hoy.csv` (visible Hoy ejecutables), `radar-mas-oportunidades.csv` (queue), `radar-ya-decididas.csv` (parked/decididas visibles), `radar-hallazgo.csv` (catálogo; all items or the active 5-state filter). Hallazgo columns (GCX-165): sku,upc,estado,qty,techo,landed,margen,gate_ok,why,url_amazon,url_ml,url_oferta,notas,oferta_encontrada.

**Importar CSV:** Más oportunidades sigue siendo enrich-only (`importOfferRows` → overlay `OFERTA_ENCONTRADA`). Hallazgo, Hoy y Ya decididas importan merge-by-`sku` los 5 estados `RECOMPRAR|PRECIO_BUENO|ESPERAR|NO|MANUAL` (+ enrich si vienen). `oferta_encontrada` / `OFERTA_ENCONTRADA` es **aparte** de `estado` — nunca se mapea oferta → RECOMPRAR. File picker + Pegar CSV. Overlay en `localStorage` (`radar-hoy:hallazgo_estado:v1`); Pages no escribe el JSON.

**Hook RESURGIDO (Codex #14):** Más oportunidades (`importOfferRows`) y Hallazgo/Hoy/Ya (`importEstadoRows`) reusan el mismo hook `afterOfferImport()` → `refreshResurgidos()` al merge de oferta. Sin endpoint nuevo y sin puente Mac. `oferta_encontrada` / `OFERTA_ENCONTRADA` ≠ `RECOMPRAR`. Resultado local en `radar-hoy:csv_import_result:v1` (`hook: refreshResurgidos`) para que Codex lea el eval. Ya→Hoy máx 3 es el FE de #16 vía el mismo `refreshResurgidos`, no un endpoint de import.

Overlay Codex (`card.external_offer` o root `external_offers_active[]`, solo `OFERTA_ENCONTRADA`): chip **Oferta encontrada**, **ABRIR** → `found_url`, y `found_landed` vs techo `max_landed_cost` / `max_landed_at_import`. Aliases `*_mxn` / `found_supplier` OK. No pisa ganancia/ROI/techo del motor. Importar CSV (Más oportunidades) solo pega ese overlay.

**Resucitar (contrato + FE):** en Import/CSV/oferta se evalúa `dismissed_or_paused`. Si util≥120 AND ROI≥30% AND margen>0 AND not (nunca | descartado 30d) AND (si pausa, la oferta cura la razón) → `status=RESURGIDO`, `resurrected_at` ISO-8601, `resurrect_reason=gate_ok_post_import`, `prev_state=dismissed|paused`, `cured_pause_reason` bool. Root `resurgidos[]`: `{sku, done_id?, status, resurrected_at, found_landed?, util, roi}`. Chip **Resurgido** (es-MX, ≥44px, distinto de COMPRAR/BUSCAR) si `card.resurgido` / `status===RESURGIDO` / `data-resurgido=true` / está en `resurgidos[]`. Al hidratar: Ya decididas → Hoy (máx 3) o Más oportunidades si Hoy está lleno; no se quedan solo en Ya. Tras resucitar se limpia `hide_until` (no se ocultan). Sin auto-buy. RESURGIDO muestra **COMPRAR** (y en Hoy **Ya lo compré**) — mismo modal / `purchases_pending` / Mac bridge. **Ya decididas** parked también puede **Registré compra**. Export multi-tab (PR #13) y overlay Oferta encontrada no se tocan.

**Nunca publiques un HTML estático de 3 tarjetas como la página ritual.** El guard `radar/check_spa.py` (CI `radar-spa-guard`) falla si falta el SPA (tabs Hoy / Más oportunidades / Ya decididas / Hallazgo, overlay Oferta encontrada / ABRIR / Importar CSV, `Ya lo hice`, `fetch` de `hoy_3_tarjetas.json` y `hallazgos_inventario.json`).
