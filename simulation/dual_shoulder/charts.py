"""Inline SVG charts for the report: line and scatter, one y-axis, hairline grid,
direct end labels, reference rules, and a hover readout (crosshair on lines,
per-point on scatters) driven by the data embedded in each figure."""
from __future__ import annotations

import html
import json
import math

W, H = 680, 320
PAD = {"l": 56, "r": 132, "t": 16, "b": 44}


def _nice_ticks(lo: float, hi: float, n: int = 5) -> list[float]:
    span = hi - lo or 1.0
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = min((s * mag for s in (1, 2, 2.5, 5, 10) if s * mag >= raw), default=mag * 10)
    start = math.floor(lo / step) * step
    ticks, v = [], start
    while v <= hi + step * 1e-6:
        if v >= lo - step * 1e-6:
            ticks.append(round(v, 10))
        v += step
    return ticks


def _fmt(v: float) -> str:
    return f"{v:.0f}" if abs(v) >= 10 or v == int(v) else f"{v:.1f}" if abs(v) >= 1 else f"{v:.2f}"


def figure(fid: str, title: str, subtitle: str, series: list[dict], x_label: str, y_label: str,
           refs: list[dict] = (), x_range=None, y_range=None, kind: str = "line",
           x_fmt: str = "{:.2f}", y_fmt: str = "{:.2f}", bands: list[dict] = ()) -> str:
    """series: {name, var (css custom property of the series colour), pts [(x, y)], label?}"""
    xs = [p[0] for s in series for p in s["pts"]]
    ys = [p[1] for s in series for p in s["pts"]] + [r["y"] for r in refs]
    x0, x1 = x_range or (min(xs), max(xs))
    y0, y1 = y_range or (min(0.0, min(ys)), max(ys) * 1.08)
    pw, ph = W - PAD["l"] - PAD["r"], H - PAD["t"] - PAD["b"]

    def sx(x):
        return PAD["l"] + (x - x0) / (x1 - x0) * pw

    def sy(y):
        return PAD["t"] + ph - (min(max(y, y0), y1) - y0) / (y1 - y0) * ph

    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-labelledby="{fid}-t" class="chart" data-fig="{fid}">',
           f'<title id="{fid}-t">{html.escape(title)}</title>']
    for b in bands:
        out.append(f'<rect x="{sx(b["x0"]):.1f}" y="{PAD["t"]}" width="{max(0.5, sx(b["x1"]) - sx(b["x0"])):.1f}" height="{ph}" class="band"/>')
        out.append(f'<text x="{(sx(b["x0"]) + sx(b["x1"])) / 2:.1f}" y="{PAD["t"] + 12}" class="band-label" text-anchor="middle">{html.escape(b["label"])}</text>')
    for t in _nice_ticks(y0, y1):
        out.append(f'<line x1="{PAD["l"]}" x2="{PAD["l"] + pw}" y1="{sy(t):.1f}" y2="{sy(t):.1f}" class="grid"/>')
        out.append(f'<text x="{PAD["l"] - 8}" y="{sy(t) + 4:.1f}" class="tick" text-anchor="end">{_fmt(t)}</text>')
    for t in _nice_ticks(x0, x1, 6):
        out.append(f'<text x="{sx(t):.1f}" y="{PAD["t"] + ph + 18}" class="tick" text-anchor="middle">{_fmt(t)}</text>')
    out.append(f'<line x1="{PAD["l"]}" x2="{PAD["l"] + pw}" y1="{PAD["t"] + ph}" y2="{PAD["t"] + ph}" class="axis"/>')
    out.append(f'<text x="{PAD["l"] + pw / 2:.1f}" y="{H - 6}" class="axis-label" text-anchor="middle">{html.escape(x_label)}</text>')
    out.append(f'<text x="14" y="{PAD["t"] + ph / 2:.1f}" class="axis-label" text-anchor="middle" transform="rotate(-90 14 {PAD["t"] + ph / 2:.1f})">{html.escape(y_label)}</text>')
    ends = []
    for r in refs:
        out.append(f'<line x1="{PAD["l"]}" x2="{PAD["l"] + pw}" y1="{sy(r["y"]):.1f}" y2="{sy(r["y"]):.1f}" class="ref"/>')
        ends.append([sy(r["y"]), r["label"], "ref-label"])
    for s in series:
        pts = s["pts"]
        if kind == "line":
            d = " ".join(f"{'M' if i == 0 else 'L'}{sx(x):.1f},{sy(y):.1f}" for i, (x, y) in enumerate(pts))
            out.append(f'<path d="{d}" class="line" style="stroke:var({s["var"]})"/>')
            x, y = pts[-1]
            out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="4" class="dot" style="fill:var({s["var"]})"/>')
            ends.append([sy(y), s.get("label", s["name"]), "end-label"])
        else:
            for x, y in pts:
                out.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3.2" class="pt" style="fill:var({s["var"]})"/>')
    # direct end labels and reference labels share the right margin; nudge apart only where they would overlap
    ends.sort()
    for i in range(1, len(ends)):
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 13)
    for yv, label, cls in ends:
        out.append(f'<text x="{PAD["l"] + pw + 6}" y="{yv + 4:.1f}" class="{cls}">{html.escape(label)}</text>')
    out.append(f'<line class="xhair" x1="0" x2="0" y1="{PAD["t"]}" y2="{PAD["t"] + ph}" visibility="hidden"/>')
    out.append(f'<rect class="hit" x="{PAD["l"]}" y="{PAD["t"]}" width="{pw}" height="{ph}"/>')
    out.append("</svg>")
    data = {"kind": kind, "x0": x0, "x1": x1, "y0": y0, "y1": y1, "pl": PAD["l"], "pw": pw, "pt": PAD["t"], "ph": ph,
            "xfmt": x_fmt, "yfmt": y_fmt,
            "xl": x_label, "series": [{"name": s["name"], "var": s["var"], "pts": s["pts"]} for s in series]}
    legend = "".join(f'<span class="key"><i style="background:var({s["var"]})"></i>{html.escape(s["name"])}</span>' for s in series)
    return (f'<figure class="fig" id="{fid}"><figcaption><b>{html.escape(title)}</b><span>{html.escape(subtitle)}</span></figcaption>'
            f'<div class="legend">{legend}</div><div class="plot">{"".join(out)}<div class="tip" hidden></div></div>'
            f'<script type="application/json" class="figdata">{html.escape(json.dumps(data), quote=False)}</script></figure>')


