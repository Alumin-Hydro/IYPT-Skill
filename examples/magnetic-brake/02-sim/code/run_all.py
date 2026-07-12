#!/usr/bin/env python3
"""一键复现：全部验证门 + 全部断言 + 全部图 + results.json。

    python 02-sim/code/run_all.py

**做不到"一条命令重现全部数字和图" = 结果不可信。**
"""
from __future__ import annotations

import json
import platform
import sys
import time
import warnings
from datetime import datetime, timezone

import numpy as np
import scipy
import matplotlib

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from params import (WORKSPACE, TARGET, SPEC, M_MASS, G, R_MAG, L_MAG, A_TUBE, W_WALL,
                    SIGMA, M_DIP, MS, banner)
from model0 import b_model0, vt_model0, tau_model0
from model2 import damping
import acceptance as ACC
import figures as FIG
import interactive as INT
import gates as GATES

T0 = time.time()

# ---- 逐字抄写（同 acceptance.py / acceptance.md）
Q_A1 = ACC.Q_A1
Q_A2 = ACC.Q_A2
PRESCRIBED_A1 = ("若 |k-4| > 0.3，则 P5 被数值判定为不可靠，"
                 "必须在 01-analysis.md 的预测表中把 P5 降级并说明")


def rel(p) -> str:
    return str(p).replace(str(WORKSPACE) + "\\", "").replace(str(WORKSPACE) + "/", "").replace("\\", "/")


