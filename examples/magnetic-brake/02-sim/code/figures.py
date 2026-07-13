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
from matplotlib.patches import Patch

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
    "AS-15": "dPhi/dz antisymmetric  (< 1e-10)",
    "AS-16": "exactly two peaks, opposite signs",
    "AS-27": "must_not: peak at a/2 (= point dipole)",
}

def _en_measured(D: dict) -> dict[str, str]:
    """断言的 `measured` 里有中文时，给图上一个英文版。

    **数字一律从 D 里算，不许硬编码。** 图上的数字和 results.json 对不上，
    是设计审查 D12 —— 而一个写死在源码里的 "5.03 mm" 迟早会和重算出来的值漂开。
    （这里原本就写死过一个 "peak at |z| = 5.03 mm"。）
    """
    return {
        "AS-5":  f"{D['ratio_w'][0]:.2f} -> {D['ratio_w'][-1]:.2f}, monotonic",
        "AS-16": (f"peak at |z| = {D['zpk']*1e3:.2f} mm  vs  a/2 = "
                  f"{D['zpk_dip']*1e3:.2f} mm  ({(D['zpk']/D['zpk_dip']-1)*100:+.0f}%)"),
    }


def make_all(AS: list[dict], D: dict) -> dict:
    A = {a["id"]: a for a in AS}
    MEAS = _en_measured(D)
    out: dict[str, dict] = {}

    def _row(a: dict) -> tuple[str, str, str, bool]:
        m = MEAS.get(a["id"], str(a["measured"]))
        return (a["id"], EN.get(a["id"], a["id"]), m, a["verdict"] in ("PASS", "PRESCRIBED"))

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

    # ============================================================ F-5 · 静止帧
    #
    #  F-5 的 kind 是 `animation` —— 但**动画也必须出一张静止帧**。
    #
    #  此前它没有：run_all.py 拿 **F-1 的 PNG** 顶了上去（两张图共用一个文件）。
    #  后果本来会是：Skill 3 照 `path` 取图，把**幂律图**配上**涡流的 caption**
    #  摆进 PPT —— 而没有任何检查会发现，因为 F-1.png 确实存在。
    #  （check_sim.py 现已加 FIG-PATH-DUP + FIG-NOSTILL。）
    #
    #  为什么静止帧是必需的，不是可选的：
    #    · **PPT 和 PDF 印不出动画。** Physics Fight 上你面对的是投影和评委手里的讲义。
    #    · Skill 4 的铁律 0 要求「真的打开 PNG 用眼睛看」—— 没有 PNG 就没法审。
    #    · SIMULATION 戳是在 SVG 里 grep 的 —— 没有 SVG 就没有戳。
    #  交互页面是**加分项**，不是**替代品**。
    with fk.Figure("F-5", STAMP, OUT_FIG, figsize=(9.8, 6.9)) as (fig, ax):
        z_mm = D["z"] * 1e3
        # 两条曲线各自**归一到自己的峰** —— 这张图问的是「峰在哪」，不是「峰多高」。
        # （幅值差异归 V-2 管：偶极子在 z=0 处把 B_z 高估 2 倍。）
        d2 = D["dphi2"] / np.max(np.abs(D["dphi2"]))
        dd = D["dphi_dip"] / np.max(np.abs(D["dphi_dip"]))
        zpk, zpk_dip = D["zpk"] * 1e3, D["zpk_dip"] * 1e3
        L_half = 5.0                                      # L/2 = 5.00 mm

        # 峰在哪一侧，**从数据里读**，不许假设。
        # （第一版就是假设正峰在 +zpk，结果两个箭头全指向了空白处 —— 而我"知道"峰在那儿，
        #   所以看图时看见的是"数据 + 两个有用的框"，不是"两个框，底下什么都没有"。铁律 0。）
        z_pos = float(z_mm[int(np.argmax(d2))])           # 正峰所在的 z（符号从数据来）
        z_pos_dip = float(z_mm[int(np.argmax(dd))])

        # 磁体本体：|z| < L/2。涡流峰**落在它的端面上** —— 这是本图的全部结论。
        ax.axvspan(-L_half, L_half, color=fk.SLOTS[2]["color"], alpha=0.10, zorder=0)
        ax.axhline(0, color=fk.INK_MUTED, lw=1.0, zorder=1)

        fk.plot_reference(ax, z_mm, dd, "point dipole  (peaks at $\\pm a/2$)")
        fk.plot_model(ax, z_mm, d2, 0, "finite magnet  (Model-2)", every=90)

        for s in (-1, 1):
            ax.axvline(s * zpk, color=fk.SLOTS[0]["color"], lw=1.6, alpha=0.60, zorder=2)
            ax.axvline(s * zpk_dip, color=fk.INK_SOFT, ls=":", lw=1.6, alpha=0.85, zorder=2)

        ax.set_xlim(-27, 27)
        # ---- 上下各留一条**空带**（|y| > 1.05，数据到不了那儿）。D9 的留头也一并解决。
        ax.set_ylim(-1.48, 1.62)

        # ---- 两条竖线**直标**在**底部**空带里。
        #
        #      两条线只差 2 mm，标签叠在一起是必然的（交互页正是这么糊掉的 —— D5）。
        #      **解法：利用它们是镜像的** —— L/2 标在**左边**那条上，a/2 标在**右边**那条上，
        #      隔开 8 mm，物理上不可能相撞。而且读者一眼看出「蓝线在外，灰线在内」。
        #
        #      为什么在底部而不是顶部：顶部右侧已经被结论框占了。**第一版把它们放顶部，
        #      "a/2" 当场被结论框压住，"magnet" 又和 "a/2" 叠成一团** —— 同一个坑，
        #      在同一张图上踩了两次。**看图，不要看代码。**
        ax.text(-zpk, -1.30, r"$L/2$", color=fk.SLOTS[0]["color"], fontsize=13,
                fontweight="bold", ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=1.5))
        ax.text(zpk_dip, -1.30, r"$a/2$", color=fk.INK_SOFT, fontsize=13,
                fontweight="bold", ha="center", va="center",
                bbox=dict(fc="white", ec="none", pad=1.5))

        # ---- 结论框：放在**右上**。曲线是奇函数，x > 8 时它一直贴在 0 以下 ——
        #      右上是这张图唯一一块真正空的地方。**不带箭头**：两条竖线已经直标过了。
        ax.text(0.985, 0.955,
                f"peak at $|z|$ = {zpk:.2f} mm $\\approx L/2$ = {L_half:.2f} mm\n"
                r"— the magnet's $\bf{end}$ $\bf{face}$." "\n"
                f"The point dipole says $a/2$ = {zpk_dip:.2f} mm.\n"
                r"Off by $\bf{+68\%}$ — A-1 breaking down, seen directly.",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=11.5, color=fk.INK, linespacing=1.5,
                bbox=dict(fc="white", ec=fk.SLOTS[0]["color"], lw=1.5, alpha=0.97,
                          boxstyle="round,pad=0.45"))

        ax.set_xlabel(r"$z - z_{\rm magnet}$   (mm)")
        ax.set_ylabel(r"$dI/dz$   (normalised to own peak)")   # 长标签会被裁 —— 短的
        ax.set_title("F-5   Eddy currents in the pipe wall  —  still frame\n"
                     r"(live: 02-sim/interactive/F-5-eddy-currents.html)", fontsize=13.5)
        # 磁体本体进**图例**，不在图上写字 —— 图上多一个浮动文字，就多一次压住数据的机会。
        h, l = ax.get_legend_handles_labels()
        h.append(Patch(fc=fk.SLOTS[2]["color"], alpha=0.10, ec="none"))
        l.append(r"magnet body  ($|z| < L/2$)")
        ax.legend(h, l, loc="upper left", fontsize=11, framealpha=0.97)
        fk.assertions(fig, [_row(A[i]) for i in ("AS-15", "AS-16", "AS-27")])
        # Lenz 的解释**移到坐标轴外面** —— 它原本是一个浮在轴内的框，
        # 正好压住蓝线的负峰。而「反对称**双**峰」正是这张图要证明的东西。（D1）
        fk.fit_range_note(fig,
                          "The current reverses across the magnet: the wall REPELS in front and "
                          "ATTRACTS behind — both oppose the fall. That is Lenz's law, drawn." "\n"
                          r"$dI/dz \propto -\partial\Phi/\partial z = "
                          r"-M_s[\mathcal{M}(z{+}L/2) - \mathcal{M}(z{-}L/2)]$: literally the "
                          "difference of two Ampèrian end-rings —" "\n"
                          r"which is $\bf{why}$ the peak sits on an end face. "
                          "The point dipole has no end faces to sit on.")
    out["F-5"] = dict(png=str(OUT_FIG / "F-5.png"), svg=str(OUT_FIG / "F-5.svg"))

    return out


if __name__ == "__main__":
    from acceptance import run
    from params import banner
    banner()
    AS, D = run(verbose=False)
    print("出图:")
    make_all(AS, D)
