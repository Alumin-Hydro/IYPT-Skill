#!/usr/bin/env python3
"""★★ magnetic-brake 的判据 × 模型双向表（**回填**：这张表当年没有，被新门打回才补的）。

**教训（electrical-damping r2 逼出来的）**：
  一条判据，只在**正确模型**上跑过 —— 那不叫验证，那叫「换了一把新的失明的锁」。
  必须双向跑：① 正确模型上会不会**误杀**？② 错模型上抓不抓得到？

**这道题的核心预言**（全部零自由参数）：

    v_t = (1024/45) · M g a⁴ / (μ₀² m² σ w)        —— 终速的闭式
    ⟹ v_t ∝ a⁴ （指数 **精确 4**）、∝ 1/w、∝ 1/m²
    ⟹ b/w 与 w 无关（薄壁）；|dΦ/dz| 的峰在 z = ±a/2（点偶极子）

**五个错模型，每一个都是学生真的会写出来的东西：**
"""
import sys

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
MU0 = 4e-7 * np.pi

M_MASS, R_MAG, L_MAG = 5.89e-3, 5e-3, 10e-3
M_DIP, SIGMA, G_ACC = 0.8125, 5.96e7, 9.81
A0, W0 = 6e-3, 1e-3                       # 基准：管内半径 6 mm、壁厚 1 mm


# ══════════════════════════════════════════════ 五个模型 + 正确模型
#   每个模型给出阻尼系数 b(a, w)。终速 v_t = M g / b。
def b_correct(a, w):
    """★ 正确：薄壁 + 点偶极子，b = (45/1024)·μ₀²m²σw/a⁴。"""
    return (45 / 1024) * MU0**2 * M_DIP**2 * SIGMA * w / a**4


def b_naive_A(a, w):
    """naive-A：**忘了 dΦ/dz，用了 Φ 本身** ⟹ 少两阶 a ⟹ b ∝ w/a²。

    **最常见的错**：涡流由 **磁通的变化率** 驱动（dΦ/dt = v·dΦ/dz），不是磁通本身。
    量纲上它甚至能自洽（只要凑一个前因子），所以特别难发现。
    """
    k = (45 / 1024) * MU0**2 * M_DIP**2 * SIGMA / A0**2      # 在基准点标定成一样
    return k * w / a**2


def b_naive_B(a, w):
    """naive-B：**b 与 w 无关**（以为「管壁只是个导体，厚不厚无所谓」）。"""
    return b_correct(a, W0) + 0 * w


def b_bug_C(a, w):
    """bug-C：**前因子错**（45/1024 → 1/16，一个很常见的积分做错）。"""
    return (1 / 16) * MU0**2 * M_DIP**2 * SIGMA * w / a**4


def b_bug_D(a, w):
    """bug-D：**a 的指数错成 3**（球坐标 vs 柱坐标搞混，或积分限漏一维）。"""
    k = (45 / 1024) * MU0**2 * M_DIP**2 * SIGMA / A0**3 * A0**4 / A0
    return k * w / a**3


def b_bug_E(a, w):
    """★ bug-E：**幂次全对，只多了一个与 v 无关的常数摩擦**（磁体蹭到管壁）。

    **最难抓的一个**：所有标度律**全部保持**（b 的 a、w 依赖一字不差），
    可 v_t 不再等于 Mg/b —— 而是 (Mg − f)/b。
    **只有「v_t 的绝对值」那条判据看得见它。**
    """
    return b_correct(a, w)


F_FRICTION = {"★ bug-E 多一个恒定摩擦": 0.15 * M_MASS * G_ACC}   # 15% 的重力

MODELS = {
    "★ 正确": b_correct,
    "naive-A 用了 Φ 而不是 dΦ/dz": b_naive_A,
    "naive-B b 与壁厚 w 无关": b_naive_B,
    "bug-C  前因子 45/1024 → 1/16": b_bug_C,
    "bug-D  a 的指数错成 3": b_bug_D,
    "★ bug-E 多一个恒定摩擦": b_bug_E,
}


def v_t(model_name, a=A0, w=W0):
    b = MODELS[model_name](a, w)
    f = F_FRICTION.get(model_name, 0.0)
    return (M_MASS * G_ACC - f) / b


# ══════════════════════════════════════════════ 判据
V_PRED = (M_MASS * G_ACC) / b_correct(A0, W0)          # 终速的解析预言


