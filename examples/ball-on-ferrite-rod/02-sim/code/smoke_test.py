#!/usr/bin/env python3
r"""注入式冒烟测试（Stage 10）：往真实代码路径注入 bug，看指定的门/断言抓不抓得到。
基线（无注入）必须安静。会误报的门比没有门更糟。每案在子进程里跑（干净隔离）。"""
from __future__ import annotations
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

CASES = {
    "1": "共振退化：resonance_A 换成常数（无峰）→ AS-2/AS-8 峰位断言",
    "2": "锁相退化：hbar 换成单值 (Aω)²/2g、CV→0 → AS-5 must_not",
    "3": "系数偏 2×：hbar 换成 2× → AS-3/AS-4 斜率/偏差",
    "4": "BC 取错：共振峰移到 c/2L（自由-自由）→ AS-8 must_not",
    "5": "Lyapunov 符号翻转：可积极限 λ 变正 → Gate 0 / AS-1",
    "6": "样本太少：hbar 用极小 n → Gate 1 收敛门",
}


def inject(case):
    import model as M
    import numpy as np
    if case == "1":
        M.resonance_A = lambda f, f1, Q, A_dc=1.0: np.ones_like(np.asarray(f, float))
    elif case == "2":
        M.hbar = lambda A, w, e, **kw: (A * w) ** 2 / (2 * M.G)
        M.bounce_cv = lambda A, w, e, **kw: 0.0
    elif case == "3":
        _orig = M.hbar
        M.hbar = lambda A, w, e, **kw: 2.0 * M.hbar_theory(A, w, e)
    elif case == "4":
        import params as P
        _r = M.resonance_A
        M.resonance_A = lambda f, f1, Q, A_dc=1.0: _r(f, P.C / (2 * P.L), Q, A_dc)  # 峰移到 c/2L
    elif case == "5":
        M.lyapunov_integrable = lambda *a, **k: +0.5      # 谎报可积极限 λ>0
    elif case == "6":
        _orig = M.hbar
        # 把**默认** n 调小到欠采样（尊重显式传入的 n）⟹ Gate 1 的 base（默认 n）欠收敛
        M.hbar = lambda A, w, e, n=400, burn=100, **kw: _orig(A, w, e, n=n, burn=burn)


def detect(case):
    """返回 (caught, msg)。"""
    import acceptance as ACC
    import gates as GATES
    if case in ("1", "4"):
        AS, D = ACC.run()
        vd = {a["id"]: a["verdict"] for a in AS}
        c = vd.get("AS-2") != "PASS" or vd.get("AS-8") != "PASS"
        return c, f"AS-2={vd.get('AS-2')} AS-8={vd.get('AS-8')}"
    if case == "2":
        AS, D = ACC.run()
        vd = {a["id"]: a["verdict"] for a in AS}
        return vd.get("AS-5") != "PASS", f"AS-5(must_not CV)={vd.get('AS-5')} (CV={D['cv']:.3f})"
    if case == "3":
        AS, D = ACC.run()
        vd = {a["id"]: a["verdict"] for a in AS}
        return (vd.get("AS-3") != "PASS" or vd.get("AS-4") != "PASS"), \
            f"AS-3={vd.get('AS-3')} AS-4={vd.get('AS-4')} (kh_dev={D['kh_dev']:+.1%})"
    if case == "5":
        g0 = GATES.gate0()
        return not g0["passed"], f"Gate0 passed={g0['passed']} (λ_int={g0['lyap_integrable']:.2f} 应<0)"
    if case == "6":
        g1 = GATES.gate1()
        return not g1["passed"], f"Gate1 passed={g1['passed']} (drifts A_low={g1['A_low_drift']:.3f})"


def run_case(case):
    if case == "0":
        bad = []
        for cid in CASES:
            caught, msg = detect(cid)
            if caught:                                    # 基线不该被抓
                print(f"  [✗✗ 误报] 探测器 {cid}: {msg}"); bad.append(cid)
            else:
                print(f"  [✓ 安静] 探测器 {cid}: {msg}")
        return 1 if bad else 0
    inject(case)
    caught, msg = detect(case)
    print(f"  [{'✓ 抓到' if caught else '✗✗ 漏网'}] {CASES[case]}")
    print(f"      {msg}")
    return 0 if caught else 1


def main():
    here = Path(__file__).resolve()
    fails = []
    print("【0】基线（无注入）—— 会误报的门比没有门更糟")
    if subprocess.run([sys.executable, str(here), "--case", "0"]).returncode:
        fails.append("0")
    for case, desc in CASES.items():
        print(f"【{case}】注入：{desc}")
        if subprocess.run([sys.executable, str(here), "--case", case]).returncode:
            fails.append(case)
    print()
    if fails:
        print(f"✗✗ 冒烟测试失败：案例 {fails} —— 有门是摆设，必须重新设计。")
        return 1
    print("✓✓ 基线安静 + 6 个注入全被指定的门抓到 —— 阶梯不是摆设。")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--case":
        raise SystemExit(run_case(sys.argv[2]))
    raise SystemExit(main())
