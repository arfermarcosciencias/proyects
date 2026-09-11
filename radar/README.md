# Radar Rotación (Pages)

Ritual URL: `/radar/` — SPA that reads `hoy_3_tarjetas.json`.

Tabs: **Hoy** · **Más oportunidades** · **Ya decididas** · **Hallazgo**.

**Hallazgo** reads `hallazgos_inventario.json` (`arfershop.radar.hallazgos_inventario.v1`) and renders the 5-decision catalog: Recomprar · Precio bueno · Esperar · No · Manual. A 404 while Codex is still emitting the JSON does not break the other tabs. Deep-link: `/radar/#hallazgo`.

Overlay Codex (`card.external_offer` o root `external_offers_active[]`, solo `OFERTA_ENCONTRADA`): chip **Oferta encontrada**, **ABRIR** → `found_url`, y `found_landed` vs techo `max_landed_cost` / `max_landed_at_import`. Aliases `*_mxn` / `found_supplier` OK. No pisa ganancia/ROI/techo del motor. Importar CSV (Más oportunidades) solo pega ese overlay.

**Nunca publiques un HTML estático de 3 tarjetas como la página ritual.** El guard `radar/check_spa.py` (CI `radar-spa-guard`) falla si falta el SPA (tabs Hoy / Más oportunidades / Ya decididas / Hallazgo, overlay Oferta encontrada / ABRIR / Importar CSV, `Ya lo hice`, `fetch` de `hoy_3_tarjetas.json` y `hallazgos_inventario.json`).
