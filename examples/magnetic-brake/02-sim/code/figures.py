#!/usr/bin/env python3
"""F-1 … F-4 静态图。F-5（动画）在 interactive.py。

**所有图经 figkit 出** —— 它无条件盖 SIMULATION 戳并同时存 PNG + SVG
（SVG 是纯文本，check_sim.py 在里面 grep 戳，伪造不了）。

**断言结果画在坐标轴外的底部条带里** —— 读者不该需要翻 results.json 才知道这张图
过没过，但也绝不能为此挡住数据。（实测教训：第一版把断言框浮在轴内，正好盖住了 F-4
里 Model-0 坍缩到水平线的那一堆点 —— 而"看见它们堆在一起"是这张图的全部意义。）

图上文字**一律英文**：IYPT 是英文赛事，图要直接进英文 PPT；而且 DejaVu Sans 没有中文
字形，中文会渲染成豆腐块。
"""
from __future__ import annotations

import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import matplotlib.pyplot as plt

from params import OUT_FIG
from model0 import PI1_THEORY
import figkit as fk

STAMP = "Model-0 vs Model-2 · spec r1"

#: 断言在**图上**的英文短标（展示用；权威版本在 acceptance.md / results.json）
EN = {
    "AS-2":  "Model-0 slope vs sigma  == -1.00",
    "AS-3":  "Model-2 slope vs sigma  == -1.00",
    "AS-4":  "Model-0 slope vs w      == -1.00",
    "AS-5":  "Model-2 bends up at large w",
    "AS-6":  "must_not: M2 slope(w) in -1.00+-0.05",
    "AS-7":  "Model-0 slope vs a      == +4.00",
    "AS-8":  "Model-2 |k - 4| > 0.3",
    "AS-9":  "must_not: k in 4.00 +- 0.10",
    "AS-10": "x at v/v_t = 0.99  == 0.277 mm",
    "AS-11": "share of 1 m pipe at v_t  > 99.9%",
    "AS-12": "Model-0 collapses: scatter < 0.1%",
    "AS-13": "Pi_1 -> 1024/45 = 22.756",
    "AS-14": "Model-2 does NOT collapse: > 5%",
}

MEAS = {
    "AS-5":  "1.48 -> 2.76, monotonic",
    "AS-16": "peak at |z| = 5.04 mm  vs  a/2 = 3.00 mm",
}


def _row(a: dict) -> tuple[str, str, str, bool]:
    m = MEAS.get(a["id"], str(a["measured"]))
    return (a["id"], EN.get(a["id"], a["id"]), m, a["verdict"] in ("PASS", "PRESCRIBED"))


