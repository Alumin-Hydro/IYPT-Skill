#!/usr/bin/env python3
"""验证阶梯：Gate 0（极限对拍）、Gate 1（收敛）、Gate 2（分层对拍）、Gate 3（解析对拍）。

**Gate 0 先跑。跑不过，后面一律不许走。**

它是纯数学恒等式，与物理对错无关 —— 即使整个物理模型都错了，(15) 在那个极限下
**仍然**必须回到 (10)，因为这是同一个积分在两种参数下的值。

于是：Gate 0 不过 -> 一定是代码错。Gate 0 过了 -> 代码被证明是对的，此后任何不符
都指向物理。**没有 Gate 0，后面每一个不符都是糊涂账。**
"""
from __future__ import annotations

import sys

import numpy as np

from params import (MU0, G, R_MAG, L_MAG, A_TUBE, W_WALL, SIGMA, M_DIP, M_MASS, MS,
                    TARGET, SWEEP, banner)

SPEC_SWEEP_A = SWEEP["a"]      # 扫描端点检查用它 —— 从契约读，不硬编码
from model0 import b_model0, vt_model0, tau_model0, distance_to_fraction
from model2 import damping

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass


# ================================================================== Gate 0

#: model-spec 的 numerical_notes 逐字（r3；写进 results.json 的 gates[].recipe）
#  r1 的配方是错的（只令 L→0，会收敛到 3.5505 而非 1）—— SPEC-DEFECT SD-1，已在 r2 修正。
GATE0_RECIPE_SPEC = (
    "关键对拍：令 R→0 且 L→0（整个磁体等比缩小：R→εR, L→εL, M_s→M_s/ε³，"
    "使 m = M_s·πR²L 固定，ε→0），同时令 w→0，(15) 必须回到 (10)，误差 <0.1%。"
)

GATE0_TOL = 1e-3        # 0.1%，直接来自 numerical_notes 原文


def gate0(eps_list=(1.0, 0.3, 0.1, 0.03, 0.01), *, verbose=True) -> dict:
    """Gate 0：极限对拍。

    **配方按 SD-1 修正**：R 和 L 必须**一起**趋于 0。

    照 spec 字面执行（只令 L→0，R 保持 5mm）会收敛到一个稳定的**非 1** 值 —— 那是
    "极限存在，但取错了极限"的指纹。原因：只让 L→0 而 R=5mm，得到的是一个半径 5mm
    的**薄圆盘**，在 r=a=6mm 处椭圆积分模数 k^2 = 4Ra/(R+a)^2 = 0.99，离远场十万八千里。
    点偶极子极限要求**整个磁体**相对 a 缩小。

    这个论证**不引用任何仿真结果**（纯几何），所以它是合法的 SPEC-DEFECT。
    """
    w_thin = W_WALL * 1e-4          # w -> 0
    b0 = b_model0(M_DIP, A_TUBE, w_thin, SIGMA)

    rows = []
    for eps in eps_list:
        R, L = R_MAG * eps, L_MAG * eps
        Ms = M_DIP / (np.pi * R ** 2 * L)          # m 固定 => Ms ~ 1/eps^3
        b2 = damping(R, L, Ms, A_TUBE, w_thin, SIGMA)
        ratio = b2 / b0
        rows.append(dict(eps=eps, R_mm=R * 1e3, L_mm=L * 1e3,
                         b2=b2, ratio=ratio, err=abs(ratio - 1.0)))

    best = min(rows, key=lambda r: r["err"])
    passed = best["err"] < GATE0_TOL
    # 误差必须单调趋于 0 —— 只取一个点分不清"通过了"和"碰巧"
    errs = [r["err"] for r in rows]
    monotone = all(errs[i] >= errs[i + 1] * 0.999 for i in range(len(errs) - 1))

    if verbose:
        print("=" * 74)
        print("Gate 0 · 极限对拍   (R, L -> 0 同时缩小，m 固定；w -> 0)")
        print("  ** 配方按 SD-1 修正：spec 原文只写了 L->0，那会收敛到 3.55 而不是 1 **")
        print()
        print(f"  {'eps':>7} {'R (mm)':>9} {'L (mm)':>9} {'b_model2':>14} {'比值':>10} {'误差':>10}")
        for r in rows:
            print(f"  {r['eps']:>7.3f} {r['R_mm']:>9.4f} {r['L_mm']:>9.4f} "
                  f"{r['b2']:>14.6e} {r['ratio']:>10.6f} {r['err']*100:>9.4f}%")
        print()
        print(f"  b_model0 = {b0:.6e}")
        print(f"  最小误差 = {best['err']*100:.4f}%  (eps={best['eps']})   门槛 = {GATE0_TOL*100}%")
        print(f"  误差单调趋于 0: {'是' if monotone else '**否 —— 可疑**'}")
        print(f"  ==> Gate 0 {'PASS' if passed else '**FAIL-CODE**'}")
        print()

    return dict(
        id="gate-0-limit",
        recipe=GATE0_RECIPE_SPEC,
        ran=True,
        passed=bool(passed and monotone),
        evidence=(f"eps={best['eps']} 时 b2/b0 = {best['ratio']:.6f}，"
                  f"误差 {best['err']*100:.4f}% < {GATE0_TOL*100}%；"
                  f"误差随 eps 单调趋于 0（{errs[0]*100:.2f}% -> {errs[-1]*100:.4f}%）。"
                  f"注意：配方按 SD-1 修正（R 与 L 一起 ->0）；照 spec 字面只令 L->0 会收敛到 3.55。"),
        numbers=dict(rows=rows, b_model0=b0, tolerance=GATE0_TOL, monotone=monotone),
    )


