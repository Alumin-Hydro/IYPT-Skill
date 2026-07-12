#!/usr/bin/env python3
"""冒烟测试：往 Model-2 里注入 bug，看验证阶梯抓不抓得到。

**任何一个没被抓到，那道门就是摆设，必须重新设计。**

Skill 1 当初就是靠「注入 3 个错误看审稿人抓不抓得到」才发现零号规则的。这是 Skill 2
的对应动作 —— 也是它唯一可信的自证。

三个注入各打一道不同的门：

    注入                          应该被哪道门抓到
    -----------------------------------------------------------------
    1. 漏掉一个 mu0（量纲错）      Gate 0（极限对拍差数量级）
    2. 偷偷用点偶极子场冒充有限长场  ** Gate 0 抓不到 ** -> 只能靠 F-2 的 must_not
    3. 广义积分截断取太短           Gate 1（收敛门：扩大截断结果会变）

注入 2 是关键：它**会通过 Gate 0**（极限对拍时磁体本来就缩成偶极子了，两边一致），
产出的曲线也完全「合理」。**只有 must_not 断言能抓它。**
这正是「符得太好也是失败」这条设计存在的理由。
"""
from __future__ import annotations

import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

import field
import model2
import gates
from params import (R_MAG, L_MAG, A_TUBE, W_WALL, SIGMA, M_DIP, M_MASS, G, MS, MU0, sweep)
from model0 import b_model0, vt_model0

ORIG_MUTUAL = field.mutual
ORIG_DPHI = field.dphi_dz
ORIG_DAMPING = model2.damping


def restore():
    field.mutual = ORIG_MUTUAL
    field.dphi_dz = ORIG_DPHI
    model2.damping = ORIG_DAMPING
    gates.damping = ORIG_DAMPING
    model2.dphi_dz = ORIG_DPHI


def slope(x, y):
    return float(np.polyfit(np.log(x), np.log(y), 1)[0])


def run_gate0():
    g = gates.gate0(verbose=False)
    best = min(g["numbers"]["rows"], key=lambda r: r["err"])
    return g["passed"], best["err"]


def run_gate1():
    """收敛门：截断范围扩大 2x，b 的变化必须 < 0.01% —— **在基准点和扫描端点上都要成立**。"""
    g = gates.gate1_convergence(verbose=False)
    worst = max(g["numbers"]["rows"], key=lambda r: max(r["d_tol"], r["d_trunc"]))
    return g["passed"], max(worst["d_tol"], worst["d_trunc"])


def run_as9():
    """F-2 的 must_not（**数值型**）：v_t-a 斜率若落在 4.00 ± 0.10 内 -> FAIL-CODE。"""
    aa = sweep("a", 9)
    v2 = np.array([M_MASS * G / model2.damping(R_MAG, L_MAG, MS, a, W_WALL, SIGMA) for a in aa])
    k = slope(aa, v2)
    triggered = abs(k - 4.0) < 0.10           # must_not 被触发 = 抓到了
    return triggered, k


def run_as27():
    """F-5 的 must_not（**结构型**）：涡流峰位若落在点偶极子解析预言的 a/2 上 -> FAIL-CODE。

    峰位是场的**结构**性质，不是拟合量：点偶极子场的峰解析地落在 a/2
    （d/dz[z(a²+z²)^{-5/2}] = 0 ⇒ z = ±a/2），有限长磁体的落在 ≈ L/2。
    """
    zz = np.linspace(0.05 * A_TUBE, 3 * A_TUBE, 1200)
    d = np.abs(field.dphi_dz(R_MAG, L_MAG, MS, A_TUBE, zz))
    zpk = float(zz[int(np.argmax(d))])
    zdip = A_TUBE / 2
    triggered = abs(zpk - zdip) / zdip < 0.05
    return triggered, zpk * 1e3


