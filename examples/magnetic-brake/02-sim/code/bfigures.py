#!/usr/bin/env python3
"""V-1 … V-4  ·  model_validation_checks[V-1]：验证「中间量」B 场：均匀磁化圆柱磁体的 B 场。

这三张图的作用是把 **A-1（点偶极子近似）的崩溃**从"间接推断"变成"直接看见"。

在此之前，A-1 崩溃的证据都是间接的：指数从 4.00 掉到 3.44、涡流峰跑到 L/2、
数据坍缩失败。这三张图直接把「真实的场」和「偶极子场」摆在一起，并指出
**管壁正好坐在两者差得最厉害的地方**。
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
from matplotlib.colors import LinearSegmentedColormap, LogNorm, BoundaryNorm
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

from params import OUT_FIG, MU0, R_MAG, L_MAG, A_TUBE, W_WALL, SIGMA, M_DIP, MS
from bfield import cylinder_field, dipole_field, onaxis_exact, gates
import figkit as fk

STAMP = "B-field · Amperian model · spec r2"

#: 单色相 sequential 色阶（documented blue ramp，palette.md 的 100 -> 700）
#: 规矩：sequential = 单色相，浅→深。**绝不用彩虹色阶。**
BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
        "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
CMAP_B = LinearSegmentedColormap.from_list("iypt_blue", BLUE)
#: 误差图用**离散**色带（ordinal）——阈值结构比连续渐变可读得多
ERR_LEVELS = [0, 5, 10, 20, 30, 50, 100, 250]
CMAP_ERR = LinearSegmentedColormap.from_list(
    "iypt_blue_ord", [BLUE[2], BLUE[4], BLUE[6], BLUE[7], BLUE[9], BLUE[10], BLUE[12]],
    N=len(ERR_LEVELS) - 1)

MM = 1e3


def _geometry(ax, *, mirror=True):
    """画磁体和管壁。"""
    R, L, a, w = R_MAG * MM, L_MAG * MM, A_TUBE * MM, W_WALL * MM
    ax.add_patch(Rectangle((-R, -L / 2), 2 * R, L, fc=fk.SLOTS[2]["color"], ec="none",
                           alpha=0.90, zorder=6))
    ax.text(0, 0, "N\nS", ha="center", va="center", color="white", fontsize=11,
            fontweight="bold", zorder=7, linespacing=1.1)
    ylo, yhi = ax.get_ylim()
    for s in ((-1, 1) if mirror else (1,)):
        ax.add_patch(Rectangle((s * a if s > 0 else -(a + w), ylo), w, yhi - ylo,
                               fc=fk.STATUS["fail"], ec="none", alpha=0.30, zorder=5))
        ax.axvline(s * a, color=fk.STATUS["fail"], lw=1.4, zorder=5)
        ax.axvline(s * (a + w), color=fk.STATUS["fail"], lw=1.4, zorder=5)


#: V-4 的断言在**图上**的英文短标（权威版本在 acceptance.md / results.json）。
#  图上文字一律英文 —— figkit 的 _assert_no_cjk 会拦下中文。
EN_V = {
    "AS-32": "error decreases monotonically with a/L",
    "AS-33": "a/L needed for 10% accuracy  in (0.7, 1.5)",
    "AS-34": "A-1 alone at a/L = 0.60  in (35%, 45%)",
    "AS-35": "must_not: A-1 alone == 82.7% (the total)",
}


def make_all(AS: list[dict] | None = None):
    """V-1 … V-4。

    AS: acceptance.run() 的断言表。给了就把 V-4 的验收结果画在图上
        （**读者不该需要翻 results.json 才知道这张图过没过**）。
    """
    A = {a["id"]: a for a in (AS or [])}
    G = gates(verbose=False)

    # ================================================== 网格
    n = 361
    x = np.linspace(-24e-3, 24e-3, n)          # 带符号的 r
    z = np.linspace(-24e-3, 24e-3, n)
    X, Z = np.meshgrid(x, z, indexing="xy")
    Rr = np.abs(X)
    sgn = np.sign(X)
    sgn[sgn == 0] = 1.0

    Br, Bz = cylinder_field(Rr, Z)
    Bx = Br * sgn                               # B_r(-r,z) = -B_r(r,z)
    Bmag = np.hypot(Bx, Bz)

    Brd, Bzd = dipole_field(Rr, Z)
    Bxd = Brd * sgn
    Err = np.hypot(Bx - Bxd, Bz - Bzd) / np.maximum(Bmag, 1e-12) * 100.0

    # 磁体内部的"偶极子误差"是**没有意义的** —— 点偶极子场在原点发散（1/r^3 -> inf）。
    # 画进去只会制造一片假的深色。挖掉。
    inside = (Rr <= R_MAG) & (np.abs(Z) <= L_MAG / 2)
    Err = np.where(inside, np.nan, Err)

    # ================================================== S-1
    with fk.Figure("V-1", STAMP, OUT_FIG, figsize=(13.2, 6.9), ncols=2) as (fig, (ax1, ax2)):
        # ---- (a) |B| + 磁力线
        im = ax1.pcolormesh(x * MM, z * MM, Bmag, cmap=CMAP_B, shading="gouraud",
                            norm=LogNorm(vmin=1e-3, vmax=1.0), zorder=1, rasterized=True)
        ax1.streamplot(x * MM, z * MM, Bx, Bz, color=fk.INK, linewidth=0.75,
                       density=1.25, arrowsize=0.85, zorder=3)
        cb = fig.colorbar(im, ax=ax1, pad=0.02, fraction=0.046,
                          ticks=[1e-3, 1e-2, 1e-1, 1.0])
        cb.set_label(r"$|\mathbf{B}|$   (T)", fontsize=12.5)
        cb.ax.set_yticklabels(["1 mT", "10 mT", "0.1 T", "1 T"])
        ax1.set_ylim(-24, 24)
        _geometry(ax1)
        ax1.set_xlabel(r"$r$   (mm)")
        ax1.set_ylabel(r"$z$   (mm)")
        ax1.set_title("(a)   The real field of the magnet\n"
                      r"(Ampèrian model: surface current $K = M_s$)", fontsize=13)
        ax1.set_aspect("equal")
        ax1.grid(False)

        # ---- (b) 偶极子近似的误差
        norm = BoundaryNorm(ERR_LEVELS, CMAP_ERR.N)
        im2 = ax2.contourf(x * MM, z * MM, np.clip(Err, 0, 249), levels=ERR_LEVELS,
                           cmap=CMAP_ERR, norm=norm, zorder=1, extend="max")
        # 等值线用**线型**区分，配图例 —— 内联标签在这种密集等值线上必然互相压住
        ax2.contour(x * MM, z * MM, Err, levels=[10], colors=[fk.INK],
                    linewidths=1.1, linestyles="--", zorder=4)
        ax2.contour(x * MM, z * MM, Err, levels=[50], colors=[fk.INK],
                    linewidths=1.9, linestyles="-", zorder=4)
        ax2.legend(handles=[
            Line2D([], [], color=fk.INK, ls="--", lw=1.1, label="10% error"),
            Line2D([], [], color=fk.INK, ls="-", lw=1.9, label="50% error"),
        ], loc="lower left", fontsize=10.5, framealpha=0.96, borderpad=0.5)
        cb2 = fig.colorbar(im2, ax=ax2, pad=0.02, fraction=0.046, ticks=ERR_LEVELS)
        cb2.set_label("point-dipole error   (%)", fontsize=12.5)
        ax2.set_ylim(-24, 24)
        _geometry(ax2)
        ax2.annotate("pipe wall:\n" + r"dipole is $\mathbf{102\%}$ off at $z=0$",
                     xy=(A_TUBE * MM + W_WALL * MM / 2, 0.0), xytext=(-6, -132),
                     textcoords="offset points", fontsize=11.5, fontweight="bold",
                     ha="center", color=fk.STATUS["fail"], zorder=9,
                     bbox=dict(fc="white", ec=fk.STATUS["fail"], lw=1.6, alpha=0.97,
                               boxstyle="round,pad=0.42"),
                     arrowprops=dict(arrowstyle="->", color=fk.STATUS["fail"], lw=2.0,
                                     connectionstyle="arc3,rad=-0.15"))
        ax2.set_xlabel(r"$r$   (mm)")
        ax2.set_ylabel(r"$z$   (mm)")
        ax2.set_title("(b)   Where the point-dipole approximation fails\n"
                      r"$|\mathbf{B}_{\rm exact}-\mathbf{B}_{\rm dipole}| \,/\, |\mathbf{B}_{\rm exact}|$"
                      "   (magnet interior masked: the dipole field diverges there)",
                      fontsize=12.2)
        ax2.set_aspect("equal")
        ax2.grid(False)

        fk.assertions(fig, [
            ("G-A", "on-axis vs textbook closed form", f"{G['G-A']['err']:.1e}", True),
            ("G-B", "far field -> point dipole (s = 50 L)", f"{G['G-B']['rows'][-1]['err']*100:.5f}%", True),
            ("G-C", "B_r: loop-integral vs closed-form dPhi/dz", f"{G['G-C']['err']:.1e}", True),
        ])
        fk.fit_range_note(fig,
                          r"A-1 requires $a \gg L$.  Here $a/L = 0.60$ — and at the wall the "
                          "dipole model is off by 102% at $z=0$." "\n"
                          "This is the same A-1 breakdown that F-2 sees as an exponent of 3.44 "
                          "instead of 4.00 — now visible directly.")
    print("  [V-1] |B| + 磁力线 + 偶极子误差图")

    # ================================================== S-2
    zz = np.linspace(-25e-3, 25e-3, 601)
    br_w, bz_w = cylinder_field(np.full_like(zz, A_TUBE), zz)
    brd_w, bzd_w = dipole_field(np.full_like(zz, A_TUBE), zz)

    with fk.Figure("V-2", STAMP, OUT_FIG, figsize=(13.2, 6.6), ncols=2) as (fig, (ax1, ax2)):
        for ax, exact, dip, lab, ttl in (
            (ax1, br_w, brd_w, r"$B_r$",
             "(a)   Radial field at the wall  —  this IS the eddy-current driver"),
            (ax2, bz_w, bzd_w, r"$B_z$", "(b)   Axial field at the wall"),
        ):
            fk.plot_reference(ax, zz * MM, dip * 1e3, "point dipole")
            ax.plot(zz * MM, exact * 1e3, color=fk.SLOTS[0]["color"], lw=2.7,
                    zorder=4, label="finite magnet (exact)")
            for s in (-1, 1):
                ax.axvline(s * L_MAG * MM / 2, color=fk.SLOTS[2]["color"], ls=":", lw=1.7, zorder=2)
            ax.axhline(0, color=fk.INK_MUTED, lw=1.0, zorder=1)
            ax.set_xlabel(r"$z$   (mm)")
            ax.set_ylabel(lab + "   (mT)")
            ax.set_title(ttl, fontsize=13)
            # 曲线占满中间，两个下角是空的 —— 图例放那儿
            ax.legend(loc="lower left", fontsize=11, framealpha=0.97)

        # 留足上方空间，别让峰值被图例/标注切掉
        m1 = max(np.abs(br_w).max(), np.abs(brd_w).max()) * 1e3
        ax1.set_ylim(-1.30 * m1, 1.30 * m1)
        ax2.set_ylim(min(bz_w.min(), bzd_w.min()) * 1e3 * 1.30,
                     max(bz_w.max(), bzd_w.max()) * 1e3 * 2.30)

        ipk = int(np.argmax(np.abs(br_w)))
        ax1.annotate(f"exact peak at $|z|$ = {abs(zz[ipk])*MM:.2f} mm  $= L/2$\n"
                     f"(the magnet's end face)\n"
                     f"dipole peak at $a/2$ = {A_TUBE*MM/2:.2f} mm",
                     xy=(abs(zz[ipk]) * MM, abs(br_w[ipk]) * 1e3),
                     xytext=(0.035, 0.955), textcoords="axes fraction",
                     fontsize=11.5, color=fk.SLOTS[0]["color"],
                     fontweight="bold", ha="left", va="top",
                     bbox=dict(fc="white", ec=fk.SLOTS[0]["color"], lw=1.4, alpha=0.97,
                               boxstyle="round,pad=0.4"),
                     arrowprops=dict(arrowstyle="->", color=fk.SLOTS[0]["color"], lw=1.8,
                                     connectionstyle="arc3,rad=0.12"))
        for s, lab in ((-1, r"$-L/2$"), (1, r"$+L/2$")):
            ax1.text(s * L_MAG * MM / 2, -1.19 * m1, lab, fontsize=10.5,
                     color=fk.SLOTS[2]["color"], fontweight="bold", ha="center", va="center",
                     bbox=dict(fc="white", ec="none", pad=1.2))

        ax2.annotate("dipole overestimates\n" + r"$B_z$ by 2$\times$ at $z=0$",
                     xy=(0, bzd_w[len(zz) // 2] * 1e3), xytext=(88, 20),
                     textcoords="offset points", fontsize=11.5, color=fk.STATUS["fail"],
                     fontweight="bold",
                     bbox=dict(fc="white", ec=fk.STATUS["fail"], lw=1.3, alpha=0.97,
                               boxstyle="round,pad=0.35"),
                     arrowprops=dict(arrowstyle="->", color=fk.STATUS["fail"], lw=1.8))
        ax2.text(-24, max(bz_w.max(), bzd_w.max()) * 1e3 * 2.0,
                 "the real field is FLATTER across the magnet\n"
                 "and pushed out to the end faces",
                 fontsize=11, color=fk.SLOTS[0]["color"], fontweight="bold", va="top")

        fk.fit_range_note(fig,
                          r"Motional EMF in a wall ring:  $\mathcal{E} = -v\,\partial\Phi/\partial z "
                          r"= v \cdot 2\pi a \cdot B_r$." "\n"
                          r"So panel (a) IS the eddy-current profile of F-5 — and its peak sits on "
                          r"the magnet's end face, not at $a/2$.")
    G["V-2_zpk"] = float(abs(zz[ipk]) * MM)
    print("  [V-2] 管壁上的 B_r 与 B_z")

    # ================================================== S-3
    za = np.linspace(0.6e-3, 60e-3, 500)
    _, bz_num = cylinder_field(np.zeros_like(za), za)
    bz_cf = onaxis_exact(za)
    _, bzd_a = dipole_field(np.zeros_like(za), za)

    with fk.Figure("V-3", STAMP, OUT_FIG, figsize=(8.6, 6.6)) as (fig, ax):
        ax.loglog()
        ax.plot(za * MM, np.abs(bz_num), color=fk.SLOTS[0]["color"], lw=3.0, zorder=3,
                label="finite magnet  (numerical, 400-node Gauss)")
        ax.plot(za * MM, np.abs(bz_cf), color=fk.STATUS["pass"], lw=1.4, ls="-",
                marker="o", markevery=28, ms=7, zorder=4,
                label="finite magnet  (textbook closed form)")
        fk.plot_reference(ax, za * MM, np.abs(bzd_a), "point dipole  " + r"($\propto z^{-3}$)")
        ax.axvline(L_MAG * MM / 2, color=fk.SLOTS[2]["color"], ls=":", lw=1.6)
        ax.axvspan(A_TUBE * MM, (A_TUBE + W_WALL) * MM, color=fk.STATUS["fail"],
                   alpha=0.25, zorder=0, label="pipe wall")
        # 偶极子在小 z 处发散到 10^3 T —— 让它撑满纵轴会把有意思的那段压扁
        ax.set_ylim(5e-4, 4.0)
        ax.set_xlim(0.55, 62)
        ax.text(0.965, 0.955,
                f"$B_z(0,0)$ = {G['G-A']['b_center']:.3f} T\n"
                r"$= \mu_0 M_s / \sqrt{2}$   (since $R = L/2$)" "\n"
                "predicted before computing  ✓",
                transform=ax.transAxes, ha="right", va="top",
                fontsize=11.5, color=fk.INK, fontweight="bold",
                bbox=dict(fc="white", ec=fk.INK_MUTED, lw=1.2, alpha=0.97,
                          boxstyle="round,pad=0.45"))
        ax.annotate("the dipole only becomes\n" + r"good beyond $\sim 3L$",
                    xy=(33, np.abs(bzd_a)[np.argmin(np.abs(za - 33e-3))]),
                    xytext=(-6, 74), textcoords="offset points", fontsize=11.5,
                    color=fk.INK_SOFT, ha="center", fontweight="bold",
                    bbox=dict(fc="white", ec="none", alpha=0.9, pad=1.5),
                    arrowprops=dict(arrowstyle="->", color=fk.INK_SOFT, lw=1.6))
        ax.annotate("the dipole is off by\n" + r"$\mathbf{2\times}$ at the pipe wall",
                    xy=(A_TUBE * MM, np.abs(bzd_a)[np.argmin(np.abs(za - A_TUBE))]),
                    xytext=(-118, 30), textcoords="offset points", fontsize=11.5,
                    color=fk.STATUS["fail"], ha="center", fontweight="bold",
                    bbox=dict(fc="white", ec=fk.STATUS["fail"], lw=1.3, alpha=0.97,
                              boxstyle="round,pad=0.35"),
                    arrowprops=dict(arrowstyle="->", color=fk.STATUS["fail"], lw=1.8))
        ax.set_xlabel(r"$z$   on the axis   (mm)")
        ax.set_ylabel(r"$|B_z|$   (T)")
        ax.set_title(r"V-3   On-axis field  —  and where the dipole starts to work",
                     fontsize=14)
        ax.legend(loc="lower left", fontsize=11, framealpha=0.97)
        fk.assertions(fig, [
            ("G-A", "numerical vs textbook closed form", f"{G['G-A']['err']:.1e}", True),
            ("pred", "B_z(0,0) predicted before computing", f"{G['G-A']['b_center']:.4f} T", True),
        ])
    print("  [V-3] 轴上的 B_z：数值 vs 闭式 vs 偶极子")

    # ================================================== S-4  ·「管子要多大才够用」
    #
    # 实验组真正会问的问题：A-1 的判据写作 a >> L，但 "≫" 不是一个数。**把它变成一个数。**
    #
    # 而且要问对量：真正要紧的不是"场"错多少，是 **v_t 错多少**。
    # 阻尼 b ∝ ∫(∂Φ/∂z)² —— 是场的**平方**，所以 v_t 的误差大约是场误差的两倍。
    #
    # 全程用薄壁近似 —— 这样隔离出的是 **A-1 一条假设**的效应（把 A-2 排除在外）。
    #
    # ★ 数字来自 model2.v4_scan() —— **和 acceptance.py 的 AS-32..AS-35 读的是同一个函数**。
    #   若这里再算一遍，两边迟早会漂开一点点，于是**图上的数字和 results.json 对不上**
    #   —— 那正是设计审查 D12 要抓的东西。**凡是既要断言又要画的数，只许算一次。**
    from model2 import v4_scan

    V4 = v4_scan(R_MAG, L_MAG, MS, A_TUBE, W_WALL, SIGMA, M_DIP)
    ratios, err_b = V4["ratios"], V4["err_b"]
    q10, q30 = V4["q10"], V4["q30"]
    err_here = V4["err_here"]
    r1, r2 = V4["f_a1"], V4["f_a2"]

    with fk.Figure("V-4", STAMP, OUT_FIG, figsize=(9.0, 6.8)) as (fig, ax):
        ax.loglog()
        fk.plot_model(ax, ratios, err_b, 0,
                      r"error in $v_t$ if you use the point-dipole model", every=2)
        for lv, c, lab in ((30, fk.STATUS["fail"], "30%"), (10, fk.STATUS["warn"], "10%")):
            ax.axhline(lv, color=c, ls="--", lw=1.6, zorder=2)
            ax.text(9.6, lv * 1.14, lab, color=c, fontsize=12, fontweight="bold",
                    ha="right", va="bottom")

        ax.axvline(A_TUBE / L_MAG, color=fk.SLOTS[2]["color"], lw=2.4, zorder=3)
        ax.annotate(f"THIS experiment:  $a/L$ = {A_TUBE/L_MAG:.2f}\n"
                    f"A-1 alone costs {err_here:.0f}%",
                    xy=(A_TUBE / L_MAG, err_here), xytext=(0.20, 0.93),
                    textcoords="axes fraction", fontsize=12, fontweight="bold",
                    color=fk.SLOTS[2]["color"], ha="left", va="top",
                    bbox=dict(fc="white", ec=fk.SLOTS[2]["color"], lw=1.6, alpha=0.97,
                              boxstyle="round,pad=0.45"),
                    arrowprops=dict(arrowstyle="->", color=fk.SLOTS[2]["color"], lw=2.2))
        ax.axvline(q10, color=fk.STATUS["pass"], ls=":", lw=2.2, zorder=3)
        ax.annotate(f"need  $a/L$ > {q10:.1f}\nfor 10% accuracy",
                    xy=(q10, 10), xytext=(0.42, 0.44), textcoords="axes fraction",
                    fontsize=12.5, fontweight="bold", color=fk.STATUS["pass"], ha="left",
                    bbox=dict(fc="white", ec=fk.STATUS["pass"], lw=1.6, alpha=0.97,
                              boxstyle="round,pad=0.45"),
                    arrowprops=dict(arrowstyle="->", color=fk.STATUS["pass"], lw=2.2))

        ax.set_xlabel(r"$a / L$      (tube inner radius  /  magnet length)")
        ax.set_ylabel(r"relative error in $v_t$   (%)")
        # 图上的编号必须和 results.json 的 figure id 一致 —— PPT 会引用 "V-4"，
        # 图上写 "S-4" 读者就对不上了。（旧编号的遗留。）
        ax.set_title(r"V-4   ‘$a \gg L$’ is not a number.  Here is the number.", fontsize=14)
        ax.legend(loc="lower left", fontsize=11.5, framealpha=0.97)
        fk.log_ticks(ax.xaxis, [0.6, 1, 2, 3, 5, 10])
        fk.log_ticks(ax.yaxis, [1, 3, 10, 30, 100, 300], fmt="{:g}%")
        ax.set_xlim(0.52, 10.5)
        ax.set_ylim(0.8, 300)
        # A-1 与 A-2 的失效是**相乘**的，不是相加的 —— 这条要说清楚，
        # 否则读者会拿 S-4 的 40% 去对 Model-2 的 +82.7%，然后以为哪里错了。
        # （r1 / r2 来自 v4_scan —— 与 AS-35 读同一个数。）
        ax.text(0.975, 0.955,
                "the two failures COMPOUND\n"
                f"  A-1  x {r1:.3f}\n"
                f"  A-2  x {r2:.3f}\n"
                f"  ---------------\n"
                f"  {r1:.3f} x {r2:.3f} = {r1*r2:.3f}\n"
                f"  => v_t off by +{(r1*r2-1)*100:.1f}%",
                transform=ax.transAxes, ha="right", va="top", fontsize=10.5,
                family="monospace", color=fk.INK, linespacing=1.45,
                bbox=dict(fc="white", ec=fk.INK_MUTED, lw=1.2, alpha=0.97,
                          boxstyle="round,pad=0.45"))
        # ★ V-4 曾经**一条断言都没有** —— 它挂着一个编出来的 id（AS-V4），
        #   而 FIG-NOASSERT 只查「非空」。现在它有 AS-32..AS-35，画在轴外。
        #
        #   `measured` 在 results.json 里是**中文**的，不能直接喂给图（DejaVu 没有 CJK
        #   字形 -> 豆腐块 □□□，而 matplotlib 一声不吭）。figkit 的 _assert_no_cjk
        #   在存图前把它拦了下来 —— **这个守卫刚刚真的救了一次**。
        #   给图一个英文版，数字**全部从 V4 算**，不许硬编码。
        meas_v = {
            "AS-32": f"monotonic: {V4['monotone']}",
            "AS-33": f"a/L > {q10:.2f}",
            "AS-34": f"{err_here:.1f}%",
            "AS-35": f"{err_here:.1f}%  ({abs(err_here - 82.73):.0f} pp from the trap 82.7%)",
        }
        if A:
            fk.assertions(fig, [(i, EN_V[i], meas_v[i],
                                 A[i]["verdict"] in ("PASS", "PRESCRIBED"))
                                for i in ("AS-32", "AS-33", "AS-34", "AS-35") if i in A])
        fk.fit_range_note(fig,
                          r"Thin wall throughout — so this curve isolates $\bf{A}$-$\bf{1}$ "
                          r"$\bf{alone}$ (the point-dipole assumption)." "\n"
                          f"For 10% accuracy in $v_t$ you need " r"$a/L$" f" > {q10:.1f}.  "
                          f"This experiment runs at {A_TUBE/L_MAG:.2f} — "
                          r"roughly $\mathbf{" f"{q10/(A_TUBE/L_MAG):.0f}" r"\times}$ too small.")
    print(f"  [V-4] 「a >> L」到底是多少：v_t 要 10% 精度需 a/L > {q10:.1f}；"
          f"本实验 a/L={A_TUBE/L_MAG:.2f} 处 A-1 单独的误差 {err_here:.1f}%")
    print(f"        分解：A-1 x{r1:.4f} · A-2 x{r2:.4f} = x{r1*r2:.4f} "
          f"-> v_t 偏差 +{(r1*r2-1)*100:.1f}%  （与实测的 +82.7% 逐位吻合）")

    G["V-4"] = dict(q10=float(q10), q30=float(q30), a_over_L=A_TUBE / L_MAG,
                    err_here=float(err_here), f_a1=float(r1), f_a2=float(r2),
                    f_total=float(V4["f_total"]))
    return G


if __name__ == "__main__":
    from params import banner
    banner()
    print("出图:")
    make_all()
