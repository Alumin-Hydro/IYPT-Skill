#!/usr/bin/env python3
r"""F-1..F-6 + V-1：契约 figures[] 的图。全部经 figkit 出（SIMULATION 戳、断言画轴外、
图上英文）。caption 数字从 D 取，不手打。make_all(AS, D) → {fig_id: meta}。"""
from __future__ import annotations
import math
import numpy as np
import figkit as FK
import model as M
from params import OMEGA1, A0, E_REST, F1, C, L, G, K_H_BASE, OUT_FIG

STAMP = "ball-on-ferrite-rod · Model-2"


def _rows(AS, ids):
    vd = {a["id"]: a["verdict"] for a in AS}
    order = {"PASS": 0, "PRESCRIBED": 1, "FAIL-MODEL": 2, "FAIL-CODE": 3}
    out = []
    for i, exp, meas in ids:
        out.append((i, exp, meas, vd[i] in ("PASS", "PRESCRIBED")))
    return out


def _verdict(AS, ids):
    order = {"PASS": 0, "PRESCRIBED": 1, "FAIL-MODEL": 2, "FAIL-CODE": 3}
    vd = {a["id"]: a["verdict"] for a in AS}
    return max((vd[i] for i in ids), key=lambda v: order[v])


# ═══════════════════════════════════════════════════════════ F-1 resonance
def f1(AS, D):
    with FK.Figure("F-1", STAMP, OUT_FIG, figsize=(9.0, 5.6),
                   title="Rod resonance A(f): peak fixes the boundary condition") as (fig, ax):
        fs, Af = D["res_fs"] / 1e3, D["res_A"]
        FK.plot_model(ax, fs, Af / Af.max(), 0, "driven tip amplitude A(f) (Lorentz, Q=100)")
        ax.axvline(D["peak_c4L"] / 1e3, color=FK.INK, ls="-", lw=1.4)
        ax.annotate(f"fixed-free f₁ = c/4L = {D['peak_c4L']/1e3:.2f} kHz  ✓ (peak here)",
                    xy=(D["peak_c4L"] / 1e3, 1.0), xytext=(6, -6), textcoords="offset points",
                    fontsize=10.5, color=FK.INK, fontweight="bold")
        ax.axvline(D["peak_c2L"] / 1e3, color=FK.SLOTS[3]["color"], ls="--", lw=1.4)
        ax.annotate(f"free-free c/2L = {D['peak_c2L']/1e3:.1f} kHz\n(no peak ⟹ not this BC)",
                    xy=(D["peak_c2L"] / 1e3, 0.4), fontsize=10, color=FK.SLOTS[3]["color"], ha="right")
        ax.set_xlabel("drive frequency f (kHz)")
        ax.set_ylabel("normalized tip amplitude A/A_max")
        ax.legend(loc="upper right", fontsize=10)
        FK.assertions(fig, _rows(AS, [
            ("AS-2", "peak at f_1 = c/4L (<5%)", f"{D['res_peak']/1e3:.2f} kHz ({D['A1_dev']:+.2%})"),
            ("AS-8", "c/4L vs c/2L discrete 2×", f"c/4L={D['peak_c4L']/1e3:.1f}, c/2L={D['peak_c2L']/1e3:.1f} kHz"),
        ]))
    cap = (f"棒受迫共振曲线，峰在 f₁=c/4L={D['peak_c4L']/1e3:.2f} kHz（固定-自由）。"
           f"★ 峰位是 A-1 的退化特征：固定-自由 c/4L vs 自由-自由 c/2L={D['peak_c2L']/1e3:.1f} kHz，"
           f"差 2× 离散。诚实局限（r2-H1'）：加 1f+2f 偏置后 14 kHz 处两种 BC 都有峰，"
           f"峰位单读数不足以定 BC，实测需模式形状。")
    return dict(assertion_ids=["AS-2", "AS-8"], verdict=_verdict(AS, ["AS-2", "AS-8"]), caption=cap)


