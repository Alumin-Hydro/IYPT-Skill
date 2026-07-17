#!/usr/bin/env python3
"""从 handoff/model-spec.json 载入参数。

**不许硬编码。** 硬编码的数字会和契约悄悄漂移——你改了 spec 里的 a，代码里还是老值，
而且没有任何检查能发现。反向边修订过 model-spec 之后，这一条尤其致命。

★ 本题的两个易错点（都来自契约本身，见 acceptance.md 的 Step 0 预注册）：
  1. 运动方程 (26) 的质量一律是 **M_eff = M + m_s/3**，不是 M。
  2. 能量审计的储能必须含 **½LI²**（三态模型），阻尼项系数是 2·M_eff·γ_oc。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

WORKSPACE = Path(__file__).resolve().parents[2]      # .../electrical-damping
SPEC_PATH = WORKSPACE / "handoff" / "model-spec.json"
OUT_FIG = WORKSPACE / "02-sim" / "figures"
OUT_INT = WORKSPACE / "02-sim" / "interactive"

SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

#: 参数基准值，按符号索引
P = {p["symbol"]: p["value"] for p in SPEC["parameters"]}
#: 扫描范围
SWEEP = {p["symbol"]: p.get("sweep_range") for p in SPEC["parameters"] if p.get("sweep_range")}

MU0      = P["\\mu_0"]
R_MAG    = P["R_m"]              # 磁体半径
L_MAG    = P["L_m"]              # 磁体长度
B_R      = P["B_r"]
M_S      = P["M_s"]              # 磁化强度 = B_r/mu0
M_DIP    = P["m"]                # 磁偶极矩 = M_s·πR_m²L_m
M_MASS   = P["M"]                # 磁体质量
M_SPRING = P["m_s"]              # 弹簧质量
M_EFF    = P["M_eff"]            # ★ 有效振动质量 = M + m_s/3 —— (26) 用它，不是 M
K_SPRING = P["k"]
GAMMA_OC = P["\\gamma_{oc}"]     # 开路本底（含导线涡流 γ_eddy）
GAMMA_EDDY = P["\\gamma_{eddy}"]

N_TURNS  = P["N"]
A_COIL   = P["a"]                # 平均绕组半径
L_COIL   = P["\\ell_c"]          # 线圈长度
D_WIRE   = P["d_w"]              # 裸线直径
P_AXIAL  = P["p_w"]              # 轴向节距（含漆）
P_RADIAL = P["p_r"]              # 径向层间距（六方嵌套）
W_COIL   = P["w"]                # 绕组厚度
R_C      = P["R_c"]              # 线圈自阻
L_IND    = P["L"]                # 线圈电感（Wheeler）
R_TEST   = P["R"]                # 基准外接电阻 20 Ω

Z0_BASE  = P["z_0"]              # 基准平衡位置 = z_pk
A0_BASE  = P["A_0"]              # 基准初振幅 3 mm

#: 派生量（公式全部来自契约的 symbols/parameters 注记）
OMEGA0 = float(np.sqrt(K_SPRING / M_EFF))            # ω₀ = sqrt(k/M_eff)，★不是 sqrt(k/M)
#: 绕组层数 = N / (每层匝数 ℓ_c/p_w)（parameters[p_w] 的 meaning 给的配方）
N_LAYER = int(round(N_TURNS * P_AXIAL / L_COIL))
#: 最内/最外层导线中心半径（均匀载流带 [A1, A2]，六方嵌套 ⟹ 层距 p_r）
A1_BAND = A_COIL - (N_LAYER - 1) / 2 * P_RADIAL
A2_BAND = A_COIL + (N_LAYER - 1) / 2 * P_RADIAL

#: S-8′（第二套线圈，∅0.20 mm）—— 全部由契约参数派生，不许手打散文里的数
N2_TURNS = P["N'"]
R_C2     = P["R_c'"]
D_WIRE2  = P["d_w'"]
#: γ_eddy ∝ N·r_w⁴（symbols[r_w] 的基本律；spec 的 N'、d' 显式给出 ⟹ 直接代入）
GAMMA_EDDY2 = GAMMA_EDDY * (N2_TURNS / N_TURNS) * (D_WIRE2 / D_WIRE) ** 4
GAMMA_OC2   = GAMMA_OC - GAMMA_EDDY + GAMMA_EDDY2

#: 目标量（对拍用的地面真值）
TARGET = {t["symbol"]: t for t in SPEC["targets"]}


def sweep(sym: str, n: int = 9) -> np.ndarray:
    """按 spec 的 sweep_range / sweep_scale 生成扫描点。"""
    p = next(p for p in SPEC["parameters"] if p["symbol"] == sym)
    lo, hi = p["sweep_range"]
    if p.get("sweep_scale") == "log":
        if lo <= 0:                                   # log 扫描含 0 端点（如 R∈[0,200]）
            pts = np.logspace(np.log10(max(hi * 1e-3, 1e-6)), np.log10(hi), n - 1)
            return np.concatenate([[lo], pts])
        return np.logspace(np.log10(lo), np.log10(hi), n)
    return np.linspace(lo, hi, n)


def banner() -> None:
    print(f"契约: {SPEC_PATH.relative_to(WORKSPACE.parent.parent)}")
    print(f"  题目   : {SPEC['problem']['slug']} ({SPEC['problem']['type']})")
    print(f"  任务   : {len(SPEC['tasks'])} 条  方程: {len(SPEC['equations'])} 条  "
          f"目标量: {len(SPEC['targets'])} 个  图: {len(SPEC['figures'])} 张")
    print(f"  RISKY 验证: {len(SPEC['risky_assumption_checks'])} 条  "
          f"中间量验证: {len(SPEC['model_validation_checks'])} 条")
    print(f"  磁体   : R_m={R_MAG*1e3:.1f}mm  L_m={L_MAG*1e3:.1f}mm  m={M_DIP:.4f} A·m²  "
          f"(mu0·M_s={MU0*M_S:.3f} T, spec B_r={B_R} T)")
    print(f"  线圈   : N={N_TURNS:.0f}  a={A_COIL*1e3:.3f}mm  l_c={L_COIL*1e3:.1f}mm  "
          f"{N_LAYER} 层, 载流带 [{A1_BAND*1e3:.3f}, {A2_BAND*1e3:.3f}]mm  "
          f"R_c={R_C:.3f}Ω  L={L_IND*1e3:.2f}mH")
    print(f"  力学   : M_eff={M_EFF*1e3:.3f}g (M={M_MASS*1e3:.2f}g + m_s/3)  k={K_SPRING} N/m  "
          f"omega0={OMEGA0:.4f} rad/s  gamma_oc={GAMMA_OC} 1/s")
    print(f"  基准   : R={R_TEST}Ω  z0={Z0_BASE*1e3:.4f}mm  A0={A0_BASE*1e3:.1f}mm")
    print(f"  S-8'   : N'={N2_TURNS:.0f}  R_c'={R_C2}Ω  gamma_oc'={GAMMA_OC2:.4f} 1/s")
    print()


if __name__ == "__main__":
    banner()
    print("扫描范围:")
    for s, r in SWEEP.items():
        print(f"  {s:10s}  [{r[0]:.4g}, {r[1]:.4g}]")
