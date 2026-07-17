#!/usr/bin/env python3
r"""acceptance.md 的可执行版：25 条断言（AS-1..AS-25），每条带逐字引文。

★ 引文纪律（零号规则）：
  - 所有 `quoted_expectation` 用 `_slice()` **程序化地从 model-spec.json 切出来**，
    不手打 —— 手打一次就会走样，走样的方向永远对自己有利。
  - `_selfcheck_quotes()` 在 run() 开头把每条引文对着 check_sim.py 同款的引文池
    验一遍（norm 后子串），本地先炸，不留给 check_sim。

★ 判定规则（acceptance.md 定死）：limit/must_not/收敛 被违反 ⟹ FAIL-CODE；
  Gate 0 已过后契约形状被违反 ⟹ FAIL-MODEL；命中预注册分支 ⟹ PRESCRIBED。
"""
from __future__ import annotations

import re
import time

import numpy as np

import field as FLD
import gates as GATES
import model0 as M0
import model2 as M2
from field import BASE, G0, Gp0_0, zpk_model0
from params import (A0_BASE, GAMMA_OC, GAMMA_OC2, K_SPRING, L_IND, M_EFF,
                    N2_TURNS, N_TURNS, OMEGA0, R_C, R_C2, R_TEST, SPEC, SWEEP)

_FIG = {f["id"]: f for f in SPEC["figures"]}
_RISK = {c["assumption_id"]: c for c in SPEC["risky_assumption_checks"]}
_TGT = {t["symbol"]: t for t in SPEC["targets"]}
_EQ = {e["id"]: e for e in SPEC["equations"]}
_VAL = {v["id"]: v for v in SPEC["model_validation_checks"]}
_ASM = {a["id"]: a for a in SPEC["assumptions"]}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _slice(text: str, start: str, end: str | None = None) -> str:
    """从原文切出 [start, …end] 的逐字子串。切不到直接炸 —— 契约变了必须知道。"""
    i = text.index(start)
    j = (text.index(end, i) + len(end)) if end else len(text)
    return text[i:j]


#: 引文池（与 check_sim.py 的 check_quotes 完全同构；validation/assumption 是本轮回填的）
def _pool() -> dict[str, str]:
    p = {}
    for f in SPEC["figures"]:
        p[f"figure:{f['id']}"] = f.get("expected_shape", "")
    for c in SPEC["risky_assumption_checks"]:
        p[f"risky_check:{c['assumption_id']}"] = " ".join(
            (c.get("pass_criterion") or "", c.get("task") or "",
             c.get("degenerate_signature") or ""))
    for t in SPEC["targets"]:
        p[f"target:{t['symbol']}"] = (t.get("analytical_prediction", "") + " "
                                      + (t.get("scaling_law") or ""))
    for e in SPEC["equations"]:
        p[f"equation_limit:{e['id']}"] = ((e.get("numerical_notes") or "") + " "
                                          + (e.get("suggested_method") or ""))
    for v in SPEC.get("model_validation_checks", []):
        p[f"validation:{v['id']}"] = " ".join(
            (v.get("intermediate_quantity") or "", v.get("why_it_can_fail_silently") or "",
             " ".join(v.get("independent_checks") or []), v.get("experimental_check") or ""))
    for a in SPEC.get("assumptions", []):
        p[f"assumption:{a['id']}"] = " ".join(
            (a.get("statement") or "", a.get("criterion") or "",
             a.get("criterion_check") or "", a.get("breaks_when") or "",
             a.get("impact_if_false") or ""))
    return p


_N26 = _EQ["(26)"]["numerical_notes"]

#: id → (source_kind, source, quoted_expectation)。切片锚点一律取原文片段。
QUOTES: dict[str, tuple[str, str, str]] = {
    "AS-1": ("equation_limit", "(26)",
             _slice(_N26, "(1) 磁体等比缩小", "扫 ε = 1, 0.3, 0.1, 0.03, 0.01）。")),
    "AS-2": ("validation", "V-1", _VAL["V-1"]["independent_checks"][4]),
    "AS-3": ("equation_limit", "(26)",
             _slice(_N26, "★ **Gate 0b（纯数学，只测积分器）**", "误差 < 1e-10。")),
    "AS-4": ("equation_limit", "(26)",
             _slice(_N26, "★ **Gate 0c（只测能量法推导）", "也不测弱阻尼假设。")),
    "AS-5": ("target", "G_{\\max}", _TGT["G_{\\max}"]["analytical_prediction"]),
    "AS-6": ("target", "z_{\\rm pk}", _TGT["z_{\\rm pk}"]["analytical_prediction"]),
    "AS-7": ("target", "\\gamma", _TGT["\\gamma"]["analytical_prediction"]),
    "AS-8": ("target", "\\zeta", _TGT["\\zeta"]["analytical_prediction"]),
    "AS-9": ("target", "t^*", _TGT["t^*"]["analytical_prediction"]),
    "AS-10": ("target", "A_c", _TGT["A_c"]["analytical_prediction"]),
    "AS-11": ("target", "c_2", _TGT["c_2"]["analytical_prediction"]),
    "AS-12": ("figure", "F-1",
              _slice(_FIG["F-1"]["expected_shape"], "**G(z) 是严格的奇函数", "b ∝ z₀²。**")),
    "AS-13": ("figure", "F-2", _FIG["F-2"]["expected_shape"]),
    "AS-14": ("figure", "F-3",
              _slice(_FIG["F-3"]["expected_shape"], "★★ **主面板（r3 重写）—— P3a",
                     "零 vs 非零 —— 离散。**")),
    "AS-15": ("figure", "F-3",
              _slice(_FIG["F-3"]["expected_shape"], "**副面板 (a)【P3b】", "而长时衰减率回到它）。")),
    "AS-16": ("figure", "F-4",
              _slice(_FIG["F-4"]["expected_shape"], "② **非线性区**（ν > 0.1）",
                     "**⇒ 与 F-5 一致了。**")),
    "AS-17": ("figure", "F-5", _FIG["F-5"]["expected_shape"]),
    "AS-18": ("figure", "F-6", _FIG["F-6"]["expected_shape"]),
    "AS-19": ("risky_check", "A-1", _RISK["A-1"]["pass_criterion"]),
    "AS-20": ("risky_check", "A-2",
              _slice(_RISK["A-2"]["pass_criterion"], "**预期不通过 —— 而这正是本题的答案。**",
                     "(iii) 数值包络与 (23a) 的闭式偏差 < 2%。")),
    "AS-21": ("risky_check", "A-8", _RISK["A-8"]["pass_criterion"]),
    "AS-22": ("validation", "V-1", " ".join(_VAL["V-1"]["independent_checks"])),
    "AS-23": ("validation", "V-2", " ".join(_VAL["V-2"]["independent_checks"])),
    "AS-24": ("validation", "V-3", " ".join(_VAL["V-3"]["independent_checks"])),
    "AS-25": ("assumption", "A-1",
              _slice(_ASM["A-1"]["impact_if_false"], "c₂ 偏 **+4.3%**（0.0345 → 0.0360）")),
}