# ═══════════════════════════════════════════════════════════ F-2 Poincaré / phase
def f2(AS, D):
    w, e = OMEGA1, E_REST
    us, phis = M.bounce_series(A0, w, e, n=6000, burn=2000)
    with FK.Figure("F-2", STAMP, OUT_FIG, figsize=(9.0, 5.6),
                   title="Bouncing map: high-Γ diffuse cloud (random phase)") as (fig, ax):
        ax.plot(phis, us, ".", ms=2.0, color=FK.SLOTS[0]["color"], alpha=0.4)
        ax.set_xlabel("impact phase φ (rad)")
        ax.set_ylabel("landing speed u (m/s)")
        ax.annotate(f"Γ={D['gamma_base']:.0f} >> π ⟹ φ effectively random\n"
                    f"⟹ statistical steady state, not a locked period-1",
                    xy=(0.03, 0.03), xycoords="axes fraction", fontsize=10.5,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=3))
        FK.assertions(fig, _rows(AS, [
            ("AS-7", "f/f_bounce >> 1 (random phase)", f"Γ={D['gamma_base']:.0f}, f/f_bounce={D['ffb']:.0f}"),
            ("AS-5", "must_not single-valued lock", f"CV={D['cv']:.2f} (broad)"),
        ]))
    cap = (f"碰撞映射的 Poincaré（落速 u vs 落相 φ）。Γ={D['gamma_base']:.0f}>>π ⟹ 落相有效随机 ⟹ "
           f"弥散云=随机相位统计稳态（非单值锁相，CV={D['cv']:.2f}）。这是本题可见弹跳的真实 regime。")
    return dict(assertion_ids=["AS-7", "AS-5"], verdict=_verdict(AS, ["AS-7", "AS-5"]), caption=cap)


# ═══════════════════════════════════════════════════════════ F-3 collapse
def f3(AS, D):
    w = OMEGA1
    with FK.Figure("F-3", STAMP, OUT_FIG, figsize=(9.0, 5.6),
                   title="Data collapse: h̄ ∝ (Aω)², slope = k_h (zero-parameter)") as (fig, ax):
        x, y = D["collapse_Aw2"], D["collapse_hb"] * 1e3
        xx = np.linspace(0, x.max() * 1.05, 100)
        FK.plot_reference(ax, xx, K_H_BASE * xx * 1e3, f"theory  k_h·(Aω)²  (k_h={K_H_BASE:.4f})")
        FK.plot_model(ax, x, y, 0, "sim h̄ (random-phase steady state)")
        ax.set_xlabel("(Aω)²  (m²/s²)")
        ax.set_ylabel("mean bounce height h̄ (mm)")
        ax.legend(loc="upper left", fontsize=10)
        ax.annotate(f"slope {D['slope_kh']:.4f} vs k_h {K_H_BASE:.4f}\n({D['kh_dev']:+.2%})",
                    xy=(0.97, 0.12), xycoords="axes fraction", ha="right", fontsize=10.5,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=3))
        FK.assertions(fig, _rows(AS, [
            ("AS-3", "slope = k_h (<5%)", f"{D['slope_kh']:.5f} ({D['kh_dev']:+.2%})"),
            ("AS-4", "h̄ = theory (<5%)", f"{D['hb_dev']:+.2%}"),
        ]))
    cap = (f"弹高数据坍缩：h̄ vs (Aω)² 过原点直线，斜率 {D['slope_kh']:.4f} vs 零参预言 "
           f"k_h=(1+e)/[4g(1-e)]={K_H_BASE:.4f}（偏 {D['kh_dev']:+.2%}）。随机相位能量平衡的零自由参数验证。")
    return dict(assertion_ids=["AS-3", "AS-4"], verdict=_verdict(AS, ["AS-3", "AS-4"]), caption=cap)