# ★★ 容差**必须有来源**（审稿模式 P18 ①）—— 不许是源码里的裸数字。
TOL = {
    "K1": (0.15, "指数是**离散**的：正确模型给 4.000，bug-D（球/柱坐标混）给 3.000。\n"
                 "  半导体级的对数拟合噪声 < 0.01；实验上 a 扫一个十进位、v_t 测到 2% "
                 "⟹ 拟合斜率的误差 ≈ 0.02。\n"
                 "  ⟹ 门槛取 **0.15** —— 远离 1.0 的间隔，也远高于噪声。**离散。**"),
    "K2": (0.15, "同 K1：正确 −1.000，naive-B（b 与 w 无关）给 **0.000**。间隔 1.0，门槛 0.15。"),
    "K3": (0.10, "**绝对值**判据 ⟹ 预言侧的不确定度主导：\n"
                 "  σ（铜的电导率，温度 ±5°C ⟹ ±2%）· m（磁矩，±3%）· a（管内径，±1% "
                 "⟹ v_t ∝ a⁴ ⟹ **±4%**）· w（±3%）\n"
                 "  ⟹ 预言的 1σ ≈ **6%**；加测量 2% ⟹ 门槛 **10%**。\n"
                 "  ★★ **⟹ 这条判据分辨不了 10% 以下的绝对值偏差** —— 见 min_detectable。"),
    "K4": (0.05, "b/w 的离散度：薄壁近似的误差是 O(w/a) = 0.2 ⟹ 在 w ∈ [0.5, 2] mm 上，\n"
                 "  正确模型的 b/w 离散度 ≈ 1%（数值实测）；naive-B 给 **~100%**。\n"
                 "  ⟹ 门槛 **5%** —— 5 倍于正确模型的离散度，20 倍低于 naive-B。"),
}


def crit_exp_a(mn, da=0.0):
    """K1【结构】v_t ∝ a^k，**k 必须精确是 4**。（指数是离散的，不是拟合出来的连续数。）"""
    aa = np.array([4e-3, 5e-3, 6e-3, 7e-3, 8e-3]) + da
    v = np.array([v_t(mn, a=a) for a in aa])
    k = np.polyfit(np.log(aa - da), np.log(v), 1)[0]      # 名义 a（实验读数）
    return abs(k - 4.0) < TOL["K1"][0], f"k = {k:.3f}（预言 4.000）"


def crit_exp_w(mn, da=0.0):
    """K2【结构】v_t ∝ w^p，**p 必须精确是 −1**（薄壁）。"""
    ww = np.array([0.5, 0.7, 1.0, 1.5, 2.0]) * 1e-3
    v = np.array([v_t(mn, a=A0 + da, w=w) for w in ww])
    p = np.polyfit(np.log(ww), np.log(v), 1)[0]
    return abs(p + 1.0) < TOL["K2"][0], f"p = {p:.3f}（预言 −1.000）"


def crit_absolute(mn, da=0.0):
    """★ K3【零自由参数】v_t 的**绝对值**必须等于闭式 (1024/45)·Mga⁴/(μ₀²m²σw)。

    ★ 它是**唯一**能抓到「标度律全对、但多一个恒定摩擦」（bug-E）的那条。
    """
    v = v_t(mn, a=A0 + da)
    return abs(v / V_PRED - 1) < TOL["K3"][0], f"v_t = {v*100:.2f} cm/s（预言 {V_PRED*100:.2f}）"


def crit_bw(mn, da=0.0):
    """K4【结构】b/w 与 w **无关**（薄壁近似的签名）。"""
    ww = np.array([0.5, 1.0, 2.0]) * 1e-3
    r = np.array([MODELS[mn](A0 + da, w) / w for w in ww])
    spread = float(np.ptp(r) / r.mean())
    return spread < TOL["K4"][0], f"b/w 的离散度 = {spread:.1%}"


CRITS = [("K1", "v_t ∝ a⁴【结构】", crit_exp_a),
         ("K2", "v_t ∝ 1/w【结构】", crit_exp_w),
         ("K3", "v_t 的绝对值【零参】", crit_absolute),
         ("K4", "b/w 与 w 无关【结构】", crit_bw)]

