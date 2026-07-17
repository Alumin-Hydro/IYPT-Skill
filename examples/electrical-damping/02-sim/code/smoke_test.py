#!/usr/bin/env python3
r"""注入式冒烟测试（Stage 10）：**你怎么知道你那些门不是摆设？**

往真实代码路径里注入 6 个 bug，每个必须被**指定的**那道门抓到；
外加基线（无注入）—— 全部门必须安静。**会误报的门比没有门更糟。**

| # | 注入 | 指定捕手 |
|---|------|----------|
| 1 | 环场公式漏 μ₀（量纲错） | Gate 0（极限对拍差 6 个量级） |
| 2 | Model-0 的 λ 冒充 Model-2 | A-1 的 L_m 扫描 must_not（0 vs 0.38 离散）+ c₂ must_not |
| 3 | 求积网格 12×12×20×20 → 3×3×3×3 | Gate 1 基准点收敛（场网格 ×2 漂移超限） |
| 4 | 样条范围写死 ±20mm（基准 13.5mm 正常） | Gate 1 **扫描端点**（z₀=15+A₀=8=23mm 撞域护栏） |
| 5 | G 冻结在 z₀（bug-F 线性化——学生最会写的错模型） | AS-17/AS-18 must_not（大振幅不偏离 / 两族一样） |
| 6 | 力项写成 2·I·G（系数错） | V-3 能量审计（机器精度上崩 12 个量级） |

每个案例在**子进程**里跑（干净隔离，不靠状态恢复）。注入打在生产路径上
（monkeypatch 模块函数 / 毒化样条缓存 / FORCE_GAIN 钩子），不是测试副本。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import numpy as np

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

CASES = {
    "1": "漏 μ₀（量纲错）→ Gate 0",
    "2": "Model-0 冒充 Model-2 → A-1 L_m must_not + c₂ must_not",
    "3": "求积网格 3×3×3×3 → Gate 1 基准收敛",
    "4": "样条范围 ±20mm 绝对值 → Gate 1 端点（域护栏）",
    "5": "G 冻结在 z₀（bug-F）→ AS-17/AS-18 must_not",
    "6": "力项 2·I·G → V-3 能量审计",
}


# ---------------------------------------------------------------- 探测器
def det_gate0() -> tuple[bool, str]:
    """CAUGHT ⟺ Gate 0 的极限对拍失败。"""
    import gates as GATES
    g = GATES.gate0_limit(eps_list=(1.0, 0.1, 0.01))
    return (not (g["monotone"] and g["final_ok"]),
            f"G0 errors={['%.1e' % e for e in g['errors']]}")


def det_a1_c2() -> tuple[bool, str]:
    """CAUGHT ⟺ L_m 扫描不动（<1e-6）或 c₂(M2) 回到 c₂(M0)（差 <2%）。"""
    import field as FLD
    import gates as GATES
    from params import SWEEP
    g5 = GATES._gmax_at_Lm(SWEEP["L_m"][0])
    g20 = GATES._gmax_at_Lm(SWEEP["L_m"][1])
    relvar = abs(g5 - g20) / g20
    c2sep = abs(FLD.model2().gp0 / FLD.Gp0_0() - 1)      # gp0 比值即 √(c₂ 比值)
    caught = relvar < 1e-6 or c2sep < 0.01
    return caught, f"L_m 扫描相对变化 {relvar:.2e}；gp0(M2)/gp0(M0)−1 = {c2sep:.2e}"


def det_gate1_base() -> tuple[bool, str]:
    """CAUGHT ⟺ 基准点观测量在场网格 ×2 下漂移 > 1e-3（Gate 1 的 K-field 检查）。"""
    import field as FLD
    import model2 as M2
    from field import GSpline, zpk_model0
    from params import R_TEST
    zpk = zpk_model0()[0]

    def gam(gs):
        tp, Ap, _ = M2.envelope(zpk, 1e-3, R_TEST, mode="3state", Gfun=gs.G, T=6.0)
        return M2.gamma_first(tp, Ap, 1e-3)

    d = abs(gam(GSpline(n=641, nrho=24, nzm=24, nr=40, nz=40)) / gam(FLD.model2()) - 1)
    return d > 1e-3, f"K-field ×2 漂移 Δ = {d:.2e}（门 1e-3）"


def det_gate1_endpoint() -> tuple[bool, str]:
    """CAUGHT ⟺ 扫描端点 (z₀=15mm, A₀=8mm) 撞样条域护栏（或对 zmax 加倍敏感）。"""
    import field as FLD
    import model2 as M2
    from params import R_TEST, SWEEP
    try:
        tp, Ap, _ = M2.envelope(SWEEP["z_0"][1], 8e-3, R_TEST, mode="3state", T=5.0)
        g_ref = M2.gamma_first(tp, Ap, 8e-3)
    except ValueError as e:                              # 域护栏 —— 响亮的失败
        return True, f"端点撞域护栏：{e}"
    gs2 = FLD.GSpline(zmax=48e-3, n=481)
    tp, Ap, _ = M2.envelope(SWEEP["z_0"][1], 8e-3, R_TEST, mode="3state",
                            Gfun=gs2.G, T=5.0)
    d = abs(M2.gamma_first(tp, Ap, 8e-3) / g_ref - 1)
    return d > 1e-2, f"端点 zmax×1.5 漂移 Δ = {d:.2e}（门 1e-2）"


def det_f5_f6() -> tuple[bool, str]:
    """CAUGHT ⟺ 大振幅不偏离 y=x（AS-17）或中心族圈间距比不上升（AS-18）。"""
    import field as FLD
    import model2 as M2
    from field import zpk_model0
    from params import GAMMA_OC, K_SPRING, M_EFF, OMEGA0, R_C, R_TEST
    zpk = zpk_model0()[0]
    tp, Ap, _ = M2.envelope(zpk, 8e-3, R_TEST, mode="3state", T=6.0, A_cut=1e-6)
    gam = M2.gamma_first(tp, Ap, 8e-3)
    x = float(FLD.model2().G(zpk)) ** 2 / (2 * np.sqrt(M_EFF * K_SPRING)
                                           * (R_TEST + R_C))
    dev = (gam - GAMMA_OC) / OMEGA0 / x - 1
    sol = M2.simulate3(0.0, 8e-3, R_TEST, T=15.0)
    tp2, Ap2 = M2.envelope_from_sol(sol, 0.0, 15.0, A_cut=1e-6)
    r = Ap2[1:] / Ap2[:-1]
    rise = float(r[-1] - r[0]) if len(r) > 3 else 0.0
    caught = dev > -0.05 or rise < 0.05
    return caught, f"大振幅偏离 {dev:+.1%}（须 <−5%）；中心族比值升 {rise:+.3f}（须 >0.05）"


def det_v3() -> tuple[bool, str]:
    """CAUGHT ⟺ 能量审计的修正恒等式残差 ≥ 1e-10。"""
    import model2 as M2
    from field import zpk_model0
    aud = M2.energy_audit(zpk_model0()[0], 3e-3, 20.0, T=6.0)
    return aud["resid_correct"] >= 1e-10, f"审计残差 {aud['resid_correct']:.1e}（门 1e-10）"


# ---------------------------------------------------------------- 注入
def inject(case: str) -> None:
    import field as FLD
    import model2 as M2
    if case == "1":                                       # 漏 μ₀
        orig = FLD.bz_loop
        FLD.bz_loop = lambda R, rho, dz: orig(R, rho, dz) / FLD.MU0
    elif case == "2":                                     # Model-0 冒充 Model-2
        FLD.lambda_table = lambda zgrid, geom=FLD.BASE, **kw: FLD.lam0(zgrid, geom)
        FLD._G2 = None                                    # 逼缓存重建
    elif case == "3":                                     # 网格太粗
        FLD._G2 = FLD.GSpline(nrho=3, nzm=3, nr=3, nz=3)
    elif case == "4":                                     # 绝对截断 ±20mm
        FLD._G2 = FLD.GSpline(zmax=20e-3, n=201)
    elif case == "5":                                     # bug-F：G 冻结在 z₀
        orig3 = M2.simulate3

        def frozen3(z0, A0, R, **kw):
            gfrozen = float(FLD.model2().G(z0))
            kw["Gfun"] = lambda z: gfrozen
            return orig3(z0, A0, R, **kw)
        M2.simulate3 = frozen3
    elif case == "6":                                     # 力项 2·I·G
        M2.FORCE_GAIN = 2.0


#: 案例 → 指定捕手（探测器）
DETECTOR = {"1": det_gate0, "2": det_a1_c2, "3": det_gate1_base,
            "4": det_gate1_endpoint, "5": det_f5_f6, "6": det_v3}


def run_case(case: str) -> int:
    if case == "0":                                       # 基线：全部探测器必须安静
        bad = []
        for cid, det in DETECTOR.items():
            caught, msg = det()
            mark = "✗✗ 误报" if caught else "✓ 安静"
            print(f"  [{mark}] 探测器 {cid}: {msg}")
            if caught:
                bad.append(cid)
        return 1 if bad else 0
    inject(case)
    caught, msg = DETECTOR[case]()
    print(f"  [{'✓ 抓到' if caught else '✗✗ 漏网'}] {CASES[case]}")
    print(f"      {msg}")
    return 0 if caught else 1


def main() -> int:
    here = Path(__file__).resolve()
    fails = []
    print("【0】基线（无注入）—— 会误报的门比没有门更糟")
    r = subprocess.run([sys.executable, str(here), "--case", "0"]).returncode
    if r:
        fails.append("0")
    for case, desc in CASES.items():
        print(f"【{case}】注入：{desc}")
        r = subprocess.run([sys.executable, str(here), "--case", case]).returncode
        if r:
            fails.append(case)
    print()
    if fails:
        print(f"✗✗ 冒烟测试失败：案例 {fails} —— 有门是摆设，必须重新设计。")
        return 1
    print("✓✓ 基线安静 + 6 个注入全部被指定的门抓到 —— 阶梯不是摆设。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--case":
        raise SystemExit(run_case(sys.argv[2]))
    raise SystemExit(main())
