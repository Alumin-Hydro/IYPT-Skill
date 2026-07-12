#!/usr/bin/env python3
"""F-5：涡流分布动画。**自包含单文件 HTML** —— 无 CDN、无外部字体、无 fetch。

可以直接发给队友、塞进 PPT、离线放。

**数据从 Python 烘焙进去（内联 JSON）。页面不许自己算物理** —— 否则它会算出一套和
results.json 不一致的数，而没有任何检查能发现。

物理：管壁上位于 z 处、厚 dz 的圆环，感应电动势 eps = -v * dPhi/dz，
电阻 dR = 2*pi*a / (sigma * w * dz)，于是环电流密度

    dI/dz = -(v * sigma * w) / (2*pi*a) * dPhi/dz

正比于 dPhi/dz —— 而它有闭式（field.py）。它是 z 的**奇函数**，所以电流分布必然是
**反对称双峰**：磁体前方与后方电流反向。前方排斥、后方吸引，两者都阻碍下落。
这正是 Lenz 定律。
"""
from __future__ import annotations

import json
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from params import OUT_INT, A_TUBE, W_WALL, R_MAG, L_MAG, SIGMA, M_DIP, MS
from field import dphi_dz, dphi_dz_dipole, peak_z_dipole

HTML = """<meta charset="utf-8">
<title>F-5 · Eddy currents in the pipe wall — magnetic brake</title>
<style>
  :root {
    --bg:#fcfcfb; --panel:#ffffff; --ink:#0b0b0b; --ink2:#52514e; --muted:#898781;
    --grid:#e1e0d9; --edge:#c3c2b7;
    --pos:#e34948;      /* current one way  */
    --neg:#2a78d6;      /* current the other way */
    --magnet:#4a3aa7;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg:#0d0d0d; --panel:#1a1a19; --ink:#ffffff; --ink2:#c3c2b7; --muted:#898781;
      --grid:#2c2c2a; --edge:#383835;
      --pos:#e66767; --neg:#3987e5; --magnet:#9085e9;
    }
  }
  body{margin:0;padding:22px;background:var(--bg);color:var(--ink);
       font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;}
  .wrap{max-width:1080px;margin:0 auto;}
  h1{font-size:21px;margin:0 0 4px;font-weight:700;letter-spacing:-.01em;}
  .sub{color:var(--ink2);font-size:14px;margin:0 0 18px;}
  .stamp{float:right;font:700 11px/1 ui-monospace,SFMono-Regular,Menlo,monospace;
         color:var(--muted);letter-spacing:.06em;padding-top:6px;}
  .stage{display:grid;grid-template-columns:210px 1fr;gap:20px;align-items:stretch;
         background:var(--panel);border:1px solid var(--edge);border-radius:12px;padding:18px;}
  @media (max-width:760px){ .stage{grid-template-columns:1fr;} }
  svg{display:block;width:100%;height:auto;overflow:visible;}
  .ctl{display:flex;gap:14px;align-items:center;margin-top:16px;flex-wrap:wrap;}
  button{font:600 14px system-ui;padding:8px 18px;border-radius:8px;cursor:pointer;
         border:1px solid var(--edge);background:var(--panel);color:var(--ink);}
  button:hover{border-color:var(--muted);}
  input[type=range]{flex:1;min-width:170px;accent-color:var(--neg);}
  .lg{display:flex;gap:20px;flex-wrap:wrap;margin-top:16px;font-size:13.5px;color:var(--ink2);}
  .lg i{display:inline-block;width:26px;height:4px;border-radius:2px;margin-right:7px;
        vertical-align:middle;}
  .note{margin-top:18px;padding:14px 16px;background:var(--panel);border:1px solid var(--edge);
        border-radius:10px;font-size:13.5px;color:var(--ink2);}
  .note b{color:var(--ink);}
  code{font:13px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--ink);}
  .kv{color:var(--muted);font-size:12.5px;margin-top:3px;}
  text{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;}
</style>

<div class="wrap">
<div class="stamp">SIMULATION · Model-2 · spec r1</div>
<h1>F-5 &nbsp;Eddy currents in the pipe wall</h1>
<p class="sub">Ring-current density <code>dI/dz</code> as the magnet falls. Antisymmetric
double peak — the current reverses across the magnet, so the wall <b>repels</b> in front and
<b>attracts</b> behind. Both oppose the fall. That is Lenz's law, drawn.</p>

<div class="stage">
  <svg id="tube" viewBox="0 0 200 420" aria-label="pipe cross-section"></svg>
  <svg id="prof" viewBox="0 0 640 420" aria-label="dI/dz profile"></svg>
</div>

<div class="ctl">
  <button id="play">Pause</button>
  <input id="scrub" type="range" min="0" max="1000" value="0">
  <span class="kv" id="pos"></span>
</div>

<div class="lg">
  <span><i style="background:var(--neg)"></i>current one way (behind the magnet)</span>
  <span><i style="background:var(--pos)"></i>current the other way (ahead of it)</span>
  <span><i style="background:var(--magnet)"></i>magnet</span>
  <span><i style="background:var(--muted);height:0;border-top:2px dashed var(--muted)"></i>point-dipole model</span>
</div>

<div class="note">
  <b>The peak sits on the magnet's end face, not at a/2.</b>
  The point-dipole model puts the current peak at <code>|z| = a/2 = __ZPKD__ mm</code>.
  The real finite magnet puts it at <code>|z| = __ZPK__ mm</code> — essentially
  <code>L/2 = __LHALF__ mm</code>, the end face itself.
  <br><br>
  That is not a coincidence. Because <code>&part;&Phi;/&part;z = M<sub>s</sub>[M(R,r,z+L/2) &minus; M(R,r,z&minus;L/2)]</code>,
  the eddy current is literally <b>the difference between two Ampèrian end-rings</b> — so it
  peaks where those rings are. It is a third independent witness that assumption <b>A-1</b>
  (point dipole) has broken down: <code>a/L = 0.60</code>, and the criterion needs <code>a &gg; L</code>.
</div>
</div>

<script>
const D = __DATA__;

const TUBE = document.getElementById('tube');
const PROF = document.getElementById('prof');
const NS = 'http://www.w3.org/2000/svg';
const mk = (t, a) => { const e = document.createElementNS(NS, t);
  for (const k in a) e.setAttribute(k, a[k]); return e; };

// ---------- 剖面图（右）：dI/dz vs z（磁体参考系 —— 它随磁体刚性平移）
const PW = 640, PH = 420, PL = 62, PR = 18, PT = 26, PB = 46;
const zx = z => PL + (z - D.z[0]) / (D.z[D.z.length-1] - D.z[0]) * (PW - PL - PR);
const iy = v => PT + (1 - (v + 1) / 2) * (PH - PT - PB);

function drawProfile() {
  PROF.innerHTML = '';
  const g = mk('g', {}); PROF.appendChild(g);
  const css = getComputedStyle(document.documentElement);
  const GRID = css.getPropertyValue('--grid'), MUT = css.getPropertyValue('--muted');
  const INK2 = css.getPropertyValue('--ink2');

  for (const v of [-1,-0.5,0,0.5,1]) {
    g.appendChild(mk('line', {x1:PL, x2:PW-PR, y1:iy(v), y2:iy(v),
      stroke: v===0 ? MUT : GRID, 'stroke-width': v===0 ? 1.4 : 1}));
    g.appendChild(mk('text', {x:PL-10, y:iy(v)+4, fill:MUT, 'font-size':12,
      'text-anchor':'end'})).textContent = v.toFixed(1);
  }
  for (const z of [-15,-10,-5,0,5,10,15]) {
    if (z < D.z[0] || z > D.z[D.z.length-1]) continue;
    g.appendChild(mk('line', {x1:zx(z), x2:zx(z), y1:PT, y2:PH-PB, stroke:GRID, 'stroke-width':1}));
    g.appendChild(mk('text', {x:zx(z), y:PH-PB+20, fill:MUT, 'font-size':12,
      'text-anchor':'middle'})).textContent = z;
  }
  g.appendChild(mk('text', {x:(PL+PW-PR)/2, y:PH-8, fill:INK2, 'font-size':13.5,
    'text-anchor':'middle'})).textContent = 'z − z_magnet   (mm)';
  const ymid = (PT + PH - PB) / 2;
  g.appendChild(mk('text', {x:16, y:ymid, fill:INK2, 'font-size':13.5,
    transform:`rotate(-90 16 ${ymid})`,
    'text-anchor':'middle'})).textContent = 'dI/dz   (normalised to own peak)';

  const path = a => a.map((v,i) => `${i?'L':'M'}${zx(D.z[i]).toFixed(2)},${iy(v).toFixed(2)}`).join('');
  g.appendChild(mk('path', {d:path(D.dip), fill:'none', stroke:MUT,
    'stroke-width':2, 'stroke-dasharray':'7 4', opacity:0.85}));
  g.appendChild(mk('path', {d:path(D.m2), fill:'none',
    stroke: css.getPropertyValue('--neg'), 'stroke-width':2.8, 'stroke-linecap':'round'}));

  // 峰位标记
  for (const [z, col, lab] of [[D.zpk, css.getPropertyValue('--neg'), 'L/2'],
                               [D.zpk_dip, MUT, 'a/2']]) {
    g.appendChild(mk('line', {x1:zx(z), x2:zx(z), y1:PT, y2:PH-PB, stroke:col,
      'stroke-width':1.4, 'stroke-dasharray':'3 3', opacity:0.9}));
    g.appendChild(mk('text', {x:zx(z)+5, y:PT+14, fill:col, 'font-size':12,
      'font-weight':600})).textContent = `${lab} = ${z.toFixed(2)} mm`;
  }
}

// ---------- 管子（左）：实验室系，磁体下落，壁上电流带随之平移
const TW = 200, TH = 420, TCX = 100;
const AW = 34, WALL = 12;                 // 管内半径 / 壁厚（像素）
const MAGW = 28, MAGH = 46;               // 磁体（像素）
const SPAN = 150;                          // 可见的管长（mm）
const my = zmm => TH/2 + (zmm) * (TH - 60) / SPAN;

function drawTube(zmag) {
  TUBE.innerHTML = '';
  const css = getComputedStyle(document.documentElement);
  const EDGE = css.getPropertyValue('--edge'), MUT = css.getPropertyValue('--muted');
  const POS = css.getPropertyValue('--pos'), NEG = css.getPropertyValue('--neg');
  const g = mk('g', {}); TUBE.appendChild(g);

  // 电流带：按 dI/dz 的符号与大小上色（磁体参考系的 profile 平移到实验室系）
  const N = D.z.length, step = 3;
  for (let i = 0; i < N - step; i += step) {
    const zlab = D.z[i] + zmag;
    const y = my(zlab);
    if (y < 8 || y > TH - 8) continue;
    const v = D.m2[i];
    const col = v >= 0 ? POS : NEG;
    const op = Math.min(1, Math.abs(v)) * 0.92;
    const hgt = Math.abs(my(D.z[i+step]) - my(D.z[i])) + 0.6;
    for (const sx of [-1, 1]) {
      g.appendChild(mk('rect', {
        x: TCX + sx * (AW + WALL) - (sx > 0 ? 0 : WALL), y: y, width: WALL, height: hgt,
        fill: col, opacity: op.toFixed(3)}));
    }
  }

  // 管壁轮廓
  for (const sx of [-1, 1]) {
    g.appendChild(mk('rect', {x: TCX + sx*(AW+WALL) - (sx>0?0:WALL), y: 6,
      width: WALL, height: TH-12, fill:'none', stroke:EDGE, 'stroke-width':1.4}));
  }

  // 磁体
  const ym = my(zmag);
  g.appendChild(mk('rect', {x: TCX - MAGW/2, y: ym - MAGH/2, width: MAGW, height: MAGH,
    rx: 3, fill: css.getPropertyValue('--magnet')}));
  g.appendChild(mk('text', {x: TCX, y: ym + 4, fill:'#fff', 'font-size':12,
    'font-weight':700, 'text-anchor':'middle'})).textContent = 'N/S';
  // 下落方向
  g.appendChild(mk('path', {d:`M${TCX},${ym+MAGH/2+10} l0,20 m-5,-6 l5,6 l5,-6`,
    stroke: css.getPropertyValue('--magnet'), 'stroke-width':2, fill:'none'}));
  g.appendChild(mk('text', {x: TCX, y: 20, fill: MUT, 'font-size':11.5,
    'text-anchor':'middle'})).textContent = 'g ↓';
}

// ---------- 动画
let t = 0, playing = true;
const scrub = document.getElementById('scrub');
const posLab = document.getElementById('pos');
const btn = document.getElementById('play');

function frame() {
  const zmag = -SPAN/2 + (t/1000) * SPAN;
  drawTube(zmag);
  posLab.textContent = `magnet at z = ${zmag.toFixed(1)} mm    ·    v_t = ${D.vt.toFixed(2)} cm/s (Model-2)`;
  if (playing) { t = (t + 2.2) % 1000; scrub.value = t; }
  requestAnimationFrame(frame);
}
btn.onclick = () => { playing = !playing; btn.textContent = playing ? 'Pause' : 'Play'; };
scrub.oninput = e => { playing = false; btn.textContent = 'Play'; t = +e.target.value; };

drawProfile();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
  drawProfile();
});
frame();
</script>
"""


