#!/usr/bin/env python3
r"""从 handoff/model-spec.json 载入参数与契约。参数一律从契约来，不硬编码
（硬编码会和契约悄悄漂移，check_sim 查不出来）。"""
from __future__ import annotations
import json
import math
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]        # examples/ball-on-ferrite-rod
SPEC_PATH = WORKSPACE / "handoff" / "model-spec.json"
SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

OUT_FIG = WORKSPACE / "02-sim" / "figures"

_P = {p["symbol"]: p["value"] for p in SPEC["parameters"]}
E      = _P["E"]
RHO    = _P["\\rho"]
C      = _P["c"]                     # 声速 √(E/ρ)
L      = _P["L"]
G      = _P["g"]
E_REST = _P["e"]                     # 恢复系数
Q_ROD  = _P["Q"]
M_BALL = _P["m"]

# 本征频率（固定-自由）f_n = (2n-1) c/4L
def f_n(n: int) -> float:
    return (2 * n - 1) * C / (4 * L)
F1 = f_n(1)
OMEGA1 = 2 * math.pi * F1

# 目标 baseline（契约给的零参预言）
_T = {t["symbol"]: t for t in SPEC["targets"]}
K_H_BASE = _T["k_h"]["baseline_value"]          # h̄/(Aω)²  = (1+e)/[4g(1-e)]
A_THR_BASE = _T["A_thr"]["baseline_value"]      # g/ω₁²
F1_BASE = _T["f_1"]["baseline_value"]

# 仿真工作点：μm 级棒尖振幅（可见弹跳，Γ≫π）
A0 = 2.0e-6
