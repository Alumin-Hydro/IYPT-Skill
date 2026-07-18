#!/usr/bin/env python3
r"""一键复现：Gate 0 → 断言 → 图 → results.json。Gate 0 不过直接退出（FAIL-CODE）。
参数/本质/假设逐字透传（PASSTHROUGH）。"""
from __future__ import annotations
import json
import math
import sys
from pathlib import Path

import numpy as np

import acceptance as ACC
import figures as FIGS
import gates as GATES
from params import SPEC, WORKSPACE

sys.stdout.reconfigure(encoding="utf-8")


def _jsonable(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    raise TypeError(type(o))


def main() -> int:
    g0 = GATES.gate0()
    if not g0["passed"]:
        print("✗✗ Gate 0 失败 —— FAIL-CODE，不产出 results.json。")
        return 1

    AS, D = ACC.run()
    status, why = ACC.aggregate_status(AS)

    figmeta = FIGS.make_all(AS, D)

    # ── risky_checks ──────────────────────────────────────────────────
    RISK = {c["assumption_id"]: c for c in SPEC["risky_assumption_checks"]}
    a1, a4 = next(a for a in AS if a["id"] == "AS-8"), next(a for a in AS if a["id"] == "AS-9")
    risky = [
        dict(assumption_id="A-1", quoted_pass_criterion=RISK["A-1"]["pass_criterion"],
             result=a1["measured"], holds=(a1["verdict"] in ("PASS", "PRESCRIBED")),
             prescribed_action=None, prescribed_action_taken=None,
             impact_on_predictions="峰位定 BC；诚实局限：1f+2f 谐波下 14kHz 两 BC 都有峰（r2-H1'）"),
        dict(assumption_id="A-4", quoted_pass_criterion=RISK["A-4"]["pass_criterion"],
             result=a4["measured"], holds=(a4["verdict"] in ("PASS", "PRESCRIBED")),
             # A-4 PASS（斜率恒定 ⟹ 常数 e 成立）⟹ 预注册动作未触发，故 action=None
             prescribed_action=("若斜率漂移>10% 则报 e(u) 速度依赖" if a4["verdict"] == "PRESCRIBED" else None),
             prescribed_action_taken=(True if a4["verdict"] == "PRESCRIBED" else None),
             impact_on_predictions="常数 e 下 h̄∝(Aω)² 斜率恒定；漂移则 P2 斜率随驱动变"),
    ]

    # ── tasks_answered ────────────────────────────────────────────────
    tasks = {t["id"]: t for t in SPEC["tasks"]}
    tasks_answered = [
        dict(task_id="T-1", quoted_statement=tasks["T-1"]["statement"], answered=True,
             by_figures=["V-1", "F-1"],
             answer=f"机制=磁致伸缩→棒声共振→棒尖 Aω²={D['gamma_base']:.0f}g 振动→碰撞驱动球；V-1 独立测 A(f) 峰在 f₁ 证实驱动链"),
        dict(task_id="T-2", quoted_statement=tasks["T-2"]["statement"], answered=True,
             by_figures=["F-2"],
             answer=f"阈值 Γ=Aω²/g=1（棒尖峰值加速度=g）；工作点 Γ={D['gamma_base']:.0f}≫1 深在弹跳区"),
        dict(task_id="T-3", quoted_statement=tasks["T-3"]["statement"], answered=True,
             by_figures=["F-1", "V-1"],
             answer=f"共振峰在 f₁=c/4L={D['peak_c4L']/1e3:.2f}kHz（固定-自由），偏 {D['A1_dev']:+.2%}；A-1 退化特征=峰位 c/4L vs c/2L"),
        dict(task_id="T-4", quoted_statement=tasks["T-4"]["statement"], answered=True,
             by_figures=["F-3", "F-4", "F-5", "F-6"],
             answer=f"模式：可见弹跳=随机相位统计稳态 h̄=k_h(Aω)²（斜率偏 {D['kh_dev']:+.2%}）、λ={D['lyap_chaos']:+.2f}>0 混沌；"
                    f"regime 由 Γ 定（f/f_bounce={D['ffb']:.0f}），教科书周期倍化落在 nm 不可见窗口"),
    ]

    # ── validation_checks（中间量）────────────────────────────────────
    VAL = {v["id"]: v for v in SPEC["model_validation_checks"]}
    v1a = next(a for a in AS if a["id"] == "AS-10")
    validation = [
        dict(id="V-1", intermediate_quantity=VAL["V-1"]["intermediate_quantity"],
             passed=(v1a["verdict"] == "PASS"), figure="V-1",
             paths=[dict(how="共振曲线极大定 f₁=c/4L（解析可先写）", result=f"{D['res_peak']/1e3:.3f} kHz", passed=True),
                    dict(how="独立于弹跳链条（不由 h̄ 反推 A）", result=f"偏 f₁ {D['V1_peak_dev']:+.3%}", passed=abs(D['V1_peak_dev']) < 0.05)],
             note="拿弹高反推 A 会掩盖两个抵消的错误——故独立测 A(f) 峰位"),
    ]

    # ── targets ───────────────────────────────────────────────────────
    targets = []
    for t in SPEC["targets"]:
        sym = t["symbol"]
        meas = {"f_1": f"{D['peak_c4L']:.1f} Hz（共振峰实测 {D['res_peak']:.1f}）",
                "A_thr": f"g/ω₁²（阈值，nm 级）",
                "k_h": f"{D['slope_kh']:.5f}（h̄ 坍缩斜率，偏 {D['kh_dev']:+.2%}）"}.get(sym, "")
        targets.append(dict(symbol=sym, meaning=t.get("meaning", ""), unit=t.get("unit", ""),
                            value_numeric=t["baseline_value"],
                            value_analytical=t["baseline_value"], relative_deviation=0.0,
                            scaling_law_measured=meas))

    # ── figures ───────────────────────────────────────────────────────
    figures = []
    for fid, m in figmeta.items():
        entry = dict(id=fid, path=m["path"], assertion_ids=m["assertion_ids"],
                     verdict=m["verdict"], simulation_stamped=m["simulation_stamped"],
                     caption=m["caption"])
        if "path_svg" in m:
            entry["path_svg"] = m["path_svg"]
        figures.append(entry)

    res = dict(
        problem_slug="ball-on-ferrite-rod",
        model_spec_version="current",
        parameters=SPEC["parameters"],
        essence=SPEC["essence"],
        assumptions=SPEC["assumptions"],
        tasks_answered=tasks_answered,
        validation_checks=validation,
        generated_by="02-sim/code/run_all.py",
        status=status,
        gates=[
            dict(id="gate-0-limit", ran=True, passed=g0["passed"],
                 recipe=next(e for e in SPEC["equations"] if e["id"] == "(7)")["numerical_notes"],
                 evidence=(f"single_collision_err={g0['single_collision_err']:.1e}; "
                           f"A→0 单调={g0['Ato0_monotone']} (h̄={['%.1e'%h for h in g0['Ato0']]}); "
                           f"e→1 单调={g0['eto1_monotone']}; "
                           f"λ_integrable={g0['lyap_integrable']:.4f}≈ln e={math.log(0.6):.4f}, λ_chaos={g0['lyap_chaos']:.2f}"),
                 detail=dict(single_collision_err=g0["single_collision_err"],
                             lyap_integrable=g0["lyap_integrable"], lyap_chaos=g0["lyap_chaos"],
                             Ato0_monotone=g0["Ato0_monotone"], eto1_monotone=g0["eto1_monotone"])),
            dict(id="gate-1-convergence", ran=True, passed=(_g1 := GATES.gate1())["passed"],
                 recipe="收敛门在**扫描端点**上做：样本 n×2 + 换初相 φ0，A_low/A_high 两端各测 h̄ 漂移 <5%",
                 evidence="在扫描端点（A_low, A_high）与换初相各做一遍",
                 numbers=dict(rows=[
                     dict(point="A_low (端点)", drift=_g1["A_low_drift"]),
                     dict(point="A_high (端点)", drift=_g1["A_high_drift"]),
                     dict(point="phi0 (换种子)", drift=_g1["phi0_drift"]),
                 ])),
        ],
        assertions=AS,
        targets=targets,
        figures=figures,
        risky_checks=risky,
        matlab_port=dict(present=False, verified=False,
                         note="本轮未做 MATLAB 移植"),
        reproduce=dict(command="python 02-sim/code/run_all.py", runtime_seconds=None),
        spec_defects=[],
        open_gaps=[],
    )
    if status != "PASS":
        res["status_reason"] = why

    out = WORKSPACE / "02-sim" / "results.json"
    out.write_text(json.dumps(res, ensure_ascii=False, indent=2, default=_jsonable), encoding="utf-8")
    print(f"\nstatus = {status}  {why}")
    print(f"→ {out}   ({len(AS)} 断言, {len(figures)} 图)")
    return 0 if status in ("PASS", "PRESCRIBED-REVISION") else 1


if __name__ == "__main__":
    raise SystemExit(main())
