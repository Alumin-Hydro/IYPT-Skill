#!/usr/bin/env python3
r"""验收断言（Stage 1，写在求解器之前）。每条 quoted_expectation **逐字**从 model-spec
的对应字段抄来（check_sim 机械校验是子串）。run() 计算 D（实测量）+ AS（断言）。"""
from __future__ import annotations
import math
import numpy as np

import model as M
import gates as GATES
from params import (SPEC, OMEGA1, A0, E_REST, G, C, L, F1, F1_BASE, K_H_BASE, A_THR_BASE, Q_ROD)

# ── 引文池（保证是 model-spec 字段的逐字子串）──────────────────────────────
_FIG = {f["id"]: f for f in SPEC["figures"]}
_TGT = {t["symbol"]: t for t in SPEC["targets"]}
_RSK = {c["assumption_id"]: c for c in SPEC["risky_assumption_checks"]}

def _fig_q(fid, sub):
    assert sub in _FIG[fid]["expected_shape"], (fid, sub)
    return sub
def _tgt_q(sym, sub):
    field = _TGT[sym]["analytical_prediction"] + " " + (_TGT[sym].get("scaling_law") or "")
    assert sub in field, (sym, sub)
    return sub
def _rsk_q(aid, sub):
    field = (_RSK[aid].get("pass_criterion", "") + " " + _RSK[aid].get("degenerate_signature", ""))
    assert sub in field, (aid, sub)
    return sub


def _mk(aid, sk, src, quote, kind, expect, measured, verdict, tol=None, interp=None, note=None, figref=None):
    a = dict(id=aid, source=src, source_kind=sk, quoted_expectation=quote,
             assert_kind=kind, expect=expect, measured=measured, verdict=verdict)
    if tol: a["tolerance"] = tol
    if interp: a["interpretation"] = interp
    if note: a["verdict_note"] = note
    if figref: a["figure_ref"] = figref
    return a


