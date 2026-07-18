#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★★ fractal-fingers 的判据 × 模型双向表。

**教训（继承自 electrical-damping r2）**：
  一条判据，只在**正确模型**上跑过 —— 那不叫验证，那叫「换了一把新的失明的锁」。
  必须双向跑：① 正确模型上会不会**误杀**？② 错模型上抓不抓得到？

**这道题的核心零自由参数预言**（Saffman–Taylor 线性稳定性，见 01-analysis.md §6）：

    σ(k) = k·[U(μ2−μ1) − γk²h²/12] / (μ1+μ2)                    —— 色散关系
    ⟹ 最快波长 λ* = π·h·sqrt(γ / (U(μ2−μ1)))                     —— 指宽选择
    ⟹ λ*/h ∝ Ca^(−1/2)，Ca = μ2 U/γ                             —— **指数 −1/2，离散**
    ⟹ λ_c/λ* = 1/sqrt(3)（临界波长 vs 最快波长）

**四个错模型，每一个都是学生真的会写出来的东西：**（见每个函数的 docstring）
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

# ── 基准参数（见 00-problem.md 设定书 S-n / 01-analysis.md §1）
H = 3.0e-4        # 漆膜厚度 [m]
MU1 = 1.5e-3      # 醇-墨（入侵相）黏度 [Pa·s]
MU2 = 0.10        # 稀释丙烯漆（防守相）黏度 [Pa·s]
GAMMA = 5.0e-3    # 醇墨/漆界面张力 [N/m]
U0 = 1.0e-2       # 铺展前沿速度 [m/s]
R0 = 3.0e-3       # 液滴半径 [m]


# ══════════════════════════════════════════════ 正确模型 + 四个错模型
#   每个模型给出「选出的指宽」λ*(U, μ1, μ2, γ, h)，以及「界面失稳与否」的判据。
def lam_correct(U=U0, mu1=MU1, mu2=MU2, gamma=GAMMA, h=H):
    """★ 正确：Saffman–Taylor 最快增长波长 λ* = π·h·sqrt(γ/(U(μ2−μ1)))。"""
    return np.pi * h * np.sqrt(gamma / (U * (mu2 - mu1)))


def _lam_ref():
    return lam_correct()


def lam_naive_A(U=U0, mu1=MU1, mu2=MU2, gamma=GAMMA, h=H):
    """naive-A：**指宽只由膜厚定，λ* ∝ h，与 Ca 无关**（只做「唯一长度是 h」的量纲分析）。

    **本题头号直觉陷阱**：学生数一遍长度尺度，只看见膜厚 h，于是 λ*~h。
    在基准点标定成和正确模型一样 ⟹ **只有「λ* 对 Ca 的指数」抓得到它。**
    """
    return (_lam_ref() / H) * h            # = const（不含 U/γ/μ）


def lam_naive_B(U=U0, mu1=MU1, mu2=MU2, gamma=GAMMA, h=H):
    """naive-B：**把毛细压强 γ/λ 直接和黏性驱动压强平衡，得 λ* ∝ Ca^(−1)**（指数 −1）。

    学生写 γ/λ ~ μ2·U/h ⟹ λ ~ γh/(μ2 U) = h/Ca —— 一个**看似合理**的量纲平衡，
    但它漏了失稳增长率里 k 的正确幂次（表面张力进的是 k³ 不是 k）。指数错成 −1。
    在基准点标定成一样 ⟹ 只有指数抓得到。
    """
    Ca = mu2 * U / gamma
    Ca0 = MU2 * U0 / GAMMA
    return _lam_ref() * (Ca0 / Ca) * (h / H)     # ∝ h·Ca^(−1)，基准点对齐


def lam_onset_C(U=U0, mu1=MU1, mu2=MU2, gamma=GAMMA, h=H):
    """★ onset-C（试金石：形状全对，只差一个常数）：**用临界波长 λ_c 当指宽，而不是最快波长 λ***。

    σ(k)=0 的临界波长 λ_c = λ*/sqrt(3)（k_c=sqrt(3)·k*）。学生把「失稳一开始出现的波长」
    错当成「实际长出来的指宽」，混淆了 onset 与 fastest-growing。
    **所有标度律一字不差**（λ_c ∝ h·Ca^(−1/2)，指数 −1/2 完全相同），
    **只有绝对值偏了 factor 1/sqrt(3) ≈ 0.577** ⟹ **只有「绝对值」那条判据看得见它。
    没有它，那条判据会显得多余。**
    """
    return lam_correct(U, mu1, mu2, gamma, h) / np.sqrt(3.0)