def _selfcheck_quotes() -> None:
    pool = {k: _norm(v) for k, v in _pool().items()}
    for aid, (kind, src, q) in QUOTES.items():
        assert _norm(q) in pool[f"{kind}:{src}"], f"{aid} 的引文不是 {kind}:{src} 的子串"


# ══════════════════════════════════════════════════════════════ 计算块（填 D）
def _block_field(D):
    gs = FLD.model2()
    D["gs"] = gs
    from scipy.optimize import minimize_scalar
    r = minimize_scalar(lambda z: -abs(gs.G(z)), bounds=(1e-6, 0.03),
                        method="bounded", options=dict(xatol=1e-11))
    D["zpk2"], D["gmax2"] = float(r.x), float(abs(gs.G(r.x)))
    D["zpk0"], D["gmax0"] = zpk_model0()
    D["gp0_2"], D["gp0_0"] = gs.gp0, Gp0_0()
    zs = np.linspace(1e-3, 30e-3, 30)
    D["sym_zero"] = float(abs(gs.G(0.0)) / D["gmax2"])
    D["sym_odd"] = float(np.max(np.abs(gs.G(zs) + gs.G(-zs))) / D["gmax2"])
    D["A_lin"] = FLD.A_lin(gs)
    D["c2_2"] = gs.gp0**2 / (2 * M_EFF * (R_TEST + R_C)) * 1e-6
    D["c2_0"] = D["gp0_0"]**2 / (2 * M_EFF * (R_TEST + R_C)) * 1e-6
    D["c2_sc2"] = gs.gp0**2 / (2 * M_EFF * R_C)                  # SI, 短路
    D["beta_sc2"] = gs.gp0**2 / R_C
    D["A_c2"] = float(np.sqrt(8 * M_EFF * GAMMA_OC / D["beta_sc2"]))
    zg = np.linspace(-25e-3, 25e-3, 401)
    D["f1_zg"], D["f1_G0"], D["f1_G2"] = zg, G0(zg), gs.G(zg)


def _block_f1(D):
    """Γ(z₀) 抛物线（±4mm，A₀=1mm，R=20）→ 顶点/曲率/比值（F-1 右面板的展示数）。"""
    z0s = np.linspace(-4e-3, 4e-3, 9)
    gams = []
    for z0 in z0s:
        tp, Ap, _ = M2.envelope(z0, 1e-3, R_TEST, mode="3state", T=None)
        gams.append(M2.fit_bernoulli(tp, Ap, 1e-3)[0])
    gams = np.array(gams)
    c, b, a = np.polyfit(z0s, gams, 2)
    D["f1_z0s"], D["f1_gams"] = z0s, gams
    D["f1_vertex"] = float(a - b**2 / (4 * c))
    D["f1_zoff"] = float(-b / (2 * c))
    D["f1_curv_mm"] = float(c * 1e-6)                            # 1/(s·mm²)
    ge = [M2.gamma_early(*M2.envelope(z, 1e-3, R_TEST, mode="3state", T=4.0)[:2])
          for z in (-4e-3, 0.0, 4e-3)]
    D["f1_ratio"] = float(min(ge[0], ge[2]) / ge[1])


def _block_f2(D):
    """R 扫描 → (16) 的直线。γ 用 gamma_first（对每个 R 一致的方法；近临界端 R=0
    只剩 1 个内部峰，gamma_early 会静默地给出 y=0 的坏点）。拟合用**相对权重**
    （w=1/y）：y 的动态范围 55×，无权最小二乘的截距会被 R=200 的尾巴主导 ——
    r2 教训「拟合被尾巴主导」的又一次现身。"""
    Rs = np.array([0.0, 2.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0])
    gams = []
    for R in Rs:
        tp, Ap, _ = M2.envelope(D["zpk0"], 1e-3, R, mode="3state",
                                T=min(10.0, max(3.0, M2.default_T(D["zpk0"], R))),
                                A_cut=1e-6)
        gams.append(M2.gamma_first(tp, Ap, 1e-3))
    gams = np.array(gams)
    assert np.all(np.isfinite(gams) & (gams > GAMMA_OC)), f"F-2 γ 提取出坏点: {gams}"
    y = 1.0 / (gams - GAMMA_OC)
    s, ic = np.polyfit(Rs, y, 1, w=1.0 / y)              # 相对权重
    resid = y - (s * Rs + ic)
    R2 = 1 - np.sum(resid**2) / np.sum((y - y.mean()) ** 2)
    D["f2_Rs"], D["f2_gams"], D["f2_y"] = Rs, gams, y
    D["f2_slope"], D["f2_icpt"], D["f2_R2"] = float(s), float(ic), float(R2)
    D["f2_G_backout"] = float(np.sqrt(2 * M_EFF / s))
    D["f2_Rc_backout"] = float(ic / s)
    D["f2_G_dev"] = D["f2_G_backout"] / abs(float(G0(D["zpk0"]))) - 1
    D["f2_Rc_dev"] = D["f2_Rc_backout"] / R_C - 1