# ═══════════════════════════════════════════════════════════ F-4 bifurcation
def f4(AS, D):
    w, e = OMEGA1, E_REST
    gammas = np.geomspace(2.0, 3000, 60)
    with FK.Figure("F-4", STAMP, OUT_FIG, figsize=(9.6, 5.8),
                   title="Bounce-height 'bifurcation': locked→spread as Γ grows") as (fig, ax):
        for gam in gammas:
            A = gam * G / w**2
            hs = M.poincare_heights(A, w, e, n=400, burn=200) / (A * w) ** 2 * G  # 归一化 h̄g/(Aω)²
            ax.plot([gam] * len(hs), hs, ".", ms=1.4, color=FK.SLOTS[0]["color"], alpha=0.25)
        ax.axvline(math.pi, color=FK.SLOTS[3]["color"], ls="--", lw=1.4)
        ax.annotate("Γ≈π: map⟷random-phase boundary\n(low-Γ chaos is nm-invisible)",
                    xy=(math.pi, ax.get_ylim()[1] * 0.8), xytext=(8, 0),
                    textcoords="offset points", fontsize=10, color=FK.SLOTS[3]["color"])
        ax.set_xscale("log")
        ax.set_xlabel("Γ = Aω²/g")
        ax.set_ylabel("normalized bounce height  h·g/(Aω)²")
        FK.assertions(fig, _rows(AS, [
            ("AS-5", "high-Γ spread (random phase)", f"CV={D['cv']:.2f}"),
            ("AS-7", "regime boundary Γ~π", f"Γ_op={D['gamma_base']:.0f}"),
        ]))
    cap = (f"弹高（归一化）随 Γ 的分岔状分布。低 Γ（≲π）确定性映射区（周期倍化/混沌，但此时弹高 nm 不可见）；"
           f"高 Γ（>>π）弥散为随机相位统计带。边界在 Γ~π=f/f_bounce~1。工作点 Γ={D['gamma_base']:.0f} 深在随机相位区。")
    return dict(assertion_ids=["AS-5", "AS-7"], verdict=_verdict(AS, ["AS-5", "AS-7"]), caption=cap)


# ═══════════════════════════════════════════════════════════ F-5 e-family (divergence)
def f5(AS, D):
    with FK.Figure("F-5", STAMP, OUT_FIG, figsize=(9.0, 5.6),
                   title="Restitution dependence: h̄ ∝ (1+e)/(1−e)") as (fig, ax):
        es, hb, ht = D["e_es"], D["e_hb"] * 1e3, D["e_theory"] * 1e3
        ee = np.linspace(0.35, 0.85, 100)
        FK.plot_reference(ax, ee, (1 + ee) / (1 - ee) * (A0 * OMEGA1) ** 2 / (4 * G) * 1e3,
                          "theory (1+e)/(1−e)·(Aω)²/4g")
        FK.plot_model(ax, es, hb, 0, "sim h̄")
        ax.set_xlabel("restitution e")
        ax.set_ylabel("mean bounce height h̄ (mm)")
        ax.legend(loc="upper left", fontsize=10)
        FK.assertions(fig, _rows(AS, [
            ("AS-9", "slope constant across sweep (<10%)", f"var {D['A4_slope_var']:.2%}"),
            ("AS-4", "h̄ = theory", f"{D['hb_dev']:+.2%}"),
        ]))
    cap = (f"弹高对恢复系数 e 的依赖，实测与 (1+e)/(1−e)·(Aω)²/4g 吻合；e→1 发散（无耗散无稳态）。"
           f"斜率在扫描范围内恒定（变化 {D['A4_slope_var']:.1%}<10% ⟹ A-4 常数 e 成立）。")
    return dict(assertion_ids=["AS-9", "AS-4"], verdict=_verdict(AS, ["AS-9", "AS-4"]), caption=cap)


