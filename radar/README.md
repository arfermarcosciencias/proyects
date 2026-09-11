# Radar Rotación (Pages)

Ritual URL: `/radar/` — SPA that reads `hoy_3_tarjetas.json`.

**Nunca publiques un HTML estático de 3 tarjetas como la página ritual.** El guard `radar/check_spa.py` (CI `radar-spa-guard`) falla si falta el SPA (tabs Hoy / Más oportunidades / Ya decididas, `Ya lo hice`, `fetch` de `hoy_3_tarjetas.json`).

Overlay Codex (`card.external_offer`, solo `OFERTA_ENCONTRADA`): chip **Oferta encontrada**, **ABRIR** → `found_url`, y `found_landed` vs techo `max_landed_cost`. No pisa ganancia/ROI/techo del motor. Importar CSV (Más oportunidades) solo pega ese overlay.