def _block_f3(D):
    """A₀ 扫描（居中短路）→ (Γ, Q)。P3a：Q ∝ A₀²；P3b：Γ → γ_oc。附 A₀=0.5mm(<A_c) 点。"""
    A0s = np.array([2e-3, 3e-3, 5e-3, 8e-3])
    out = []
    for A0 in A0s:
        tp, Ap, _ = M2.envelope(0.0, A0, 0.0, mode="3state", T=30.0)
        G_, Q_, ok = M2.fit_bernoulli(tp, Ap, A0)
        out.append((tp, Ap, G_, Q_))
    D["f3_A0s"] = A0s
    D["f3_envs"] = [(tp, Ap) for tp, Ap, *_ in out]
    D["f3_gams"] = np.array([g for *_, g, _ in out])
    D["f3_Qs"] = np.array([q for *_, q in out])
    s, ic = np.polyfit(A0s**2, D["f3_Qs"], 1)
    D["f3_slope"], D["f3_icpt"] = float(s), float(ic)
    D["f3_pred_slope"] = float(D["c2_sc2"] / (4 * GAMMA_OC))
    D["f3_slope_dev"] = D["f3_slope"] / D["f3_pred_slope"] - 1
    # (iii) 包络对 (23a)（拟合形式）的最大偏差 —— A-2(iii) 的 <2%
    devs = []
    for A0, (tp, Ap), (_, _, G_, Q_) in zip(A0s, D["f3_envs"], out):
        Afit = M2.envelope_23a(tp, A0, G_, Q_)
        devs.append(float(np.max(np.abs(Ap - Afit) / Afit)))
    D["f3_dev23a"] = max(devs)
    # A₀ = 0.5 mm < A_c：开路本底主导的展示点（A-2 预注册动作 ① 的对照）
    tp, Ap, _ = M2.envelope(0.0, 0.5e-3, 0.0, mode="3state", T=30.0, A_cut=5e-6)
    D["f3_sub"] = (tp, Ap, *M2.fit_bernoulli(tp, Ap, 0.5e-3)[:2])
    # S-8′ 对照（细实心线）：β′ = (N′/N)²·G'(0)²/R_c′，窗口应 >1 个十进位
    gp0p = D["gp0_2"] * N2_TURNS / N_TURNS
    D["s8_beta_sc"] = gp0p**2 / R_C2
    D["s8_Ac"] = float(np.sqrt(8 * M_EFF * GAMMA_OC2 / D["s8_beta_sc"]))
    D["s8_window"] = float(np.log10(D["A_lin"] / D["s8_Ac"]))
    D["s2_window"] = float(np.log10(D["A_lin"] / D["A_c2"]))


def _block_f4(D):
    """ν(z₀, A₀) 网格 + 契约点名的两个值 + F-4↔F-5 一致性。"""
    gs = D["gs"]
    D["nu_3mm"] = FLD.nu(gs, D["zpk0"], 3e-3)
    D["nu_8mm"] = FLD.nu(gs, D["zpk0"], 8e-3)
    D["nu_at_f5"] = FLD.nu(gs, D["zpk0"], 0.8 * D["zpk0"])
    z0g = np.linspace(0.0, 15e-3, 121)
    A0g = np.geomspace(0.2e-3, 10e-3, 101)
    NU = np.empty((len(A0g), len(z0g)))
    for j, z0 in enumerate(z0g):
        u = np.linspace(-A0g[-1], A0g[-1], 481)
        Gz0 = float(gs.G(z0))
        Gu = gs.G(z0 + u)
        for i, A in enumerate(A0g):
            m = np.abs(u) <= A
            NU[i, j] = np.inf if Gz0 == 0 else float(
                np.max(np.abs(Gu[m] - Gz0)) / abs(Gz0))
    D["f4_z0g"], D["f4_A0g"], D["f4_NU"] = z0g, A0g, NU


def _block_f5(D):
    """坍缩：≥5 组 (M_eff, k, R, z₀) 小振幅 → y=x；大振幅系统性偏离（是结论）。"""
    zpk = D["zpk0"]
    cfgs = [("base", M_EFF, K_SPRING, 20.0, zpk),
            ("M*1.4", 1.4 * M_EFF, K_SPRING, 20.0, zpk),
            ("k*0.6", M_EFF, 0.6 * K_SPRING, 20.0, zpk),
            ("R=5", M_EFF, K_SPRING, 5.0, zpk),
            ("R=100", M_EFF, K_SPRING, 100.0, zpk),
            ("z0=7mm", M_EFF, K_SPRING, 20.0, 7e-3),
            ("z0=13mm", M_EFF, K_SPRING, 20.0, 13e-3)]
    xs, ys, labels = [], [], []
    gs = D["gs"]
    for lab, Me, k, R, z0 in cfgs:
        om0 = float(np.sqrt(k / Me))
        tp, Ap, _ = M2.envelope(z0, 0.8e-3, R, mode="3state", T=6.0, A_cut=1e-6,
                                M_eff=Me, k=k)
        gam = M2.gamma_first(tp, Ap, 0.8e-3)             # 统一方法：A₀ 处的初始衰减率
        xs.append(float(gs.G(z0)) ** 2 / (2 * np.sqrt(Me * k) * (R + R_C)))
        ys.append((gam - GAMMA_OC) / om0)
        labels.append(lab)
    xs, ys = np.array(xs), np.array(ys)
    s, ic = np.polyfit(xs, ys, 1)
    scatter = float(np.std(ys / xs - 1))
    # 大振幅组（A₀/z_pk ≈ 0.77）—— 必须系统性偏离
    big = [("A0=8mm", M_EFF, K_SPRING, 20.0, zpk),
           ("A0=8mm,R=5", M_EFF, K_SPRING, 5.0, zpk),
           ("A0=8mm,k*0.6", M_EFF, 0.6 * K_SPRING, 20.0, zpk)]
    bx, by = [], []
    for lab, Me, k, R, z0 in big:
        om0 = float(np.sqrt(k / Me))
        tp, Ap, _ = M2.envelope(z0, 8e-3, R, mode="3state", T=6.0, A_cut=1e-6,
                                M_eff=Me, k=k)
        gam = M2.gamma_first(tp, Ap, 8e-3)               # ★ 量 A₀=8mm 处的阻尼，
        bx.append(float(gs.G(z0)) ** 2 / (2 * np.sqrt(Me * k) * (R + R_C)))
        by.append((gam - GAMMA_OC) / om0)                #   不是衰剩下的尾巴
    bx, by = np.array(bx), np.array(by)
    D["f5"] = dict(xs=xs, ys=ys, labels=labels, slope=float(s), icpt=float(ic),
                   scatter=scatter, bx=bx, by=by,
                   big_dev=(by / bx - 1).tolist())


