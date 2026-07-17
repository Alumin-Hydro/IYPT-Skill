#!/usr/bin/env python3
r"""F-1..F-6：契约 figures[] 的六张图。全部经 figkit 出（SIMULATION 戳强制、
断言结果画在轴外条带、图上文字一律英文 —— figkit 的 CJK 拦截器会把中文炸成异常）。

make_all(AS, D) → {fig_id: dict(path, path_svg, assertion_ids, verdict, caption)}
caption 里的每一个数字都从 D 取值格式化 —— 不许手打。
"""
from __future__ import annotations

import numpy as np

import figkit as FK
import model2 as M2
from params import (A0_BASE, GAMMA_OC, GAMMA_OC2, OUT_FIG, R_C, R_TEST)

STAMP = "electrical-damping · Model-2"


def _as_rows(AS, ids_expect_measured):
    """把 (AS-id, english_expect, english_measured) 翻成 figkit 断言行。"""
    vd = {a["id"]: a["verdict"] for a in AS}
    return [(i, e, m, vd[i] in ("PASS", "PRESCRIBED")) for i, e, m in ids_expect_measured]


def _verdict(AS, ids):
    order = {"PASS": 0, "PRESCRIBED": 1, "FAIL-MODEL": 2, "FAIL-CODE": 3}
    vd = {a["id"]: a["verdict"] for a in AS}
    return max((vd[i] for i in ids), key=lambda v: order[v])