# ═══════════════════════════════════════════════════════════ F-6 Lyapunov
def f6(AS, D):
    w, e = OMEGA1, E_REST
    gammas = np.geomspace(5, 3000, 24)
    lams = [M.lyapunov(gam * G / w**2, w, e, n=3000, burn=400) for gam in gammas]
    with FK.Figure("F-6", STAMP, OUT_FIG, figsize=(9.0, 5.6),
                   title="Lyapunov exponent: chaos (λ>0) vs integrable Gate-0 (λ<0)") as (fig, ax):
        FK.plot_model(ax, gammas, lams, 0, "λ_max (per collision), chaotic map")
        ax.axhline(0, color=FK.GRID, lw=1)
        ax.axhline(D["lyap_integrable"], color=FK.SLOTS[3]["color"], ls="--", lw=1.4)
        ax.annotate(f"Gate-0: integrable limit (fixed phase) λ = ln e = {D['lyap_integrable']:.2f} < 0\n"
                    f"⟹ positive λ is real chaos, not float noise",
                    xy=(0.03, 0.06), xycoords="axes fraction", fontsize=10,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=3))
        ax.set_xscale("log")
        ax.set_xlabel("Γ = Aω²/g")
        ax.set_ylabel("max Lyapunov exponent λ (per collision)")
        ax.legend(loc="upper right", fontsize=10)
        FK.assertions(fig, _rows(AS, [
            ("AS-6", "λ_chaos>0 & λ_integrable<0", f"λ_c={D['lyap_chaos']:+.2f}, λ_i={D['lyap_integrable']:+.3f}"),
        ]))
    cap = (f"弹跳映射的最大 Lyapunov 指数（每次碰撞）在整个随机相位区 λ>0（混沌）。"
           f"★ Gate-0 对拍：可积极限（固定相位）λ=ln e={D['lyap_integrable']:.2f}<0（收缩）——"
           f"证明正 λ 是真混沌不是浮点噪声。")
    return dict(assertion_ids=["AS-6"], verdict=_verdict(AS, ["AS-6"]), caption=cap)


# ═══════════════════════════════════════════════════════════ V-1 intermediate qty
def v1(AS, D):
    fs, Af = D["res_fs"] / 1e3, D["res_A"]
    with FK.Figure("V-1", STAMP, OUT_FIG, figsize=(9.0, 5.6),
                   title="V-1 · intermediate quantity: tip amplitude A(f), measured independently") as (fig, ax):
        FK.plot_model(ax, fs, Af / Af.max(), 0, "A(f) — laser vibrometer (independent of bounce)")
        ax.axvline(F1 / 1e3, color=FK.INK, ls="-", lw=1.2)
        ax.set_xlabel("drive frequency f (kHz)")
        ax.set_ylabel("tip amplitude A/A_max")
        ax.legend(loc="upper right", fontsize=10)
        ax.annotate("measure A(f) directly (interferometer),\n"
                    "NOT back-inferred from bounce height\n"
                    "(that would mask two cancelling errors)",
                    xy=(0.03, 0.45), xycoords="axes fraction", fontsize=9.5,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=3))
        FK.assertions(fig, _rows(AS, [
            ("AS-10", "A(f) peak = f_1 (<5%)", f"{D['res_peak']/1e3:.2f} kHz ({D['V1_peak_dev']:+.2%})"),
        ]))
    cap = (f"V-1 中间量：棒尖振幅 A(f) 峰在 f₁={F1/1e3:.2f} kHz，独立于弹跳链条（激光测振/干涉直接测），"
           f"不由弹高反推 —— 反推会掩盖两个互相抵消的错误。这是『验中间量』而非『拿末态反证模型』。")
    return dict(assertion_ids=["AS-10"], verdict=_verdict(AS, ["AS-10"]), caption=cap)


def make_all(AS, D) -> dict:
    out = {}
    for fid, fn in (("F-1", f1), ("F-2", f2), ("F-3", f3), ("F-4", f4),
                    ("F-5", f5), ("F-6", f6), ("V-1", v1)):
        meta = fn(AS, D)
        meta["path"] = f"02-sim/figures/{fid}.png"
        meta["path_svg"] = f"02-sim/figures/{fid}.svg"
        meta["simulation_stamped"] = True
        out[fid] = meta
    return out


if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    import acceptance as ACC
    AS, D = ACC.run()
    make_all(AS, D)
    print("figures written")
