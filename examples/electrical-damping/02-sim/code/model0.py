#!/usr/bin/env python3
r"""Model-0：闭式解直接代入 —— 7 个 target 的解析预言。

**它必须精确重现 `targets[].baseline_value`** —— 重现不了，是参数读错了或单位错了，
先修这个，别的什么都不许动（SKILL.md Stage 3）。

★ 单位陷阱（契约 targets[c_2] 点名）：c₂ 的闭式给 SI（1/(s·m²)），契约声明的单位是
  1/(s·mm²) ⟹ ×1e-6 必须显式写出。
"""
from __future__ import annotations

import numpy as np

from field import BASE, Gp0_0, zpk_model0
from params import A0_BASE, GAMMA_OC, K_SPRING, M_EFF, R_C, R_TEST, TARGET


def targets_model0() -> dict[str, float]:
    """7 个 target 的 Model-0 值。键 = 契约 targets[].symbol。"""
    zpk, gmax = zpk_model0(BASE)                       # (6) 数值求极值 —— 契约点名「无闭式」
    gp0 = Gp0_0(BASE)                                  # (7)
    beta_sc = gp0**2 / R_C                             # β = G'(0)²/(R+R_c)，短路 R=0
    return {
        "G_{\\max}": gmax,
        "z_{\\rm pk}": zpk,
        "\\gamma": GAMMA_OC + gmax**2 / (2 * M_EFF * (R_TEST + R_C)),
        "\\zeta": gmax**2 / (2 * np.sqrt(M_EFF * K_SPRING) * (R_TEST + R_C)),
        "t^*": 4 * M_EFF / (beta_sc * A0_BASE**2),     # ★ 短路 R=0，A₀=3mm（契约 baseline_conditions）
        "A_c": float(np.sqrt(8 * M_EFF * GAMMA_OC / beta_sc)),
        "c_2": gp0**2 / (2 * M_EFF * (R_TEST + R_C)) * 1e-6,   # ★ SI → 1/(s·mm²)
    }


#: 每个 target 的容差（acceptance.md AS-5..AS-11：G_max <0.5%，其余 <1%）
TOL = {"G_{\\max}": 0.005, "z_{\\rm pk}": 0.01, "\\gamma": 0.01, "\\zeta": 0.01,
       "t^*": 0.01, "A_c": 0.01, "c_2": 0.01}


def check_baselines(verbose: bool = True) -> dict[str, dict]:
    """Model-0 vs 契约 baseline_value。返回 {symbol: {value, baseline, rel, ok}}。"""
    vals = targets_model0()
    out = {}
    for sym, v in vals.items():
        base = TARGET[sym]["baseline_value"]
        rel = v / base - 1
        out[sym] = dict(value=v, baseline=base, rel=rel, ok=bool(abs(rel) < TOL[sym]))
        if verbose:
            mark = "✓" if out[sym]["ok"] else "✗✗"
            print(f"  {mark} {sym:12s} model0={v:.7g}  baseline={base:.7g}  "
                  f"偏差 {rel:+.3%}  (tol {TOL[sym]:.1%})")
    return out


if __name__ == "__main__":
    print("Model-0 闭式 vs 契约 baseline_value（重现不了 = 参数/单位读错，先修）")
    res = check_baselines()
    bad = [s for s, r in res.items() if not r["ok"]]
    print("✗✗ 有 baseline 重现不了" if bad else "✓ 7 个 baseline 全部重现")
    raise SystemExit(1 if bad else 0)