def report(name, gate0, gate1, as9, as27, *, is_baseline=False):
    (g0_ok, g0_e), (g1_ok, g1_d), (as9_hit, k), (as27_hit, zpk) = gate0, gate1, as9, as27
    print(f"  Gate 0 (极限对拍)      : {'PASS' if g0_ok else '** FAIL-CODE **':<18}  误差 {g0_e*100:.4f}%")
    print(f"  Gate 1 (收敛门)        : {'PASS' if g1_ok else '** FAIL-CODE **':<18}  最差变化 {g1_d*100:.4f}%")
    print(f"  AS-9  must_not (数值型): {'** FAIL-CODE **' if as9_hit else 'PASS':<18}  k = {k:.4f}")
    print(f"  AS-27 must_not (结构型): {'** FAIL-CODE **' if as27_hit else 'PASS':<18}  "
          f"峰位 {zpk:.2f} mm  (a/2 = {A_TUBE*1e3/2:.2f}, L/2 = {L_MAG*1e3/2:.2f})")
    caught = (not g0_ok) or (not g1_ok) or as9_hit or as27_hit
    who = []
    if not g0_ok: who.append("Gate 0")
    if not g1_ok: who.append("Gate 1")
    if as9_hit:   who.append("AS-9 (数值型 must_not)")
    if as27_hit:  who.append("AS-27 (结构型 must_not)")
    print()

    if is_baseline:
        # 基线**不该**被抓 —— 会误报的门比没有门更糟。
        if caught:
            print(f"  ==>  ✗✗ **基线被误报了！**（{'、'.join(who)}）门在冤枉好人，必须重新校准。")
        else:
            print(f"  ==>  ✓ 基线干净，四道检查都没误报。**这是必要条件。**")
    elif caught:
        print(f"  ==>  ✓ 抓到了。抓它的是：{'、'.join(who)}")
    else:
        print(f"  ==>  ✗✗ **没抓到！这些门是摆设，必须重新设计。**")
    return caught, who