def gate0_literal_recipe() -> dict:
    """照 spec **字面**执行的配方（只令 L->0，R 保持）。用来举证 SD-1。

    这不是"验证"，是**举证** —— 它证明契约里那个配方确实取错了极限。
    """
    w_thin = W_WALL * 1e-4
    b0 = b_model0(M_DIP, A_TUBE, w_thin, SIGMA)
    rows = []
    for f in (1.0, 0.1, 0.03, 0.01):
        L = L_MAG * f
        Ms = M_DIP / (np.pi * R_MAG ** 2 * L)      # R 保持 5mm ！
        b2 = damping(R_MAG, L, Ms, A_TUBE, w_thin, SIGMA)
        rows.append(dict(L_mm=L * 1e3, ratio=b2 / b0))
    return dict(rows=rows, converges_to=rows[-1]["ratio"])


# ================================================================== Gate 1

GATE1_TOL = 1e-4       # 断言容差 (0.1%) 的 1/10


def gate1_convergence(*, verbose=True) -> dict:
    """收敛门：结果必须与网格 / 容差 / 截断无关。

    **不做这个，你那个"斜率 -1.02"可能纯粹是网格太粗 —— 然后你会以为发现了物理。**

    ★ **必须在扫描端点上也做**，不能只在基准点做。

    这和 Skill 1 的「机制预算必须做扫描端点检查」是同一个道理：**基准点收敛，
    不代表扫描的另一端也收敛。**

    真实的坑（冒烟测试注入 4 复现过）：广义积分的截断长度若写成**绝对值**而不是
    自然尺度的倍数，那么参数扫描时 a 一变，zmax/a 就变了 —— 它会在扫描的一端
    悄悄失效。基准点上一切正常，Gate 0 也过，但大 a 端的每个点都偏小一点，
    **于是你的斜率是错的**。
    """
    a_lo, a_hi = SPEC_SWEEP_A
    pts = [("基准  a=6.0mm", A_TUBE),
           ("扫描下端 a=%.1fmm" % (a_lo * 1e3), a_lo),
           ("扫描上端 a=%.1fmm" % (a_hi * 1e3), a_hi)]

    base = dict(zmax_factor=200.0, epsrel=1e-10, limit=400)
    rows = []
    for label, a in pts:
        args = (R_MAG, L_MAG, MS, a, W_WALL, SIGMA)
        b0_ = damping(*args, **base)
        b_tol = damping(*args, **{**base, "epsrel": 1e-11})          # 容差收紧 10x
        b_trunc = damping(*args, **{**base, "zmax_factor": 400.0})   # 截断扩大 2x
        rows.append(dict(point=label, a=a, b=b0_,
                         d_tol=abs(b_tol - b0_) / b0_,
                         d_trunc=abs(b_trunc - b0_) / b0_))

    passed = all(r["d_tol"] < GATE1_TOL and r["d_trunc"] < GATE1_TOL for r in rows)

    if verbose:
        print("=" * 74)
        print("Gate 1 · 收敛门   (结果必须与数值参数无关 —— **且在扫描端点上也要成立**)")
        print()
        print(f"  {'检查点':<20} {'b':>14} {'容差收紧10x':>14} {'截断扩大2x':>14}  判定")
        for r in rows:
            ok = r["d_tol"] < GATE1_TOL and r["d_trunc"] < GATE1_TOL
            print(f"  {r['point']:<20} {r['b']:>14.8f} {r['d_tol']*100:>13.5f}% "
                  f"{r['d_trunc']*100:>13.5f}%  {'PASS' if ok else '**FAIL-CODE**'}")
        print()
        print(f"  门槛: 相对变化 < {GATE1_TOL*100}%（= 断言容差 0.1% 的 1/10）")
        print(f"  ==> Gate 1 {'PASS' if passed else '**FAIL-CODE**'}")
        print()

    worst = max(rows, key=lambda r: max(r["d_tol"], r["d_trunc"]))
    return dict(
        id="gate-1-convergence",
        ran=True,
        passed=bool(passed),
        evidence=(f"在基准点与 a 扫描的两个端点上各做一遍。最差的一点是「{worst['point']}」："
                  f"容差收紧 10x 时 b 变化 {worst['d_tol']*100:.5f}%，"
                  f"截断范围扩大 2x 时 b 变化 {worst['d_trunc']*100:.5f}%。"
                  f"均 < {GATE1_TOL*100}%（断言容差 0.1% 的 1/10）。"
                  f"**扫描端点检查是必须的**：绝对截断长度会在扫描的一端悄悄失效，"
                  f"而基准点上看不出来。"),
        numbers=dict(rows=rows, tolerance=GATE1_TOL),
    )


