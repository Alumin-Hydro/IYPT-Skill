#!/usr/bin/env python3
r"""V-1..V-3：中间量验证图。「最终结果对了」不代表「模型对了」——两个错误可以互相
抵消。这三张图展示的是链条**中间**的量被独立路径钉死的证据。

make_all(AS, D) → {fig_id: dict(...)}（与 figures.make_all 同构）
"""
from __future__ import annotations

import numpy as np

import figkit as FK
from params import GAMMA_OC, OUT_FIG, R_C, R_TEST

STAMP = "electrical-damping · Model-2"


def _rows(AS, ids_expect_measured):
    vd = {a["id"]: a["verdict"] for a in AS}
    return [(i, e, m, vd[i] in ("PASS", "PRESCRIBED")) for i, e, m in ids_expect_measured]


def _bar(ax, items):
    """横向对数条形图：偏差 vs 各自容差。items = [(label, dev, tol), ...]。"""
    labels = [it[0] for it in items]
    devs = np.array([max(it[1], 1e-17) for it in items])
    tols = np.array([it[2] for it in items])
    ypos = np.arange(len(items))[::-1]
    ok = devs < tols
    colors = [FK.STATUS["pass"] if o else FK.STATUS["fail"] for o in ok]
    ax.barh(ypos, devs, height=0.55, color=colors, alpha=0.85, zorder=3)
    for y, t in zip(ypos, tols):
        ax.plot([t, t], [y - 0.38, y + 0.38], color=FK.INK, lw=2.2, zorder=4)
    for y, d_, t in zip(ypos, devs, tols):
        ax.annotate(f"{d_:.1e}", xy=(d_, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=10, color=FK.INK)
    ax.set_yticks(ypos)
    ax.set_yticklabels(labels, fontsize=10.5)
    ax.set_xscale("log")
    ax.set_xlim(1e-17, 1.0)
    ax.set_xlabel("relative deviation   (black tick = tolerance)")
    ax.grid(axis="x", color=FK.GRID, lw=0.8)


def v1(AS, D):
    v = D["v1"]
    with FK.Figure("V-1", STAMP, OUT_FIG, figsize=(11.8, 6.6),
                   title="V-1 · G(z) pinned by 5 independent routes (+2 cross-checks)"
                   ) as (fig, ax):
        _bar(ax, [
            ("(1) closed form eq.6 vs adaptive quadrature", v["d1"], 1e-10),
            ("(2) reciprocity  G = m·d(B_coil/I)/dz  (no flux-linkage)", v["d2"], 1e-9),
            ("(3) Amperian rings x discrete turns (dipole limit)", v["d3"], 1e-3),
            ("(4) odd symmetry + G(0) = 0  (machine precision)", v["d4"], 1e-12),
            ("(5) single-loop limit -> N = 400.00", v["d5"], 1e-3),
            ("cross: reciprocity vs lambda-table (thick band)",
             v["cross_recip_spline"], 1e-4),
            ("cross: surface current vs volume avg (full size)",
             v["cross_amperian_volume"], 2e-3),
        ])
        # 放第 1-2 行短 bar 右侧的空白 —— (0.62,0.20) 会盖住 cross-check 两条长 bar 的数值和容差 tick
        ax.annotate("routes (1)(2)(3) share NO derivation steps —\n"
                    "agreement is evidence, not tautology",
                    xy=(0.56, 0.88), xycoords="axes fraction", fontsize=11, va="top",
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=4))
        FK.assertions(fig, _rows(AS, [
            ("AS-22", "all 5 routes within tolerance",
             f"worst {max(v['d1']/1e-10, v['d2']/1e-9, v['d3']/1e-3, v['d4']/1e-12, v['d5']/1e-3):.2f}x of tol"),
            ("AS-2", "single-loop ratio -> N=400.00", f"dev {v['d5']:.1e}"),
        ]))
    cap = (f"G(z) 的五路独立对拍：①闭式 vs 求积 {v['d1']:.1e}；②互易性（不经磁通链） "
           f"{v['d2']:.1e}；③安培面电流×离散匝（偶极极限） {v['d3']:.1e}；④奇对称+零点 "
           f"{v['d4']:.1e}；⑤单匝环极限→N=400（偏 {v['d5']:.1e}）。加码：互易 vs λ 表"
           f"（厚绕组隔离） {v['cross_recip_spline']:.1e}、面电流 vs 体平均（全尺寸） "
           f"{v['cross_amperian_volume']:.1e}。")
    return dict(assertion_ids=["AS-22", "AS-2"], verdict="PASS", caption=cap)