print("=" * 104)
print("★★ magnetic-brake · 判据 × 模型双向表")
print("   正确模型这一列必须全 PASS（**不误杀**）；每个错模型必须至少被一条抓到（**不失明**）。")
print("=" * 104)

rows = {(cid, m): fn(m) for cid, _, fn in CRITS for m in MODELS}
print(f"  {'判据':26}" + "".join(f" {m[:13]:>15}" for m in MODELS))
print("  " + "-" * 100)
for cid, name, _ in CRITS:
    print(f"  {cid + ' ' + name:26}"
          + "".join(f" {'✓ PASS' if rows[(cid, m)][0] else '✗ 抓到':>15}" for m in MODELS))

print("\n  ── 判定 ──")
bad = False
for m in MODELS:
    ps = [rows[(c, m)][0] for c, _, _ in CRITS]
    if m.startswith("★ 正确"):
        print(f"  {m:30} 全部 PASS？ {'✓ 是（不误杀）' if all(ps) else '✗✗ 否 —— 误杀了正确模型'}")
        bad |= not all(ps)
    else:
        hit = [c for (c, _, _), p in zip(CRITS, ps) if not p]
        print(f"  {m:30} 被抓到？ {'✓ 是  ← ' + '、'.join(hit) if hit else '✗✗ 否 —— 漏网！'}")
        bad |= not hit

# ═══════════════════════════ ② ★ 「不误杀」扫协议自己承认的系统误差（P18 ④）
#   管内径的加工/测量公差 δa。**b ∝ 1/a⁴ ⟹ v_t ∝ a⁴ ⟹ 这是最敏感的一项。**
print("\n  " + "─" * 100)
print("  ② ★ 「不误杀」扫 **管内径公差 δa** —— v_t ∝ a⁴，这是协议里最敏感的一项系统误差")
print("  " + "─" * 100)
def _correct_survives(da):
    """正确模型在管内径公差 δa 下，判据**没有一条判死它**（不误杀）。"""
    return all(fn("★ 正确", da=da)[0] for _, _, fn in CRITS)


def _delta_star(lo, hi, tol=2e-6):
    """★★ r4-H1（回填 electrical-damping 逼出来的教训）：**二分**找边界，不靠网格撞。

    固定网格会跳过真边界、把 delta_max 报虚（electrical-damping 实测：网格报 0.17 mm，
    二分定出真值 ≈0.134 mm，虚高 30%）。`_eps_star` 早就会二分了，δ 却还在用网格 ——
    **同一个病换个维度**（P18 ④）。返回 (boundary, (last_pass, first_fail))。"""
    if _correct_survives(hi):
        return None, None
    assert _correct_survives(lo), "δa=lo 就误杀正确模型 ⟹ CRIT-FALSEKILL，不是 robustness"
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if _correct_survives(mid):
            lo = mid
        else:
            hi = mid
    return hi, (lo, hi)


DAS = [0.0, 0.02e-3, 0.05e-3, 0.10e-3, 0.15e-3]      # 展示用粗扫（边界从二分取，不从它撞）
print(f"  {'δa [mm]':>9}" + "".join(f"{c:>10}" for c, _, _ in CRITS))
for da in DAS:
    res = [fn("★ 正确", da=da)[0] for _, _, fn in CRITS]
    print(f"  {da*1e3:>9.2f}" + "".join(f"{'✓' if r else '✗✗ 判死':>10}" for r in res))
DA_SCAN_HI = 0.20e-3                                  # ★ r5-H1：扫描上界写进契约（≥3×卡尺 0.02mm）
DA_BUDGET = 0.02e-3                                   # ★ r6-H2：游标卡尺精度 ±0.02 mm
da_max, da_bracket = _delta_star(0.0, DA_SCAN_HI)    # ★ 二分定边界（非网格）
DA_SAFE = 0.10e-3
_da_margin = (da_max / DA_SAFE) if da_max else float("inf")
# ★ r7 审稿 H1（回填）：判死悬崖必须在噪声（游标卡尺）外，否则正确模型被噪声推过悬崖误杀。
bad |= (da_max is not None and da_max < DA_BUDGET)
print(f"\n  ⟹ **判据的有效窗口：δa < {(da_max or 999)*1e3:.4f} mm**（**二分定出**，"
      f"括在 [{da_bracket[0]*1e3:.4f}, {da_bracket[1]*1e3:.4f}] mm）"
      if da_max else "\n  ⟹ 全范围不误杀")