# ================================================================== Gate 2 / 3

def gate3_analytical(*, verbose=True) -> dict:
    """解析对拍：Model-0 必须**精确**重现 targets[].baseline_value。

    重现不了 = 参数读错或单位错。**先修这个，别往下走。**
    """
    b0 = b_model0(M_DIP, A_TUBE, W_WALL, SIGMA)
    vt0 = vt_model0(M_DIP, A_TUBE, W_WALL, SIGMA)
    tau0 = tau_model0(vt0)

    checks = [
        ("b",       b0,   TARGET["b"]["baseline_value"],        1e-3),
        ("v_t",     vt0,  TARGET["v_t"]["baseline_value"],      5e-3),
        ("\\tau",   tau0, TARGET["\\tau"]["baseline_value"],    5e-3),
    ]
    rows, ok = [], True
    for sym, got, want, tol in checks:
        dev = abs(got - want) / want
        good = dev < tol
        ok &= good
        rows.append(dict(symbol=sym, computed=float(got), spec_baseline=want,
                         rel_dev=float(dev), passed=bool(good)))

    if verbose:
        print("=" * 74)
        print("Gate 3 · 解析对拍   (Model-0 vs model-spec 的 baseline_value —— 地面真值)")
        print()
        print(f"  {'量':<8} {'算出来的':>14} {'spec 基准':>14} {'相对偏差':>12}  判定")
        for r in rows:
            print(f"  {r['symbol']:<8} {r['computed']:>14.6g} {r['spec_baseline']:>14.6g} "
                  f"{r['rel_dev']*100:>11.4f}%  {'PASS' if r['passed'] else '**FAIL-CODE**'}")
        print()
        print(f"  ==> Gate 3 {'PASS' if ok else '**FAIL-CODE**'}")
        print()

    return dict(
        id="gate-3-analytical",
        ran=True,
        passed=bool(ok),
        evidence="; ".join(f"{r['symbol']}: 算得 {r['computed']:.6g}，"
                           f"spec 基准 {r['spec_baseline']:.6g}，偏差 {r['rel_dev']*100:.4f}%"
                           for r in rows),
        numbers=dict(rows=rows),
    )


def gate2_layered(*, verbose=True) -> dict:
    """分层对拍：Model-2 在「场退化为点偶极子」时必须回到 Model-0 的 b（同一壁厚下）。

    这是 Gate 0 的一个**弱化版**但更直接的检查：只换场模型，不缩磁体。
    薄壁近似 + 点偶极子场 -> 必须精确等于 (10)。
    """
    w_thin = W_WALL * 1e-4
    b_dip = damping(R_MAG, L_MAG, MS, A_TUBE, w_thin, SIGMA,
                    thin_wall=True, dipole_field=True, m_dip=M_DIP)
    b0 = b_model0(M_DIP, A_TUBE, w_thin, SIGMA)
    dev = abs(b_dip - b0) / b0
    passed = dev < 1e-4

    if verbose:
        print("=" * 74)
        print("Gate 2 · 分层对拍   (Model-2 的积分器 + 点偶极子场 + 薄壁  ==  (10) 的闭式解)")
        print()
        print(f"  数值积分 (点偶极子场, 薄壁) = {b_dip:.8e}")
        print(f"  闭式解 (10)                 = {b0:.8e}")
        print(f"  相对偏差                    = {dev*100:.6f}%")
        print(f"  ==> Gate 2 {'PASS' if passed else '**FAIL-CODE**'}")
        print()

    return dict(
        id="gate-2-layered",
        ran=True,
        passed=bool(passed),
        evidence=(f"用 Model-2 的积分器 + 点偶极子场 + 薄壁近似，得 b = {b_dip:.8e}；"
                  f"闭式解 (10) 给出 {b0:.8e}；相对偏差 {dev*100:.6f}% < 0.01%。"
                  f"这证明积分器本身是对的，与场模型无关。"),
        numbers=dict(b_integrated_dipole=b_dip, b_closed_form=b0, rel_dev=dev),
    )


# ==================================================================

def run_all_gates(verbose=True) -> list[dict]:
    """按序跑。**Gate 0 不过就停** —— 后面的结果没有意义。"""
    g0 = gate0(verbose=verbose)
    if not g0["passed"]:
        print("!! Gate 0 未通过 —— **代码错了**。后面一律不许走。")
        return [g0]
    return [g0, gate1_convergence(verbose=verbose),
            gate2_layered(verbose=verbose), gate3_analytical(verbose=verbose)]


if __name__ == "__main__":
    banner()
    if "--gate0" in sys.argv:
        g = gate0()
        sys.exit(0 if g["passed"] else 1)

    gates = run_all_gates()
    print("=" * 74)
    for g in gates:
        print(f"  {g['id']:<22} {'PASS' if g['passed'] else '**FAIL**'}")
    sys.exit(0 if all(g["passed"] for g in gates) else 1)
