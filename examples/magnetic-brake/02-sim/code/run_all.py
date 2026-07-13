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
import bfigures as BFIG

T0 = time.time()

# ---- 逐字抄写（同 acceptance.py / acceptance.md）
Q_A1 = ACC.Q_A1
Q_A2 = ACC.Q_A2
PRESCRIBED_A1 = ("若 |k-4| > 0.3，则 P5 被数值判定为不可靠，"
                 "必须在 01-analysis.md 的预测表中把 P5 降级并说明")
PRESCRIBED_A2 = ("把 P2 的适用域收窄到 w/a ≲ 0.03，并在 01-analysis.md 的预测表中说明")


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
    print("=" * 86)
    print("模型验证：中间量 B 场（model_validation_checks[V-1]）")
    print("=" * 86)
    BG = BFIG.make_all(AS)        # V-1 … V-4（AS 传进去，V-4 的断言要画在图上）
    print()

    # ================================================== status 判定
    verdicts = [a["verdict"] for a in AS]
    if "FAIL-CODE" in verdicts:
        status = "FAIL-CODE"
        reason = "有断言判 FAIL-CODE。不许交付下游。"
    elif "FAIL-MODEL" in verdicts:
        status = "MODEL-CHALLENGED"
        bad = [a["id"] for a in AS if a["verdict"] == "FAIL-MODEL"]
        reason = (f"{', '.join(bad)} 判 FAIL-MODEL。Gate 0 已通过，代码被证明是对的 —— "
                  f"这是真实的假设失效，触发反向边（docs/pipeline.md §5.3）。")
    elif "PRESCRIBED" in verdicts:
        status = "PRESCRIBED-REVISION"
        pre = [a["id"] for a in AS if a["verdict"] == "PRESCRIBED"]
        reason = (
            f"{', '.join(pre)} 判 PRESCRIBED —— 命中 Skill 1 在 pass_criterion 里**预先注册**的分支，"
            f"已照办。这不是失败：动作在数据出现之前就写在 spec 里了（归档 model-spec-r1.json 是物证），"
            f"**这是预注册，不是事后合理化（P16）**。\n"
            f"  · A-1：|k−4| = {abs(D['k2a']-4):.4f} > 0.3 ⇒ P5 降级（仅在 a ≫ L 时成立）。\n"
            f"  · A-2：基准点偏差 {D['a2_dev_1mm']*100:.2f}%，落在预期区间 (15%, 26%) 内 ⇒ "
            f"P2 适用域收窄到 w/a ≲ 0.03（该处偏差 {D['a2_dev_small']*100:.1f}%）。\n"
            f"  两条 RISKY 假设都**如预期地不成立** —— 模型边界被正确定位，这正是它们被标为 RISKY 的意义。\n"
            f"  （历史：r1 那次运行判 MODEL-CHALLENGED，见 02-sim/results-r1.json 与 "
            f"model-challenge-r1.md。Skill 1 已按物理理由修订至 r3——A-2 的一阶系数漏了个 2。）"
        )
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

    def _verdict(ids: list[str]) -> str:
        v = [x["verdict"] for x in AS if x["id"] in ids]
        return ("FAIL-CODE" if "FAIL-CODE" in v else
                "FAIL-MODEL" if "FAIL-MODEL" in v else
                "PRESCRIBED" if "PRESCRIBED" in v else "PASS")

    figures = []
    # ★ F-5 有**自己的**静止帧了。
    #
    #   此前这里写的是 `path=rel(figs["F-1"]["png"])` —— 因为 F-5 的 kind 是 animation，
    #   没有静态 PNG，于是拿 F-1 的顶上。后果：**两张图共用一个文件**，Skill 3 照 `path`
    #   取图会把幂律图配上涡流的 caption 摆进 PPT。没有任何检查会发现 —— F-1.png 确实存在。
    #
    #   **动画也必须出一张静止帧**（PPT/PDF 印不出动画；Skill 4 要打开 PNG 看；
    #   SIMULATION 戳在 SVG 里 grep）。交互页是**加分项**，不是替代品。
    #   check_sim.py 现已机械检查：FIG-PATH-DUP + FIG-NOSTILL。
    for fid in ("F-1", "F-2", "F-3", "F-4", "F-5"):
        ids = fig_as.get(fid, [])
        f = dict(id=fid, path=rel(figs[fid]["png"]), path_svg=rel(figs[fid]["svg"]),
                 assertion_ids=ids, verdict=_verdict(ids),
                 simulation_stamped=True, caption=caps[fid])
        if fid == "F-5":
            f["path_interactive"] = rel(f5)
        figures.append(f)

    # ---- V-1 … V-4：模型验证图（中间量 B 场）
    vcaps = {
        "V-1": "真实的 B 场 vs 点偶极子场。**管壁正坐在偶极子近似错得最厉害的地方**——"
               "z=0 处误差 102%（高估整整一倍）。这把 A-1 的崩溃从「间接推断」变成「直接看见」。",
        "V-2": f"管壁处的 B_r **就是涡流的驱动源**（EMF = v·2πa·B_r）。精确峰位在 |z| = "
               f"{BG['V-2_zpk']:.2f} mm ≈ L/2（磁体端面），而偶极子预言 a/2 = 3.00 mm。"
               f"B_z 在 z=0 处被偶极子高估 2 倍。与 F-5 的涡流峰位是同一个数。",
        "V-3": f"轴上 B_z：数值积分与教科书闭式解**完全重合**（误差 {BG['G-A']['err']:.1e}）。"
               f"磁体中心 B_z(0,0) = {BG['G-A']['b_center']:.3f} T = μ₀M_s/√2 —— **算之前就预言了这个数**。",
        # 每个数都从 BG 里来，一个都不许硬编码 —— caption 会被 Skill 3 **逐字**抄进 PPT，
        # 硬编码的数字会和结果悄悄漂移（这正是设计审查 D12 要抓的）。
        "V-4": f"把「a ≫ L」变成一个数：v_t 要 10% 精度需 a/L > {BG['V-4']['q10']:.1f}，"
               f"本实验 {BG['V-4']['a_over_L']:.2f} —— 差约 2 倍。"
               f"（全程薄壁，**只隔离 A-1**：{BG['V-4']['err_here']:.0f}%，"
               f"**不是** Model-2 vs Model-0 的 +{(BG['V-4']['f_total']-1)*100:.1f}%"
               f"——后者含 A-1×A-2 两条，且是**相乘**的。）",
    }
    # ★ assertion_ids 从 fig_as 来 —— **不许编 id**。
    #
    #   此前这里写的是 `assertion_ids=[f"AS-V{vid[-1]}"]`，即 AS-V1…AS-V4 ——
    #   **这四个 id 在 assertions[] 里一个都不存在。**
    #
    #   为什么它能活到今天：FIG-NOASSERT 只查「assertion_ids 非空」，而一个编出来的
    #   id 是非空的，于是它大摇大摆走了过去。**非空 ≠ 有效。**
    #   连带掩盖了一个更糟的事实：**V-4 一条真断言都没有** —— 而 FIG-NOASSERT
    #   本来就是为了抓这个而写的。（V-4 现在有 AS-32…AS-35 了。）
    #
    #   check_sim.py 现已加 FIG-ASSERT-DANGLING：**凡是 id 之间的引用，都必须解析一遍。**
    for vid in ("V-1", "V-2", "V-3", "V-4"):
        ids = fig_as.get(vid, [])
        figures.append(dict(
            id=vid, path=f"02-sim/figures/{vid}.png", path_svg=f"02-sim/figures/{vid}.svg",
            assertion_ids=ids, verdict=_verdict(ids),
            simulation_stamped=True, caption=vcaps[vid]))

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
                     f"基准点 w=1mm 偏差 **{D['a2_dev_1mm']*100:.2f}%**，落在预期区间 (15%, 26%) 内 ✓"
                     f"（下界 = 结论所需的门槛，上界 = 点偶极子场的闭式值 25.95%）。"
                     f"结构性 must_not（AS-23）：b/w 相对变化 {D['bw_var']*100:.1f}% 且单调下降 —— "
                     f"**径向积分确实实现了**（若它是常数，说明根本没实现）。"
                     f"w=3mm 处偏差 {D['a2_dev_3mm']*100:.2f}%。"),
             holds=False,
             prescribed_action=PRESCRIBED_A2,
             prescribed_action_taken=True,
             impact_on_predictions=(
                 "A-2 **如预期地不成立** —— 这不是失败，是模型边界被正确定位。"
                 "【r3】原台账的一阶估计 O(w/a)≈17% **漏了系数 2**：径向积分的被积函数是 ∝ r^-4"
                 "（额外的 1/r 来自 dr/2πr 的权重），积出来 b_full/b_thin = (1/3ε)[1-(1+ε)^-3] "
                 "= 1 - 2ε + O(ε²)。闭式精确值 25.95%（桌上可算，不需任何数值）。"
                 "后果：(1) Model-0 的闭式解 (11) 在基准点就带有约 26% 的薄壁误差——"
                 "**这是独立于 A-1 的另一份**；(2) **P2（v_t ∝ w⁻¹）的适用域已收窄到 w/a ≲ 0.03**"
                 f"（该处偏差 {D['a2_dev_small']*100:.1f}%），基准点 w/a=0.167 不在适用域内。"
                 "注意 A-1 与 A-2 的失效是**相乘**的：×1.3993 · ×1.3059 = ×1.8273 ⇒ v_t 偏差 +82.7%。")),
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

    # ================================================== ★ 任务逐条打勾
    #  真实的 IYPT 报告，最后一页就是这张表。Skill 3 直接拿它做总结页。
    TASKS = {t["id"]: t for t in SPEC["tasks"]}
    tasks_answered = [
        dict(task_id="T-1", quoted_statement=TASKS["T-1"]["statement"],
             answered=True, by_figures=["F-5", "V-1", "V-2", "V-3"],
             answer=("**重力驱动与涡流耗散的竞争达到平衡**：驱动力恒为 Mg（与 v 无关），"
                     "而涡流阻尼 ∝ v，故系统必然收敛到唯一终速 v_t = Mg/b。"
                     "涡流由**管壁处的径向磁场 B_r** 驱动（EMF = v·2πa·B_r），"
                     "呈**反对称双峰**（前方排斥、后方吸引，两者都阻碍下落——Lenz）。"
                     "机制预算已排除空气阻力、摩擦、磁滞等候选。")),
        dict(task_id="T-2", quoted_statement=TASKS["T-2"]["statement"],
             answered=True, by_figures=["F-1", "F-2"],
             answer=(f"v_t ∝ σ^(-1.00) w^(-1) a^(+4) B_r^(-2) M^(+1)（Model-0，零自由参数）。"
                     f"**σ 的 -1 精确成立**（两个模型都给 -1.0000）。"
                     f"**但 a^4 站不住**：有限长磁体给出的指数是 {D['k2a']:.2f}，不是 4.00 —— "
                     f"因为 A-1（点偶极子，判据 a≫L）在 a/L=0.60 处根本不成立。P5 已按预注册动作降级。"
                     f"w^(-1) 亦被 A-2 削弱，适用域收窄到 w/a ≲ 0.03。")),
        dict(task_id="T-3", quoted_statement=TASKS["T-3"]["statement"],
             answered=True, by_figures=["F-4", "V-4"],
             answer=(f"**相关**：σ, w, a, m(B_r), M —— 数据坍缩图证明 Π₁ = f(Π₂) 这个标度结构"
                     f"本身是对的（Model-0 的 5 组参数散布 0.0000%）。"
                     f"**不相关**：管长（瞬态只占 0.28 mm）、管材磁化率（铜 χ_m ≈ -1e-5）。"
                     f"**但坍缩在 Model-2 下失败（散布 {D['scatter2']*100:.1f}%）——这本身就是结论**："
                     f"A-1 崩溃引入了**第三个**无量纲组 L/a，也就是说「磁体长度」其实是相关的，"
                     f"而 Model-0 的标度分析看不见它。V-4 给出定量边界：v_t 要 10% 精度需 a/L > 1.1。")),
        dict(task_id="T-4", quoted_statement=TASKS["T-4"]["statement"],
             answered=True, by_figures=["F-3"],
             answer=(f"**一阶弛豫，无过冲、无振荡、无多稳、无混沌**（线性阻尼 F = bv）。"
                     f"加速段只占 {D['x99']*1e3:.3f} mm —— **1 m 管中 99.97% 的行程处于终速**，"
                     f"故「全程恒速」是安全的近似。**但这一条是被证明的，不是被默认的。**")),
    ]

    # ================================================== ★ 中间量验证（不是验最终结果）
    BGA, BGB, BGC = BG["G-A"], BG["G-B"], BG["G-C"]
    validation_checks = [
        dict(id="V-1", intermediate_quantity="磁体的磁场分布 B(r,z)，特别是管壁处的径向分量 B_r(a,z)",
             passed=all([BGA["passed"], BGB["passed"], BGC["passed"], BG["conv"]["passed"]]),
             figure="02-sim/figures/V-1.png",
             paths=[
                 dict(how="轴上闭式解：与有限长螺线管的教科书公式逐点对拍。"
                          "并且 B_z(0,0) = μ₀M_s/√2 = 0.919 T 是**算之前就写下的预言**（因 R = L/2）",
                      result=f"最大相对误差 {BGA['err']:.2e}；B_z(0,0) = {BGA['b_center']:.4f} T"
                             f"（预言 {BGA['b_center_pred']:.4f} T）",
                      passed=bool(BGA["passed"])),
                 dict(how="远场极限：s ≫ L 时必须退化为点偶极子场",
                      result=f"s = 50L 处相对偏差 {BGB['rows'][-1]['err']*100:.5f}%",
                      passed=bool(BGB["passed"])),
                 dict(how="★ B_r 的**两条完全不同**的推导路径：① 把侧面电流拆成圆环，"
                          "用 Biot–Savart + 椭圆积分积起来；② 由 Φ = 2πr·A_φ 与 B_r = −∂A_φ/∂z，"
                          "得 B_r = −(1/2πr)·∂Φ/∂z（互感 + Leibniz 化简后有闭式）。"
                          "**两条路毫无共同之处。**",
                      result=f"最大相对误差 {BGC['err']:.2e}",
                      passed=bool(BGC["passed"])),
                 dict(how="收敛门：Gauss 求积节点 400 → 800",
                      result=f"相对变化 {BG['conv']['err']:.2e}",
                      passed=bool(BG["conv"]["passed"])),
             ],
             note=("**「最终结果对了」不代表「模型对了」。** b ∝ ∫(∂Φ/∂z)² 是场的**平方**的积分："
                   "若场整体错一个常数因子 c、而 M_s 的反推又漏掉 1/c，b 仍然「对」，终速也「对」——"
                   "**但 v_t 对 a 的指数会错，涡流峰位也会错。用末速度反证模型，正好看不见这类错误。**"
                   "所以这里验的是链条**中间**的那个量（B 场），用**三条互不依赖**的路。"
                   "实验上对应：高斯计沿轴取点测 B，**反推印证 M_s**（而不是用标称 B_r）。")),
    ]

    results = dict(
        problem_slug=SPEC["problem"]["slug"],
        model_spec_version="r4",
        tasks_answered=tasks_answered,
        validation_checks=validation_checks,
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