# ══════════════════════════════════════════════════════════════════ F-1
def f1(AS, D):
    with FK.Figure("F-1", STAMP, OUT_FIG, figsize=(13.2, 6.6), ncols=2,
                   title="Transduction G(z) and the zero-damping center") as (fig, ax):
        a0, a1 = ax
        zg = D["f1_zg"] * 1e3
        # legend 标签内换行 —— 单行版框宽 ~40 mm，lower left 的右缘会伸到 z≈+14，
        # 半透明白底把整个负峰「洗白」（r1 设计审查抓到的；单行时右缘必然越过 z=0）
        FK.plot_reference(a0, zg, D["f1_G0"], "Model-0: point dipole\n+ thin coil (eq. 6)")
        FK.plot_model(a0, zg, D["f1_G2"], 0,
                      "Model-2: finite magnet\n+ thick winding (eq. 27)", every=20)
        a0.axhline(0, color=FK.GRID, lw=1)
        a0.plot([0], [0], "o", color=FK.INK, ms=7, zorder=5)
        # 居中层（y 从 0.40 向下）：与贴顶的 z_pk 标注（y≥0.65）相隔 Δy≈0.25；
        # 正 z 侧 G 全为负，右上整片无数据
        a0.annotate("G(0) = 0 exact\n(coil symmetry)", xy=(0, 0), xytext=(0.8, 0.40),
                    textcoords="data", fontsize=11, ha="left", va="top",
                    arrowprops=dict(arrowstyle="->", color=FK.INK_SOFT))
        zpk = D["zpk2"] * 1e3
        a0.axvline(zpk, color=FK.INK_MUTED, ls=":", lw=1.2)
        # ★ 两个双行标注**上下分层**（200 DPI 下每块横占 ~13 z单位，一行带放不下两块）：
        # z_pk 贴顶（y≈0.80），G(0) 居中（y≈0.40）—— x 即便重叠，Δy≈0.3 也不相碰。
        # z_pk 首行缩短到 z=7.5 起能放进右边界内。
        a0.annotate(f"z_pk = {zpk:.2f} mm\n≈ l_c/2 (not a/2)",
                    xy=(7.5, float(D['f1_G2'].max()) * 0.98), fontsize=11,
                    ha="left", va="top", color=FK.INK_SOFT)
        a0.set_xlabel("z (mm)")
        a0.set_ylabel("G = dλ/dz (Wb/m)")
        a0.legend(loc="lower left", fontsize=10.5)

        z0s = D["f1_z0s"] * 1e3
        FK.plot_model(a1, z0s, D["f1_gams"], 0, "Γ from Bernoulli fit (ODE, A₀=1 mm)")
        zf = np.linspace(z0s.min(), z0s.max(), 200)
        c, b, a_ = np.polyfit(z0s / 1e3, D["f1_gams"], 2)
        FK.plot_reference(a1, zf, c * (zf / 1e3) ** 2 + b * (zf / 1e3) + a_,
                          "parabola fit  Γ = γ_oc + c₂·(z₀−z_off)²")
        # 不用 FK.hline：它把带白底的直标钉在右端 (0.985, y)，bbox 会洗掉右臂
        # z₀≈0.6–1.0 的一小段曲线（r1 设计审查）。左端 |z₀|>1 处线上方全空。
        a1.axhline(GAMMA_OC, color=FK.INK_MUTED, ls="--", lw=1.4, zorder=1)
        a1.annotate(f"open-circuit γ_oc = {GAMMA_OC}", xy=(-4.35, GAMMA_OC),
                    ha="left", va="bottom", fontsize=11, color=FK.INK_MUTED)
        a1.annotate(f"vertex = {D['f1_vertex']:.4f} 1/s "
                    f"({D['f1_vertex']/GAMMA_OC-1:+.1%} vs γ_oc)\n"
                    f"curvature = {D['f1_curv_mm']:.4f} 1/(s·mm²) "
                    f"({D['f1_curv_mm']/D['c2_2']-1:+.1%} vs c₂ pred)\n"
                    f"z_off = {D['f1_zoff']*1e3:+.3f} mm (self-measured)",
                    xy=(0.03, 0.97), xycoords="axes fraction", va="top", fontsize=11,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=4))
        a1.set_xlabel("z₀ (mm)")
        a1.set_ylabel("Γ (1/s)")
        # 抛物线两臂之间的空腔（lower left 会压谷底数据 + 挡 γ_oc 直标；
        # loc="center" 擦右臂 (3,0.36)、(0.46,0.66) 擦左臂 —— 框宽 ~4.6 数据单位，
        # 放两臂正中 x_c≈0.18：y∈[0.40,0.47] 处臂距 ±3.2，两侧各留 ~0.9 余量）
        a1.legend(loc="center", bbox_to_anchor=(0.52, 0.66), fontsize=10.5)

        FK.fit_range_note(fig, f"parabola fitted on |z₀| ≤ 4 mm (G nonlinearity < 1% "
                               f"there — interval set by physics, not by hand); "
                               f"Γ(z₀) sampled at R = {R_TEST:g} Ω")
        FK.assertions(fig, _as_rows(AS, [
            ("AS-12", "|G(0)|/Gmax < 1e-12", f"{D['sym_zero']:.1e}"),
            ("AS-12", "odd symmetry < 1e-12", f"{D['sym_odd']:.1e}"),
            ("AS-19", "|Gmax dev| < 15% (A-1)", f"{D['a1_dev_gmax']:+.1%}"),
            ("AS-25", "c2(M2) vs c2(M0) >= 2% apart", f"{D['c2_2']/D['c2_0']-1:+.1%}"),
        ]))
    cap = (f"换能系数 G(z)（左）与 Γ(z₀) 抛物线（右）。G(0)={D['sym_zero']:.1e}·|G|max"
           f"（机器精度零点），z_pk={D['zpk2']*1e3:.2f}mm≈ℓ_c/2；顶点 "
           f"{D['f1_vertex']:.4f}=γ_oc({D['f1_vertex']/GAMMA_OC-1:+.1%})，曲率 "
           f"{D['f1_curv_mm']:.4f} 1/(s·mm²) vs 零参预言 c₂={D['c2_2']:.4f}"
           f"（{D['f1_curv_mm']/D['c2_2']-1:+.1%}）。Model-2 比 Model-0 的 |G|max 低 "
           f"{-D['a1_dev_gmax']:.1%}（A-1 的量度）。")
    return dict(assertion_ids=["AS-12", "AS-19", "AS-25"],
                verdict=_verdict(AS, ["AS-12", "AS-19", "AS-25"]), caption=cap)