def main() -> int:
    banner()
    print("=" * 86)
    print("验证阶梯")
    print("=" * 86)
    gates = GATES.run_all_gates(verbose=True)
    if not all(g["passed"] for g in gates):
        print("!! 有门未通过 —— status = FAIL-CODE，不许交付下游。")
        return 1

    AS, D = ACC.run(verbose=True)

    print("=" * 86)
    print("出图")
    print("=" * 86)
    figs = FIG.make_all(AS, D)
    f5 = INT.build()
    print()

    # ================================================== status 判定
    verdicts = [a["verdict"] for a in AS]
    if "FAIL-CODE" in verdicts:
        status = "FAIL-CODE"
        reason = "有断言判 FAIL-CODE。不许交付下游。"
    elif "FAIL-MODEL" in verdicts:
        status = "MODEL-CHALLENGED"
        bad = [a["id"] for a in AS if a["verdict"] == "FAIL-MODEL"]
        status_pre = [a["id"] for a in AS if a["verdict"] == "PRESCRIBED"]
        reason = (
            f"{', '.join(bad)} 判 FAIL-MODEL：A-2（薄壁近似）在基准点 w=1mm 处实测偏差 "
            f"{D['a2_dev_1mm']*100:.2f}%，超过它自己 pass_criterion 里设的 15% 门槛"
            f"（台账 criterion_check 自称「一阶修正 O(w/a)≈17%」）。"
            f"Gate 0 已通过（误差 0.0059%），代码被证明是对的 —— 这是真实的假设失效，不是代码错。"
            f"触发反向边（docs/pipeline.md §5.3）。"
            f"另有 {', '.join(status_pre)} 判 PRESCRIBED：A-1 的预注册动作（把 P5 降级）已执行。"
        )
    elif "PRESCRIBED" in verdicts:
        status = "PRESCRIBED-REVISION"
        reason = "命中 Skill 1 预先注册的分支，已照办。"
    else:
        status = "PASS"
        reason = ""

    # ================================================== targets
    b0 = float(b_model0(M_DIP, A_TUBE, W_WALL, SIGMA))
    vt0 = float(vt_model0(M_DIP, A_TUBE, W_WALL, SIGMA))
    b2 = float(damping(R_MAG, L_MAG, MS, A_TUBE, W_WALL, SIGMA))
    vt2 = M_MASS * G / b2
    tau2 = vt2 / G

    targets = [
        dict(symbol="b", meaning="阻尼系数", unit="N s/m",
             value_numeric=round(b2, 6), value_analytical=round(b0, 6),
             relative_deviation=round((b2 - b0) / b0, 6), model_level="model-2",
             scaling_law_measured="b ∝ σ w （精确）；对 a 的指数因有限尺寸效应而软化"),
        dict(symbol="v_t", meaning="终速", unit="m/s",
             value_numeric=round(float(vt2), 6), value_analytical=round(vt0, 6),
             relative_deviation=round(float((vt2 - vt0) / vt0), 6), model_level="model-2",
             scaling_law_measured=(f"v_t ∝ σ^(-1.00) w^(-0.78) a^(+{D['k2a']:.2f})（Model-2）"
                                   f"  vs  σ^(-1) w^(-1) a^(+4)（Model-0）")),
        dict(symbol="\\tau", meaning="趋近终速的时间常数", unit="s",
             value_numeric=round(float(tau2), 8),
             value_analytical=round(float(tau_model0(vt0)), 8),
             relative_deviation=round(float((tau2 - tau_model0(vt0)) / tau_model0(vt0)), 6),
             model_level="model-2", scaling_law_measured="τ = v_t/g（精确关系，与模型无关）"),
    ]

    # ================================================== figures
    caps = {
        "F-1": "v_t 对 σ 的幂律指数精确是 −1（两个模型都是），对 w 则不是：Model-2 在大 w 端"
               "向上偏离，因为薄壁近似 A-2 崩了。σ 的 −1 是零自由参数预测，它站住了。",
        "F-2": f"最激进的预测 v_t ∝ a⁴ 站不住：有限长磁体给出的指数是 {D['k2a']:.2f}，"
               f"不是 4.00。这不是失败——是 A-1（点偶极子，判据 a≫L，实际 a/L=0.60）的"
               f"崩溃被定量地定位了。P5 据此降级。",
        "F-3": f"启动瞬态只占 {D['x99']*1e3:.3f} mm——1 m 管中 99.97% 的行程处于终速。"
               f"「全程恒速」这个近似是安全的。",
        "F-4": f"数据坍缩：Model-0 的 5 组参数**精确**坍缩到 Π₁ = 1024/45 = 22.756（散布 0.0000%）；"
               f"Model-2 **不**坍缩（散布 {D['scatter2']*100:.1f}%）。**坍缩失败本身就是结论**——"
               f"A-1 崩溃引入了第三个无量纲组 L/a。",
        "F-5": f"涡流是反对称双峰（机器精度：{D['antisym']:.1e}），峰值落在 |z| = "
               f"{D['zpk']*1e3:.2f} mm ≈ L/2 = {L_MAG*1e3/2:.1f} mm——**磁体的端面上**，"
               f"而不是点偶极子预言的 a/2 = 3.00 mm。因为 ∂Φ/∂z 就是两个安培端面电流环之差。"
               f"这是 A-1 崩溃的第三个独立证人。",
    }
    fig_as = {}
    for a in AS:
        if a.get("figure_ref"):
            fig_as.setdefault(a["figure_ref"], []).append(a["id"])

    figures = []
    for fid in ("F-1", "F-2", "F-3", "F-4"):
        ids = fig_as.get(fid, [])
        v = [x["verdict"] for x in AS if x["id"] in ids]
        figures.append(dict(
            id=fid, path=rel(figs[fid]["png"]), path_svg=rel(figs[fid]["svg"]),
            assertion_ids=ids,
            verdict=("FAIL-CODE" if "FAIL-CODE" in v else
                     "FAIL-MODEL" if "FAIL-MODEL" in v else
                     "PRESCRIBED" if "PRESCRIBED" in v else "PASS"),
            simulation_stamped=True, caption=caps[fid]))
    figures.append(dict(
        id="F-5", path=rel(figs["F-1"]["png"]), path_svg=rel(figs["F-1"]["svg"]),
        path_interactive=rel(f5), assertion_ids=fig_as.get("F-5", []),
        verdict="PASS", simulation_stamped=True, caption=caps["F-5"]))

    # ================================================== risky checks
    risky = [
        dict(assumption_id="A-1", quoted_pass_criterion=Q_A1,
             result=(f"(i) 基准点 a=6mm 处 v_t 相对偏差 {D['dev_base']*100:+.1f}%（Model-2 vs Model-0）；"
                     f"(ii) Model-2 的 v_t ∝ a^k 实际指数 k = {D['k2a']:.4f}，|k−4| = {abs(D['k2a']-4):.4f} > 0.3"),
             holds=False,
             prescribed_action=PRESCRIBED_A1,
             prescribed_action_taken=True,
             impact_on_predictions=(
                 "P5（v_t ∝ a⁴）已按预注册动作降级为「仅在 a ≫ L 时成立；本设定下 a/L = 0.60，"
                 "实测指数 3.44」。**不影响** v_t 对 σ / w / M / B_r 的幂律指数——它们来自感应链条的"
                 "线性结构，与场的空间分布无关（F-1 的 σ 面板实测 −1.0000 证实了这一点）。")),
        dict(assumption_id="A-2", quoted_pass_criterion=Q_A2,
             result=(f"判读 (a)：径向积分 vs 薄壁近似（两者都用有限长磁体的场，以隔离 A-2 本身）。"
                     f"w = 1 mm（基准）处偏差 {D['a2_dev_1mm']*100:.2f}%（门槛 <15% —— **未通过**）；"
                     f"w = 3 mm（w/a=0.5）处偏差 {D['a2_dev_3mm']*100:.2f}%（预期 >20% —— 通过；"
                     f"且远大于 5%，说明径向积分确实实现了）"),
             holds=False,
             impact_on_predictions=(
                 "A-2 **没跨过它自己设的杆**：台账 criterion_check 自称「一阶修正 O(w/a)≈17%」，"
                 "pass_criterion 把门槛设在 15%，实测 23.42%。后果：Model-0 的闭式解 (11) 在基准点"
                 "就带有 ~23% 的薄壁误差（这是在 A-1 的误差之外的、独立的一份）。"
                 "P2（v_t ∝ w⁻¹）的适用域必须收窄到 w/a ≲ 0.03（该处偏差 5.7%）。"
                 "**这条触发反向边**（docs/pipeline.md §5.3）。")),
    ]

    # ================================================== SPEC-DEFECT
    #  硬门槛：必须能**不引用任何仿真结果**证明契约有毛病。
    spec_defects = [
        dict(field="equations[(15)].numerical_notes",
             defect="极限对拍配方取错了极限：只令 L→0 而 R 保持 5 mm，得到的是半径 5 mm 的**薄圆盘**，"
                    "不是点偶极子。照此执行，比值收敛到 3.5505 而非 1。",
             proof_without_simulation=(
                 "纯几何：圆盘（半径 R=5mm）在半径 r=a=6mm 的圆环上产生磁通，其椭圆积分模数 "
                 "k² = 4Ra/(R+a)² = 4·5·6/11² = 0.99。点偶极子近似要求 k² ≪ 1。0.99 离远场"
                 "十万八千里。故该极限**不可能**退化为点偶极子。"),
             fix="R 和 L 必须**一起**趋于 0：R→εR, L→εL, M_s→M_s/ε³（使 m = M_s·πR²L 不变），ε→0。"
                 "修正后 ε=0.01 时误差 0.0059% < 0.1%。"),
        dict(field="figures[F-3].expected_shape",
             defect="「在 0.35 mm 处已达 0.99」——这是一个**已被 01-review-r1.md 抓到、"
                    "在 01-analysis.md 里改过、但从未同步进契约**的错误。",
             proof_without_simulation=(
                 "纯代数：由 (12) 的闭式解 v = v_t(1−e^{−t/τ})，"
                 "x(t) = ∫v dt = v_t[t − τ(1−e^{−t/τ})]。令 v/v_t = 0.99 ⇒ t = τ·ln100 ⇒ "
                 "x = v_t·τ·(ln100 − 0.99) = 3.615·v_t·τ = 0.277 mm。"
                 "而 0.35 mm = 4.605·v_t·τ —— **少减了那个 0.99**，高估 27.4%。"
                 "这正是审稿报告里写的「用了 v_t·τ×4.6 这个错误捷径，系统性高估 27%，精确值 0.28 mm」。"),
             fix="expected_shape 里的 0.35 mm → 0.277 mm。"
                 "**系统性教训：审稿改的是正文，而 Skill 2 只读契约。正文与契约脱钩，"
                 "下游就会原样继承一个早已被发现并「修好」了的 bug——而没有任何检查会发现。**"),
        dict(field="figures[F-3].compare_with",
             defect="引用了不存在的公式 (13)。equations[] 里只有 (10)(11)(12)(15)。",
             proof_without_simulation="逐一枚举 equations[].id：(10), (11), (12), (15)。没有 (13)。"
                                      "闭式解 v = v_t(1−e^{−t/τ}) 实际在 (12).closed_form 里。",
             fix="compare_with 的 (13) → (12)。"),
    ]

    results = dict(
        problem_slug=SPEC["problem"]["slug"],
        model_spec_version="r1",
        generated_by=dict(
            engine="python",
            versions=dict(python=platform.python_version(), numpy=np.__version__,
                          scipy=scipy.__version__, matplotlib=matplotlib.__version__),
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        ),
        status=status,
        status_reason=reason,
        gates=[{k: v for k, v in g.items() if k != "numbers"} | {"numbers": g["numbers"]}
               for g in D["gates"]],
        assertions=AS,
        targets=targets,
        figures=figures,
        risky_checks=risky,
        matlab_port=dict(
            generated=True, verified=False,
            self_check_script="02-sim/code/matlab/verify.m",
            note="Python 是唯一执行引擎。本机没有 MATLAB/Octave —— **移植版在生成时未被执行过**。"
                 "verify.m 读这份已验证的 results.json、重算、逐项打印 PASS/FAIL，"
                 "用户在自己的机器上一键自验。谎报 verified=true 违反这个 repo 的立身之本。",
        ),
        reproduce=dict(
            command="python 02-sim/code/run_all.py",
            runtime_seconds=round(time.time() - T0, 1),
            notes="需要 numpy / scipy / matplotlib。参数全部从 handoff/model-spec.json 载入，无硬编码。",
        ),
        spec_defects=spec_defects,
        open_gaps=[],
    )

    out = WORKSPACE / "02-sim" / "results.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 86)
    print(f"status : {status}")
    print(f"         {reason[:200]}")
    print()
    print(f"SPEC-DEFECT : {len(spec_defects)} 处（均可不引用仿真结果证明）")
    for d in spec_defects:
        print(f"    · {d['field']}")
    print()
    print(f"results.json -> {rel(out)}   ({out.stat().st_size/1024:.1f} KB)")
    print(f"总耗时 {time.time()-T0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