def lam_sign_D(U=U0, mu1=MU1, mu2=MU2, gamma=GAMMA, h=H):
    """sign-D：λ* 的大小和指数全对，但**丢了失稳的符号条件**（见 unstable_*）。"""
    return lam_correct(U, mu1, mu2, gamma, h)


# 「界面失稳与否」：Saffman–Taylor 要求**低黏驱替高黏**（μ2>μ1）才有增长模。
def unstable_correct(mu1, mu2):
    return mu2 > mu1


def unstable_sign_D(mu1, mu2):
    """sign-D：**忘了 (μ2−μ1) 的符号**，以为任何黏度反差都会长指（用了 |μ2−μ1|）。

    学生只记得「有黏度差就 fingering」，漏了「必须是低黏推高黏」。
    ⟹ 它会在**稳定**的构型（高黏推低黏）里谎报 fingering。
    """
    return mu1 != mu2


LAM = {
    "★ 正确": lam_correct,
    "naive-A 指宽只由膜厚定": lam_naive_A,
    "naive-B 毛细平衡给 Ca^-1": lam_naive_B,
    "★ onset-C 用临界波长而非最快波长": lam_onset_C,
    "sign-D 丢了失稳符号条件": lam_sign_D,
}
UNSTABLE = {
    "★ 正确": unstable_correct,
    "naive-A 指宽只由膜厚定": unstable_correct,
    "naive-B 毛细平衡给 Ca^-1": unstable_correct,
    "★ onset-C 用临界波长而非最快波长": unstable_correct,
    "sign-D 丢了失稳符号条件": unstable_sign_D,
}

# ══════════════════════════════════════════════ 判据（容差必须有来源，P18 ①）
TOL = {
    "K1": (0.15,
           "指数是**离散**的：正确给 −0.500，naive-A（只由 h 定）给 0.000，"
           "naive-B（毛细平衡）给 −1.000 —— 相邻间隔 ≥ 0.5。\n"
           "  实验：Ca 扫一个十进位、λ* 由 FFT 峰位测到 ~5% ⟹ 对数拟合斜率误差 ≈ 0.03。\n"
           "  ⟹ 门槛 0.15 —— 远离 0.5 的间隔、也远高于噪声。**离散。**"),
    "K2": (0.20,
           "**绝对值/零自由参数**判据 ⟹ 预言侧不确定度主导：\n"
           "  λ* ∝ h·(γ/(U·μ2))^(1/2) ⟹ δλ*/λ* = δh/h + ½(δγ/γ + δU/U + δμ2/μ2)。\n"
           "  h(膜厚 ±10%) · γ(界面张力 ±15%) · U(前沿速度 ±10%) · μ2(漆黏度 ±10%)\n"
           "  ⟹ 1σ ≈ 10% + ½·(15+10+10)% ≈ **17%** ⟹ 门槛 **20%**。\n"
           "  ★★ **⟹ 这条判据分辨不了 20% 以下的绝对值偏差** —— 见 min_detectable。"),
    "K3": (None,
           "**结构性布尔判据**（失稳符号），无数值容差：\n"
           "  Saffman–Taylor 要求 μ2>μ1 才有增长模。在**反转反差**（μ2<μ1）下，\n"
           "  正确模型必须预言 σ_max ≤ 0（**不长指**）。这是离散的是/否，不需要门槛。"),
}


def crit_K1_exp_Ca(model, dgamma=0.0):
    """K1【结构】λ* ∝ Ca^p，**p 必须精确是 −1/2**（Ca 由扫 U 得到）。

    dgamma：预言侧 γ 的系统偏差（robustness 用）—— 常数缩放不改指数，K1 对它免疫。
    """
    UU = np.array([3e-3, 5e-3, 1e-2, 2e-2, 4e-2])
    Ca = MU2 * UU / GAMMA
    lam = np.array([LAM[model](U=U, gamma=GAMMA * (1 + dgamma)) for U in UU])
    p = np.polyfit(np.log(Ca), np.log(lam), 1)[0]
    return abs(p + 0.5) < TOL["K1"][0], f"p = {p:.3f}（预言 −0.500）"