def _block_f6(D):
    """相图两族（各 5 条初条件）+ 圈间距比。

    trajs 只画前 T_draw 秒（center 族全程 15 s ≈ 45 圈会叠成实心环，图上什么都看不见）；
    **ratios（AS-18 的断言数据）永远用全程 T** —— 画图截断不许碰断言。
    """
    zpk = D["zpk0"]
    A0s = [1.5e-3, 3e-3, 4.5e-3, 6e-3, 8e-3]
    T_DRAW = {"zpk": 4.0, "center": 6.0}
    fam = {}
    for z0, tag, T in ((zpk, "zpk", 4.0), (0.0, "center", 15.0)):
        trajs, ratios = [], []
        for A0 in A0s:
            sol = M2.simulate3(z0, A0, R_TEST, T=T)
            tt = np.linspace(0, T_DRAW[tag], 4000)
            z, v = sol.sol(tt)[0], sol.sol(tt)[1]
            trajs.append((A0, (z - z0) * 1e3, v / OMEGA0 * 1e3))
            tp, Ap = M2.envelope_from_sol(sol, z0, T, A_cut=1e-6)
            if len(Ap) >= 3:
                r = Ap[1:] / Ap[:-1]
                ratios.append((A0, r))
        fam[tag] = dict(trajs=trajs, ratios=ratios,
                        T_draw=T_DRAW[tag], T_full=T)
    rz = np.concatenate([r for _, r in fam["zpk"]["ratios"]])
    D["f6_cv_zpk"] = float(np.std(rz) / np.mean(rz))
    rc = fam["center"]["ratios"][-1][1]                          # A₀=8mm 的比值序列
    D["f6_rise_center"] = float(rc[-1] - rc[0])
    D["f6_r_center"] = rc
    D["f6"] = fam


def _block_a1(D):
    """A-1：固定 m 扫 L_m —— Model-0 精确不动（0），Model-2 必须动（≈0.38）。"""
    Lms = np.array([5e-3, 10e-3, 15e-3, 20e-3])
    g2 = np.array([GATES._gmax_at_Lm(L) for L in Lms])
    g0 = np.array([zpk_model0(FLD.Geometry(**{**BASE.__dict__, "L_m": L,
                   "M_s": BASE.M_s * BASE.L_m / L}))[1] for L in Lms])
    D["a1_Lms"], D["a1_g2"], D["a1_g0"] = Lms, g2, g0
    D["a1_relvar2"] = float((g2.max() - g2.min()) / g2[1])
    D["a1_relvar0"] = float((g0.max() - g0.min()) / g0[1])
    D["a1_dev_gmax"] = D["gmax2"] / D["gmax0"] - 1
    D["a1_zpk_shift"] = D["zpk2"] / D["zpk0"] - 1


def _block_a8(D):
    """A-8：b≡βz²，A₀ = 2..8 mm，包络 vs (23)；误差 ∝ ζ_eff²（log-log 斜率 = 2）。"""
    beta = Gp0_0() ** 2 / R_C
    A0s = np.array([2, 3, 4, 5, 6, 7, 8]) * 1e-3
    errs, zeffs = [], []
    for A0 in A0s:
        tp, Ap, _ = M2.envelope(0.0, A0, 0.0, mode="2state",
                                bfun=lambda z: beta * z * z, T=12.0,
                                rtol=1e-11, atol=1e-15)
        Ac = M2.envelope_23(tp, A0, beta)
        errs.append(float(np.max(np.abs(Ap - Ac) / Ac)))
        zeffs.append((GAMMA_OC + beta * A0**2 / (8 * M_EFF)) / OMEGA0)
    errs, zeffs = np.array(errs), np.array(zeffs)
    D["a8_A0s"], D["a8_errs"], D["a8_zeffs"] = A0s, errs, zeffs
    D["a8_slope"] = float(np.polyfit(np.log(zeffs), np.log(errs), 1)[0])
    D["a8_e3"], D["a8_e8"] = float(errs[1]), float(errs[-1])
    D["a8_monotone"] = bool(np.all(np.diff(errs) > 0))


def _block_v1(D):
    """V-1 五路独立对拍 + 两条加码交叉（互易 vs 样条、面电流 vs 体平均）。"""
    zs = np.linspace(-24e-3, 24e-3, 13)
    zs = zs[np.abs(zs) > 1e-6]
    # ① 闭式 (6) vs 数值积分（点偶极子 + 薄线圈）
    d1 = max(abs(FLD.G_direct_quad(z) - float(G0(z))) for z in zs) / D["gmax0"]
    # ② 互易性（薄线圈级，数值求导，不经磁通链）
    thin = FLD.Geometry(**{**BASE.__dict__, "band_h": 0.0})
    d2 = float(np.max(np.abs(FLD.G_reciprocity(zs, thin) - G0(zs))) / D["gmax0"])
    # ③ Amperian 面电流 × 离散匝，在点偶极子 + 薄线圈极限下 vs ①②
    eps = 0.03
    gsm = FLD.Geometry(**{**BASE.__dict__, "R_m": BASE.R_m * eps, "L_m": BASE.L_m * eps,
                          "M_s": BASE.M_s / eps**3, "band_h": 0.0})
    zg = np.linspace(-24e-3, 24e-3, 49)
    from scipy.interpolate import CubicSpline
    lam_a = FLD.lam_amperian(zg, gsm, n_ring=80, n_layer=1, per_layer=240)
    Ga = CubicSpline(zg, lam_a).derivative(1)(zs)
    d3 = float(np.max(np.abs(Ga - G0(zs))) / D["gmax0"])
    # ④ 对称性（Model-2 样条，已在 _block_field 算过）
    d4 = max(D["sym_zero"], D["sym_odd"])
    # ⑤ 单匝环极限（gate0 已算）
    d5 = D["g0loop_dev"]
    # 加码 1：互易(厚绕组、点偶极子响应) vs λ 表(磁体缩到 ε=0.01、厚绕组)的 G ——
    #        隔离「厚绕组处理」这一环（不能拿它比 Model-2 全 λ：那差的是 A-1 的体平均，
    #        ~1.7%，是物理不是误差）
    zq = np.linspace(-20e-3, 20e-3, 7)
    eps2 = 0.01
    g_tiny = FLD.Geometry(**{**BASE.__dict__, "R_m": BASE.R_m * eps2,
                             "L_m": BASE.L_m * eps2, "M_s": BASE.M_s / eps2**3})
    zg2 = np.linspace(-24e-3, 24e-3, 97)
    lam_t = FLD.lambda_table(zg2, g_tiny)
    Gt = CubicSpline(zg2, lam_t).derivative(1)(zq)
    x1 = float(np.max(np.abs(FLD.G_reciprocity(zq, BASE) - Gt)) / D["gmax2"])
    # 加码 2：面电流(全尺寸) vs 体平均 λ —— 均匀磁化的两种等价表述，只差离散化
    lam_full = FLD.lam_amperian(zq, BASE, n_ring=80)
    x2 = float(np.max(np.abs(lam_full - D["gs"].lam(zq)))
               / np.max(np.abs(D["gs"].lam(zq))))
    D["v1"] = dict(d1=float(d1), d2=d2, d3=d3, d4=float(d4), d5=float(d5),
                   cross_recip_spline=x1, cross_amperian_volume=x2)


