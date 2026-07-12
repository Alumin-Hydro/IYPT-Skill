#!/usr/bin/env python3
"""验收断言的可执行版。对应 02-sim/acceptance.md。

**每条断言的 quoted_expectation 都是从 model-spec.json 逐字抄来的**（不是程序拉的——
抄写这个动作本身就是强制去读它。SD-1 和 SD-2 正是在抄的过程中被发现的）。

容差**一律取自 spec 原文**，不许来自"我已经知道结果是多少"。
最要命的一条是 AS-21：作者在 spike 里已看到偏差会超过 15%，门槛仍照 spec 写 15%，
**让它 FAIL**。那是关于这个模型的真实信息 —— 藏起来才是灾难。
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

from params import (G, R_MAG, L_MAG, A_TUBE, W_WALL, SIGMA, M_DIP, M_MASS, MS,
                    TARGET, sweep, banner)
from field import dphi_dz, dphi_dz_dipole, peak_z_dipole
from model0 import (b_model0, vt_model0, tau_model0, distance_to_fraction,
                    v_of_t, x_of_t, pi1, pi2, PI1_THEORY)
from model2 import damping, vt_model2
import gates as G8


def slope(x, y) -> tuple[float, float]:
    lx, ly = np.log(np.asarray(x, float)), np.log(np.asarray(y, float))
    k, b = np.polyfit(lx, ly, 1)
    r2 = 1.0 - np.sum((ly - (k * lx + b)) ** 2) / np.sum((ly - ly.mean()) ** 2)
    return float(k), float(r2)


def A(aid, source, kind, quote, interp, akind, expect, tol, measured, verdict, note="", fig=None):
    d = dict(id=aid, source=source, source_kind=kind, quoted_expectation=quote,
             assert_kind=akind, expect=expect, tolerance=tol,
             measured=measured, verdict=verdict)
    if interp:
        d["interpretation"] = interp
    if note:
        d["verdict_note"] = note
    if fig:
        d["figure_ref"] = fig
    return d


# ---- model-spec.json 的原文，逐字抄写 --------------------------------------
Q_EQ15 = ("关键对拍：令 L→0 且保持 m = M_s·V 固定(退化为点偶极子)、同时令 w→0，"
          "(15) 必须回到 (10)，误差 <0.1%。")
Q_F1 = ("两条直线，斜率均为 -1.00。Model-2 在大 w 端(w/a→0.5)应向上偏离 Model-0(A-2 崩)"
        "——若不偏离，反而说明代码没真正实现有限壁厚")
Q_F2 = ("Model-0 是斜率恰为 +4.00 的直线。**Model-2 预期斜率显著小于 4**"
        "（因 a/L 仅 0.6–1.2，近场衰减比 r^-3 慢）。两条线在小 a 端分歧最大。"
        "若 Model-2 也给出 4.00，说明有限尺寸修正没被正确实现——回去查代码")
Q_F3 = "在 0.35 mm 处已达 0.99，之后完全平坦。1 m 管中 99.97% 的行程处于终速"
Q_F4 = ("**所有点坍缩到同一条曲线 f(Pi_2) 上**（这是关键——若不坍缩，说明遗漏了一个"
        "无量纲组，很可能是 L/a）。Pi_2 → 0 时趋于水平渐近线 22.756。"
        "注意：Model-2 的点预期**不会**完全坍缩，因为 A-1 崩溃引入了第三个无量纲组 L/a"
        "——这个「坍缩失败」本身就是结论")
Q_F5 = ("反对称的双峰结构（磁体前方与后方电流反向），峰值位于 z = ±a/2 附近，"
        "随磁体一起向下平移。前后电流反向是 Lenz 定律的直接体现——前方排斥、后方吸引，"
        "两者都阻碍下落")
Q_A1 = ("报告两件事：(i) 基准点 a=6mm 处 v_t 的相对偏差；(ii) Model-2 的 v_t∝a^k 的实际指数 k。"
        "若 |k-4| > 0.3，则 P5 被数值判定为不可靠，必须在 01-analysis.md 的预测表中把 P5 降级并说明。"
        "预期 k 明显小于 4——这不是失败，是模型边界被正确定位。")
Q_A2 = ("在 w = 1 mm（基准）处相对偏差 < 15% 则 A-2 在基准点站得住。"
        "在 w = 3 mm（w/a=0.5）处预期偏差显著（>20%）——若此处偏差仍 <5%，"
        "说明径向积分没被正确实现，回去查代码。")
Q_TB = "b = \\dfrac{45}{1024}\\dfrac{\\mu_0^2 m^2 \\sigma w}{a^4}"
Q_TV = "v_t = \\dfrac{1024}{45}\\dfrac{M g a^4}{\\mu_0^2 m^2 \\sigma w}"
Q_TT = "\\tau = M/b = v_t/g"

I_F1 = ("原文自相矛盾：同时说「斜率均为 -1.00」和「Model-2 在大 w 端应向上偏离」。"
        "选定读法：「-1.00」是**领头阶**断言，「偏离」是同句立刻给出的限定。"
        "据此拆成 σ 面板（两条线都精确 -1，因 σ 只是 b 的线性前因子，与场分布无关）"
        "和 w 面板（Model-0 精确 -1；Model-2 因 A-2 崩溃而在大 w 端上翘）。")
I_F2 = ("「显著小于 4」需要一个数。取 A-1 的 pass_criterion 给的 0.3 —— "
        "**这个阈值是 spec 自己给的，不是作者挑的**。")
I_F3 = ("原文的 0.35 mm 是 SPEC-DEFECT（SD-2）：纯代数可证正确值为 "
        "x = v_t·τ·(ln100 - 0.99) = 0.277 mm；0.35 mm = 4.6·v_t·τ 少减了那个 0.99。"
        "这正是 01-review-r1.md 已抓到、但只改了正文没同步进契约的错误。断言按 0.277 mm 写。")
I_F4 = ("原文对 Model-0 和 Model-2 给的是**相反**的预期，必须拆开：Model-0 必须坍缩"
        "（其 Pi_1 恒等于 1024/45，与所有参数无关，是恒等式）；Model-2 预期**不**坍缩"
        "——「坍缩失败本身就是结论」。**把 Model-2 的坍缩失败判成 FAIL 再回头去修它，"
        "就毁掉了本题最有价值的结论。**")
I_F5 = ("「峰值位于 z = ±a/2」是**点偶极子**的结果（由 d/dz[z(a²+z²)^{-5/2}]=0 得 z=±a/2）。"
        "但 F-5 画的是 Model-2（有限长磁体），峰位会被两个端面拉开，预期偏离 a/2。"
        "故 AS-16 不写成「峰位必须等于 a/2」（那会把 A-1 的崩溃误判成代码错），"
        "而是测量峰位并报告它偏离 a/2 多少 —— 偏离本身是 A-1 崩溃的又一个独立证据。"
        "反对称性（AS-15）则是严格的，由 dΦ/dz 的奇函数结构保证，与场模型无关。")
I_A2 = ("原文的「相对偏差」没说是谁比谁。选定读法 (a)：**保留径向积分 vs 薄壁近似**"
        "（两者都用有限长磁体的场）。理由：A-2 讲的是径向均匀性，与场的空间分布无关；"
        "读法 (b)（Model-2 vs Model-0）会把 A-1 的误差和 A-2 的误差搅在一起，测不出 A-2 本身。"
        "task 字段的措辞「保留径向积分（而非薄壁近似 w/(2πa)）」对比的正是这两者，支持读法 (a)。")


def run(verbose=True) -> tuple[list[dict], dict]:
    AS: list[dict] = []
    D: dict = {}

    # ================================================== Gate 0 -> AS-1
    g0 = G8.gate0(verbose=False)
    best = min(g0["numbers"]["rows"], key=lambda r: r["err"])
    AS.append(A("AS-1", "(15)", "equation_limit", Q_EQ15,
                "配方按 SD-1 修正：R 与 L 必须一起 →0。照原文字面只令 L→0 会收敛到 3.5505 "
                "而非 1 ——「极限存在，但取错了极限」的指纹。",
                "limit", "|b_model2/b_model0 - 1| < 0.1%  (eps -> 0)", "0.1%（取自 numerical_notes 原文）",
                f"eps={best['eps']}: 误差 {best['err']*100:.4f}%（单调趋于 0）",
                "PASS" if g0["passed"] else "FAIL-CODE"))

    # ================================================== F-1 -> AS-2..AS-6
    sig = sweep("\\sigma", 7)
    v0_s = np.array([vt_model0(M_DIP, A_TUBE, W_WALL, s) for s in sig])
    v2_s = np.array([vt_model2(R_MAG, L_MAG, MS, A_TUBE, W_WALL, s, M_MASS, G) for s in sig])
    k0s, _ = slope(sig, v0_s)
    k2s, _ = slope(sig, v2_s)

    ws = sweep("w", 9)
    v0_w = np.array([vt_model0(M_DIP, A_TUBE, w, SIGMA) for w in ws])
    v2_w = np.array([vt_model2(R_MAG, L_MAG, MS, A_TUBE, w, SIGMA, M_MASS, G) for w in ws])
    k0w, _ = slope(ws, v0_w)
    k2w, _ = slope(ws, v2_w)
    ratio_w = v2_w / v0_w
    monotone_up = bool(np.all(np.diff(ratio_w) > 0))

    D.update(sig=sig, v0_s=v0_s, v2_s=v2_s, k0s=k0s, k2s=k2s,
             ws=ws, v0_w=v0_w, v2_w=v2_w, k0w=k0w, k2w=k2w, ratio_w=ratio_w)

    AS.append(A("AS-2", "F-1", "figure", Q_F1, I_F1, "slope",
                "Model-0 的 v_t-sigma loglog 斜率 == -1.00", "±0.02",
                round(k0s, 4), "PASS" if abs(k0s + 1) < 0.02 else "FAIL-CODE", fig="F-1"))
    AS.append(A("AS-3", "F-1", "figure", Q_F1, I_F1, "slope",
                "Model-2 的 v_t-sigma loglog 斜率 == -1.00", "±0.02",
                round(k2s, 4), "PASS" if abs(k2s + 1) < 0.02 else "FAIL-MODEL", fig="F-1"))
    AS.append(A("AS-4", "F-1", "figure", Q_F1, I_F1, "slope",
                "Model-0 的 v_t-w loglog 斜率 == -1.00", "±0.02",
                round(k0w, 4), "PASS" if abs(k0w + 1) < 0.02 else "FAIL-CODE", fig="F-1"))
    AS.append(A("AS-5", "F-1", "figure", Q_F1, I_F1, "deviation",
                "Model-2 在大 w 端向上偏离 Model-0：比值 v2/v0 随 w 单调递增", "单调性严格",
                f"{ratio_w[0]:.2f} -> {ratio_w[-1]:.2f}（单调递增: {monotone_up}）",
                "PASS" if monotone_up else "FAIL-MODEL", fig="F-1"))
    as6_hit = abs(k2w + 1.0) < 0.05
    AS.append(A("AS-6", "F-1", "figure", Q_F1, I_F1, "must_not",
                "NOT (Model-2 的 v_t-w 斜率 in -1.00 ± 0.05) —— 若落在里面，说明有限壁厚根本没实现",
                "±0.05", round(k2w, 4),
                "FAIL-CODE" if as6_hit else "PASS",
                "must_not 被触发：Model-2 的 w 斜率回到了 -1.00，有限壁厚没进代码" if as6_hit else "",
                fig="F-1"))

    # ================================================== F-2 -> AS-7..AS-9
    aa = sweep("a", 9)
    v0_a = np.array([vt_model0(M_DIP, a, W_WALL, SIGMA) for a in aa])
    v2_a = np.array([vt_model2(R_MAG, L_MAG, MS, a, W_WALL, SIGMA, M_MASS, G) for a in aa])
    k0a, r2_0a = slope(aa, v0_a)
    k2a, r2_2a = slope(aa, v2_a)
    D.update(aa=aa, v0_a=v0_a, v2_a=v2_a, k0a=k0a, k2a=k2a, r2_2a=r2_2a)

    AS.append(A("AS-7", "F-2", "figure", Q_F2, I_F2, "slope",
                "Model-0 的 v_t-a loglog 斜率 == +4.00（地面真值）", "±0.02",
                round(k0a, 4), "PASS" if abs(k0a - 4) < 0.02 else "FAIL-CODE", fig="F-2"))
    AS.append(A("AS-8", "F-2", "figure", Q_F2, I_F2, "slope",
                "|k_Model-2 - 4| > 0.3（「显著小于 4」，阈值取自 A-1 的 pass_criterion）", "—",
                round(k2a, 4), "PASS" if abs(k2a - 4) > 0.3 else "FAIL-MODEL", fig="F-2"))
    as9_hit = abs(k2a - 4.0) < 0.10
    AS.append(A("AS-9", "F-2", "figure", Q_F2, I_F2, "must_not",
                "NOT (k_Model-2 in 4.00 ± 0.10) —— 若落在里面，说明有限尺寸修正没进代码",
                "±0.10", round(k2a, 4),
                "FAIL-CODE" if as9_hit else "PASS",
                "must_not 被触发：Model-2 的斜率回到 4.00，有限尺寸修正没实现" if as9_hit else "",
                fig="F-2"))

    # ================================================== F-3 -> AS-10, AS-11
    vt0 = vt_model0(M_DIP, A_TUBE, W_WALL, SIGMA)
    tau0 = tau_model0(vt0)
    x99 = distance_to_fraction(0.99, vt0, tau0)
    x99_spec_wrong = vt0 * tau0 * np.log(100)          # 契约里那个错误捷径
    L_PIPE = 1.0
    frac_at_vt = 1.0 - x99 / L_PIPE

    tt = np.logspace(-5, np.log10(60), 500)
    D.update(vt0=vt0, tau0=tau0, x99=x99, x99_spec_wrong=x99_spec_wrong,
             t=tt, v_t_curve=v_of_t(tt, vt0, tau0), x_curve=x_of_t(tt, vt0, tau0),
             frac_at_vt=frac_at_vt)

    AS.append(A("AS-10", "F-3", "figure", Q_F3, I_F3, "value",
                "v/v_t = 0.99 处的下落距离 x = v_t·tau·(ln100 - 0.99) = 0.277 mm（SD-2 修正后）",
                "±2%", f"{x99*1e3:.4f} mm",
                "PASS" if abs(x99 * 1e3 - 0.277) / 0.277 < 0.02 else "FAIL-CODE", fig="F-3"))
    AS.append(A("AS-11", "F-3", "figure", Q_F3, I_F3, "asymptote",
                "1 m 管中处于终速（v/v_t > 0.99）的行程占比 > 99.9%", "—",
                f"{frac_at_vt*100:.4f}%",
                "PASS" if frac_at_vt > 0.999 else "FAIL-MODEL", fig="F-3"))

    # ================================================== F-4 -> AS-12..AS-14
    combos = [
        (5.96e7, 1.0e-3,  6.0e-3),
        (3.50e7, 0.5e-3,  8.0e-3),
        (5.96e7, 2.0e-3, 10.0e-3),
        (1.50e7, 1.5e-3,  7.0e-3),
        (5.96e7, 0.3e-3, 12.0e-3),
    ]
    p1_0, p1_2, p2s = [], [], []
    for s, w, a in combos:
        b0 = b_model0(M_DIP, a, w, s)
        b2 = damping(R_MAG, L_MAG, MS, a, w, s)
        p1_0.append(float(pi1(M_MASS * G / b0, M_DIP, a, w, s)))
        p1_2.append(float(pi1(M_MASS * G / b2, M_DIP, a, w, s)))
        p2s.append(float(pi2(w, a)))
    sc0 = (max(p1_0) - min(p1_0)) / np.mean(p1_0)
    sc2 = (max(p1_2) - min(p1_2)) / np.mean(p1_2)
    D.update(combos=combos, p1_0=p1_0, p1_2=p1_2, p2s=p2s, scatter0=sc0, scatter2=sc2)

    AS.append(A("AS-12", "F-4", "figure", Q_F4, I_F4, "collapse",
                "Model-0：5 组不同 (sigma,w,a) 的 Pi_1 相对散布 < 0.1%（应为恒等式）", "0.1%",
                f"{sc0*100:.4f}%", "PASS" if sc0 < 1e-3 else "FAIL-CODE", fig="F-4"))
    AS.append(A("AS-13", "F-4", "figure", Q_F4, I_F4, "asymptote",
                "Pi_2 -> 0 时 Pi_1 -> 1024/45 = 22.756", "±0.5%",
                f"{np.mean(p1_0):.4f}",
                "PASS" if abs(np.mean(p1_0) - PI1_THEORY) / PI1_THEORY < 5e-3 else "FAIL-CODE",
                fig="F-4"))
    AS.append(A("AS-14", "F-4", "figure", Q_F4, I_F4, "collapse",
                "Model-2：Pi_1 相对散布 > 5%（即**不**坍缩 —— 这是预期的结论）", "—",
                f"{sc2*100:.2f}%", "PASS" if sc2 > 0.05 else "FAIL-MODEL",
                "坍缩失败是预期结果：A-1 崩溃引入了第三个无量纲组 L/a。"
                "原文亲口说「这个『坍缩失败』本身就是结论」。", fig="F-4"))

    # ================================================== F-5 -> AS-15, AS-16
    zz = np.linspace(-6 * A_TUBE, 6 * A_TUBE, 2001)
    dphi2 = dphi_dz(R_MAG, L_MAG, MS, A_TUBE, zz)
    dphi_d = dphi_dz_dipole(M_DIP, A_TUBE, zz)
    antisym = float(np.max(np.abs(dphi2 + dphi2[::-1])) / np.max(np.abs(dphi2)))

    # 峰位必须**收敛**，不能是网格分辨率的产物 —— 先粗定位再用 Brent 精修
    from scipy.optimize import minimize_scalar
    ipk = int(np.argmax(np.abs(dphi2)))
    z_lo, z_hi = zz[max(ipk - 3, 0)], zz[min(ipk + 3, len(zz) - 1)]
    res = minimize_scalar(lambda z: -abs(float(dphi_dz(R_MAG, L_MAG, MS, A_TUBE, z))),
                          bracket=None, bounds=(min(z_lo, z_hi), max(z_lo, z_hi)),
                          method="bounded", options=dict(xatol=1e-9))
    zpk = abs(float(res.x))
    zpk_dip = peak_z_dipole(A_TUBE)
    # 双峰：恰好两个极值，符号相反
    pos_pk = zz[int(np.argmax(dphi2))]
    neg_pk = zz[int(np.argmin(dphi2))]
    two_peaks = bool(pos_pk * neg_pk < 0)
    D.update(z=zz, dphi2=dphi2, dphi_dip=dphi_d, zpk=zpk, zpk_dip=zpk_dip,
             antisym=antisym, two_peaks=two_peaks)

    AS.append(A("AS-15", "F-5", "figure", Q_F5, I_F5, "monotonic",
                "dPhi/dz 严格反对称: max|f(z)+f(-z)| / max|f| < 1e-10", "机器精度",
                f"{antisym:.3e}", "PASS" if antisym < 1e-10 else "FAIL-CODE", fig="F-5"))
    AS.append(A("AS-16", "F-5", "figure", Q_F5, I_F5, "peak",
                "双峰结构存在（恰好两个极值，符号相反）；报告峰位相对 a/2 的偏离", "双峰必须存在",
                f"z_peak = {zpk*1e3:.3f} mm  vs  a/2 = {zpk_dip*1e3:.3f} mm "
                f"（偏离 {(zpk/zpk_dip - 1)*100:+.1f}%）；双峰: {two_peaks}",
                "PASS" if two_peaks else "FAIL-MODEL",
                "峰位显著偏离点偶极子的 a/2 —— 这是 A-1 崩溃的又一个独立证据，"
                "不是代码错（见 AS-16 判读）。", fig="F-5"))

    # ---- AS-27：**结构性** must_not。冒烟测试逼出来的（见 acceptance.md）。
    #
    # 注入「点偶极子场 + 正确的径向积分」后，v_t-a 的斜率落在 3.79 —— 既不是 4.00
    # （AS-9 的陷阱），也不是真值 3.44（AS-8），**从两条断言之间溜过去了**。
    #
    # 因为 spec 埋的陷阱是按「整个 Model-2 偷偷变成 Model-0」校准的，而真实的 bug
    # 往往是**只少了一个修正**。
    #
    # 教训：**must_not 不能只检查「拟合出来的数」，必须检查「结构」。**
    # 峰位是场的**结构性质**，不是拟合量：点偶极子场的峰**解析地**落在 a/2
    # （d/dz[z(a²+z²)^{-5/2}] = 0 ⇒ z = ±a/2），有限长磁体的落在 ≈ L/2。
    peak_at_dipole = abs(zpk - zpk_dip) / zpk_dip < 0.05
    AS.append(A("AS-27", "F-5", "figure", Q_F5,
                "结构性 must_not（冒烟测试逼出来的）：如果涡流峰位落在点偶极子解析预言的 a/2 上，"
                "那说明代码根本没在用有限长磁体的场 —— 你只是把 Model-0 换了个壳。"
                "峰位是场的**结构**性质，不是拟合量，因此比「斜率是不是 4.00」可靠得多。",
                "must_not",
                "NOT (|z_peak - a/2| / (a/2) < 5%) —— 若落在 a/2 上，说明用的是点偶极子场",
                "5%（a/2 = 3.00 mm vs L/2 = 5.00 mm，两者相差 67%，5% 的带宽绰绰有余）",
                f"|z_peak - a/2|/(a/2) = {abs(zpk-zpk_dip)/zpk_dip*100:.1f}%",
                "FAIL-CODE" if peak_at_dipole else "PASS",
                "must_not 被触发：涡流峰落在 a/2 上 —— 你在用点偶极子场冒充有限长磁体的场"
                if peak_at_dipole else "", fig="F-5"))

    # ================================================== targets -> AS-17..19
    b0b = float(b_model0(M_DIP, A_TUBE, W_WALL, SIGMA))
    for aid, sym, q, got, tol in (
        ("AS-17", "b",      Q_TB, b0b,          1e-3),
        ("AS-18", "v_t",    Q_TV, float(vt0),   5e-3),
        ("AS-19", "\\tau",  Q_TT, float(tau0),  5e-3),
    ):
        want = TARGET[sym]["baseline_value"]
        dev = abs(got - want) / want
        AS.append(A(aid, sym, "target", q, None, "value",
                    f"Model-0 数值 == baseline_value = {want}", f"±{tol*100}%",
                    round(got, 8), "PASS" if dev < tol else "FAIL-CODE",
                    "" if dev < tol else f"偏差 {dev*100:.3f}% 超过 {tol*100}% —— 参数读错或单位错"))

    # ================================================== A-1 -> AS-20
    b2_base = damping(R_MAG, L_MAG, MS, A_TUBE, W_WALL, SIGMA)
    vt2_base = M_MASS * G / b2_base
    dev_base = (vt2_base - vt0) / vt0
    a1_trig = abs(k2a - 4.0) > 0.3
    D.update(b2_base=b2_base, vt2_base=vt2_base, dev_base=dev_base)

    AS.append(A("AS-20", "A-1", "risky_check", Q_A1, None, "slope",
                "报告 (i) a=6mm 处 v_t 相对偏差；(ii) 指数 k。触发条件 |k-4| > 0.3 -> P5 降级",
                "阈值 0.3，取自 pass_criterion 原文",
                f"(i) 基准点偏差 {dev_base*100:+.1f}%；(ii) k = {k2a:.4f}，|k-4| = {abs(k2a-4):.4f}",
                "PRESCRIBED" if a1_trig else "PASS",
                "触发了 pass_criterion 里**预先注册**的应对动作：把 P5 降级。"
                "这不是 HARKing —— 动作在数据出现之前就写在 spec 里了（预注册）。"
                if a1_trig else ""))

    # ================================================== A-2 -> AS-21..23
    #  判读 (a)：径向积分 vs 薄壁近似，**两者都用有限长磁体的场**（隔离 A-2 本身）
    a2 = {}
    for w in (1.0e-3, 3.0e-3):
        b_thin = damping(R_MAG, L_MAG, MS, A_TUBE, w, SIGMA, thin_wall=True)
        b_full = damping(R_MAG, L_MAG, MS, A_TUBE, w, SIGMA, thin_wall=False)
        a2[w] = abs(b_full - b_thin) / b_thin
    d1, d3 = a2[1.0e-3], a2[3.0e-3]
    D.update(a2_dev_1mm=d1, a2_dev_3mm=d3)

    AS.append(A("AS-21", "A-2", "risky_check", Q_A2, I_A2, "deviation",
                "w = 1 mm（基准）处，径向积分 vs 薄壁近似的相对偏差 < 15%",
                "**15%，直接取自 spec 原文。作者已知实测会超过它，仍照写。**",
                f"{d1*100:.2f}%", "PASS" if d1 < 0.15 else "FAIL-MODEL",
                "" if d1 < 0.15 else
                f"A-2 **没跨过它自己设的杆**：台账 criterion_check 自称「一阶修正 O(w/a)≈17%」、"
                f"pass_criterion 把门槛设在 15%，实测 {d1*100:.1f}%。"
                f"Gate 0 已过（0.0059%），代码被证明是对的 —— 这是真实的假设失效，不是代码错。"))
    AS.append(A("AS-22", "A-2", "risky_check", Q_A2, I_A2, "deviation",
                "w = 3 mm（w/a=0.5）处相对偏差 > 20%", "20%，取自 spec",
                f"{d3*100:.2f}%", "PASS" if d3 > 0.20 else "FAIL-MODEL"))
    as23_hit = d3 < 0.05
    AS.append(A("AS-23", "A-2", "risky_check", Q_A2, I_A2, "must_not",
                "NOT (w=3mm 处偏差 < 5%) —— 若 <5%，说明径向积分根本没实现", "5%，取自 spec",
                f"{d3*100:.2f}%", "FAIL-CODE" if as23_hit else "PASS",
                "must_not 被触发：径向积分没实现" if as23_hit else ""))

    # ================================================== Gate 1 -> AS-24..26
    #  ★ 收敛门必须在**扫描端点**上也做，不能只在基准点做。
    #    （和 Skill 1 的「机制预算必须做扫描端点检查」是同一个道理。）
    #    冒烟测试注入 4 证明了这条：绝对截断长度会在扫描的一端悄悄失效，
    #    基准点上看不出来，Gate 0 也过 —— 但大 a 端每个点都偏小一点，于是斜率是错的。
    g1 = G8.gate1_convergence(verbose=False)
    rows = g1["numbers"]["rows"]
    w_tol = max(rows, key=lambda r: r["d_tol"])
    w_tr = max(rows, key=lambda r: r["d_trunc"])
    AS.append(A("AS-24", "gate-1", "convergence", "n/a", None, "value",
                "求积容差收紧 10x 后 b 的相对变化 < 0.01%（基准点 + a 扫描的两个端点）",
                "0.01%（= 断言容差 0.1% 的 1/10）",
                f"最差 {w_tol['d_tol']*100:.6f}%（在「{w_tol['point']}」）",
                "PASS" if w_tol["d_tol"] < 1e-4 else "FAIL-CODE"))
    AS.append(A("AS-25", "gate-1", "convergence", "n/a", None, "value",
                "广义积分截断扩大 2x 后 b 的相对变化 < 0.01%（基准点 + a 扫描的两个端点）",
                "0.01%", f"最差 {w_tr['d_trunc']*100:.6f}%（在「{w_tr['point']}」）",
                "PASS" if w_tr["d_trunc"] < 1e-4 else "FAIL-CODE"))

    aa2 = sweep("a", 17)                       # 扫描点数加密 2x
    v2_a2 = np.array([vt_model2(R_MAG, L_MAG, MS, a, W_WALL, SIGMA, M_MASS, G) for a in aa2])
    k2a_dense, _ = slope(aa2, v2_a2)
    dk = abs(k2a_dense - k2a)
    AS.append(A("AS-26", "gate-1", "convergence", "n/a", None, "value",
                "扫描点数加密 2x 后拟合斜率 k 的变化 < 0.005", "0.005",
                f"{dk:.6f}", "PASS" if dk < 5e-3 else "FAIL-CODE"))

    D["gates"] = [g0, g1, G8.gate2_layered(verbose=False), G8.gate3_analytical(verbose=False)]
    D["a1_triggered"] = a1_trig

    if verbose:
        print("=" * 86)
        print("验收断言")
        print("=" * 86)
        print(f"  {'id':<7} {'来源':<9} {'类型':<11} {'实测':<44} 判定")
        print("  " + "-" * 82)
        for a in AS:
            v = a["verdict"]
            mark = {"PASS": " ", "PRESCRIBED": "*", "FAIL-MODEL": "!", "FAIL-CODE": "X"}[v]
            print(f"  {a['id']:<7} {a['source']:<9} {a['assert_kind']:<11} "
                  f"{str(a['measured'])[:43]:<44} {mark} {v}")
        print()
        cnt = {}
        for a in AS:
            cnt[a["verdict"]] = cnt.get(a["verdict"], 0) + 1
        print("  " + "   ".join(f"{k}: {v}" for k, v in sorted(cnt.items())))
        print()

    return AS, D


if __name__ == "__main__":
    banner()
    run()