def crit_K2_absolute(model, dgamma=0.0):
    """★ K2【零自由参数】λ* 的**绝对值**必须等于 π·h·sqrt(γ/(U(μ2−μ1)))。

    ★ **唯一**能抓到 onset-C（形状全对、只差 1/sqrt(3)）的那条。
    dgamma：预言侧用了偏差 γ ⟹ 预言 λ* ∝ sqrt(1+dgamma)，实测用真 γ ⟹ 比值 sqrt(1+dgamma)。
    """
    lam_pred = LAM[model](gamma=GAMMA * (1 + dgamma))
    lam_true = _lam_ref()
    return abs(lam_pred / lam_true - 1) < TOL["K2"][0], \
        f"λ* = {lam_pred*1e3:.3f} mm（预言 {lam_true*1e3:.3f}）"


def crit_K3_stability(model, dgamma=0.0):
    """K3【结构】反转黏度反差（μ2<μ1，高黏推低黏）时，模型必须预言**不长指**。"""
    stable_ok = not UNSTABLE[model](MU2, MU1)      # 传入 (mu1=MU2, mu2=MU1) —— 反转
    return stable_ok, ("反转反差下：稳定（不长指）✓" if stable_ok
                       else "反转反差下：**谎报 fingering** ✗")


CRITS = [("K1", "λ* ∝ Ca^(−1/2)【结构】", crit_K1_exp_Ca),
         ("K2", "λ* 的绝对值【零参】", crit_K2_absolute),
         ("K3", "失稳需 μ2>μ1【结构】", crit_K3_stability)]

# ── 打印双向表
LAM_B = _lam_ref()
K_STAR = 2.0 * np.sqrt(U0 * (MU2 - MU1) / (GAMMA * H**2))
N_FING = 2 * np.pi * R0 / LAM_B
CA0 = MU2 * U0 / GAMMA
print("=" * 104)
print("★★ fractal-fingers · 判据 × 模型双向表")
print("   正确模型这一列必须全 PASS（**不误杀**）；每个错模型必须至少被一条抓到（**不失明**）。")
print("=" * 104)
print(f"  基准：λ* = {LAM_B*1e3:.4f} mm，k* = {K_STAR:.2f} /m，"
      f"指数 N ≈ 2πR/λ* = {N_FING:.3f}，Ca = {CA0:.4f}")
print("  " + "-" * 100)

rows = {(cid, m): fn(m) for cid, _, fn in CRITS for m in LAM}
print(f"  {'判据':30}" + "".join(f" {m[:15]:>17}" for m in LAM))
print("  " + "-" * 100)
for cid, name, _ in CRITS:
    print(f"  {cid + ' ' + name:30}"
          + "".join(f" {'✓ PASS' if rows[(cid, m)][0] else '✗ 抓到':>17}" for m in LAM))

print("\n  ── 判定 ──")
bad = False
for m in LAM:
    ps = [rows[(c, m)][0] for c, _, _ in CRITS]
    if m.startswith("★ 正确"):
        print(f"  {m:34} 全部 PASS？ {'✓ 是（不误杀）' if all(ps) else '✗✗ 否 —— 误杀了正确模型'}")
        bad |= not all(ps)
    else:
        hit = [c for (c, _, _), p in zip(CRITS, ps) if not p]
        print(f"  {m:34} 被抓到？ {'✓ 是  ← ' + '、'.join(hit) if hit else '✗✗ 否 —— 漏网！'}")
        bad |= not hit

# ═══════════════════════════ ② ★ 「不误杀」扫协议自己承认的系统误差（P18 ④）
#   界面张力 γ 是**最不确定**的输入（这对醇墨/稀漆没有表值，且随醇蒸发而变）。
#   λ* ∝ γ^(1/2) ⟹ γ 的系统偏差会经 K2（绝对值）误杀正确模型。
print("\n  " + "─" * 100)
print("  ② ★ 「不误杀」扫 **界面张力 γ 的系统偏差 δγ/γ** —— 它是协议里最不确定的一项输入")
print("  " + "─" * 100)


def _correct_survives(dg):
    """正确模型在 γ 系统偏差 dg 下，判据**没有一条判死它**（不误杀）。"""
    return all(fn("★ 正确", dgamma=dg)[0] for _, _, fn in CRITS)


def _delta_star(lo, hi, tol=1e-4):
    """★★ 二分找边界（r4-H1：不能靠网格撞）。返回 (boundary, (last_pass, first_fail))。"""
    if _correct_survives(hi):
        return None, None
    assert _correct_survives(lo), "δγ=lo 就误杀 ⟹ CRIT-FALSEKILL，不是 robustness"
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if _correct_survives(mid):
            lo = mid
        else:
            hi = mid
    return hi, (lo, hi)