print(f"  ⟹ **协议必须把管内径量到 {DA_SAFE*1e3:.2f} mm 以内**"
      f"（游标卡尺 ±0.02 mm ⟹ 够；安全裕度 {_da_margin:.1f}×）。")

# ═══════════════════════════ ③ ★★ 扫错误幅度 ε，报 ε*（P18 ②）
print("\n  " + "─" * 100)
print("  ③ ★★ 扫**错误幅度** ε，报「**最小可检测幅度** ε*」—— 不是挑一个数说「抓到了」")
print("  " + "─" * 100)


def _eps_star(mk, lo, hi, tol=0.005):
    """二分：最小的能被**任一条**判据抓到的 ε。"""
    if all(fn(*mk(hi))[0] for _, _, fn in CRITS):
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if not all(fn(*mk(mid))[0] for _, _, fn in CRITS):
            hi = mid
        else:
            lo = mid
    return hi


_orig_C, _orig_E = MODELS["bug-C  前因子 45/1024 → 1/16"], F_FRICTION["★ bug-E 多一个恒定摩擦"]


def _mk_C(e):
    MODELS["bug-C  前因子 45/1024 → 1/16"] = lambda a, w: (1 + e) * b_correct(a, w)
    return ("bug-C  前因子 45/1024 → 1/16",)


def _mk_E(e):
    F_FRICTION["★ bug-E 多一个恒定摩擦"] = e * M_MASS * G_ACC
    return ("★ bug-E 多一个恒定摩擦",)


eC = _eps_star(_mk_C, 0.0, 0.5)
MODELS["bug-C  前因子 45/1024 → 1/16"] = _orig_C
eE = _eps_star(_mk_E, 0.0, 0.5)
F_FRICTION["★ bug-E 多一个恒定摩擦"] = _orig_E
print(f"  **bug-C（前因子错 ε）**：ε* = **{eC:.0%}** ——「判据能分辨 b 的 {eC:.0%} 偏差」")
print(f"     ★ 而 K3 的容差就是 10%（预言侧的 σ/m/a/w 不确定度）—— **ε\\* 就是那个数。**")
print(f"     **⟹ 想抓更小的偏差，只能先把 σ、m、a 量得更准 —— 判据本身已经到头了。**")
print(f"  **bug-E（恒定摩擦 ε·Mg）**：ε* = **{eE:.0%}**（真实的 bug-E 设的是 15%）")

print("\n  ── 明细 ──")
for cid, name, _ in CRITS:
    print(f"\n  【{cid} {name}】  容差 {TOL[cid][0]}")
    for m in MODELS:
        ok, dt = rows[(cid, m)]
        print(f"    {'✓' if ok else '✗'} {m:30} {dt}")

WHY = {
    "naive-A 用了 Φ 而不是 dΦ/dz":
        "**本题的头号陷阱**：涡流由**磁通的变化率**驱动（dΦ/dt = v·dΦ/dz），不是磁通本身。"
        "量纲上它甚至能自洽（只要凑一个前因子）—— **所以只有「a 的指数」抓得到它。**",
    "naive-B b 与壁厚 w 无关":
        "「管壁只是个导体，厚不厚无所谓」—— 直觉上很自然，而且薄壁时 b 确实近似 ∝ w，"
        "**一个只在基准点标定过的模型，看不出区别。**",
    "bug-C  前因子 45/1024 → 1/16":
        "**最容易犯的实现 bug**：那个 45/1024 是一个不平凡的积分结果，很容易做错。"
        "**所有标度律都对，只有绝对值错。**",
    "bug-D  a 的指数错成 3":
        "球坐标 vs 柱坐标搞混，或者积分漏了一维。**指数错 1 —— 而指数是这道题的招牌。**",
    "★ bug-E 多一个恒定摩擦":
        "**最难抓的一个**：磁体蹭到管壁 ⟹ 多一个与 v 无关的摩擦力 f。"
        "**所有标度律一字不差地保持**（b 的 a、w 依赖全对），只有 v_t 的**绝对值**偏了 15%。"
        "**⇒ 只有 K3（绝对值）看得见它。而没有 bug-E，K3 就会显得多余。**",
}

import hashlib
import json
from pathlib import Path