def main() -> int:
    print("=" * 78)
    print("冒烟测试 —— 往 Model-2 注入 bug，看验证阶梯抓不抓得到")
    print("=" * 78)
    results = {}

    def run4():
        return run_gate0(), run_gate1(), run_as9(), run_as27()

    # ------------------------------------------------ 0) 基线（无注入）
    #  **会误报的门比没有门更糟** —— 它会把真实的物理发现当成 bug 去"修"。
    restore()
    print("\n【0】基线（无注入）—— 四道检查都应该判 PASS\n")
    r = report("baseline", *run4(), is_baseline=True)
    results["baseline"] = r
    assert not r[0], "基线被抓了！门在误报 —— 会误报的门比没有门更糟。"

    # ------------------------------------------------ 1) 漏掉一个 mu0（量纲错）
    restore()
    print("\n" + "=" * 78)
    print("\n【1】注入：mutual() 里漏掉 mu0  —— 经典的量纲错\n")
    field.mutual = lambda R, r, d: ORIG_MUTUAL(R, r, d) / MU0
    field.dphi_dz = lambda R, L, Ms, r, z: Ms * (
        field.mutual(R, r, np.asarray(z, float) + L / 2.0)
        - field.mutual(R, r, np.asarray(z, float) - L / 2.0))
    model2.dphi_dz = field.dphi_dz
    results["missing_mu0"] = report("missing_mu0", *run4())

    # ------------------------------------------------ 2) 偷偷用点偶极子场
    restore()
    print("\n" + "=" * 78)
    print("\n【2】注入：偷偷用点偶极子场冒充有限长磁体的场")
    print("     —— 代码「跑得通」、曲线「很合理」，而且 **会通过 Gate 0**")
    print("        （极限对拍时磁体本来就缩成偶极子了，两边一致）")
    print()
    print("     ** 第一版验收表在这里翻过车 **：只换场、径向积分还在，斜率落在 3.79 ——")
    print("     既不是 4.00（AS-9 的陷阱），也不是真值 3.44（AS-8），**从两条断言之间溜过去了**。")
    print("     因为 spec 埋的陷阱是按「整个 Model-2 偷偷变成 Model-0」校准的，")
    print("     而真实的 bug 往往**只少了一个修正**。")
    print("     修法：加一条**结构型** must_not（AS-27，查峰位），而不是只查拟合出来的数。\n")
    field.dphi_dz = lambda R, L, Ms, r, z: field.dphi_dz_dipole(M_DIP, r, z)
    model2.dphi_dz = field.dphi_dz
    results["fake_dipole"] = report("fake_dipole", *run4())

    # ------------------------------------------------ 3) 广义积分截断太短
    restore()
    print("\n" + "=" * 78)
    print("\n【3】注入：广义积分截断从 200a 砍到 1.2a")
    print("     —— 结果**系统性偏小**，而且偏得平滑：曲线看起来完全正常，")
    print("        只是每个点都错了一点，于是你的**斜率**是错的\n")
    _d = ORIG_DAMPING

    def truncated(R, L, Ms, a, w, sigma, **kw):
        kw["zmax_factor"] = 1.2          # 硬编码：无视调用者传的 zmax_factor
        return _d(R, L, Ms, a, w, sigma, **kw)

    model2.damping = truncated
    gates.damping = truncated
    results["short_truncation"] = report("short_truncation", *run4())

    # ------------------------------------------------ 4) 截断长度写成**绝对值**
    restore()
    print("\n" + "=" * 78)
    print("\n【4】注入：广义积分截断写成**绝对值** zmax = 24 mm，而不是自然尺度的倍数")
    print("     —— 这是我自己在 numerical-recipes.md 里警告过的坑：")
    print("        「参数扫描时 a 会变，绝对截断长度会在扫描的一端悄悄失效」")
    print()
    print("     a=6mm 时 zmax = 4.0a（误差 0.026%）-> **Gate 0 过得去**")
    print("     a=12mm 时 zmax = 2.0a（误差 1.05%）-> 大 a 端每个点都偏小一点")
    print("     基准点上一切正常，曲线完全正常，**只是斜率是错的**。")
    print()
    print("     ** 只有「在扫描端点上也检查收敛」的 Gate 1 能抓到它。 **\n")
    _d2 = ORIG_DAMPING

    def abs_trunc(R, L, Ms, a, w, sigma, **kw):
        # zmax_factor 被解释成"相对基准 a 的倍数"——于是它变成了一个绝对长度
        f = kw.pop("zmax_factor", 200.0)
        kw["zmax_factor"] = f * (A_TUBE / a) * (4.0 / 200.0)     # 基准处等效 4a
        return _d2(R, L, Ms, a, w, sigma, **kw)

    model2.damping = abs_trunc
    gates.damping = abs_trunc
    results["absolute_truncation"] = report("absolute_truncation", *run4())

    restore()

    # ------------------------------------------------ 汇总
    print("\n" + "=" * 78)
    print("汇总")
    print("=" * 78)
    print(f"  {'注入':<36} {'抓到了？':<10} 抓它的门")
    print("  " + "-" * 76)
    order = (("missing_mu0", "1. 漏掉 mu0（量纲错）"),
             ("fake_dipole", "2. 点偶极子场冒充有限长场"),
             ("short_truncation", "3. 广义积分截断太短"),
             ("absolute_truncation", "4. 截断写成绝对值（扫描端点失效）"))
    for name, label in order:
        caught, who = results[name]
        print(f"  {label:<34} {'✓ 是' if caught else '✗✗ 否':<12} "
              f"{'、'.join(who) or '—— 没有门抓到 ——'}")
    print()

    allc = all(results[k][0] for k, _ in order)
    if allc:
        print("  ✓ 四个注入全部被抓到。**每道门都不是摆设。**")
        print()
        print("  两条硬教训（都是被冒烟测试逼出来的，不是设计时想到的）：")
        print()
        print("    · 注入 2 -> **must_not 不能只检查「拟合出来的数」，必须检查「结构」。**")
        print("      第一版只有数值型 must_not（斜率是不是 4.00）。注入「点偶极子场 + 正确的")
        print("      径向积分」后斜率落在 3.79 —— 既不是 4.00 也不是真值 3.44，**从两条断言")
        print("      之间溜过去了**。因为 spec 埋的陷阱是按「整个 Model-2 变成 Model-0」校准的，")
        print("      而真实的 bug 往往**只少了一个修正**。")
        print("      修法：AS-27 查涡流峰位 —— 那是场的**结构**性质，不是拟合量。")
        print()
        print("    · 注入 4 -> **收敛门必须在扫描端点上做，不能只在基准点做。**")
        print("      和 Skill 1 的「机制预算必须做扫描端点检查」是同一个道理。")
    else:
        print("  ✗✗ 有注入没被抓到 —— 对应的门是摆设，必须重新设计。")
    return 0 if allc else 1


if __name__ == "__main__":
    sys.exit(main())