DGS = [0.0, 0.10, 0.20, 0.30, 0.40, 0.50]
print(f"  {'δγ/γ':>8}" + "".join(f"{c:>10}" for c, _, _ in CRITS))
for dg in DGS:
    res = [fn("★ 正确", dgamma=dg)[0] for _, _, fn in CRITS]
    print(f"  {dg:>8.2f}" + "".join(f"{'✓' if r else '✗✗ 判死':>10}" for r in res))

DG_SCAN_HI = 1.00     # ★ 扫描上界（≥ 3×budget）
DG_BUDGET = 0.30      # ★ γ 的实际不确定度（悬滴法测醇墨/稀漆对，且随蒸发漂移）±30%
dg_max, dg_bracket = _delta_star(0.0, DG_SCAN_HI)
_dg_margin = (dg_max / DG_BUDGET) if dg_max else float("inf")
# ★ r7-H1：判死悬崖必须在噪声（γ 不确定度）外，否则正确模型被噪声推过悬崖误杀。
bad |= (dg_max is not None and dg_max < DG_BUDGET)
print(f"\n  ⟹ **判据的有效窗口：δγ/γ < {(dg_max or 999)*100:.2f}%**（**二分定出**，"
      f"括在 [{dg_bracket[0]*100:.2f}, {dg_bracket[1]*100:.2f}]%）" if dg_max
      else "\n  ⟹ 全范围不误杀")
print(f"  ⟹ **协议必须独立测 γ 到 ±{DG_BUDGET*100:.0f}% 以内**"
      f"（悬滴法直接测醇墨/稀漆对；安全裕度 {_dg_margin:.2f}×）。")

# ═══════════════════════════ ③ ★★ 扫错误幅度 ε，报 ε*（P18 ②）
print("\n  " + "─" * 100)
print("  ③ ★★ 扫**常数偏置** ε（λ*→(1+ε)λ*），报「**最小可检测幅度** ε*」")
print("  " + "─" * 100)


def _eps_star(lo, hi, tol=0.002):
    """二分：最小的能被**任一条**判据抓到的常数偏置 ε。只有 K2（绝对值）看得见常数偏置。"""
    def off_survives(e):
        lam_pred = (1 + e) * _lam_ref()
        return abs(lam_pred / _lam_ref() - 1) < TOL["K2"][0]
    if off_survives(hi):
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if off_survives(mid):
            lo = mid
        else:
            hi = mid
    return hi


eps = _eps_star(0.0, 1.0)
onset_offset = 1.0 / np.sqrt(3.0) - 1.0     # onset-C 的偏置：−42.3%
print(f"  **常数偏置**：ε* = **{eps:.0%}** ——「判据能分辨指宽 {eps:.0%} 的绝对偏差」")
print(f"     ★ 而 K2 的容差就是 20%（预言侧 h/γ/U/μ2 不确定度）—— **ε* 就是那个数。**")
print(f"     **⟹ 想抓更小的偏差，只能先把 h、γ、U 量得更准 —— 判据本身已经到头了。**")
print(f"  **onset-C 的偏置** = 1/√3 − 1 = **{onset_offset:.1%}** > ε* ⟹ 被 K2 抓到 ✓")

print("\n  ── 明细 ──")
for cid, name, _ in CRITS:
    print(f"\n  【{cid} {name}】  容差 {TOL[cid][0]}")
    for m in LAM:
        ok, dt = rows[(cid, m)]
        print(f"    {'✓' if ok else '✗'} {m:34} {dt}")

WHY = {
    "naive-A 指宽只由膜厚定":
        "**本题头号直觉陷阱**：数一遍长度尺度，只看见膜厚 h ⟹ λ*~h。"
        "在基准点标定成和正确模型一样，**只有「λ* 对 Ca 的指数」抓得到它。**",
    "naive-B 毛细平衡给 Ca^-1":
        "把毛细压强 γ/λ 直接和黏性驱动压强 μ2·U/h 平衡 ⟹ λ ~ γh/(μ2 U) = h/Ca。"
        "**一个看似合理的量纲平衡**，但漏了增长率里表面张力进的是 k³ 而非 k ⟹ 指数错成 −1。",
    "★ onset-C 用临界波长而非最快波长":
        "**最难抓的一个**：把 σ(k)=0 的临界波长 λ_c 错当成实际指宽，混淆 onset 与 fastest-growing。"
        "**所有标度律一字不差**（λ_c ∝ h·Ca^(−1/2)，指数完全相同），只有绝对值偏了 1/√3。"
        "**⇒ 只有 K2（绝对值）看得见它。没有它，K2 就会显得多余。**",
    "sign-D 丢了失稳符号条件":
        "只记得「有黏度差就 fingering」，漏了「必须是**低黏推高黏**（μ2>μ1）」。"
        "⟹ 它会在稳定构型（高黏推低黏）里**谎报 fingering**。只有 K3（符号）看得见它。",
}

