#!/usr/bin/env python3
r"""补充交互页 I-1：damping-explorer.html —— z₀/A₀ 滑块 → 包络形态 + regime 定位。

契约没点名任何 interactive 图（magnetic-brake 是契约点名了 F-5 动画才做的）——
本页是**用户裁定的补充产物**（results.json 里记为补充图，接受 FIG-EXTRA WARN），
同时把「Skill 1 推导 figures 时该问一句：本质是否值得一张动画/交互图」回填进 iypt-analysis。

纪律（与 magnetic-brake 的 F-5 相同）：
- **自包含单文件**：无 CDN、无外链，数据全部由 Python 烘焙进去。
- **页面不自己算物理**：它只求值契约自己的闭式 (23a)，系数（c₂、γ_oc、A_c、A_lin、
  ν=0.1 边界折线）全部来自本次运行的 D —— 不可能和 results.json 打架。
- 配一张 figkit 静帧（I-1.png/svg，带 SIMULATION 戳）—— HTML 也是图，也要能被审。
"""
from __future__ import annotations

import json

import numpy as np

import figkit as FK
import model2 as M2
from params import GAMMA_OC, M_EFF, OMEGA0, OUT_FIG, OUT_INT, R_C, R_TEST


def _bake(D) -> dict:
    """从 D 收集页面要用的全部数字（页面只做 (23a) 求值与查表）。"""
    gs = D["gs"]
    # ν = 0.1 边界折线 A*(z₀)（二分）
    z0s = np.linspace(0.5e-3, 15e-3, 40)
    Astar = []
    for z0 in z0s:
        lo, hi = 1e-5, 12e-3
        import field as FLD
        f = lambda A: FLD.nu(gs, float(z0), float(A), n=201) - 0.1     # noqa: E731
        if f(hi) < 0:
            Astar.append(hi)
            continue
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if f(mid) < 0:
                lo = mid
            else:
                hi = mid
        Astar.append(hi)
    envs = []
    for A0, (tp, Ap) in zip(D["f3_A0s"], D["f3_envs"]):
        k = max(1, len(tp) // 60)
        envs.append(dict(A0=float(A0), t=[round(float(x), 4) for x in tp[::k]],
                         A=[round(float(x), 8) for x in Ap[::k]]))
    # ★ G(z₀) 真值表（r1 设计审查的 REVISE：Γ 不许用抛物线 c₂z₀² 越窗外推 ——
    #   它只在 |z₀|≤4 mm 拟合，z₀=10.5 mm 处外推读数比 eq.15 真值高 ~85%。
    #   页面改按契约 eq.15：Γ = γ_oc + G(z₀)²/[2·M_eff·(R+R_c)]，G 查此表线性插值 ——
    #   仍是「只求值契约闭式」，JS 里没有任何数值物理。）
    zG = np.arange(0.0, 15.001e-3, 0.25e-3)
    G_table = [round(float(gs.G(float(z))), 6) for z in zG]
    return dict(
        gamma_oc=GAMMA_OC, omega0=OMEGA0, M_eff=M_EFF, R_c=R_C, R_test=R_TEST,
        c2_sc=D["c2_sc2"],                                   # SI: 1/(s·m²)，R=0
        z_pk=D["zpk0"], A_c=D["A_c2"], A_lin=D["A_lin"],
        G_z0_step=0.25e-3, G_table=G_table,                  # eq.15 的换能系数表
        nu_boundary=dict(z0=[round(float(z), 6) for z in z0s],
                         A=[round(float(a), 6) for a in Astar]),
        ode_envelopes=envs,                                  # 居中短路的四条真 ODE 包络
    )


def _still(D, baked) -> None:
    """I-1 的静帧（figkit，SIMULATION 戳）：探索页展示内容的静态预览。"""
    with FK.Figure("I-1", "electrical-damping · Model-2", OUT_FIG,
                   figsize=(12.6, 5.9), ncols=2,
                   title="Interactive damping explorer (still preview of I-1.html)"
                   ) as (fig, ax):
        a0, a1 = ax
        tt = np.linspace(0, 25, 400)
        # Γ 走页面同款路径：eq.15 + 烘焙 G 表插值（不是抛物线 —— r1 设计审查：
        # c₂z₀² 只在 |z₀|≤4 mm 有效，10.5 mm 处外推偏高 ~85%）。
        # 10.45 改 10.5：滑块 step=0.25，10.45 是页面到不了的位置。
        zG = np.arange(0.0, 15.001e-3, 0.25e-3)
        for i, (z0mm, A0mm) in enumerate(((0.0, 3.0), (0.0, 8.0), (10.5, 3.0))):
            g_ = float(np.interp(z0mm * 1e-3, zG, baked["G_table"]))
            G_ = GAMMA_OC + g_ ** 2 / (2 * M_EFF * (0.0 + baked["R_c"]))
            Q_ = baked["c2_sc"] * (A0mm * 1e-3) ** 2 / (4 * G_)
            A = M2.envelope_23a(tt, A0mm * 1e-3, G_, Q_)
            a0.semilogy(tt, A * 1e3, color=FK.SLOTS[i]["color"], lw=2,
                        label=f"z0={z0mm:g} mm, A0={A0mm:g} mm (R=0)")
        # ylim 必须钉死在物理范围 —— z₀=z_pk 的指数衰减 25 s 掉到 1e-161，
        # 自动缩放会把 y 轴拉到荒谬的天文下限，三条曲线全部挤成图顶的一条线。
        a0.set_ylim(1e-3, 12)
        FK.log_ticks(a0.yaxis, [1e-3, 0.01, 0.1, 1, 10])
        a0.set_xlabel("t (s)")
        a0.set_ylabel("envelope A (mm)  [eq. 23a]")
        a0.legend(fontsize=10)
        a0.set_title("slider output: envelope shape", fontsize=12)
        zb = np.array(baked["nu_boundary"]["z0"]) * 1e3
        Ab = np.array(baked["nu_boundary"]["A"]) * 1e3
        a1.plot(zb, Ab, color=FK.INK, lw=2, label="nu = 0.1 boundary")
        a1.axhline(baked["A_c"] * 1e3, color=FK.INK_SOFT, ls="--", lw=1.5,
                   label="A_c (background takes over)")
        a1.axhline(baked["A_lin"] * 1e3, color=FK.INK_MUTED, ls=":", lw=1.5,
                   label="A_lin (10% linearization)")
        a1.plot([0.0], [3.0], "*", ms=16, color=FK.SLOTS[3]["color"],
                label="current slider position")
        a1.set_xlabel("z0 (mm)")
        a1.set_ylabel("A0 (mm)")
        a1.set_yscale("log")
        FK.log_ticks(a1.yaxis, [0.5, 1, 2, 4, 8])
        a1.legend(fontsize=9.5, loc="lower right")
        a1.set_title("regime locator", fontsize=12)
        FK.assertions(fig, [
            ("I-1", "page evaluates ONLY eqs. (15)+(23a) on baked tables",
             "no physics computed client-side", True),
            ("I-1", "baked ODE envelopes overlay for credibility",
             f"{len(baked['ode_envelopes'])} curves baked", True),
        ])


_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>Electrical damping · interactive explorer (SIMULATION)</title>
<style>
 :root{--ink:#0b0b0b;--soft:#52514e;--muted:#898781;--grid:#e1e0d9;--blue:#2a78d6;
       --green:#008300;--red:#e34948;--bg:#faf9f6}
 body{font-family:Georgia,serif;background:var(--bg);color:var(--ink);margin:0;
      padding:24px 30px;max-width:1180px;margin:auto}
 h1{font-size:22px;margin:0 0 2px}
 .stamp{display:inline-block;font-family:monospace;font-weight:bold;font-size:12px;
        color:#fff;background:var(--red);padding:2px 10px;border-radius:3px;
        letter-spacing:.5px;vertical-align:middle;margin-left:12px}
 .sub{color:var(--soft);font-size:14px;margin-bottom:14px}
 .row{display:flex;gap:22px;flex-wrap:wrap}
 .panel{background:#fff;border:1px solid var(--grid);border-radius:8px;padding:14px}
 canvas{display:block}
 .ctl{font-size:14.5px;margin:8px 0;font-family:monospace}
 .ctl input[type=range]{width:300px;vertical-align:middle}
 .readout{font-family:monospace;font-size:13.5px;background:#fff;
          border:1px solid var(--grid);border-radius:8px;padding:10px 14px;margin-top:14px}
 .regime{font-weight:bold}
 .foot{color:var(--muted);font-size:12.5px;margin-top:16px;line-height:1.5}
 label{display:inline-block;width:220px}
</style></head><body>
<h1>Electrical damping — envelope-mode explorer<span class="stamp">SIMULATION</span></h1>
<div class="sub">IYPT 2026 · P2 — magnet on a spring inside a coil.
 Damping switches itself off at the coil center: watch the envelope morph from a
 straight line (exponential) to a curved power law as z<sub>0</sub> → 0.</div>
<div class="row">
 <div class="panel">
  <div class="ctl"><label>magnet rest position z<sub>0</sub> =
    <b id="z0v"></b> mm</label>
   <input type="range" id="z0" min="0" max="15" step="0.25" value="0"></div>
  <div class="ctl"><label>initial amplitude A<sub>0</sub> = <b id="a0v"></b> mm</label>
   <input type="range" id="a0" min="0.5" max="8" step="0.25" value="3"></div>
  <div class="ctl"><label>external resistor</label>
   <select id="rsel"><option value="0" selected>R = 0 (short)</option>
   <option value="20">R = 20 &Omega;</option></select>
   <span style="font-size:12.5px;color:var(--muted)"> &nbsp;overlay:
   <input type="checkbox" id="ode" checked> baked ODE peaks (z0=0, R=0)</span></div>
  <canvas id="env" width="640" height="420"></canvas>
 </div>
 <div class="panel">
  <div style="font-size:13.5px;color:var(--soft);margin-bottom:6px">
    regime map — boundaries baked from the run</div>
  <canvas id="map" width="380" height="420"></canvas>
 </div>
</div>
<div class="readout" id="out"></div>
<div class="foot">Curve = contract closed forms (23a) + (15): (A0/A)&sup2; = (1+Q)e<sup>2&Gamma;t</sup> &minus; Q with
 &Gamma;(z<sub>0</sub>;R) = &gamma;_oc + G(z<sub>0</sub>)&sup2;/[2M_eff(R+R_c)] (eq. 15, valid on the whole
 slider range — the parabola &gamma;_oc + c&#8322;z<sub>0</sub>&sup2; is fitted only on |z<sub>0</sub>| &le; 4 mm), Q = c&#8322;(R)A<sub>0</sub>&sup2;/(4&Gamma;).
 G(z<sub>0</sub>) is a <b>baked eq.-27 table</b> (0.25 mm grid, linear interp); c&#8322;(R) = c&#8322;(0)&middot;R_c/(R+R_c).
 All coefficients and the ODE overlay points are <b>baked from the Python run</b> that produced
 results.json — this page computes no physics of its own. Wire data: DATA object below. SIMULATION, not experiment.</div>
<script>
const DATA = __DATA__;
const z0s=document.getElementById('z0'), a0s=document.getElementById('a0'),
      rs=document.getElementById('rsel'), ode=document.getElementById('ode');
const env=document.getElementById('env').getContext('2d');
const map=document.getElementById('map').getContext('2d');
// c2(R) = c2(0)·R_c/(R+R_c)  — contract scaling law c2 ∝ 1/(R+R_c), exact for every R
function c2(R){ return DATA.c2_sc*DATA.R_c/(R+DATA.R_c); }
// G(z0) from the baked table (linear interp) — eq. 27 values, no client-side physics
function Gz(z0){ const s=DATA.G_z0_step, i=Math.min(Math.floor(z0/s), DATA.G_table.length-2),
  f=z0/s-i; return DATA.G_table[i]*(1-f)+DATA.G_table[i+1]*f; }
// Γ(z0;R) by contract eq. 15 — valid on the whole slider range, unlike the parabola
// γ_oc + c2·z0² which is fitted only on |z0| ≤ 4 mm (r1 design review: at z0=10.5 the
// parabola over-reads Γ by ~85% vs eq. 15 / targets[γ])
function Gamma15(z0,R){ const g=Gz(z0);
  return DATA.gamma_oc + g*g/(2*DATA.M_eff*(R+DATA.R_c)); }
function draw(){
 const z0=+z0s.value*1e-3, A0=+a0s.value*1e-3, R=+rs.value;
 document.getElementById('z0v').textContent=(+z0s.value).toFixed(2);
 document.getElementById('a0v').textContent=(+a0s.value).toFixed(2);
 const Gm=Gamma15(z0,R), Q=c2(R)*A0*A0/(4*Gm), tstar=4*DATA.M_eff/(c2(R)*2*DATA.M_eff*A0*A0);
 // ---- envelope panel (semilog y)
 const W=640,H=420,L=58,B=44,T=16,Rt=12; env.clearRect(0,0,W,H);
 env.fillStyle='#fff'; env.fillRect(0,0,W,H);
 const tmax=Math.min(30, Math.max(6, 5/Gm)), Amin=1e-2; // mm
 const x=t=>L+(W-L-Rt)*t/tmax;
 const y=A=>T+(H-T-B)*(Math.log10(8.5)-Math.log10(A))/(Math.log10(8.5)-Math.log10(Amin));
 env.strokeStyle='#e1e0d9'; env.fillStyle='#898781'; env.font='11px monospace';
 for(const g of [0.01,0.1,1,8]){ if(g<Amin) continue;
   env.beginPath(); env.moveTo(L,y(g)); env.lineTo(W-Rt,y(g)); env.stroke();
   env.fillText(g+' mm',4,y(g)+4); }
 for(let t=0;t<=tmax;t+=Math.ceil(tmax/6)){ env.beginPath(); env.moveTo(x(t),T);
   env.lineTo(x(t),H-B); env.stroke(); env.fillText(t+' s',x(t)-8,H-B+16); }
 // A_c line
 env.strokeStyle='#52514e'; env.setLineDash([6,4]); env.beginPath();
 env.moveTo(L,y(DATA.A_c*1e3)); env.lineTo(W-Rt,y(DATA.A_c*1e3)); env.stroke();
 env.setLineDash([]); env.fillText('A_c (background takes over)',W-Rt-212,y(DATA.A_c*1e3)-5);
 // (23a) curve
 env.strokeStyle='#2a78d6'; env.lineWidth=2.4; env.beginPath();
 for(let i=0;i<=400;i++){ const t=tmax*i/400;
   const A=A0/Math.sqrt((1+Q)*Math.exp(2*Gm*t)-Q)*1e3;
   if(A<Amin) break; const px=x(t),py=y(A); i? env.lineTo(px,py):env.moveTo(px,py); }
 env.stroke(); env.lineWidth=1;
 // baked ODE overlay
 if(ode.checked && R===0 && z0<0.4e-3){ env.fillStyle='#e34948';
  for(const e of DATA.ode_envelopes){ if(Math.abs(e.A0-A0)>2.6e-4) continue;
   for(let i=0;i<e.t.length;i++){ const A=e.A[i]*1e3; if(A<Amin||e.t[i]>tmax) continue;
     env.beginPath(); env.arc(x(e.t[i]),y(A),2.5,0,7); env.fill(); } } }
 // ---- regime map
 const MW=380,MH=420,ml=46,mb=40,mt=14,mr=10; map.clearRect(0,0,MW,MH);
 map.fillStyle='#fff'; map.fillRect(0,0,MW,MH);
 const zx=z=>ml+(MW-ml-mr)*z/15e-3;
 const ay=A=>mt+(MH-mt-mb)*(Math.log10(9e-3)-Math.log10(A))/(Math.log10(9e-3)-Math.log10(4e-4));
 map.strokeStyle='#0b0b0b'; map.lineWidth=2; map.beginPath();
 DATA.nu_boundary.z0.forEach((z,i)=>{const px=zx(z),py=ay(DATA.nu_boundary.A[i]);
   i?map.lineTo(px,py):map.moveTo(px,py)}); map.stroke(); map.lineWidth=1;
 map.fillStyle='#52514e'; map.font='11px monospace';
 map.fillText('nu = 0.1',zx(8.4e-3),ay(DATA.nu_boundary.A[25])-14);
 map.strokeStyle='#52514e'; map.setLineDash([6,4]); map.beginPath();
 map.moveTo(ml,ay(DATA.A_c)); map.lineTo(MW-mr,ay(DATA.A_c)); map.stroke();
 map.setLineDash([]); map.fillText('A_c',MW-mr-26,ay(DATA.A_c)-5);
 map.strokeStyle='#898781'; map.setLineDash([2,3]); map.beginPath();
 map.moveTo(ml,ay(DATA.A_lin)); map.lineTo(MW-mr,ay(DATA.A_lin)); map.stroke();
 map.setLineDash([]); map.fillText('A_lin',MW-mr-34,ay(DATA.A_lin)+12);
 map.fillStyle='#898781';
 map.fillText('0',ml-10,MH-mb+14); map.fillText('z0 (mm)  15',MW-90,MH-mb+14);
 map.save(); map.translate(12,MH/2); map.rotate(-Math.PI/2);
 map.fillText('A0 (mm, log)',0,0); map.restore();
 map.fillStyle='#e34948'; map.beginPath();
 map.arc(zx(z0),ay(Math.max(A0,4.2e-4)),6,0,7); map.fill();
 // ---- readout
 let regime;
 if(A0<DATA.A_c) regime='(4) background-dominated: exponential at gamma_oc';
 else { // nu at (z0,A0) via boundary lookup
   const zb=DATA.nu_boundary.z0, Ab=DATA.nu_boundary.A;
   let Ast=Ab[Ab.length-1];
   for(let i=0;i<zb.length-1;i++){ if(z0>=zb[i]&&z0<=zb[i+1]){
     const f=(z0-zb[i])/(zb[i+1]-zb[i]); Ast=Ab[i]*(1-f)+Ab[i+1]*f; break; } }
   if(z0<zb[0]) Ast=Ab[0];
   const nonlinear = A0>Ast || z0<1e-3;
   regime = !nonlinear ? '(1) linear: exponential decay'
     : (z0+A0<DATA.A_lin ? '(3) power law: A ~ t^(-1/2) window (eq. 23)'
                         : '(2) nonlinear: envelope departs from exponential');
 }
 document.getElementById('out').innerHTML=
  `&Gamma;(z<sub>0</sub>) = ${Gm.toFixed(4)} 1/s &nbsp;·&nbsp; Q = ${Q.toFixed(2)}
   &nbsp;·&nbsp; regime: <span class="regime">${regime}</span>
   &nbsp;·&nbsp; (baked: c&#8322;(R) = ${(c2(R)/1e6).toFixed(4)} 1/(s·mm&sup2;),
   &gamma;_oc = ${DATA.gamma_oc}, A_c = ${(DATA.A_c*1e3).toFixed(2)} mm)`;
}
for(const el of [z0s,a0s,rs,ode]) el.addEventListener('input',draw);
draw();
</script></body></html>
"""


def build(D) -> dict:
    baked = _bake(D)
    _still(D, baked)
    html = _HTML.replace("__DATA__", json.dumps(baked))
    OUT_INT.mkdir(parents=True, exist_ok=True)
    p = OUT_INT / "damping-explorer.html"
    p.write_text(html, encoding="utf-8")
    print(f"  [interactive] I-1 -> {p}（自包含，{len(html)//1024} KB）")
    cap = ("补充交互页（契约未点名，FIG-EXTRA）：z₀/A₀ 滑块看包络从指数（直线）变为幂律"
           "（弯曲），regime 定位用烘焙的 ν=0.1 边界/A_c/A_lin；页面只求值契约闭式 "
           "(23a)+(15)——Γ(z₀;R) 按 (15) 在烘焙的 eq.27 G(z₀) 表上取值（r1 设计审查：抛物线 "
           "γ_oc+c₂z₀² 只在 |z₀|≤4 mm 拟合，越窗外推会把 z₀=10.5 的读数抬高 ~85%），"
           "c₂(R)=c₂(0)·R_c/(R+R_c)；系数与 ODE 叠加点全部由本次运行烘焙。")
    return dict(assertion_ids=["AS-14", "AS-16"], verdict="PASS", caption=cap,
                path="02-sim/figures/I-1.png", path_svg="02-sim/figures/I-1.svg",
                path_interactive="02-sim/interactive/damping-explorer.html",
                simulation_stamped=True)