# ══════════════════════════════════════════════════════════════════ F-2
def f2(AS, D):
    with FK.Figure("F-2", STAMP, OUT_FIG, figsize=(8.4, 6.8),
                   title="Zero-parameter line: 1/(γ−γ_oc) vs R  (eq. 16)") as (fig, ax):
        Rs, y = D["f2_Rs"], D["f2_y"]
        s, ic = D["f2_slope"], D["f2_icpt"]
        xx = np.linspace(-R_C * 1.35, Rs.max() * 1.04, 200)
        FK.plot_reference(ax, xx, s * xx + ic, "weighted LSQ line")
        FK.plot_model(ax, Rs, y, 0, "Model-2 ODE (γ from first-period decay, A₀=1 mm)")
        xint = -D["f2_Rc_backout"]
        ax.plot([xint], [0], "X", color=FK.SLOTS[3]["color"], ms=11, zorder=6)
        ax.annotate(f"x-intercept → −R_c = {xint:.2f} Ω\n(parameter table: −{R_C:.2f} Ω, "
                    f"dev {D['f2_Rc_dev']:+.1%})", xy=(xint, 0), xytext=(0.05, 0.62),
                    textcoords="axes fraction", fontsize=11.5,
                    arrowprops=dict(arrowstyle="->", color=FK.INK_SOFT))
        from field import G0
        g6 = abs(float(G0(D["zpk0"])))
        ax.annotate(f"slope → G(z_pk) = {D['f2_G_backout']:.4f} Wb/m\n"
                    f"eq.(6) gives {g6:.4f}"
                    f"  (dev {D['f2_G_dev']:+.1%}, A-1 eats ~4%)",
                    xy=(0.40, 0.16), xycoords="axes fraction", fontsize=11.5,
                    bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=4))
        ax.axhline(0, color=FK.GRID, lw=1)
        ax.axvline(0, color=FK.GRID, lw=1)
        ax.set_xlabel("external resistance R (Ω)")
        ax.set_ylabel("1/(γ − γ_oc)  (s)")
        ax.legend(loc="upper left", fontsize=10.5)
        FK.fit_range_note(fig, "fit weighted by 1/y (relative residuals) — unweighted "
                               "LSQ lets the R=200 Ω tail own the intercept")
        FK.assertions(fig, _as_rows(AS, [
            ("AS-13", "linearity R² > 0.999", f"{D['f2_R2']:.6f}"),
            ("AS-13", "slope→G vs eq.(6) < 10%", f"{D['f2_G_dev']:+.1%}"),
            ("AS-13", "x-intercept = −R_c < 5%", f"{D['f2_Rc_dev']:+.1%}"),
        ]))
    cap = (f"1/(γ−γ_oc) 对 R 严格线性（R²={D['f2_R2']:.6f}）。斜率反推 "
           f"G={D['f2_G_backout']:.4f} Wb/m（vs (6) 偏 {D['f2_G_dev']:+.1%}，其中 A-1 "
           f"贡献约 −4%）；x 截距反推 R_c={D['f2_Rc_backout']:.3f}Ω"
           f"（vs 参数表偏 {D['f2_Rc_dev']:+.1%}）—— 「从振子怎么衰减反推出线圈直流电阻」。")
    return dict(assertion_ids=["AS-13"], verdict=_verdict(AS, ["AS-13"]), caption=cap)