out = {
    "generated_by": "01-criteria/criterion_matrix.py",
    "purpose": "★★★ 判据 × 模型的**双向**表 + P18 的三个新维度。\n"
               "只跑「正确模型」那一列 = 换了一把新的失明的锁。\n"
               "**而只跑布尔值，那张表可以被调到全绿（审稿模式 P18）。**",
    "robustness_scan": {
        "parameter": "δγ/γ = 界面张力 γ 的系统相对偏差 [1]",
        "why": "★ **「不误杀」必须在协议自己承认的系统误差上跑过**（P18 ④）。\n"
               "**γ 是最不确定的输入**：醇墨/稀漆对没有表值，且随醇蒸发而漂移。\n"
               "λ* ∝ γ^(1/2) ⟹ γ 的系统偏差经 K2（绝对值）误杀正确模型。\n"
               "★★ r4-H1：边界**必须二分定出**，不能靠网格撞。\n"
               "★★ r5-H1：必须报 `scan_upper_bound` —— 否则 delta_max=None 与「没扫够远」不可区分。",
        "scan_upper_bound": round(float(DG_SCAN_HI), 6),
        "systematic_error_budget": round(float(DG_BUDGET), 6),
        "delta_max": None if dg_max is None else round(float(dg_max), 6),
        "delta_max_bracket": (None if dg_bracket is None else
                              [round(float(dg_bracket[0]), 6),
                               round(float(dg_bracket[1]), 6)]),
        "verdict": (f"判据的有效窗口：**δγ/γ < {dg_max*100:.2f}%**（**二分定出**，"
                    f"括在 [{dg_bracket[0]*100:.2f}, {dg_bracket[1]*100:.2f}]%）。"
                    f"协议必须独立测 γ 到 **±{DG_BUDGET*100:.0f}%** 以内"
                    f"（悬滴法测醇墨/稀漆对；安全裕度 {_dg_margin:.2f}×）。"
                    if dg_max else "在 δγ/γ ≤ 1.0 的全范围内都不误杀"),
    },
    "min_detectable": {
        "why": "★★ 一个错模型「被抓到了 ✓」**没有信息量 —— 因为幅度是作者挑的**（P18 ②）。\n"
               "**扫常数偏置 ε，报「最小可检测幅度」ε\\*** —— 那才是判据集的分辨率。",
        "constant_offset": {
            "eps_star": round(float(eps), 4),
            "caught_by": ["K2"],
            "note": f"「判据能分辨指宽 **{eps:.0%}** 的绝对偏差」。\n"
                    "★ 而 K2 的容差就是 20%（预言侧 h/γ/U/μ2 不确定度）—— **ε\\* 就是那个数**。\n"
                    "**⟹ 想抓更小的偏差，只能先把 h、γ、U 量得更准。判据本身已经到头了。**\n"
                    f"onset-C 的偏置 = 1/√3 − 1 = {onset_offset*100:.1f}% > ε\\* ⟹ 被 K2 抓到。",
        },
    },
    "wrong_models": [
        {"id": m, "statement": m.split(maxsplit=1)[-1], "why_a_student_writes_it": WHY[m]}
        for m in LAM if not m.startswith("★ 正确")],
    "criteria": [
        {"id": cid, "statement": f"{cid} {name}",
         "tolerance": TOL[cid][0],
         "tolerance_source": TOL[cid][1],
         "passes_correct": bool(rows[(cid, "★ 正确")][0]),
         "correct_model_detail": rows[(cid, "★ 正确")][1],
         "catches": [{"id": m, "detail": rows[(cid, m)][1]} for m in LAM
                     if not m.startswith("★ 正确") and not rows[(cid, m)][0]]}
        for cid, name, _ in CRITS],
    "verdict": "FAIL" if bad else "PASS",
    # ★ r7-H2：源码 sha256 戳 —— DESYNC 门重算比对，抓「改源码忘重跑」。
    "source_sha256": hashlib.sha256(
        Path(__file__).read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest(),
}
Path(__file__).with_name("matrix.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("\n  → 写入 01-criteria/matrix.json")

print("\n" + "=" * 104)
print("✗✗ 有判据失明或误杀 —— **不许交付**" if bad else "✓✓ 三条判据全部双向成立")
print("=" * 104)
sys.exit(1 if bad else 0)
