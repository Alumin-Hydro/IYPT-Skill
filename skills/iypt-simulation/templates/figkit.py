#!/usr/bin/env python3
"""IYPT 出图工具箱。

**所有图必须经这里出。** 不是为了统一风格——是为了让三件事变成**强制**的：

1. 每张图盖 SIMULATION 戳（pipeline.md §7 的底线，check_sim.py 在 SVG 里 grep 它）
2. 每个系列同时带 色 + 线型 + 标记（灰度打印和色盲时，颜色会消失）
3. 幂律斜率在标注之前先检查"它到底直不直"（R^2），不直就拒绝标

设计见 references/figure-style.md。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

_STYLE = Path(__file__).with_name("iypt.mplstyle")
if _STYLE.is_file():
    plt.style.use(str(_STYLE))

# ---------------------------------------------------------------- 色板

#: 分类槽位。**色 + 线型 + 标记捆绑在一起** —— 这是灰度/色盲下唯一还活着的通道。
#: 已用 dataviz 验证器验过（白底、全配对 CVD）。见 references/figure-style.md。
SLOTS = [
    dict(color="#2a78d6", ls="-",                        marker="o"),  # blue    4.42:1
    dict(color="#008300", ls="-.",                       marker="s"),  # green   4.95:1
    dict(color="#4a3aa7", ls=":",                        marker="^"),  # violet  8.56:1
    dict(color="#e34948", ls=(0, (6, 2)),                marker="D"),  # red     3.95:1
    dict(color="#eb6834", ls=(0, (4, 1, 1, 1, 1, 1)),    marker="v"),  # orange  3.20:1
]

INK        = "#0b0b0b"   # 19.68:1
INK_SOFT   = "#52514e"   #  7.94:1  <- 解析参照线用它
INK_MUTED  = "#898781"   #  3.59:1
GRID       = "#e1e0d9"   #  1.32:1

STATUS = {"pass": "#0ca30c", "fail": "#d03b3b", "warn": "#fab219"}


def slot(i: int) -> dict:
    """第 i 个分类槽（0-based）。**按顺序分配，绝不循环。**"""
    if i >= len(SLOTS):
        raise ValueError(
            f"要第 {i+1} 个系列，但只有 {len(SLOTS)} 个槽。\n"
            "第 6 个系列不是「再生成一个色」—— 它意味着这张图该拆成小多图 "
            "(small multiples) 了。见 references/figure-style.md。"
        )
    return dict(SLOTS[i])


# ---------------------------------------------------------------- 画图元件

def plot_reference(ax, x, y, label: str, **kw):
    """解析参照线（Model-0 / 闭式解 / 理论值）。

    **中性墨 + 虚线 + 无标记。**

    为什么不给它一个彩色槽位：它不是「系列 2」，它是**被检验的零假设**。
    为什么不画标记：解析解可以在任意点求值 —— 画标记等于假装你只算了几个点。
    """
    kw.setdefault("color", INK_SOFT)
    kw.setdefault("ls", "--")
    kw.setdefault("lw", 1.8)
    kw.setdefault("zorder", 2)
    return ax.plot(x, y, marker="None", label=label, **kw)


def plot_model(ax, x, y, i: int, label: str, *, every: int = 1, **kw):
    """数值结果曲线。**实线 + 标记**。

    **标记落在你真正算过的点上** —— 这是诚实性规则，不是美学规则。
    一条光滑无标记的「数值解」曲线是在假装你有无穷多个点；
    Opponent 会问「这条曲线你算了几个点？」，图上有标记，答案就在图上。

    every: 点太密时每 n 个画一个标记（线仍然全画）。
    """
    s = slot(i)
    s.update(kw)
    s.setdefault("lw", 2.0)
    s.setdefault("zorder", 3)
    s.setdefault("markevery", every)
    return ax.plot(x, y, label=label, **s)


def log_ticks(axis, values, fmt="{:g}"):
    """给对数轴设**显式**刻度，并关掉次刻度标签。

    对数轴在不到两个十进位的窄范围里，matplotlib 会连次刻度一起贴标签
    （2×10⁻¹、3×10⁻¹、4×10⁻¹、6×10⁻¹、10⁰、2×10⁰…），**它们会挤成一团糊掉**。
    参数扫描图几乎总是落在这个窄范围里，所以这个坑几乎必踩。
    """
    from matplotlib.ticker import FixedLocator, NullFormatter, FuncFormatter
    axis.set_major_locator(FixedLocator(list(values)))
    axis.set_major_formatter(FuncFormatter(lambda v, _: fmt.format(v)))
    axis.set_minor_formatter(NullFormatter())


def hline(ax, y: float, label: str, **kw):
    """理论水平线（如坍缩图的 Pi_1 = 1024/45）。细虚线 + 直标。"""
    kw.setdefault("color", INK_MUTED)
    kw.setdefault("ls", "--")
    kw.setdefault("lw", 1.4)
    kw.setdefault("zorder", 1)
    ax.axhline(y, **kw)
    ax.annotate(label, xy=(0.985, y), xycoords=("axes fraction", "data"),
                ha="right", va="bottom", fontsize=11, color=INK_MUTED,
                bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))


# ---------------------------------------------------------------- 幂律拟合

def fit_slope(x, y, *, name: str = "") -> tuple[float, float]:
    """log-log 拟合斜率。返回 (slope, R^2)。

    **R^2 是必须看的**：不管数据直不直，你都会得到一个斜率。有系统性弯曲的，
    「斜率」是没有意义的 —— **弯曲本身才是结论**。
    """
    lx, ly = np.log(np.asarray(x, float)), np.log(np.asarray(y, float))
    k, b = np.polyfit(lx, ly, 1)
    resid = ly - (k * lx + b)
    ss_tot = np.sum((ly - ly.mean()) ** 2)
    r2 = 1.0 - np.sum(resid ** 2) / ss_tot if ss_tot > 0 else 1.0
    if r2 < 0.99:
        print(f"  [figkit] ⚠ {name or '曲线'} 的 loglog 拟合 R^2 = {r2:.4f} < 0.99 —— "
              f"它不是一条直线。**斜率在这里没有意义，弯曲本身才是结论。**")
    return float(k), float(r2)


def annotate_slope(ax, x, y, k: float, r2: float, *, i: int | None = None,
                   frac: float = 0.62, force: bool = False, fmt: str = "k = {k:.2f}"):
    """把拟合斜率标在线上。**别让观众拿尺子量。**

    R^2 < 0.99 时拒绝标注（除非 force=True）—— 因为那条「斜率」是假的。
    """
    if r2 < 0.99 and not force:
        print(f"  [figkit] 拒绝标注斜率：R^2 = {r2:.4f} < 0.99，这不是幂律。"
              f"（真要标就传 force=True，并在图注里说明它只是个「有效指数」）")
        return
    x, y = np.asarray(x, float), np.asarray(y, float)
    j = int(len(x) * frac)
    j = min(max(j, 1), len(x) - 2)
    color = SLOTS[i]["color"] if i is not None else INK_SOFT
    ax.annotate(fmt.format(k=k), xy=(x[j], y[j]), xytext=(10, 10),
                textcoords="offset points", fontsize=12.5, color=color,
                fontweight="bold",
                bbox=dict(fc="white", ec=color, lw=1.0, alpha=0.9, pad=2.5))


# ---------------------------------------------------------------- 验收断言框

def assertions(fig, rows: list[tuple[str, str, str, bool]]):
    """登记断言，画在**坐标轴外**的底部条带里（Figure.__exit__ 负责排版）。

    **读者不该需要翻 results.json 才知道这张图过没过。**

    但也**绝不能为此挡住数据** —— 画在轴内的浮动框迟早会压住它要解释的那条曲线。
    （实测教训：F-4 的断言框正好盖住了 Model-0 坍缩到水平线的那一堆点，
    而"看见它们堆在一起"是这张图的全部意义。）

    rows: [(id, expect, measured, passed), ...]
          **全部用英文短句** —— 图要直接进英文 PPT，而且 DejaVu Sans 没有中文字形，
          中文会渲染成豆腐块。
    """
    fig._iypt_assertions = list(rows)


def fit_range_note(fig, text: str):
    """拟合区间必须写出来 —— 换个区间斜率会变，不写区间的斜率是不可复现的数字。"""
    fig._iypt_fitnote = text


# ---------------------------------------------------------------- Figure 上下文

class Figure:
    """出图上下文。**退出时无条件盖 SIMULATION 戳，并同时存 PNG + SVG。**

    戳是关不掉的 —— 这就是它的意义。SVG 是纯文本 XML，check_sim.py 直接在里面
    grep "SIMULATION"：**这个检查伪造不了，除非你真的盖了戳。**

        with Figure("F-2", "Model-2 · spec r1", outdir) as (fig, ax):
            plot_reference(ax, a, vt0, "Model-0 (point dipole)")
            plot_model(ax, a, vt2, 0, "Model-2 (finite magnet)")
    """

    def __init__(self, fig_id: str, stamp: str, outdir, *, title: str = "",
                 figsize=(7.4, 5.4), nrows=1, ncols=1, **kw):
        self.fig_id = fig_id
        self.stamp = stamp
        self.outdir = Path(outdir)
        self.title = title
        self.fig, self.axes = plt.subplots(nrows, ncols, figsize=figsize, **kw)
        self.paths: dict[str, str] = {}

    def __enter__(self):
        return self.fig, self.axes

    def __exit__(self, exc_type, exc, tb):
        if exc_type is not None:
            plt.close(self.fig)
            return False

        fig = self.fig
        rows = getattr(fig, "_iypt_assertions", [])
        note = getattr(fig, "_iypt_fitnote", "")

        if self.title:
            fig.suptitle(self.title, fontsize=16, fontweight="bold")

        # ---- 底部的垂直堆叠。**全部按英寸算**，再换成 figure fraction。
        #      （混用英寸和 figure fraction 是上一版戳压在断言框上的原因。）
        #
        #        axes ────────────────────────
        #        断言条带 (n 行)
        #        拟合区间注 (可多行)
        #        SIMULATION 戳
        #        ──────────────────────────────
        n = len(rows)
        note_lines = (note.count("\n") + 1) if note else 0
        h = fig.get_size_inches()[1]

        y_stamp = 0.07
        y_note = y_stamp + 0.20
        note_h = 0.21 * note_lines
        y_box = (y_note + note_h + 0.16) if note else (y_stamp + 0.24)
        box_h = 0.21 * n + 0.22

        top_of_stack = (y_box + box_h) if n else (y_note + note_h if note else y_stamp + 0.16)
        bottom = (top_of_stack + 0.14) / h

        fig.tight_layout(rect=(0, bottom, 1, 0.965 if self.title else 1.0))

        # ---- 断言条带：**画在坐标轴外**，绝不挡数据
        if rows:
            all_ok = all(r[3] for r in rows)
            we = max(len(r[1]) for r in rows)
            wi = max(len(r[0]) for r in rows)
            lines = [f"{'PASS' if ok else 'FAIL'}  {i:<{wi}}  {e:<{we}}  ->  {m}"
                     for i, e, m, ok in rows]
            fig.text(
                0.5, y_box / h, "\n".join(lines),
                ha="center", va="bottom", multialignment="left",      # 块居中，行内左对齐
                fontsize=10, family="monospace", color=INK, linespacing=1.55,
                bbox=dict(fc="white", ec=STATUS["pass"] if all_ok else STATUS["fail"],
                          lw=1.6, alpha=1.0, pad=6.0, boxstyle="round,pad=0.55"),
            )

        if note:
            fig.text(0.5, y_note / h, note, ha="center", va="bottom", multialignment="center",
                     fontsize=10.5, color=INK_MUTED, style="italic", linespacing=1.4)

        # ---- SIMULATION 戳。无条件。不可关闭。
        #      仿真结果绝不伪装成实验数据 —— pipeline.md §7。
        fig.text(
            0.995, y_stamp / h - 0.008, f"SIMULATION · {self.stamp}",
            ha="right", va="bottom", fontsize=9.5, color=INK_MUTED,
            fontweight="bold", family="monospace", alpha=0.95,
        )

        self.outdir.mkdir(parents=True, exist_ok=True)
        for ext in ("png", "svg"):
            p = self.outdir / f"{self.fig_id}.{ext}"
            fig.savefig(p, format=ext, bbox_inches=None)
            self.paths[ext] = str(p)
        plt.close(fig)

        print(f"  [figkit] {self.fig_id} -> {self.paths['png']}  (+ .svg, 已盖 SIMULATION 戳)")
        return False