def _block_v2(D):
    """V-2：R_c/L 复算、F-2 截距反推、电感自洽（三态 vs 二维）。"""
    RHO_CU = 1.72e-8                    # 标准铜 @20°C（V-2 ① 原文的公式常数，非模型输入）
    from params import A_COIL, D_WIRE, L_COIL, MU0, N_TURNS
    Rc_calc = RHO_CU * (N_TURNS * 2 * np.pi * A_COIL) / (np.pi * (D_WIRE / 2) ** 2)
    L_calc = (MU0 * N_TURNS**2 * np.pi * A_COIL**2) / (L_COIL + 0.9 * A_COIL)  # Wheeler
    # ③ 三态 vs 二维（γ 之差）。★ SPEC-DEFECT #4（acceptance.md）：
    #   准静态展开给出有效质量修正 ΔM = −LG²/R_tot² ⟹ δγ/γ = 2ζ_el·(ω₀L/R_tot)。
    #   A-4 的「<1.3%」只界了 ω₀L/R_tot，漏了 2ζ_el 的放大 —— 在 R=0（ζ_el≈0.72）
    #   代数地必然超界。修正后的检查：γ 差与准静态预言吻合（<0.3%）+ 基准点 R=20 处
    #   原判据成立（<1.3%）。R=0 的原文失败量级一并记录为 defect 证据。
    out32 = {}
    for R in (0.0, R_TEST):
        tp, Ap, _ = M2.envelope(D["zpk0"], 1e-3, R, mode="3state", T=3.0, A_cut=1e-7)
        g3 = M2.gamma_first(tp, Ap, 1e-3)
        tp, Ap, _ = M2.envelope(D["zpk0"], 1e-3, R, mode="2state", T=3.0, A_cut=1e-7)
        g2 = M2.gamma_first(tp, Ap, 1e-3)
        zeta_el = (g2 - GAMMA_OC) / OMEGA0
        pred = 2 * zeta_el * OMEGA0 * L_IND / (R + R_C)
        out32[R] = dict(g3=float(g3), g2=float(g2), dev=float(abs(g3 / g2 - 1)),
                        pred=float(pred))
    D["v2"] = dict(Rc_calc=float(Rc_calc), Rc_dev=float(Rc_calc / R_C - 1),
                   L_calc=float(L_calc), L_dev=float(L_calc / L_IND - 1),
                   icpt_Rc_dev=float(D["f2_Rc_dev"]),
                   omegaL_ratio=float(OMEGA0 * L_IND / R_C),
                   s32=out32,
                   state32_dev_R20=out32[R_TEST]["dev"],
                   state32_R0_measured=out32[0.0]["dev"],
                   state32_R0_pred=out32[0.0]["pred"],
                   state32_R0_mismatch=float(abs(out32[0.0]["dev"]
                                                 - out32[0.0]["pred"])))


def _block_v3(D):
    """V-3：能量审计（修正恒等式 + 契约原文版的失配证据）、开路守恒、单调性。"""
    aud = M2.energy_audit(D["zpk0"], 3e-3, R_TEST, T=6.0)
    drift, dser = M2.open_circuit_drift(100, series=True)
    D["v3"] = dict(**aud, drift=float(drift), drift_series=dser)


# ══════════════════════════════════════════════════════════════ 断言评估
def _mk(aid, kind, expect, measured, verdict, tol=None, interp=None, note=None,
        figure_ref=None):
    sk, src, q = QUOTES[aid]
    a = dict(id=aid, source=src, source_kind=sk, quoted_expectation=q,
             assert_kind=kind, expect=expect, measured=measured, verdict=verdict)
    if tol is not None:
        a["tolerance"] = tol
    if interp:
        a["interpretation"] = interp
    if note:
        a["verdict_note"] = note
    if figure_ref:
        a["figure_ref"] = figure_ref
    return a