def make_all(AS: list[dict], D: dict) -> dict:
    A = {a["id"]: a for a in AS}
    out: dict[str, dict] = {}

    # ============================================================ F-1
    with fk.Figure("F-1", STAMP, OUT_FIG, figsize=(12.6, 6.6), ncols=2) as (fig, (ax1, ax2)):
        ax1.loglog()
        fk.plot_reference(ax1, D["sig"], D["v0_s"], "Model-0  (closed form)")
        fk.plot_model(ax1, D["sig"], D["v2_s"], 0, "Model-2  (finite magnet + wall)")
        fk.annotate_slope(ax1, D["sig"], D["v0_s"], D["k0s"], 1.0, frac=0.30)
        fk.annotate_slope(ax1, D["sig"], D["v2_s"], D["k2s"], 1.0, i=0, frac=0.66)
        ax1.set_xlabel(r"$\sigma$  (S/m)")
        ax1.set_ylabel(r"$v_t$  (m/s)")
        ax1.set_title(r"(a)   $v_t$ vs conductivity  —  both exactly $-1$", fontsize=13.5)
        ax1.legend(loc="upper right", fontsize=11)

        ax2.loglog()
        fk.plot_reference(ax2, D["ws"] * 1e3, D["v0_w"], "Model-0  (thin wall)")
        fk.plot_model(ax2, D["ws"] * 1e3, D["v2_w"], 0, "Model-2  (radial integral)")
        fk.annotate_slope(ax2, D["ws"] * 1e3, D["v0_w"], D["k0w"], 1.0, frac=0.28)
        ax2.annotate("bends up:  A-2 breaks\n" + r"($w/a \to 0.5$)",
                     xy=(D["ws"][-1] * 1e3, D["v2_w"][-1]), xytext=(-118, 40),
                     textcoords="offset points", fontsize=11.5, color=fk.SLOTS[0]["color"],
                     fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color=fk.SLOTS[0]["color"], lw=1.6))
        ax2.set_xlabel(r"$w$  (mm)")
        ax2.set_ylabel(r"$v_t$  (m/s)")
        ax2.set_title(r"(b)   $v_t$ vs wall thickness  —  Model-2 departs", fontsize=13.5)
        ax2.legend(loc="upper right", fontsize=11)
        # 窄对数范围下 matplotlib 会给次刻度也贴标签，全挤成一团 —— 显式设刻度
        fk.log_ticks(ax1.xaxis, [1.5e7, 2e7, 3e7, 4e7, 6e7], fmt="{:.2g}")
        ax1.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v/1e7:g}e7"))
        fk.log_ticks(ax2.xaxis, [0.2, 0.3, 0.5, 1.0, 2.0, 3.0])

        fk.assertions(fig, [_row(A[i]) for i in ("AS-2", "AS-3", "AS-4", "AS-5", "AS-6")])
        fk.fit_range_note(fig, r"fit ranges:   $\sigma \in [1.5,\ 5.96]\times 10^{7}$ S/m"
                               r"      $w \in [0.2,\ 3.0]$ mm")
    out["F-1"] = dict(png=str(OUT_FIG / "F-1.png"), svg=str(OUT_FIG / "F-1.svg"))

    # ============================================================ F-2
    with fk.Figure("F-2", STAMP, OUT_FIG, figsize=(8.4, 7.2)) as (fig, ax):
        ax.loglog()
        fk.plot_reference(ax, D["aa"] * 1e3, D["v0_a"], "Model-0  (point dipole)")
        fk.plot_model(ax, D["aa"] * 1e3, D["v2_a"], 0, "Model-2  (finite magnet)")
        fk.annotate_slope(ax, D["aa"] * 1e3, D["v0_a"], D["k0a"], 1.0, frac=0.58)
        fk.annotate_slope(ax, D["aa"] * 1e3, D["v2_a"], D["k2a"], D["r2_2a"], i=0, frac=0.42)
        ax.set_xlabel(r"$a$   (tube inner radius, mm)")
        ax.set_ylabel(r"$v_t$   (m/s)")
        ax.set_title(r"F-2   Is $v_t \propto a^{4}$ ?   —   the most aggressive prediction",
                     fontsize=14.5)
        ax.legend(loc="upper left", fontsize=11.5)
        fk.assertions(fig, [_row(A[i]) for i in ("AS-7", "AS-8", "AS-9")])
        fk.fit_range_note(fig, r"fit range:  $a \in [5.5,\ 12]$ mm."
                               r"   $a/L = 0.55$–$1.2$ :  the point-dipole criterion $a \gg L$"
                               r" never holds  $\Rightarrow$  P5 is downgraded.")
    out["F-2"] = dict(png=str(OUT_FIG / "F-2.png"), svg=str(OUT_FIG / "F-2.svg"))

    # ============================================================ F-3
    with fk.Figure("F-3", "Model-0 · spec r1", OUT_FIG, figsize=(8.4, 6.4)) as (fig, ax):
        x_mm = D["x_curve"] * 1e3
        good = x_mm > 1e-4
        ax.semilogx(x_mm[good], D["v_t_curve"][good] / D["vt0"],
                    color=fk.SLOTS[0]["color"], lw=2.4, zorder=3, label=r"$v/v_t$   (closed form)")
        ax.axhline(0.99, color=fk.INK_MUTED, ls=":", lw=1.3)
        ax.axvline(D["x99"] * 1e3, color=fk.STATUS["pass"], ls="--", lw=1.7, zorder=2)
        ax.annotate(f"0.99 $v_t$ reached at\n$x$ = {D['x99']*1e3:.3f} mm",
                    xy=(D["x99"] * 1e3, 0.99), xytext=(34, -66), textcoords="offset points",
                    fontsize=12, color=fk.STATUS["pass"], fontweight="bold",
                    arrowprops=dict(arrowstyle="->", color=fk.STATUS["pass"], lw=1.7))
        ax.axvline(D["x99_spec_wrong"] * 1e3, color=fk.STATUS["fail"], ls=":", lw=1.5, zorder=2)
        ax.annotate("spec said 0.35 mm\n(SPEC-DEFECT SD-2:\n" + r"dropped the $-0.99$ term)",
                    xy=(D["x99_spec_wrong"] * 1e3, 0.42), xytext=(34, -6),
                    textcoords="offset points", fontsize=10.5, color=fk.STATUS["fail"],
                    ha="left", va="center",
                    arrowprops=dict(arrowstyle="->", color=fk.STATUS["fail"], lw=1.4, ls=":"))
        ax.set_xlabel("fall distance   (mm)")
        ax.set_ylabel(r"$v\ /\ v_t$")
        ax.set_ylim(0, 1.09)
        ax.set_title("F-3   Start-up transient  —  99.97% of a 1 m pipe is at terminal velocity",
                     fontsize=13.5)
        ax.legend(loc="lower right", fontsize=11.5)
        fk.assertions(fig, [_row(A[i]) for i in ("AS-10", "AS-11")])
    out["F-3"] = dict(png=str(OUT_FIG / "F-3.png"), svg=str(OUT_FIG / "F-3.svg"))

    # ============================================================ F-4  · 钱图
    with fk.Figure("F-4", STAMP, OUT_FIG, figsize=(9.2, 7.4)) as (fig, ax):
        fk.hline(ax, PI1_THEORY, r"$\Pi_1 = 1024/45 = 22.756$")

        # Model-0：全部中性墨、同一标记 —— 它们**堆**到那条水平线上。堆叠本身就是信息。
        ax.scatter(D["p2s"], D["p1_0"], s=210, marker="_", linewidths=3.0,
                   color=fk.INK_SOFT, zorder=4, label="Model-0   (all 5 runs collapse)")

        # Model-2：5 个槽 + 5 种标记 —— 散开，且每个都是一次真正独立的运行
        for j, (p2, p1) in enumerate(zip(D["p2s"], D["p1_2"])):
            s = fk.slot(j)
            sig, w, a = D["combos"][j]
            ax.scatter([p2], [p1], s=145, marker=s["marker"], color=s["color"],
                       zorder=5, edgecolors="white", linewidths=1.2,
                       label=(rf"Model-2:  $\sigma$={sig/1e7:.2f}e7,  "
                              rf"$w$={w*1e3:.1f} mm,  $a$={a*1e3:.0f} mm"))

        ax.set_xlabel(r"$\Pi_2 = w/a$")
        ax.set_ylabel(r"$\Pi_1 = v_t\,\mu_0^2 m^2 \sigma w \ /\ (M g a^4)$")
        ax.set_title("F-4   Data collapse  —  and the informative failure of it", fontsize=14.5)
        ax.set_ylim(20.5, 47)
        ax.set_xlim(0.012, 0.235)
        ax.legend(loc="upper left", fontsize=10, framealpha=0.95)
        fk.assertions(fig, [_row(A[i]) for i in ("AS-12", "AS-13", "AS-14")])
        fk.fit_range_note(fig,
                          "Model-2 does NOT collapse (scatter 44.9%) — A-1's breakdown introduces "
                          r"a third group $L/a$." "\n"
                          "That failure to collapse IS the result, not a bug.")
    out["F-4"] = dict(png=str(OUT_FIG / "F-4.png"), svg=str(OUT_FIG / "F-4.svg"))

    return out


if __name__ == "__main__":
    from acceptance import run
    from params import banner
    banner()
    AS, D = run(verbose=False)
    print("出图:")
    make_all(AS, D)