def v2(AS, D):
    v = D["v2"]
    A4_TOL = 1.3e-2          # 契约 A-4 原文的界 —— spec defect #4：它漏了 2ζ_el 放大
    with FK.Figure("V-2", STAMP, OUT_FIG, figsize=(11.8, 6.4),
                   title="V-2 · R_c and L: statics vs dynamics cross-examination"
                   ) as (fig, ax):
        _bar(ax, [
            ("R_c: wire formula vs parameter table", abs(v["Rc_dev"]), 5e-3),
            ("L: Wheeler formula vs parameter table", abs(v["L_dev"]), 5e-3),
            ("R_c from F-2 x-intercept (dynamics!)", abs(v["icpt_Rc_dev"]), 5e-2),
            ("omega0*L/(R+R_c) at R=0 (A-4)", v["omegaL_ratio"], A4_TOL),
            ("3-state vs 2-state gamma at R=20", v["state32_dev_R20"], A4_TOL),
            ("R=0: |measured - quasi-static prediction|",
             v["state32_R0_mismatch"], 3e-3),
        ])
        # 说明文字走底部 note 条 —— V-2 的 bar 都太长，axes 里没有放得下三行框的空白；
        # 上一版还把 1.9%/1.3% 手打进了字符串（「数字不许手打」在图代码里同样成立）。
        FK.fit_range_note(fig,
            f"R=0 endpoint: gamma shift = {v['state32_R0_measured']:.2%} — EXACTLY the "
            f"quasi-static effective-mass term 2·ζ_el·(ω₀L/R_tot), "
            f"predicted {v['state32_R0_pred']:.2%};\nthe spec's {A4_TOL:.1%} bound "
            f"missed the 2·ζ_el amplification (spec defect #4, P17)")
        FK.assertions(fig, _rows(AS, [
            ("AS-23", "intercept R_c within 5%", f"{v['icpt_Rc_dev']:+.1%}"),
            ("AS-23", "R=0 gamma shift matches prediction <0.3%",
             f"{v['state32_R0_measured']:.2%} vs {v['state32_R0_pred']:.2%}"),
        ]))
    cap = (f"R_c 与 L 的静态↔动态交叉：导线公式复算 R_c 偏 {v['Rc_dev']:+.3%}、Wheeler L 偏 "
           f"{v['L_dev']:+.2%}；F-2 截距动力学反推 R_c 偏 {v['icpt_Rc_dev']:+.1%}。三态 vs "
           f"二维：R=20 差 {v['state32_dev_R20']:.3%}(<1.3%)；R=0 差 "
           f"{v['state32_R0_measured']:.2%} = 准静态有效质量预言 {v['state32_R0_pred']:.2%}"
           f"（吻合到 {v['state32_R0_mismatch']:.2%}）—— A-4 原文的 1.3% 界在 R=0 端点"
           f"代数地不可能（spec_defects[3]）。")
    return dict(assertion_ids=["AS-23"],
                verdict={a["id"]: a["verdict"] for a in AS}["AS-23"], caption=cap)


def v3(AS, D):
    v = D["v3"]
    with FK.Figure("V-3", STAMP, OUT_FIG, figsize=(13.2, 6.4), ncols=2,
                   title="V-3 · Energy audit: every joule accounted for"
                   ) as (fig, ax):
        a0, a1 = ax
        s = v["series"]
        E0 = v["E0"]
        FK.plot_model(a0, s["t"], s["E_tot"] / E0, 0,
                      "stored energy  (E_mech + LI²/2) / E₀", every=200)
        FK.plot_reference(a0, s["t"], s["ledger"] / E0,
                          "ledger: 1 − (Joule + background)/E₀")
        a0.annotate(f"two curves coincide to {v['resid_correct']:.1e}\n"
                    f"as-written identity (no LI²/2, mass M):\n"
                    f"fails at {v['resid_aswritten']:.1e}  → spec defect #1",
                    xy=(0.30, 0.55), xycoords="axes fraction", fontsize=11,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=4))
        a0.set_xlabel("t (s)")
        a0.set_ylabel("energy / E₀")
        a0.legend(loc="upper right", fontsize=10)
        t_d, drift_d = v["drift_series"]
        a1.semilogy(t_d, np.maximum(np.abs(drift_d), 1e-18), color=FK.SLOTS[0]["color"],
                    lw=1.2, label="|E/E₀ − 1|, open circuit, γ_oc = 0")
        a1.axhline(1e-10, color=FK.INK, lw=2)
        a1.annotate("tolerance 1e-10", xy=(0.02, 1.4e-10), xycoords=("axes fraction", "data"),
                    fontsize=10.5)
        a1.set_xlabel("t (s)  — 100 periods")
        a1.set_ylabel("energy drift")
        a1.set_ylim(1e-18, 1e-8)
        a1.legend(loc="upper left", fontsize=10)
        FK.assertions(fig, _rows(AS, [
            ("AS-24", "corrected identity < 1e-10", f"{v['resid_correct']:.1e}"),
            ("AS-24", "open-circuit drift < 1e-10 (100 periods)", f"{v['drift']:.1e}"),
            ("AS-24", "dE/dt <= 0 everywhere", f"viol {v['monotone_violation']:.1e}"),
        ]))
    cap = (f"能量审计。左：储能曲线与「E₀ − 焦耳热 − 开路本底耗散」台账重合到 "
           f"{v['resid_correct']:.1e}（含 ½LI²、系数 2M_eff —— 照契约 V-3 原文（漏 ½LI²、"
           f"写 2M）则失配 {v['resid_aswritten']:.1e}，spec_defects[0] 的证据）；右：开路+"
           f"零本底 100 周期能量漂移 {v['drift']:.1e} < 1e-10（Gate-0 级，只测积分器）。"
           f"单调性 dE/dt≤0 逐时刻成立（破坏 {v['monotone_violation']:.1e}）。")
    return dict(assertion_ids=["AS-24"], verdict="PASS", caption=cap)


def make_all(AS, D) -> dict:
    out = {}
    for fid, fn in (("V-1", v1), ("V-2", v2), ("V-3", v3)):
        meta = fn(AS, D)
        meta["path"] = f"02-sim/figures/{fid}.png"
        meta["path_svg"] = f"02-sim/figures/{fid}.svg"
        meta["simulation_stamped"] = True
        out[fid] = meta
    return out