SCRIPT = r"""
for (const fig of document.querySelectorAll('figure.fig')) {
  const D = JSON.parse(fig.querySelector('.figdata').textContent);
  const svg = fig.querySelector('svg'), tip = fig.querySelector('.tip'), xh = svg.querySelector('.xhair');
  const f = (fmt, v) => { const m = fmt.match(/\.(\d)f/); return m ? v.toFixed(+m[1]) : String(v); };
  const toX = px => D.x0 + (px - D.pl) / D.pw * (D.x1 - D.x0);
  const show = (ev, html) => { tip.innerHTML = html; tip.hidden = false;
    const r = fig.querySelector('.plot').getBoundingClientRect();
    let left = ev.clientX - r.left + 14; if (left > r.width - 190) left = ev.clientX - r.left - 200;
    tip.style.left = left + 'px'; tip.style.top = (ev.clientY - r.top + 10) + 'px'; };
  svg.querySelector('.hit').addEventListener('mousemove', ev => {
    const pt = svg.createSVGPoint(); pt.x = ev.clientX; pt.y = ev.clientY;
    const p = pt.matrixTransform(svg.getScreenCTM().inverse()); const x = toX(p.x);
    if (D.kind === 'line') {
      xh.setAttribute('x1', p.x); xh.setAttribute('x2', p.x); xh.setAttribute('visibility', 'visible');
      let rows = '';
      for (const s of D.series) { let best = s.pts[0];
        for (const q of s.pts) if (Math.abs(q[0] - x) < Math.abs(best[0] - x)) best = q;
        rows += `<div><i style="background:var(${s.var})"></i>${s.name}<b>${f(D.yfmt, best[1])}</b></div>`; }
      show(ev, `<div class="th">${D.xl}: ${f(D.xfmt, x)}</div>` + rows);
    } else {
      // scatter: the nearest point on screen
      const sx = v => D.pl + (v - D.x0) / (D.x1 - D.x0) * D.pw, sy = v => D.pt + D.ph - (v - D.y0) / (D.y1 - D.y0) * D.ph;
      let best = null, bd = 1e9;
      for (const s of D.series) for (const q of s.pts) { const d = Math.hypot(sx(q[0]) - p.x, sy(q[1]) - p.y); if (d < bd) { bd = d; best = [s, q]; } }
      if (bd > 24) { tip.hidden = true; return; }
      if (best) show(ev, `<div class="th">${D.xl}: ${f(D.xfmt, best[1][0])}</div><div><i style="background:var(${best[0].var})"></i>${best[0].name}<b>${f(D.yfmt, best[1][1])}</b></div>`);
    }
  });
  svg.querySelector('.hit').addEventListener('mouseleave', () => { tip.hidden = true; xh.setAttribute('visibility', 'hidden'); });
}
"""