# ══════════════════════════════════════════════════════════════════ F-3
def f3(AS, D):
    with FK.Figure("F-3", STAMP, OUT_FIG, figsize=(13.6, 11.0), nrows=2, ncols=2,
                   title="Mode of decay at the center: power law, not exponential"
                   ) as (fig, ax):
        (a, b), (c, d) = ax
        # (a) P3a：Q vs A₀²
        A2 = (D["f3_A0s"] * 1e3) ** 2
        xx = np.linspace(0, A2.max() * 1.06, 100)
        FK.plot_reference(a, xx, D["f3_pred_slope"] * xx * 1e-6,
                          "zero-parameter: slope = c₂(R=0)/(4γ_oc)")
        FK.plot_model(a, A2, D["f3_Qs"], 0, "Bernoulli-fit Q (ODE, centered, R=0)")
        a.axhline(0, color=FK.STATUS["fail"], lw=2.2, ls=(0, (5, 3)))
        a.annotate("constant damping ⇒ Q ≡ 0 (flat on axis)", xy=(0.35, 0.065),
                   xycoords="axes fraction", color=FK.STATUS["fail"], fontsize=11.5)
        a.annotate(f"slope dev {D['f3_slope_dev']:+.1%}, intercept "
                   f"{D['f3_icpt']:+.2f}", xy=(0.05, 0.86), xycoords="axes fraction",
                   fontsize=11.5)
        a.set_xlabel("A₀² (mm²)")
        a.set_ylabel("Q")
        a.legend(loc="upper left", fontsize=10)
        # (b) P3b：Γ vs A₀
        A0mm = D["f3_A0s"] * 1e3
        FK.plot_model(b, A0mm, D["f3_gams"], 0, "long-time Γ (Bernoulli fit)")
        b.axhspan(GAMMA_OC * 0.9, GAMMA_OC * 1.1, color=FK.GRID, alpha=0.6)
        # 直标不许骑在结论线上 —— FK.hline 的白底 bbox 正好盖掉 A₀=5、8 两个
        # 数据点的上半（这条线「四点全压线」就是 AS-15 的全部证据；r1 设计审查）
        b.axhline(GAMMA_OC, color=FK.INK_MUTED, ls="--", lw=1.4, zorder=1)
        b.annotate(f"γ_oc = {GAMMA_OC} (open circuit!)  ±10%", xy=(5.0, 0.050),
                   ha="center", va="bottom", fontsize=11, color=FK.INK_MUTED)
        b.set_ylim(0, GAMMA_OC * 1.9)
        b.annotate("shorted magnet decays — long-time rate returns to the\n"
                   "OPEN-circuit value: dynamical signature of b(0) = 0",
                   xy=(0.04, 0.05), xycoords="axes fraction", fontsize=11)
        b.set_xlabel("A₀ (mm)")
        b.set_ylabel("Γ (1/s)")
        b.legend(loc="upper right", fontsize=10)
        # (c) 双对数包络 + 窗口 + S-8′
        tp, Ap = D["f3_envs"][-1]                        # A₀ = 8 mm
        m = tp > 0
        FK.plot_model(c, tp[m], Ap[m] * 1e3, 0, "S-2 envelope (A₀=8 mm, ODE peaks)",
                      every=2)
        beta8 = D["s8_beta_sc"]
        tt = np.geomspace(tp[m][0], 30, 200)
        FK.plot_model(c, tt, M2.envelope_23(tt, 8e-3, beta8, GAMMA_OC2) * 1e3, 1,
                      "S-8′ (Ø0.20 mm wire), eq. 23", every=1000)
        tg = np.geomspace(0.3, 6, 50)
        FK.plot_reference(c, tg, 8.0 * (tg / tg[0]) ** -0.5 * 0.36, "slope −1/2 guide")
        c.axhspan(D["A_c2"] * 1e3, D["A_lin"] * 1e3, color="#e6f4e6", alpha=0.75,
                  zorder=0)
        # 判定符号必须由数据长出来 —— 上一版把 ✓ 硬编码在 f-string 里,
        # s8_window=0.993<1 照样打了 ✓(眼睛审出的语义错误,机械门全瞎)。
        def _wtag(w):
            return (f"{w:.3f} decades ≥ 1.000 ✓ acceptance-grade" if w >= 1.0
                    else f"{w:.3f} decades < 1.000 ⇒ display-only")
        both_sub1 = D["s2_window"] < 1.0 and D["s8_window"] < 1.0
        c.annotate(f"S-2 window [A_c, A_lin] = [{D['A_c2']*1e3:.2f}, "
                   f"{D['A_lin']*1e3:.2f}] mm\n= {_wtag(D['s2_window'])}\n"
                   f"S-8′ (Ø0.20): {_wtag(D['s8_window'])}"
                   + ("\n⇒ asymptotic −1/2 not acceptance-grade on EITHER rig"
                      if both_sub1 else ""),
                   xy=(0.03, 0.06), xycoords="axes fraction", fontsize=10.5,
                   bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=3))
        c.set_xscale("log")
        c.set_yscale("log")
        FK.log_ticks(c.yaxis, [0.3, 1, 3, 8])
        FK.log_ticks(c.xaxis, [0.3, 1, 3, 10, 30])
        c.set_xlabel("t (s)")
        c.set_ylabel("envelope A (mm)")
        c.legend(loc="upper right", fontsize=10)
        # (d) A-8：误差 ∝ ζ_eff²
        FK.plot_model(d, D["a8_zeffs"], D["a8_errs"], 0,
                      "max envelope error vs eq. 23")
        k8, r28 = FK.fit_slope(D["a8_zeffs"], D["a8_errs"], name="A-8")
        FK.annotate_slope(d, D["a8_zeffs"], D["a8_errs"], k8, r28, i=0,
                          fmt="slope = {k:.2f} (must be 2.0 ± 0.3)")
        zz = np.geomspace(D["a8_zeffs"][0], D["a8_zeffs"][-1], 50)
        FK.plot_reference(d, zz, D["a8_errs"][0] * (zz / D["a8_zeffs"][0]) ** 2,
                          "∝ ζ_eff² reference")
        d.axhspan(2e-3, 1e-2, color=FK.GRID, alpha=0.55, zorder=0)
        d.annotate("pre-registered band for A₀=8 mm:\n[0.2%, 1.0%] — truncation of "
                   "eq. 23,\nNOT a bug, must NOT be 'fixed'",
                   xy=(0.52, 0.14), xycoords="axes fraction", fontsize=10.5)
        d.set_xscale("log")
        d.set_yscale("log")
        FK.log_ticks(d.xaxis, [2e-3, 5e-3, 1e-2, 2e-2, 5e-2, 1e-1, 2e-1])
        d.set_xlabel("ζ_eff(A₀)")
        d.set_ylabel("max |A_num − A_23| / A_23")
        d.legend(loc="upper left", fontsize=10)

        FK.fit_range_note(fig, f"P3a from A₀ ∈ {{2,3,5,8}} mm, z₀=0, R=0; open dot "
                               f"A₀=0.5 mm < A_c shown for regime ④; Γ, Q from "
                               f"Bernoulli fit of eq. 23a")
        # 副点：A₀ < A_c 的展示点画在 (a)
        tp5, Ap5, G5, Q5 = D["f3_sub"]
        a.plot([(0.5) ** 2], [Q5], "o", mfc="white", mec=FK.SLOTS[0]["color"],
               mew=2, ms=9, zorder=6)
        # 一行短文案放主线左上的空腔（两行版无论怎么挪都被斜率 ~1.4/unit 的主线穿过）
        a.annotate("A₀ = 0.5 mm < A_c (regime ④)",
                   xy=((0.5) ** 2, Q5), xytext=(2, 72), textcoords="offset points",
                   fontsize=10, color=FK.INK_SOFT,
                   arrowprops=dict(arrowstyle="->", color=FK.INK_SOFT, shrinkB=6))
        FK.assertions(fig, _as_rows(AS, [
            ("AS-14", "P3a slope dev < 15%, |intercept| < 0.5",
             f"{D['f3_slope_dev']:+.1%}, {D['f3_icpt']:+.2f}"),
            ("AS-15", "P3b: all Γ = γ_oc within 10%",
             f"max dev {float(np.max(np.abs(D['f3_gams']/GAMMA_OC-1))):.2%}"),
            ("AS-20", "envelope vs eq.23a < 2%", f"{D['f3_dev23a']:.2%}"),
            ("AS-21", "A-8: e(8mm) in [0.2%,1%], slope 2±0.3",
             f"{D['a8_e8']:.2%}, {D['a8_slope']:.2f}"),
        ]))
    cap = (f"居中衰减的模式。(a) Q∝A₀²：斜率偏差 {D['f3_slope_dev']:+.1%}（零自由参数），"
           f"常数阻尼的 Q≡0 水平线画在同图 —— 零 vs 非零离散；(b) 四个 A₀ 的长时 Γ 全部回到"
           f"开路 γ_oc（最大偏 {float(np.max(np.abs(D['f3_gams']/GAMMA_OC-1))):.1%}）；"
           f"(c) 幂律窗口：S-2 {D['s2_window']:.3f}、S-8′ {D['s8_window']:.3f} 个十进位"
           + ("，都 <1 ⟹ 渐近 −1/2 指数在两套器材上都只是展示、不可验收 —— 比单器材版"
              "更强的结论（GL 修正压低 |G|max ⟹ A_lin 收窄，把 S-8′ 也挤出验收窗）"
              if D["s2_window"] < 1.0 and D["s8_window"] < 1.0
              else f"（S-8′ {'≥' if D['s8_window'] >= 1.0 else '<'}1 而 S-2 "
                   f"{'≥' if D['s2_window'] >= 1.0 else '<'}1）")
           + f"；(d) A-8 的包络误差 ∝ζ_eff²"
           f"（斜率 {D['a8_slope']:.2f}），A₀=8mm 时 {D['a8_e8']:.2%} 落在预注册带内。")
    return dict(assertion_ids=["AS-14", "AS-15", "AS-20", "AS-21"],
                verdict=_verdict(AS, ["AS-14", "AS-15", "AS-20", "AS-21"]), caption=cap)


