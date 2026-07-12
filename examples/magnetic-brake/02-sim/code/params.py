#!/usr/bin/env python3
"""从 handoff/model-spec.json 载入参数。

**不许硬编码。** 硬编码的数字会和契约悄悄漂移——你改了 spec 里的 a，代码里还是老值，
而且没有任何检查能发现。反向边修订过 model-spec 之后，这一条尤其致命。
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

WORKSPACE = Path(__file__).resolve().parents[2]      # .../magnetic-brake
SPEC_PATH = WORKSPACE / "handoff" / "model-spec.json"
OUT_FIG = WORKSPACE / "02-sim" / "figures"
OUT_INT = WORKSPACE / "02-sim" / "interactive"

SPEC = json.loads(SPEC_PATH.read_text(encoding="utf-8"))

#: 参数基准值，按符号索引
P = {p["symbol"]: p["value"] for p in SPEC["parameters"]}
#: 扫描范围
SWEEP = {p["symbol"]: p.get("sweep_range") for p in SPEC["parameters"] if p.get("sweep_range")}

MU0   = P["\\mu_0"]
G     = P["g"]
R_MAG = P["R"]          # 磁体半径
L_MAG = P["L"]          # 磁体长度
A_TUBE= P["a"]          # 管内半径
W_WALL= P["w"]          # 壁厚
SIGMA = P["\\sigma"]    # 电导率
M_DIP = P["m"]          # 磁偶极矩
M_MASS= P["M"]          # 磁体质量
B_R   = P["B_r"]

#: 磁化强度 M_s = m / V。安培模型的侧面束缚面电流 K = M_s。
MS = M_DIP / (np.pi * R_MAG**2 * L_MAG)

#: 目标量的解析预测基准值（对拍用的地面真值）
TARGET = {t["symbol"]: t for t in SPEC["targets"]}


def sweep(sym: str, n: int = 9) -> np.ndarray:
    """按 spec 的 sweep_range / sweep_scale 生成扫描点。"""
    p = next(p for p in SPEC["parameters"] if p["symbol"] == sym)
    lo, hi = p["sweep_range"]
    if p.get("sweep_scale") == "log":
        return np.logspace(np.log10(lo), np.log10(hi), n)
    return np.linspace(lo, hi, n)


def banner() -> None:
    print(f"契约: {SPEC_PATH.relative_to(WORKSPACE.parent.parent)}")
    print(f"  题目   : {SPEC['problem']['slug']} ({SPEC['problem']['type']})")
    print(f"  方程   : {len(SPEC['equations'])} 条  "
          f"目标量: {len(SPEC['targets'])} 个  "
          f"图: {len(SPEC['figures'])} 张  "
          f"RISKY 验证: {len(SPEC['risky_assumption_checks'])} 条")
    print(f"  基准   : R={R_MAG*1e3:.1f}mm  L={L_MAG*1e3:.1f}mm  a={A_TUBE*1e3:.1f}mm  "
          f"w={W_WALL*1e3:.1f}mm  sigma={SIGMA:.2e} S/m")
    print(f"  M_s    = {MS:.4e} A/m   ->  mu0*M_s = {MU0*MS:.4f} T  (spec 的 B_r = {B_R} T)")
    print()


if __name__ == "__main__":
    banner()
    print("扫描范围:")
    for s, r in SWEEP.items():
        print(f"  {s:10s}  [{r[0]:.4g}, {r[1]:.4g}]")