def run():
    w, A, e = OMEGA1, A0, E_REST
    D = {}
    g0 = GATES.gate0(); g1 = GATES.gate1()
    D["gate0"], D["gate1"] = g0, g1

    # 共振曲线 → 峰位
    fs = np.linspace(0.5 * F1, 1.5 * F1, 4001)
    Af = M.resonance_A(fs, F1, Q_ROD)
    D["res_fs"], D["res_A"] = fs, Af
    D["res_peak"] = float(fs[np.argmax(Af)])

    # h̄ vs (Aω)² 坍缩：扫 A（固定 e），拟合斜率 k_h
    As = np.array([0.5, 0.75, 1.0, 1.5, 2.0, 3.0]) * A0
    Aw2 = (As * w) ** 2
    hbs = np.array([M.hbar(a, w, e) for a in As])
    slope = float(np.polyfit(Aw2, hbs, 1)[0])
    D["collapse_As"], D["collapse_Aw2"], D["collapse_hb"] = As, Aw2, hbs
    D["slope_kh"] = slope
    D["kh_dev"] = slope / K_H_BASE - 1

    # h̄ vs 理论（基准点）
    D["hb_sim"] = M.hbar(A, w, e)
    D["hb_theory"] = M.hbar_theory(A, w, e)
    D["hb_dev"] = D["hb_sim"] / D["hb_theory"] - 1
    D["cv"] = M.bounce_cv(A, w, e)          # 分布宽度（随机相位 ~1；锁相 ~0）

    # e 依赖（发散结构）：h̄(e) vs (1+e)/(1-e)
    es = np.array([0.4, 0.5, 0.6, 0.7, 0.8])
    D["e_es"] = es
    D["e_hb"] = np.array([M.hbar(A, w, ee) for ee in es])
    D["e_theory"] = np.array([M.hbar_theory(A, w, ee) for ee in es])

    # Lyapunov：混沌 λ>0 + 可积对拍 λ=ln e
    D["lyap_chaos"] = g0["lyap_chaos"]
    D["lyap_integrable"] = g0["lyap_integrable"]

    # regime：f/f_bounce = Γ/π·√((1+e)/2(1-e))，边界 Γ~π（几处 Γ 报比值）
    D["gamma_base"] = M.gamma_of(A, w)
    D["ffb"] = D["gamma_base"] / math.pi * math.sqrt((1 + e) / (2 * (1 - e)))

    # risky A-1：峰位在 c/4L（固定-自由）vs c/2L（自由-自由）
    D["peak_c4L"] = C / (4 * L)
    D["peak_c2L"] = C / (2 * L)
    D["A1_dev"] = D["res_peak"] / D["peak_c4L"] - 1

    # risky A-4：斜率 k 在扫描范围内是否恒定（换碰撞速度=换 A 段，看局部斜率漂移）
    k_lo = float(np.polyfit(Aw2[:3], hbs[:3], 1)[0])
    k_hi = float(np.polyfit(Aw2[3:], hbs[3:], 1)[0])
    D["A4_slope_lo"], D["A4_slope_hi"] = k_lo, k_hi
    D["A4_slope_var"] = abs(k_hi / k_lo - 1)

    # V-1 中间量：棒尖振幅独立（共振曲线峰位 = f_1，独立于弹跳）
    D["V1_peak_dev"] = D["res_peak"] / F1_BASE - 1

    # ── 断言 ───────────────────────────────────────────────────────────
    AS = []
    AS.append(_mk("AS-1", "target", "k_h", _tgt_q("k_h", "h̄=k_h·(Aω)²"), "limit",
                  "Gate0：单碰撞解析精确、A→0⟹h̄→0（单调）、e→1⟹h̄→∞（单调）、可积极限 λ=ln e<0",
                  f"single_err={g0['single_collision_err']:.1e}；A→0 单调={g0['Ato0_monotone']}；"
                  f"e→1 单调={g0['eto1_monotone']}；λ_integrable={g0['lyap_integrable']:.3f}(≈ln e={math.log(e):.3f})",
                  "PASS" if g0["passed"] else "FAIL-CODE", tol="纯数学恒等式：single<1e-12、λ 偏 ln e<0.05"))
    AS.append(_mk("AS-2", "figure", "F-1", _fig_q("F-1", "在 f_1=c/4L 处尖峰"), "peak",
                  "共振曲线峰在 f_1=c/4L", f"峰在 {D['res_peak']:.0f} Hz（c/4L={D['peak_c4L']:.0f}，偏 {D['A1_dev']:+.2%}）",
                  "PASS" if abs(D["A1_dev"]) < 0.05 else "FAIL-CODE", tol="<5%",
                  interp="峰位按共振曲线极大定；固定-自由 c/4L vs 自由-自由 c/2L 差 2×（A-1 退化特征）", figref="F-1"))
    AS.append(_mk("AS-3", "figure", "F-3", _fig_q("F-3", "过原点直线，斜率 k_h=(1+e)/[4g(1-e)]"), "slope",
                  "h̄ vs (Aω)² 过原点直线，斜率 = k_h（零参）",
                  f"斜率 {D['slope_kh']:.5f} vs k_h={K_H_BASE:.5f}（偏 {D['kh_dev']:+.2%}）",
                  "PASS" if abs(D["kh_dev"]) < 0.05 else "FAIL-MODEL", tol="<5%（Gate0 已过 ⟹ 不符即物理）",
                  interp="随机相位稳态斜率；不同 (A,ω) 坍缩到同一斜率", figref="F-3"))
    AS.append(_mk("AS-4", "target", "k_h", _tgt_q("k_h", "h̄=k_h·(Aω)²"), "deviation",
                  "基准点 h̄ = 理论闭式", f"h̄_sim={D['hb_sim']*1e3:.3f}mm vs 理论 {D['hb_theory']*1e3:.3f}mm（偏 {D['hb_dev']:+.2%}）",
                  "PASS" if abs(D["hb_dev"]) < 0.05 else "FAIL-MODEL", tol="<5%"))
    AS.append(_mk("AS-5", "figure", "F-4", _fig_q("F-4", "高 Γ 弥散为随机相位带"), "must_not",
                  "must_not：弹高**不许**是单值锁相（那是忽略能量泵入的退化模型）——分布必须宽",
                  f"CV={D['cv']:.3f}（随机相位应 >>0；单值锁相 CV→0）",
                  "PASS" if D["cv"] > 0.3 else "FAIL-CODE", tol="CV>0.3（结构性：宽 vs 单值离散）",
                  interp="CV 宽 ⟹ 随机相位统计稳态；若 CV→0 说明代码退化成『抛到峰值速度』的单值模型", figref="F-4"))
    AS.append(_mk("AS-6", "figure", "F-6", _fig_q("F-6", "λ 在混沌区 >0"), "value",
                  "混沌 λ>0，且可积极限 λ<0（证明正 λ 是真混沌不是噪声）",
                  f"λ_chaos={D['lyap_chaos']:+.2f}（>0）；λ_integrable={D['lyap_integrable']:+.3f}（<0）",
                  "PASS" if (D["lyap_chaos"] > 0 and D["lyap_integrable"] < 0) else "FAIL-CODE",
                  tol="λ_chaos>0 且 λ_integrable<0", interp="弹跳映射最大 Lyapunov（每次碰撞）；可积对拍=固定相位", figref="F-6"))
    AS.append(_mk("AS-7", "figure", "F-5", _fig_q("F-5", "以 Γ~π 分界"), "value",
                  "regime 由 Γ 定，f/f_bounce=Γ/π·√((1+e)/2(1-e))，工作点在随机相位区（>>1）",
                  f"Γ={D['gamma_base']:.0f}，f/f_bounce={D['ffb']:.0f}（>>1 ⟹ 随机相位）",
                  "PASS" if D["ffb"] > 10 else "FAIL-MODEL", tol="f/f_bounce>>1", figref="F-5",
                  interp="读法：regime 由单一 Γ 划界（f/f_bounce=Γ/π·√因子），工作点 f/f_bounce>>1 判为随机相位区；不取『混沌需另一个独立参数』的读法"))
    AS.append(_mk("AS-8", "risky_check", "A-1", _rsk_q("A-1", "两者差 2×，离散"), "must_not",
                  "A-1 退化特征（must_not）：共振峰**不许**落在 c/2L（自由-自由）——若落在 c/2L 说明 BC 取错，退化回自由-自由",
                  f"峰在 {D['res_peak']:.0f} Hz（偏 c/4L {D['A1_dev']:+.2%}）；到 c/2L={D['peak_c2L']:.0f} 的距离 {D['res_peak']/D['peak_c2L']-1:+.1%}（远，非退化）",
                  "PASS" if abs(D["A1_dev"]) < 0.05 else "FAIL-MODEL", tol="峰位离 c/2L 远（>40%）；离 c/4L 近（<5%）",
                  note="★ 诚实局限（r2-H1'）：加 1f+2f 偏置后 14kHz 处两种 BC 都有峰，峰位单读数不足以定 BC——此断言只验『无谐波理想扫频』下的峰位；实测需模式形状/多点测振"))
    AS.append(_mk("AS-9", "risky_check", "A-4", _rsk_q("A-4", "k 在扫描范围内恒定（相对变化 <10%）"), "must_not",
                  "A-4 退化特征（must_not）：h̄ vs (Aω)² 的斜率**不许**随扫描系统性漂移——漂移则 e(u) 速度依赖（退化）",
                  f"低段斜率 {D['A4_slope_lo']:.4f} vs 高段 {D['A4_slope_hi']:.4f}（变化 {D['A4_slope_var']:.2%}）",
                  "PASS" if D["A4_slope_var"] < 0.10 else "PRESCRIBED", tol="斜率漂移 <10%（常数 e）",
                  note="常数 e 下斜率应恒定；若漂移>10% ⟹ e(u) 速度依赖（A-4 RISKY 的退化特征）"))
    AS.append(_mk("AS-10", "figure", "V-1", _fig_q("V-1", "A(f) 峰证明棒被声共振驱动"), "peak",
                  "V-1 中间量：棒尖振幅 A(f) 峰位独立验证（不由弹高反推）",
                  f"A(f) 峰在 {D['res_peak']:.0f} Hz = f_1（偏 {D['V1_peak_dev']:+.2%}）",
                  "PASS" if abs(D["V1_peak_dev"]) < 0.05 else "FAIL-CODE", tol="<5%",
                  interp="共振曲线峰位独立于弹跳链条——验中间量而非拿弹高倒推", figref="V-1"))
    return AS, D


def aggregate_status(AS):
    verds = [a["verdict"] for a in AS]
    if any(v == "FAIL-CODE" for v in verds):
        return "FAIL-CODE", "有 FAIL-CODE 断言（Gate0/must_not/收敛/中间量）"
    if any(v == "FAIL-MODEL" for v in verds):
        return "MODEL-CHALLENGED", "Gate0 已过但有断言违反（走反向边）"
    if any(v == "PRESCRIBED" for v in verds):
        return "PRESCRIBED-REVISION", "命中预注册分支"
    return "PASS", "全部断言通过"


if __name__ == "__main__":
    import sys; sys.stdout.reconfigure(encoding="utf-8")
    AS, D = run()
    for a in AS:
        print(f"  {a['verdict']:16s} {a['id']:6s} {a['measured'][:80]}")
    print(aggregate_status(AS))