def build() -> str:
    z = np.linspace(-3.2 * A_TUBE, 3.2 * A_TUBE, 401)

    d2 = dphi_dz(R_MAG, L_MAG, MS, A_TUBE, z)
    dd = dphi_dz_dipole(M_DIP, A_TUBE, z)

    # dI/dz = -(v sigma w)/(2 pi a) * dPhi/dz  —— 正比于 -dPhi/dz。
    # 两条曲线各自按自己的峰归一化：这里比较的是**形状与峰位**，不是幅值。
    i2 = -d2 / np.max(np.abs(d2))
    idd = -dd / np.max(np.abs(dd))

    zpk = abs(float(z[int(np.argmax(np.abs(d2)))])) * 1e3
    zpk_dip = peak_z_dipole(A_TUBE) * 1e3

    from model2 import damping
    from params import M_MASS, G
    vt2 = M_MASS * G / damping(R_MAG, L_MAG, MS, A_TUBE, W_WALL, SIGMA)

    data = dict(
        z=[round(v * 1e3, 4) for v in z],
        m2=[round(float(v), 5) for v in i2],
        dip=[round(float(v), 5) for v in idd],
        zpk=round(zpk, 3), zpk_dip=round(zpk_dip, 3),
        vt=round(float(vt2) * 100, 3),
    )

    html = (HTML
            .replace("__DATA__", json.dumps(data, separators=(",", ":")))
            .replace("__ZPKD__", f"{zpk_dip:.2f}")
            .replace("__ZPK__", f"{zpk:.2f}")
            .replace("__LHALF__", f"{L_MAG*1e3/2:.2f}"))

    OUT_INT.mkdir(parents=True, exist_ok=True)
    out = OUT_INT / "F-5-eddy-currents.html"
    out.write_text(html, encoding="utf-8")
    print(f"  [F-5] -> {out}   ({len(html)/1024:.0f} KB, 自包含单文件)")
    print(f"        峰位 |z| = {zpk:.3f} mm   vs   点偶极子的 a/2 = {zpk_dip:.3f} mm"
          f"   (L/2 = {L_MAG*1e3/2:.2f} mm)")
    return str(out)


if __name__ == "__main__":
    from params import banner
    banner()
    build()