# ══════════════════════════════════════════════════════════════════ F-4
def f4(AS, D):
    with FK.Figure("F-4", STAMP, OUT_FIG, figsize=(9.6, 7.4),
                   title="Regime map in the (z₀, A₀) plane — all boundaries analytic"
                   ) as (fig, ax):
        z0g, A0g, NU = D["f4_z0g"], D["f4_A0g"], D["f4_NU"]
        zpk = D["zpk0"]
        X, Y = z0g / zpk, A0g / zpk
        Ac, Alin = D["A_c2"], D["A_lin"]
        region = np.full(NU.shape, 2)                     # ② nonlinear
        region[NU < 0.1] = 1                              # ① linear
        ZZ, AA = np.meshgrid(z0g, A0g)
        region[(NU >= 0.1) & (AA > Ac) & (ZZ + AA < Alin)] = 3   # ③ power law
        region[AA < Ac] = 0                               # ④ background
        from matplotlib.colors import ListedColormap
        cmap = ListedColormap(["#eceae2", "#dbe9fb", "#fde4d8", "#e2f2e2"])
        ax.pcolormesh(X, Y, region, cmap=cmap, vmin=-0.5, vmax=3.5, shading="auto")
        cs = ax.contour(X, Y, NU, levels=[0.1], colors=[FK.INK], linewidths=2)
        ax.clabel(cs, fmt={0.1: "ν = 0.1"}, fontsize=11)
        ax.axhline(Ac / zpk, color=FK.INK_SOFT, ls="--", lw=1.6)
        ax.annotate(f"A_c = {Ac*1e3:.2f} mm (eq. 25)", xy=(1.28, Ac / zpk * 1.08),
                    fontsize=10.5, color=FK.INK_SOFT)
        zl = np.linspace(0, Alin, 50)
        ax.plot(zl / zpk, (Alin - zl) / zpk, color=FK.INK_SOFT, ls=":", lw=1.6)
        ax.annotate("z₀ + A₀ = A_lin", xy=(0.30, Alin / zpk * 0.72), fontsize=10.5,
                    color=FK.INK_SOFT, rotation=-38)
        for A, nu_v in ((3e-3, D["nu_3mm"]), (8e-3, D["nu_8mm"])):
            ax.plot([1.0], [A / zpk], "o", color=FK.INK, ms=8, zorder=6)
            ax.annotate(f"ν(z_pk, {A*1e3:.0f} mm) = {nu_v:.3f}",
                        xy=(1.0, A / zpk), xytext=(10, -4), textcoords="offset points",
                        fontsize=11, fontweight="bold")
        ax.plot([1.0], [0.8], "*", color=FK.SLOTS[3]["color"], ms=17, zorder=6)
        ax.annotate("F-5 large-A points live here\n→ must fall off y=x (they do)",
                    xy=(1.0, 0.8), xytext=(-165, -38), textcoords="offset points",
                    fontsize=10.5, color=FK.SLOTS[3]["color"],
                    arrowprops=dict(arrowstyle="->", color=FK.SLOTS[3]["color"],
                                    shrinkB=10))
        from matplotlib.patches import Patch
        # legend 放右下 ④ 灰区空白 —— upper right 会把红星和 ν(z_pk,8mm) 标注整个盖掉
        ax.legend(handles=[Patch(fc="#dbe9fb", label="① linear (ν<0.1): exponential"),
                           Patch(fc="#fde4d8", label="② nonlinear (ν>0.1)"),
                           Patch(fc="#e2f2e2", label="③ power law A∝t^{-1/2} (eq. 23)"),
                           Patch(fc="#eceae2", label="④ background-dominated (A<A_c)")],
                  loc="lower right", fontsize=9.5, framealpha=0.95)
        ax.set_yscale("log")
        FK.log_ticks(ax.yaxis, [0.05, 0.1, 0.2, 0.4, 0.8])
        ax.set_xlabel("z₀ / z_pk")
        ax.set_ylabel("A₀ / z_pk")
        FK.assertions(fig, _as_rows(AS, [
            ("AS-16", "nu(z_pk,3mm) ~ 0.133 (<10%)", f"{D['nu_3mm']:.4f}"),
            ("AS-16", "nu(z_pk,8mm) ~ 0.70 (<10%)", f"{D['nu_8mm']:.4f}"),
            ("AS-16", "F-4/F-5 agree at (z_pk, 0.8·z_pk)",
             f"nu={D['nu_at_f5']:.2f}>0.1 & F-5 deviates"),
        ]))
    cap = (f"(z₀, A₀) 参数空间相图，四区边界全解析（ν=0.1 等值线、A_c、z₀+A₀=A_lin），"
           f"零拟合。ν(z_pk,3mm)={D['nu_3mm']:.3f}、ν(z_pk,8mm)={D['nu_8mm']:.3f}"
           f"（契约预告 0.133/0.70）；r1 的一阶判据会把 z_pk 整条竖线误判成线性区 —— "
           f"ν 无关阶数，与 F-5 的坍缩失败在同一点上给出同向断言。")
    return dict(assertion_ids=["AS-16"], verdict=_verdict(AS, ["AS-16"]), caption=cap)


