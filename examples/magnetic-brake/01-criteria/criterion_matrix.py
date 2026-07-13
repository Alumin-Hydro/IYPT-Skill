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


def crit_exp_a(mn):
    """K1【结构】v_t ∝ a^k，**k 必须精确是 4**。（指数是离散的，不是拟合出来的连续数。）"""
    aa = np.array([4e-3, 5e-3, 6e-3, 7e-3, 8e-3])
    v = np.array([v_t(mn, a=a) for a in aa])
    k = np.polyfit(np.log(aa), np.log(v), 1)[0]
    return abs(k - 4.0) < 0.15, f"k = {k:.3f}（预言 4.000）"


def crit_exp_w(mn):
    """K2【结构】v_t ∝ w^p，**p 必须精确是 −1**（薄壁）。"""
    ww = np.array([0.5, 0.7, 1.0, 1.5, 2.0]) * 1e-3
    v = np.array([v_t(mn, w=w) for w in ww])
    p = np.polyfit(np.log(ww), np.log(v), 1)[0]
    return abs(p + 1.0) < 0.15, f"p = {p:.3f}（预言 −1.000）"


def crit_absolute(mn):
    """★ K3【零自由参数】v_t 的**绝对值**必须等于闭式 (1024/45)·Mga⁴/(μ₀²m²σw)。

    ★ 它是**唯一**能抓到「标度律全对、但多一个恒定摩擦」（bug-E）的那条。
    """
    v = v_t(mn)
    return abs(v / V_PRED - 1) < 0.10, f"v_t = {v*100:.2f} cm/s（预言 {V_PRED*100:.2f}）"


def crit_bw(mn):
    """K4【结构】b/w 与 w **无关**（薄壁近似的签名）。"""
    ww = np.array([0.5, 1.0, 2.0]) * 1e-3
    r = np.array([MODELS[mn](A0, w) / w for w in ww])
    spread = float(np.ptp(r) / r.mean())
    return spread < 0.05, f"b/w 的离散度 = {spread:.1%}"


CRITS = [("K1 v_t ∝ a⁴【结构】", crit_exp_a),
         ("K2 v_t ∝ 1/w【结构】", crit_exp_w),
         ("K3 v_t 的绝对值【零参】", crit_absolute),
         ("K4 b/w 与 w 无关【结构】", crit_bw)]

print("=" * 104)
print("★★ magnetic-brake · 判据 × 模型双向表")
print("   正确模型这一列必须全 PASS（**不误杀**）；每个错模型必须至少被一条抓到（**不失明**）。")
print("=" * 104)

rows = {c: {m: f(m) for m in MODELS} for c, f in CRITS}
print(f"  {'判据':26}" + "".join(f" {m[:13]:>15}" for m in MODELS))
print("  " + "-" * 100)
for c, _ in CRITS:
    print(f"  {c:26}" + "".join(f" {'✓ PASS' if rows[c][m][0] else '✗ FAIL':>15}" for m in MODELS))

print("\n  ── 判定 ──")
bad = False
for m in MODELS:
    ps = [rows[c][m][0] for c, _ in CRITS]
    if m.startswith("★ 正确"):
        print(f"  {m:30} 全部 PASS？ {'✓ 是（不误杀）' if all(ps) else '✗✗ 否 —— 误杀了正确模型'}")
        bad |= not all(ps)
    else:
        hit = [c.split()[0] for (c, _), p in zip(CRITS, ps) if not p]
        print(f"  {m:30} 被抓到？ {'✓ 是  ← ' + '、'.join(hit) if hit else '✗✗ 否 —— 漏网！'}")
        bad |= not hit

print("\n  ── 明细 ──")
for c, _ in CRITS:
    print(f"\n  【{c}】")
    for m in MODELS:
        ok, dt = rows[c][m]
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

import json
from pathlib import Path

out = {
    "generated_by": "01-criteria/criterion_matrix.py",
    "purpose": "★★ 判据 × 模型的**双向**表。只跑「正确模型」那一列 = 换了一把新的失明的锁。",
    "wrong_models": [
        {"id": m, "statement": m.split(maxsplit=1)[-1], "why_a_student_writes_it": WHY[m]}
        for m in MODELS if not m.startswith("★ 正确")],
    "criteria": [
        {"id": c.split()[0], "statement": c,
         "passes_correct": bool(rows[c]["★ 正确"][0]),
         "correct_model_detail": rows[c]["★ 正确"][1],
         "catches": [m for m in MODELS
                     if not m.startswith("★ 正确") and not rows[c][m][0]]}
        for c, _ in CRITS],
    "verdict": "FAIL" if bad else "PASS",
}
Path(__file__).with_name("matrix.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("\n  → 写入 01-criteria/matrix.json")

print("\n" + "=" * 104)
print("✗✗ 有判据失明或误杀 —— **不许交付**" if bad else "✓✓ 四条判据全部双向成立")
print("=" * 104)
sys.exit(1 if bad else 0)
