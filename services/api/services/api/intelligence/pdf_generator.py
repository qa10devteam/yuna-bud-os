"""PDF Generator — eksport kosztorysu do PDF via Jinja2 + WeasyPrint.

Generuje profesjonalny PDF kosztorysu budowlanego z:
- Nagłówkiem (inwestor, obiekt, kwartał)
- Tabelą pozycji (KST, opis, jm, ilość, R, M, S, CJ, wartość)
- Podsumowaniem R/M/S/Ko/Z/Kz/netto/VAT/brutto
- Intelligence cache (benchmark percentile, win probability)
"""
from __future__ import annotations

from datetime import date
from typing import Any

from jinja2 import Environment, BaseLoader


# ─── HTML Template ────────────────────────────────────────────────────────────

KOSZTORYS_HTML = r"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="UTF-8">
<title>Kosztorys — {{ header.nazwa }}</title>
<style>
  @page { margin: 15mm 12mm; size: A4; }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: 'DejaVu Sans', Arial, sans-serif; font-size: 8pt; color: #1a1a1a; }
  h1 { font-size: 13pt; font-weight: 700; color: #1a1a6c; margin-bottom: 2mm; }
  h2 { font-size: 9pt; font-weight: 700; color: #1a1a6c; margin: 4mm 0 1mm; }
  .header-block { border: 1px solid #c0c0e0; border-radius: 3px; padding: 4mm; margin-bottom: 5mm; }
  .header-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2mm; }
  .field label { font-size: 7pt; color: #666; font-weight: 600; text-transform: uppercase; letter-spacing: 0.3px; }
  .field span { display: block; font-size: 8.5pt; color: #111; margin-top: 0.5mm; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 4mm; }
  thead tr { background: #1a1a6c; color: white; }
  thead th { padding: 2mm 1.5mm; text-align: left; font-size: 7pt; font-weight: 600; }
  thead th.num { text-align: right; }
  tbody tr { border-bottom: 0.5px solid #e0e0f0; }
  tbody tr:nth-child(even) { background: #f8f8fc; }
  td { padding: 1.5mm 1.5mm; font-size: 7.5pt; vertical-align: top; }
  td.num { text-align: right; font-variant-numeric: tabular-nums; }
  td.code { color: #555; font-size: 7pt; }
  td.anomaly { background: #fff0f0; }
  .summary { border: 1px solid #c0c0e0; border-radius: 3px; padding: 4mm; margin-top: 4mm; }
  .summary-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 3mm; }
  .sum-row { display: flex; justify-content: space-between; padding: 1mm 0; border-bottom: 0.5px solid #e8e8f8; font-size: 8pt; }
  .sum-row.total { font-weight: 700; font-size: 10pt; color: #1a1a6c; border-top: 1.5px solid #1a1a6c; border-bottom: none; padding-top: 2mm; margin-top: 1mm; }
  .intelligence { background: #f0f0ff; border: 1px solid #c0c0e0; border-radius: 3px; padding: 3mm; margin-top: 3mm; }
  .intel-row { display: flex; justify-content: space-between; font-size: 7.5pt; padding: 0.8mm 0; }
  .badge { display: inline-block; padding: 0.5mm 2mm; border-radius: 10px; font-size: 7pt; font-weight: 600; }
  .badge-green { background: #e8f5e9; color: #2e7d32; }
  .badge-yellow { background: #fff8e1; color: #e65100; }
  .badge-red { background: #ffebee; color: #c62828; }
  .footer { margin-top: 5mm; font-size: 7pt; color: #888; text-align: center; border-top: 0.5px solid #ddd; padding-top: 2mm; }
  .logo { font-size: 11pt; font-weight: 700; color: #1a1a6c; }
  .logo span { color: #4040cc; }
</style>
</head>
<body>

<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:3mm;">
  <div>
    <div class="logo">Terra<span>.OS</span></div>
    <div style="font-size:7pt;color:#888;">Platforma Inteligencji Przetargowej</div>
  </div>
  <div style="text-align:right;font-size:7pt;color:#666;">
    Data: {{ today }}<br>
    Q{{ header.kwartalnr }}/{{ header.kwartalrok }}
  </div>
</div>

<h1>KOSZTORYS — {{ header.nazwa }}</h1>

<div class="header-block">
  <div class="header-grid">
    <div class="field"><label>Inwestor</label><span>{{ header.inwestor or '—' }}</span></div>
    <div class="field"><label>Obiekt</label><span>{{ header.obiekt or '—' }}</span></div>
    <div class="field"><label>Lokalizacja</label><span>{{ header.lokalizacja or '—' }}</span></div>
    <div class="field"><label>Typ</label><span>{{ header.typ | upper }}</span></div>
    <div class="field"><label>Status</label><span>{{ header.status | upper }}</span></div>
    <div class="field"><label>Data</label><span>{{ header.data_opracowania or today }}</span></div>
  </div>
</div>

<h2>NARZUTY</h2>
<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:2mm;margin-bottom:4mm;">
  <div class="field"><label>Ko/R</label><span>{{ header.ko_r_pct }}%</span></div>
  <div class="field"><label>Ko/S</label><span>{{ header.ko_s_pct }}%</span></div>
  <div class="field"><label>Z</label><span>{{ header.z_pct }}%</span></div>
  <div class="field"><label>Kz</label><span>{{ header.kz_pct }}%</span></div>
  <div class="field"><label>VAT</label><span>{{ header.vat_pct }}%</span></div>
</div>

{% for dzial in dzialy %}
<h2>{{ loop.index }}. {{ dzial.nazwa }}</h2>
<table>
  <thead>
    <tr>
      <th style="width:3%">Lp.</th>
      <th style="width:12%">Kod</th>
      <th style="width:30%">Opis</th>
      <th style="width:5%">Jm</th>
      <th class="num" style="width:6%">Ilość</th>
      <th class="num" style="width:7%">R jcena</th>
      <th class="num" style="width:7%">M jcena</th>
      <th class="num" style="width:7%">S jcena</th>
      <th class="num" style="width:8%">CJ netto</th>
      <th class="num" style="width:10%">Wartość</th>
    </tr>
  </thead>
  <tbody>
    {% for poz in dzial.pozycje %}
    <tr class="{{ 'anomaly' if poz.is_anomaly else '' }}">
      <td>{{ poz.lp }}</td>
      <td class="code">{{ poz.kst_code or '—' }}</td>
      <td>{{ poz.opis }}</td>
      <td>{{ poz.jednostka }}</td>
      <td class="num">{{ poz.ilosc | round(2) }}</td>
      <td class="num">{{ '%.2f' % poz.r_jcena }}</td>
      <td class="num">{{ '%.2f' % poz.m_jcena }}</td>
      <td class="num">{{ '%.2f' % poz.s_jcena }}</td>
      <td class="num" style="font-weight:600">{{ '%.4f' % poz.jcena_netto }}</td>
      <td class="num" style="font-weight:600;color:#1a1a6c">{{ '%.2f' % poz.wartosc_netto }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% else %}
<table>
  <thead>
    <tr>
      <th style="width:3%">Lp.</th>
      <th style="width:12%">Kod</th>
      <th style="width:30%">Opis</th>
      <th style="width:5%">Jm</th>
      <th class="num" style="width:6%">Ilość</th>
      <th class="num" style="width:7%">R jcena</th>
      <th class="num" style="width:7%">M jcena</th>
      <th class="num" style="width:7%">S jcena</th>
      <th class="num" style="width:8%">CJ netto</th>
      <th class="num" style="width:10%">Wartość</th>
    </tr>
  </thead>
  <tbody>
    {% for poz in all_pozycje %}
    <tr class="{{ 'anomaly' if poz.is_anomaly else '' }}">
      <td>{{ poz.lp }}</td>
      <td class="code">{{ poz.kst_code or '—' }}</td>
      <td>{{ poz.opis }}</td>
      <td>{{ poz.jednostka }}</td>
      <td class="num">{{ poz.ilosc | round(2) }}</td>
      <td class="num">{{ '%.2f' % poz.r_jcena }}</td>
      <td class="num">{{ '%.2f' % poz.m_jcena }}</td>
      <td class="num">{{ '%.2f' % poz.s_jcena }}</td>
      <td class="num" style="font-weight:600">{{ '%.4f' % poz.jcena_netto }}</td>
      <td class="num" style="font-weight:600;color:#1a1a6c">{{ '%.2f' % poz.wartosc_netto }}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endfor %}

<div class="summary">
  <div class="summary-grid">
    <div>
      <h2 style="margin-top:0">ZESTAWIENIE KOSZTÓW</h2>
      <div class="sum-row"><span>Robocizna (R)</span><span>{{ sums.r | pln }}</span></div>
      <div class="sum-row"><span>Materiały (M)</span><span>{{ sums.m | pln }}</span></div>
      <div class="sum-row"><span>Sprzęt (S)</span><span>{{ sums.s | pln }}</span></div>
      <div class="sum-row"><span>Koszty pośrednie (Ko)</span><span>{{ sums.ko | pln }}</span></div>
      <div class="sum-row"><span>Koszty zakupu (Kz)</span><span>{{ sums.kz | pln }}</span></div>
      <div class="sum-row"><span>Zysk (Z)</span><span>{{ sums.z | pln }}</span></div>
      <div class="sum-row" style="border-top:1px solid #ccc;margin-top:1mm;padding-top:1mm;font-weight:600">
        <span>SUMA NETTO</span><span>{{ sums.netto | pln }}</span>
      </div>
      <div class="sum-row"><span>VAT {{ header.vat_pct }}%</span><span>{{ sums.vat | pln }}</span></div>
      <div class="sum-row total"><span>WARTOŚĆ BRUTTO</span><span>{{ sums.brutto | pln }}</span></div>
    </div>
    <div>
      {% if intel %}
      <div class="intelligence">
        <h2 style="margin-top:0;font-size:8pt">INTELLIGENCE</h2>
        {% if intel.benchmark_percentile %}
        <div class="intel-row">
          <span>Percentyl rynkowy</span>
          <span class="badge {{ 'badge-green' if intel.benchmark_percentile < 50 else 'badge-yellow' if intel.benchmark_percentile < 75 else 'badge-red' }}">
            {{ intel.benchmark_percentile | round(1) }}%
          </span>
        </div>
        {% endif %}
        {% if intel.win_probability %}
        <div class="intel-row">
          <span>P(wygrania)</span>
          <span class="badge {{ 'badge-green' if intel.win_probability > 0.6 else 'badge-yellow' if intel.win_probability > 0.35 else 'badge-red' }}">
            {{ (intel.win_probability * 100) | round(1) }}%
          </span>
        </div>
        {% endif %}
        {% if intel.anomaly_score is not none %}
        <div class="intel-row">
          <span>Anomaly rate</span>
          <span class="badge {{ 'badge-green' if intel.anomaly_score < 0.1 else 'badge-yellow' if intel.anomaly_score < 0.25 else 'badge-red' }}">
            {{ (intel.anomaly_score * 100) | round(1) }}%
          </span>
        </div>
        {% endif %}
      </div>
      {% endif %}
      <div style="margin-top:3mm;">
        <div class="sum-row"><span>Liczba pozycji</span><span>{{ n_pozycje }}</span></div>
        <div class="sum-row"><span>Udział R w netto</span><span>{{ ((sums.r / sums.netto * 100) if sums.netto else 0) | round(1) }}%</span></div>
        <div class="sum-row"><span>Udział M w netto</span><span>{{ ((sums.m / sums.netto * 100) if sums.netto else 0) | round(1) }}%</span></div>
      </div>
    </div>
  </div>
</div>

<div class="footer">
  YU-NA — Platforma Inteligencji Przetargowej | Wygenerowano: {{ today }}
  {% if header.tender_id %} | Przetarg: {{ header.tender_id[:8] }}...{% endif %}
</div>

</body>
</html>
"""


def _pln_filter(val: Any) -> str:
    try:
        v = float(val or 0)
        return f"{v:,.2f} PLN".replace(",", " ")
    except (ValueError, TypeError):
        return "0.00 PLN"


def generate_pdf(
    header: dict,
    pozycje: list[dict],
    dzialy: list[dict] | None = None,
    sums: dict | None = None,
    intel: dict | None = None,
) -> bytes:
    """Generuj PDF kosztorysu.

    Args:
        header: Nagłówek kosztorysu (nazwa, inwestor, obiekt, narzuty...)
        pozycje: Lista pozycji (lp, kst_code, opis, jednostka, ilosc, r_jcena, m_jcena, s_jcena, jcena_netto, wartosc_netto, is_anomaly)
        dzialy: Lista działów z pozycjami (opcjonalnie)
        sums: Sumy (r, m, s, ko, kz, z, netto, vat, brutto)
        intel: Intelligence cache (benchmark_percentile, win_probability, anomaly_score)

    Returns: bytes PDF
    """
    import weasyprint  # noqa: PLC0415

    if sums is None:
        sums = _calc_sums(pozycje, header)

    env = Environment(loader=BaseLoader())
    env.filters["pln"] = _pln_filter

    # Grupuj pozycje per dział
    dzialy_render: list[dict] = []
    if dzialy:
        for d in dzialy:
            d_copy = dict(d)
            d_copy["pozycje"] = [p for p in pozycje if str(p.get("dzial_id")) == str(d["id"])]
            dzialy_render.append(d_copy)

    tmpl = env.from_string(KOSZTORYS_HTML)
    html = tmpl.render(
        header=header,
        dzialy=dzialy_render,
        all_pozycje=pozycje,
        sums=sums,
        intel=intel or {},
        today=date.today().strftime("%d.%m.%Y"),
        n_pozycje=len(pozycje),
    )

    pdf_bytes: bytes = weasyprint.HTML(string=html).write_pdf() or b""
    return pdf_bytes


def _calc_sums(pozycje: list[dict], header: dict) -> dict:
    """Oblicz sumy z listy pozycji (fallback gdy brak w nagłówku)."""
    r = sum(float(p.get("r_total") or 0) for p in pozycje)
    m = sum(float(p.get("m_total") or 0) for p in pozycje)
    s = sum(float(p.get("s_total") or 0) for p in pozycje)
    ko = sum(float(p.get("ko_total") or 0) for p in pozycje)
    kz = sum(float(p.get("kz_total") or 0) for p in pozycje)
    z = sum(float(p.get("z_total") or 0) for p in pozycje)
    netto = sum(float(p.get("wartosc_netto") or 0) for p in pozycje)
    vat_pct = float(header.get("vat_pct") or 23)
    vat = round(netto * vat_pct / 100, 2)
    brutto = round(netto + vat, 2)
    return dict(r=r, m=m, s=s, ko=ko, kz=kz, z=z, netto=netto, vat=vat, brutto=brutto)