out = {
    "generated_by": "01-criteria/criterion_matrix.py",
    "purpose": "★★★ 判据 × 模型的**双向**表 + P18 的三个新维度。\n"
               "只跑「正确模型」那一列 = 换了一把新的失明的锁。\n"
               "**而只跑布尔值，那张表可以被调到全绿（审稿模式 P18）。**",
    "robustness_scan": {
        "parameter": "δa = 管内径的加工/测量公差 [m]",
        "why": "★ **「不误杀」必须在协议自己承认的系统误差上跑过**（P18 ④）。\n"
               "**v_t ∝ a⁴ ⟹ 管内径是最敏感的一项**：a 偏 1% ⟹ v_t 偏 4%。\n"
               "★★ r4-H1（回填）：边界**必须二分定出**，不能靠网格撞（网格会把 delta_max 报虚）。\n"
               "★★ r5-H1（回填）：必须报 `scan_upper_bound` —— 否则 delta_max=None 与「没扫够远」不可区分。",
        "scan_upper_bound": round(float(DA_SCAN_HI), 7),
        "systematic_error_budget": round(float(DA_BUDGET), 7),
        "delta_max": None if da_max is None else round(float(da_max), 7),
        "delta_max_bracket": (None if da_bracket is None else
                              [round(float(da_bracket[0]), 7),
                               round(float(da_bracket[1]), 7)]),
        "verdict": (f"判据的有效窗口：**δa < {da_max*1e3:.3f} mm**（**二分定出**，"
                    f"括在 [{da_bracket[0]*1e3:.3f}, {da_bracket[1]*1e3:.3f}] mm）。"
                    f"协议必须把管内径量到 **{DA_SAFE*1e3:.2f} mm** 以内"
                    f"（游标卡尺 ±0.02 mm ⟹ 够，裕度 {_da_margin:.1f}×）。"
                    if da_max else "在 δa ≤ 0.20 mm 的全范围内都不误杀"),
    },
    "min_detectable": {
        "why": "★★ 一个错模型「被抓到了 ✓」**没有信息量 —— 因为幅度是作者挑的**（P18 ②）。\n"
               "**扫 ε，报「最小可检测幅度」ε\\*** —— 那才是判据集的分辨率。",
        "bug-C_prefactor": {
            "eps_star": round(float(eC), 4),
            "caught_by": ["K3"],
            "note": f"「判据能分辨 b 的 **{eC:.0%}** 偏差」。\n"
                    "★ 而 K3 的容差就是 10%（预言侧的 σ/m/a/w 不确定度）—— **ε\\* 就是那个数**。\n"
                    "**⟹ 想抓更小的偏差，只能先把 σ、m、a 量得更准。判据本身已经到头了。**",
        },
        "bug-E_friction": {
            "eps_star": round(float(eE), 4),
            "caught_by": ["K3"],
            "note": f"真实的 bug-E 设的是 **15%** 的恒定摩擦 —— ε\\* = **{eE:.0%}**。",
        },
    },
    "wrong_models": [
        {"id": m, "statement": m.split(maxsplit=1)[-1], "why_a_student_writes_it": WHY[m]}
        for m in MODELS if not m.startswith("★ 正确")],
    "criteria": [
        {"id": cid, "statement": f"{cid} {name}",
         "tolerance": TOL[cid][0],
         "tolerance_source": TOL[cid][1],
         "passes_correct": bool(rows[(cid, "★ 正确")][0]),
         "correct_model_detail": rows[(cid, "★ 正确")][1],
         "catches": [{"id": m, "detail": rows[(cid, m)][1]} for m in MODELS
                     if not m.startswith("★ 正确") and not rows[(cid, m)][0]]}
        for cid, name, _ in CRITS],
    "verdict": "FAIL" if bad else "PASS",
    # ★ r7 审稿 H2（回填）：源码 sha256 戳 —— DESYNC 门重算比对，抓「改源码忘重跑」。
    #   规范化行尾（\r\n→\n）后再哈希，免得跨平台 checkout 误报。
    "source_sha256": hashlib.sha256(
        Path(__file__).read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest(),
}
Path(__file__).with_name("matrix.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("\n  → 写入 01-criteria/matrix.json")

print("\n" + "=" * 104)
print("✗✗ 有判据失明或误杀 —— **不许交付**" if bad else "✓✓ 四条判据全部双向成立")
print("=" * 104)
sys.exit(1 if bad else 0)