def run(g0=None, verbose: bool = True):
    """跑全部断言。返回 (AS 列表, D 数字仓库)。g0 = gates.run_gate0() 的结果（None 则现跑）。"""
    _selfcheck_quotes()
    t_start = time.time()
    if g0 is None:
        g0 = GATES.run_gate0(verbose=False)
    D: dict = {"gate0": g0}
    n = g0["numbers"]
    D["g0loop_dev"] = n["G0-loop"]["deviation"]

    blocks = [("field", _block_field), ("f1", _block_f1), ("f2", _block_f2),
              ("f3", _block_f3), ("f4", _block_f4), ("f5", _block_f5),
              ("f6", _block_f6), ("a1", _block_a1), ("a8", _block_a8),
              ("v1", _block_v1), ("v2", _block_v2), ("v3", _block_v3)]
    for name, fn in blocks:
        t0 = time.time()
        fn(D)
        if verbose:
            print(f"    [{time.time()-t_start:5.0f}s] 计算块 {name:6s} 完成 "
                  f"({time.time()-t0:.0f}s)")

    t0 = M0.check_baselines(verbose=False)
    AS: list[dict] = []

    # —— Gate 0 族（limit ⟹ 违反即 FAIL-CODE）
    e = n["G0"]
    AS.append(_mk("AS-1", "limit",
                  "err(ε=0.01) < 0.1% 且 err(ε) 随 ε=1,0.3,0.1,0.03,0.01 单调↓",
                  f"err = {['%.2e' % x for x in e['errors']]}，单调={e['monotone']}",
                  "PASS" if e["monotone"] and e["final_ok"] else "FAIL-CODE",
                  tol="0.1%（配方给定）；单调性无容差",
                  interp="三个尺度（R_m、L_m、w）一起收缩，m 固定；"
                         "max_z|λ₂−λ₀|/max_z|λ₀|，z∈[−32,32]mm"))
    lo = n["G0-loop"]
    AS.append(_mk("AS-2", "limit", "λ₀(z; ℓ_c→0)/(μ₀ma²/[2(a²+z²)^{3/2}]) → N = 400.00",
                  f"比值 → {lo['ratios'][-1]:.4f}，偏差 {lo['deviation']:.2e}",
                  "PASS" if lo["passed"] else "FAIL-CODE", tol="<0.1%",
                  figure_ref="V-1"))
    gb = n["G0b"]
    AS.append(_mk("AS-3", "limit", "max_t|z_num − A₀e^{−γt}cos(ω_d t)|/A₀ < 1e-10",
                  f"{gb['error']:.2e}", "PASS" if gb["passed"] else "FAIL-CODE",
                  tol="1e-10（配方给定）",
                  interp="v(0) = −γA₀ 使教科书式为精确解（acceptance.md AS-3）"))
    gc = n["G0c"]
    AS.append(_mk("AS-4", "limit", "max|A_num − A_(23)|/A_(23) < 0.05% @ A₀=3mm",
                  f"{gc['error']:.2e}", "PASS" if gc["passed"] else "FAIL-CODE",
                  tol="0.05%（配方钉死在 A₀=3mm）"))

    # —— Targets（Model-0 必须重现 baseline）
    for aid, sym in (("AS-5", "G_{\\max}"), ("AS-6", "z_{\\rm pk}"), ("AS-7", "\\gamma"),
                     ("AS-8", "\\zeta"), ("AS-9", "t^*"), ("AS-10", "A_c"),
                     ("AS-11", "c_2")):
        r = t0[sym]
        kind = {"AS-5": "value", "AS-6": "peak"}.get(aid, "deviation")
        note = None
        if sym == "c_2":
            note = ("r8 契约的 baseline 曾写 0.0345832（第 4 位 4→5 笔误，偏 +0.29%，"
                    "预注册 spec_defects[2]）——r9 已按 closed_form 复算修正为 0.0344832，"
                    "本断言即按 r9 值验收；SPEC-SELFCONTRADICT 已按存储精度收紧防再犯")
        AS.append(_mk(aid, kind, f"Model-0 {sym} = baseline {r['baseline']:.7g}",
                      f"{r['value']:.7g}（偏差 {r['rel']:+.3%}）",
                      "PASS" if r["ok"] else "FAIL-CODE",
                      tol="0.5%" if aid == "AS-5" else "1%", note=note))

    # —— Figures
    AS.append(_mk("AS-12", "peak",
                  "|G(0)|/|G|max < 1e-12；|G(−z)+G(z)|/|G|max < 1e-12；峰位 = z_pk（<1%）",
                  f"G(0) 比值 {D['sym_zero']:.2e}；奇对称 {D['sym_odd']:.2e}；"
                  f"z_pk(M0) 偏差 {t0['z_{\\rm pk}']['rel']:+.3%}，"
                  f"z_pk(M2) = {D['zpk2']*1e3:.3f} mm",
                  "PASS" if max(D["sym_zero"], D["sym_odd"]) < 1e-12
                  and t0["z_{\\rm pk}"]["ok"] else "FAIL-CODE",
                  tol="对称性 1e-12（纯对称性）；峰位 1%",
                  interp="对称性在 Model-2 样条上判（λ 表逐点独立计算，不做镜像强制 —— "
                         "对称性是被测出来的，不是被构造的）；峰位断言按引文对 Model-0 的 "
                         "z_pk=10.45mm 判，Model-2 的 10.60mm 一并报告",
                  figure_ref="F-1"))
    ok13 = (D["f2_R2"] > 0.999 and abs(D["f2_G_dev"]) < 0.10
            and abs(D["f2_Rc_dev"]) < 0.05)
    AS.append(_mk("AS-13", "slope",
                  "R²>0.999；斜率反推 G(z₀) vs (6) <10%；x 截距 = −R_c <5%",
                  f"R²={D['f2_R2']:.6f}；G 反推 {D['f2_G_backout']:.4f} vs (6) "
                  f"{abs(float(G0(D['zpk0']))):.4f}（{D['f2_G_dev']:+.2%}）；"
                  f"R_c 反推 {D['f2_Rc_backout']:.3f} Ω（{D['f2_Rc_dev']:+.2%}）",
                  "PASS" if ok13 else "FAIL-MODEL",
                  tol="斜率 10%、截距 5%（契约给定）",
                  interp="γ 提取用 A₀=1mm（ν=0.015，线性区干净）+ gamma_early；"
                         "近临界端（R≤5Ω）峰衰得快，A_cut 放到 1µm",
                  note=f"G 反推偏 {D['f2_G_dev']:+.1%} 主要是 A-1（有限磁体 vs 点偶极子 "
                       f"−4.0%）—— 契约 H9 预告过它会吃掉容差的一部分",
                  figure_ref="F-2"))
    ok14 = abs(D["f3_slope_dev"]) < 0.15 and abs(D["f3_icpt"]) < 0.5
    AS.append(_mk("AS-14", "slope",
                  "Q vs A₀² 过原点直线，斜率 = c₂(R=0)/(4γ_oc) <15%，|截距|<0.5",
                  f"斜率 {D['f3_slope']:.4g} vs 预言 {D['f3_pred_slope']:.4g}"
                  f"（{D['f3_slope_dev']:+.2%}），截距 {D['f3_icpt']:+.3f}",
                  "PASS" if ok14 else "FAIL-MODEL",
                  tol="斜率 15%、截距 0.5（criteria[P3a]）",
                  interp="A₀ ∈ {2,3,5,8} mm（引文给定），z₀=0、R=0，Q 由 (23a) 的 "
                         "Bernoulli 拟合提取；预言斜率用 Model-2 的 G'(0)（契约 "
                         "criterion_matrix.correct_model：下游真正积的模型）",
                  figure_ref="F-3"))
    p3b_dev = float(np.max(np.abs(D["f3_gams"] / GAMMA_OC - 1)))
    AS.append(_mk("AS-15", "value", "居中短路 A₀=2/3/5/8mm 的长时 Γ = γ_oc（<10%）",
                  f"Γ = {[f'{g:.4f}' for g in D['f3_gams']]}，最大偏差 {p3b_dev:.2%}",
                  "PASS" if p3b_dev < 0.10 else "FAIL-MODEL",
                  tol="10%（criteria[P3b]）",
                  interp="「长时 Γ」= (23a) 拟合的指数率参数（t→∞ 时包络 ∝ e^{−Γt}），"
                         "T=30s 覆盖尾段 —— 不是初始衰减率（那个是 γ_oc 的 13~86 倍）",
                  figure_ref="F-3"))
    ok16 = (abs(D["nu_3mm"] / 0.133 - 1) < 0.10 and abs(D["nu_8mm"] / 0.70 - 1) < 0.10)
    consist = bool(D["nu_at_f5"] > 0.1
                   and all(d < -0.05 for d in D["f5"]["big_dev"]))
    AS.append(_mk("AS-16", "value",
                  "ν(z_pk,3mm)≈0.133、ν(z_pk,8mm)≈0.70（<10%）；F-4 与 F-5 在 "
                  "(z_pk, A₀/z_pk~0.8) 处结论一致",
                  f"ν(3mm)={D['nu_3mm']:.4f}，ν(8mm)={D['nu_8mm']:.4f}；"
                  f"ν@(z_pk,0.8z_pk)={D['nu_at_f5']:.3f}>0.1 且 F-5 大振幅全部偏离 "
                  f"⟹ 一致={consist}",
                  "PASS" if ok16 and consist else "FAIL-CODE",
                  tol="ν 值 10%；一致性布尔",
                  interp="ν 按 symbols[ν] 的定义在 Model-2 样条上取稠密最大；引文的 "
                         "0.133/0.70 由中点求积的 G 算出（本工作区用 Gauss–Legendre，"
                         "G'' 级差异 ~2% ⟹ ν 差 ~10% 内属求积代差）；「一致」= ν>0.1 "
                         "且 F-5 的 A₀=8mm 组全部偏离 y=x",
                  figure_ref="F-4"))
    f5 = D["f5"]
    small_ok = (abs(f5["slope"] - 1) < 0.01 and abs(f5["icpt"]) < 0.005
                and f5["scatter"] < 0.01)
    big_ok = all(d < -0.05 for d in f5["big_dev"])
    AS.append(_mk("AS-17", "collapse",
                  "小振幅：斜率 1.000±0.01、截距 0±0.005、散布<1%；大振幅必须系统性偏离",
                  f"斜率 {f5['slope']:.4f}，截距 {f5['icpt']:+.5f}，散布 "
                  f"{f5['scatter']:.3%}；大振幅偏离 "
                  f"{['%+.1f%%' % (100*d) for d in f5['big_dev']]}",
                  "PASS" if small_ok and big_ok else "FAIL-CODE",
                  tol="如引文；大振幅偏离 >5% 同向",
                  interp="7 组 (M_eff,k,R,z₀)，A₀=0.8mm（A₀/z_pk=0.077<0.1）；γ 一律取 "
                         "A₀ 处的初始包络衰减率（gamma_first —— 峰提取器会先衰掉半个摆幅，"
                         "gamma_early 对初始非线性把 −28% 稀释成 −2%，实测教训）；x 用 "
                         "M_eff（spec_defects[1]：契约 F-5 的 x 轴写 M 与 targets[ζ] 矛盾）",
                  note="大振幅偏离是结论（Π₄ = A₀/z_pk 登场），不是 bug —— 不许修",
                  figure_ref="F-5"))
    ok18 = D["f6_cv_zpk"] < 0.02 and D["f6_rise_center"] > 0.05
    AS.append(_mk("AS-18", "must_not",
                  "z₀=z_pk 圈间距比恒定（CV<2%）；z₀=0 比值随振幅↓趋于 1（上升>0.05）；"
                  "两族必须不同",
                  f"CV(z_pk)={D['f6_cv_zpk']:.3%}；中心族比值 "
                  f"{D['f6_r_center'][0]:.3f}→{D['f6_r_center'][-1]:.3f}"
                  f"（升 {D['f6_rise_center']:.3f}）",
                  "PASS" if ok18 else "FAIL-CODE",
                  interp="「圈间距比」量化为相邻包络峰比 A_{n+1}/A_n：z_pk 族取全族比值的"
                         "变异系数（线性 ⟹ 恒等于 e^{−γT_d}）；中心族取 A₀=8mm 轨迹的"
                         "首末比值之差（b∝z² ⟹ 随振幅衰减单调升向 1）",
                  note="两族一样 = 代码用了常数阻尼", figure_ref="F-6"))

    # —— RISKY（must_not 承载 degenerate_signature —— DEGEN-UNUSED 查它）
    a1_ok = (abs(D["a1_dev_gmax"]) < 0.15 and D["sym_zero"] < 1e-12
             and D["a1_relvar2"] >= 1e-6 and D["a1_relvar0"] < 1e-12)
    AS.append(_mk("AS-19", "must_not",
                  "|G|max 偏差<15%；G(0)=0 到 1e-12；扫 L_m 时 Model-2 相对变化 ≥1e-6"
                  "（Model-0 精确为 0）",
                  f"|G|max 偏差 {D['a1_dev_gmax']:+.2%}（M2 {D['gmax2']:.4f} vs M0 "
                  f"{D['gmax0']:.4f}）；G(0) {D['sym_zero']:.1e}；L_m 扫描相对变化 "
                  f"M2={D['a1_relvar2']:.3f} / M0={D['a1_relvar0']:.1e}；"
                  f"z_pk 移 {D['a1_zpk_shift']:+.2%}",
                  "PASS" if a1_ok else
                  ("PRESCRIBED" if abs(D["a1_dev_gmax"]) >= 0.15 else "FAIL-CODE"),
                  tol="15%（预期 ≈4.5%）；L_m 门槛 1e-6（预期 0.38）",
                  note="A-1 成立（偏差 4% < 15%）：点偶极子可用于标定，偏差是 A-1 的量度",
                  figure_ref="F-1"))
    b_ratio = (D["sym_zero"] * D["gmax2"]) ** 2 / D["gmax2"] ** 2
    a2_ok = (b_ratio < 1e-10 and ok14 and D["f3_dev23a"] < 0.02)
    AS.append(_mk("AS-20", "must_not",
                  "b(0)/b(z_pk)<1e-10；P3a 斜率<15% 截距<0.5；包络 vs (23a) <2%",
                  f"b(0)/b(z_pk) = {b_ratio:.1e}；P3a {D['f3_slope_dev']:+.2%}/"
                  f"{D['f3_icpt']:+.2f}；包络 vs (23a) 最大偏差 {D['f3_dev23a']:.3%}",
                  "PASS" if a2_ok else "FAIL-CODE",
                  note="A-2 在 z₀=0 被无穷违反 —— 这是 T-2/T-4 的答案，不是灾难；"
                       "b(0)=0 是纯对称性", figure_ref="F-3"))
    a8_ok = (D["a8_e3"] < 5e-4 and 2e-3 <= D["a8_e8"] <= 1e-2
             and abs(D["a8_slope"] - 2.0) < 0.3 and D["a8_monotone"])
    a8_verdict = ("PASS" if a8_ok else
                  ("PRESCRIBED" if D["a8_e8"] > 1e-2 else "FAIL-CODE"))
    AS.append(_mk("AS-21", "must_not",
                  "e(3mm)<0.05%；e(8mm)∈[0.2%,1.0%]（≈0.46%）；log-log 斜率 2.0±0.3；"
                  "误差随 ζ_eff 单调增",
                  f"e(3mm)={D['a8_e3']:.2%}，e(8mm)={D['a8_e8']:.2%}，斜率 "
                  f"{D['a8_slope']:.2f}，单调={D['a8_monotone']}",
                  a8_verdict, tol="斜率 2.0±0.3（离散判别 2 vs 1 vs 0）",
                  note="e(8mm)≈0.5% 是 (23) 的 O(ζ_eff²) 截断误差 —— 不是 bug，不许修",
                  figure_ref="F-3"))

    # —— 中间量验证
    v1 = D["v1"]
    v1_ok = (v1["d1"] < 1e-10 and v1["d2"] < 1e-9 and v1["d3"] < 1e-3
             and v1["d4"] < 1e-12 and v1["d5"] < 1e-3)
    AS.append(_mk("AS-22", "value",
                  "① <1e-10；② 互易 <1e-9；③ Amperian <0.1%；④ 对称 <1e-12；⑤ →N=400 <0.1%",
                  f"① {v1['d1']:.1e} ② {v1['d2']:.1e} ③ {v1['d3']:.1e} "
                  f"④ {v1['d4']:.1e} ⑤ {v1['d5']:.1e}；加码：互易×样条 "
                  f"{v1['cross_recip_spline']:.1e}，面电流×体平均 "
                  f"{v1['cross_amperian_volume']:.1e}",
                  "PASS" if v1_ok else "FAIL-CODE", figure_ref="V-1"))
    v2 = D["v2"]
    v2_ok = (abs(v2["Rc_dev"]) < 5e-3 and abs(v2["L_dev"]) < 5e-3
             and abs(v2["icpt_Rc_dev"]) < 0.05 and v2["omegaL_ratio"] < 0.013
             and v2["state32_dev_R20"] < 0.013 and v2["state32_R0_mismatch"] < 3e-3)
    AS.append(_mk("AS-23", "value",
                  "① R_c/L 复算 <0.5%；② F-2 截距反推 R_c <5%；③ ω₀L/R_c <1.3%；"
                  "三态 vs 二维：R=20 处 <1.3%，R=0 处与准静态预言 2ζ_el·ω₀L/R_tot "
                  "吻合 <0.3%（原文的 <1.3% 在 R=0 代数地不可能 —— spec_defects[3]）",
                  f"R_c 复算 {v2['Rc_calc']:.4f}Ω（{v2['Rc_dev']:+.3%}），L 复算 "
                  f"{v2['L_calc']*1e3:.3f}mH（{v2['L_dev']:+.3%}）；截距反推 "
                  f"{v2['icpt_Rc_dev']:+.2%}；ω₀L/R_c={v2['omegaL_ratio']:.4f}；"
                  f"三态vs二维 R=20: {v2['state32_dev_R20']:.3%}，R=0: 实测 "
                  f"{v2['state32_R0_measured']:.2%} vs 预言 {v2['state32_R0_pred']:.2%}"
                  f"（差 {v2['state32_R0_mismatch']:.2%}）",
                  "PASS" if v2_ok else "FAIL-CODE",
                  note="R=0 的 1.9% 不是 bug：L 的首阶效应是有效质量修正 ΔM=−LG²/R_tot²"
                       " ⟹ δγ/γ = 2ζ_el·ω₀L/R_tot，被 2ζ_el≈1.45 放大 —— A-4 的界漏了"
                       "这个因子（P17：判据界错了量）。实测与准静态预言吻合到 0.05%。",
                  figure_ref="V-2"))
    v3 = D["v3"]
    v3_ok = (v3["resid_correct"] < 1e-10 and v3["drift"] < 1e-10
             and v3["monotone_violation"] < 1e-12)
    AS.append(_mk("AS-24", "value",
                  "①(修正恒等式) <1e-10；② 100 周期漂移 <1e-10；③ dE/dt≤0 逐时刻",
                  f"① {v3['resid_correct']:.1e}（照契约原文（无 ½LI²、系数 2M）则 "
                  f"{v3['resid_aswritten']:.1e} —— spec_defects[0] 的证据）；"
                  f"② {v3['drift']:.1e}；③ 破坏 {v3['monotone_violation']:.1e}",
                  "PASS" if v3_ok else "FAIL-CODE",
                  interp="储能含 ½LI²、阻尼系数 2·M_eff·γ_oc（由 (26) 推出，见 "
                         "acceptance.md Step 0 预注册 #1）", figure_ref="V-3"))
    c2_sep = abs(D["c2_2"] / D["c2_0"] - 1)
    AS.append(_mk("AS-25", "must_not",
                  "|c₂(Model-2)/c₂(Model-0) − 1| ≥ 2%（预期 +4.3%）",
                  f"c₂(M2)={D['c2_2']:.5f} vs c₂(M0)={D['c2_0']:.5f}：{c2_sep:+.2%}",
                  "PASS" if c2_sep >= 0.02 else "FAIL-CODE",
                  tol="门槛 2%（真值 4.3% 的一半；离散区分「修正在/不在」）",
                  note="若回到 Model-0 值 = 有限磁体修正没进代码（「符得太好」）",
                  figure_ref="F-1"))

    if verbose:
        print(f"\n断言表（{len(AS)} 条，{time.time()-t_start:.0f}s）：")
        for a in AS:
            mark = {"PASS": "✓", "PRESCRIBED": "◆"}.get(a["verdict"], "✗✗")
            print(f"  {mark} {a['id']:6s} [{a['verdict']:10s}] {a['measured'][:84]}")
    return AS, D


def aggregate_status(AS) -> tuple[str, str]:
    """FAIL-CODE > MODEL-CHALLENGED > PRESCRIBED-REVISION > PASS。"""
    v = {a["verdict"] for a in AS}
    if "FAIL-CODE" in v:
        ids = [a["id"] for a in AS if a["verdict"] == "FAIL-CODE"]
        return "FAIL-CODE", f"{ids} 判 FAIL-CODE —— 不许交付，回去改代码"
    if "FAIL-MODEL" in v:
        ids = [a["id"] for a in AS if a["verdict"] == "FAIL-MODEL"]
        return "MODEL-CHALLENGED", f"{ids} 判 FAIL-MODEL 且无预注册应对 —— 走反向边"
    if "PRESCRIBED" in v:
        ids = [a["id"] for a in AS if a["verdict"] == "PRESCRIBED"]
        return "PRESCRIBED-REVISION", f"{ids} 命中预注册分支，按契约写的动作执行"
    return "PASS", ""


if __name__ == "__main__":
    AS, D = run()
    st, why = aggregate_status(AS)
    print(f"\nstatus = {st}  {why}")