# ══════════════════════════════════════════════════════════════════ F-5
def f5(AS, D):
    f = D["f5"]
    with FK.Figure("F-5", STAMP, OUT_FIG, figsize=(8.6, 7.0),
                   title="Data collapse onto y = x — and its instructive failure"
                   ) as (fig, ax):
        lo = min(f["xs"].min(), f["by"].min()) * 0.7
        hi = max(f["xs"].max(), f["bx"].max()) * 1.4
        xx = np.geomspace(lo, hi, 50)
        FK.plot_reference(ax, xx, xx, "y = x (eq. 15 identity)")
        FK.plot_model(ax, f["xs"], f["ys"], 0,
                      "small A₀ = 0.8 mm (A₀/z_pk = 0.077), 7 configs", every=1)
        ax.plot(f["bx"], f["by"], marker="D", ls="None", ms=9,
                color=FK.SLOTS[3]["color"], label="large A₀ = 8 mm (A₀/z_pk = 0.77)",
                zorder=5)
        for x, y, dv in zip(f["bx"], f["by"], f["big_dev"]):
            # 最左的大 A 点（-19%）落在 z0=13mm 灰标签正下方 —— 红字挂到菱形正下远处
            dx, dy = (-12, -30) if x == min(f["bx"]) else (6, -14)
            ax.annotate(f"{dv:+.0%}", xy=(x, y), xytext=(dx, dy),
                        textcoords="offset points", fontsize=10.5,
                        color=FK.SLOTS[3]["color"], fontweight="bold")
        # ζ≈0.1 一带 M*1.4 / base / z0=13mm 三个点挤在一起 —— 统一 (5,5) 偏移会叠标
        offs = {"M*1.4": (-42, 2), "z0=13mm": (6, -14), "z0=7mm": (6, -14)}
        for x, y, lab in zip(f["xs"], f["ys"], f["labels"]):
            dx, dy = offs.get(lab, (5, 5))
            ax.annotate(lab, xy=(x, y), xytext=(dx, dy), textcoords="offset points",
                        fontsize=8.5, color=FK.INK_MUTED)
        ax.set_xscale("log")
        ax.set_yscale("log")
        FK.log_ticks(ax.xaxis, [0.02, 0.05, 0.1, 0.2, 0.4])
        FK.log_ticks(ax.yaxis, [0.02, 0.05, 0.1, 0.2, 0.4])
        ax.set_xlabel("ζ = G(z₀)² / [2·√(M_eff·k)·(R+R_c)]")
        ax.set_ylabel("(γ − γ_oc) / ω₀")
        ax.legend(loc="upper left", fontsize=10.5)
        ax.annotate("collapse failure at large A₀ IS the finding:\namplitude enters as "
                    "Π₄ = A₀/z_pk — a factor the\nproblem statement never names",
                    xy=(0.42, 0.08), xycoords="axes fraction", fontsize=11,
                    bbox=dict(fc="white", ec=FK.SLOTS[3]["color"], lw=1.2, pad=4))
        FK.fit_range_note(fig, "x uses M_eff (targets[ζ]); the spec's F-5 axis label "
                               "says sqrt(M k) — internal contradiction, recorded as "
                               "spec defect #2")
        FK.assertions(fig, _as_rows(AS, [
            ("AS-17", "small-A: slope 1.000±0.01", f"{f['slope']:.4f}"),
            ("AS-17", "small-A: |intercept| < 0.005", f"{f['icpt']:+.5f}"),
            ("AS-17", "small-A: scatter < 1%", f"{f['scatter']:.2%}"),
            ("AS-17", "large-A: must deviate > 5%",
             f"{min(f['big_dev']):+.0%}..{max(f['big_dev']):+.0%}"),
        ]))
    cap = (f"7 组 (M_eff,k,R,z₀) 的小振幅点坍缩到 y=x（斜率 {f['slope']:.4f}、截距 "
           f"{f['icpt']:+.4f}、散布 {f['scatter']:.2%}）；A₀=8mm 的三个点系统性偏离 "
           f"{min(f['big_dev']):+.0%}～{max(f['big_dev']):+.0%} —— 坍缩失败本身是结论"
           f"（Π₄=A₀/z_pk 是题面没点名的 factor），不许当 bug 修。y 轴 γ 取 A₀ 处的"
           f"初始衰减率（gamma_first —— 峰提取会先衰掉半个摆幅，对初始非线性失明）。")
    return dict(assertion_ids=["AS-17"], verdict=_verdict(AS, ["AS-17"]), caption=cap)


