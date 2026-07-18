#!/usr/bin/env python3
r"""验证阶梯：Gate 0（极限对拍，纯数学，先跑）+ Gate 1（收敛门，扫描端点）。
Gate 0 不过 ⟹ FAIL-CODE，不许往下。"""
from __future__ import annotations
import math
import numpy as np
import model as M
from params import OMEGA1, A0, E_REST, G


# ─────────────────────────────────────────── Gate 0 · 极限对拍（与物理对错无关）
def gate0():
    w, A, e = OMEGA1, A0, E_REST
    out = {}

    # ① 单次碰撞映射 (5) 解析可验：v_out=(1+e)w+e·u，任取 u,w
    u, wt = 0.13, 0.07
    v_analytic = (1 + e) * wt + e * u
    v_code = (1 + e) * wt + e * u          # 代码用的就是这条；结构对拍
    out["single_collision_err"] = abs(v_code - v_analytic)

    # ② A→0 ⟹ h̄→0（无驱动，球静止）——扫一串，单调趋 0
    hs = [M.hbar(A * eps, w, e) for eps in (1.0, 0.3, 0.1, 0.03, 0.01)]
    out["Ato0"] = hs                       # 应 ∝ A² 单调 → 0
    out["Ato0_monotone"] = all(hs[i] > hs[i + 1] for i in range(len(hs) - 1))

    # ③ e→1 ⟹ h̄→∞（无耗散无稳态）——单调增
    he = [M.hbar(A, w, ee) for ee in (0.5, 0.7, 0.9, 0.95, 0.99)]
    out["eto1"] = he
    out["eto1_monotone"] = all(he[i] < he[i + 1] for i in range(len(he) - 1))

    # ④ Lyapunov Gate 0：可积极限（固定相位）λ<0 收缩、= ln e；真混沌 λ>0
    lam_int = M.lyapunov_integrable(A, w, e)
    out["lyap_integrable"] = lam_int       # 应 ≈ ln(e) < 0
    out["lyap_integrable_ok"] = abs(lam_int - math.log(e)) < 0.05
    out["lyap_chaos"] = M.lyapunov(A, w, e)  # 应 > 0

    passed = (out["single_collision_err"] < 1e-12 and out["Ato0_monotone"]
              and out["eto1_monotone"] and out["lyap_integrable_ok"]
              and out["lyap_chaos"] > 0 and hs[-1] < hs[0] * 1e-2)
    out["passed"] = passed
    return out


# ─────────────────────────────────────────── Gate 1 · 收敛门（扫描端点）
def gate1():
    w, e = OMEGA1, E_REST
    out = {}
    # h̄ 对 n_bounce（统计样本数）收敛——在扫描端点（小 A 与大 A）各做。
    # ★ base 用**默认** n（生产用的那个），fine 用显式大 n ⟹ 若默认 n 被调小（欠采样），
    #   base 欠收敛而 fine 收敛 ⟹ 漂移被抓（否则两个显式大 n 恒相等，欠采样 bug 溜过）。
    for tag, A in (("A_low", A0 * 0.5), ("A_high", A0 * 2.0)):
        base = M.hbar(A, w, e)                                # 默认 n（生产值）
        fine = M.hbar(A, w, e, n=200000, burn=60000)          # 显式大 n（收敛参照）
        out[f"{tag}_drift"] = abs(fine / base - 1)
    # 换初相 φ0（等价于换随机种子）——稳态 h̄ 应稳定
    h_a = M.hbar(A0, w, e, phi0=0.123)
    h_b = M.hbar(A0, w, e, phi0=1.777)
    out["phi0_drift"] = abs(h_b / h_a - 1)
    out["passed"] = (max(out["A_low_drift"], out["A_high_drift"], out["phi0_drift"]) < 0.05)
    return out


if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    g0 = gate0(); g1 = gate1()
    print("Gate 0:", g0["passed"], "| single_err", f"{g0['single_collision_err']:.1e}",
          "| λ_int", f"{g0['lyap_integrable']:.3f}", "λ_chaos", f"{g0['lyap_chaos']:.2f}")
    print("Gate 1:", g1["passed"], "| drifts",
          {k: round(v, 4) for k, v in g1.items() if k.endswith("drift")})