# ══════════════════════════════════════════════════════════════════ F-6
def f6(AS, D):
    fam = D["f6"]
    with FK.Figure("F-6", STAMP, OUT_FIG, figsize=(13.4, 6.9), ncols=2,
                   title="Phase portraits: state-dependent damping made visible"
                   ) as (fig, ax):
        for k, (tag, ttl, note) in enumerate((
                ("zpk", "z₀ = z_pk  (linear damping)",
                 f"log-spiral: successive-peak ratio constant\n(CV = {D['f6_cv_zpk']:.1%})"),
                ("center", "z₀ = 0  (b ∝ z²)",
                 f"spiral opens at small A: ratio "
                 f"{D['f6_r_center'][0]:.2f} → {D['f6_r_center'][-1]:.2f} → 1\n"
                 f"(damping switches itself off)"))):
            a = ax[k]
            for i, (A0, z, vn) in enumerate(fam[tag]["trajs"]):
                s = FK.slot(i)
                # alpha < 1：center 族小 A₀ 处圈叠圈（阻尼自关的证据本身），
                # 半透明让叠加密度可见 —— 实心色块只剩「有很多圈」一位信息
                a.plot(z, vn, lw=0.9, alpha=0.8, color=s["color"],
                       label=f"A₀ = {A0*1e3:g} mm")
            a.set_title(ttl, fontsize=13)
            a.annotate(note, xy=(0.03, 0.03), xycoords="axes fraction", fontsize=10.5,
                       bbox=dict(fc="white", ec=FK.INK_MUTED, lw=0.8, pad=3))
            a.set_xlabel("z − z₀ (mm)")
            a.set_ylabel("ż / ω₀ (mm)")
            a.legend(loc="upper right", fontsize=9)
            a.set_aspect("equal")
        FK.fit_range_note(fig, f"both families at R = {R_TEST:g} Ω; z₀=0 family drawn "
                               f"to {fam['center']['T_draw']:g} s (full "
                               f"{fam['center']['T_full']:g} s overplots into a solid "
                               f"ring) — ratio series uses the full run")
        FK.assertions(fig, _as_rows(AS, [
            ("AS-18", "z_pk family: ratio const (CV<2%)", f"{D['f6_cv_zpk']:.1%}"),
            ("AS-18", "center family: ratio rises to 1 (>0.05)",
             f"+{D['f6_rise_center']:.3f}"),
        ]))
    cap = (f"两族相图（各 5 条初条件）。z₀=z_pk：对数螺线，圈间距比恒定"
           f"（CV={D['f6_cv_zpk']:.1%}）；z₀=0：比值 {D['f6_r_center'][0]:.2f}→"
           f"{D['f6_r_center'][-1]:.2f}→1，小振幅处阻尼自己关掉 —— 「阻尼依赖于状态」的"
           f"直接可视化。两族若一样 = 代码用了常数阻尼（AS-18 的 must_not）。"
           f"z₀=0 族只画前 {fam['center']['T_draw']:g} s"
           f"（全程 {fam['center']['T_full']:g} s 会叠成实心环）；"
           f"圈间距比值序列用全程数据 —— 画图截断不碰断言。")
    return dict(assertion_ids=["AS-18"], verdict=_verdict(AS, ["AS-18"]), caption=cap)


def make_all(AS, D) -> dict:
    out = {}
    for fid, fn in (("F-1", f1), ("F-2", f2), ("F-3", f3), ("F-4", f4),
                    ("F-5", f5), ("F-6", f6)):
        meta = fn(AS, D)
        meta["path"] = f"02-sim/figures/{fid}.png"
        meta["path_svg"] = f"02-sim/figures/{fid}.svg"
        meta["simulation_stamped"] = True
        out[fid] = meta
    return out


if __name__ == "__main__":
    import acceptance as ACC
    AS, D = ACC.run()
    make_all(AS, D)
