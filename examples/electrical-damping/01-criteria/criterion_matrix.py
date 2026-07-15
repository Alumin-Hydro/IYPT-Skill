#!/usr/bin/env python3
r"""★★★ r4 的判据矩阵 —— **双向表 + 三个 r3 审稿逼出来的新维度**（审稿模式 P18）。

r3 交了一张全绿的表。**r3 的审稿证明：那张表可以被调到全绿。**
四道 CRIT 门查的全是**布尔值** —— 它们看不见「抓得有多勉强」，也看不见「容差从哪来」。

**这一版补上 P18 的五条**：

  ① **容差有来源**（`tolerance_source`）—— 不再是源码里的裸数字。
     r3：`< 0.12` / `< 0.20` / `< 0.15`，正文里要么没有、要么写的是 15%（**矛盾**）。
  ② **★ 扫错误幅度 ε，报「最小可检测幅度」ε\***，不再挑一个数说「抓到了」。
     r3：`bug-C` 设成「β 错 **+30%**」（被 12% 容差抓到 ✓），
     **而作者自己在 `why_a_student_writes_it` 里写着「标称 B_r 公差 ±5% ⟹ b 偏 ±10%」**
     —— **10% < 12% ⟹ 他亲手描述的那个真实场景，五条判据一条都抓不到。**
  ③ **★ 「正确模型」= Model-2**（有限磁体 + 厚绕组）—— **契约命令 Skill 2 积的就是它**。
     r3 用的是 Model-0（点偶极子 + 薄线圈）⟹ G'(0) 差 **+2.2%** ⟹ c₂ 差 **+4.3%**
     ⟹ **P1c 的容差在 Skill 2 开跑之前就被吃掉 1/3。**
  ④ **★ 「不误杀」在协议自己承认的系统误差上跑**（残余定心误差 δ）。
     r3 把 `z0` 钉死在 `0.0`（**精确的零**），而 §9 白纸黑字写着「**不要试图把磁体对准中心**」。
  ⑤ **★ 区分 CAUGHT（判据的字面逻辑抓到）与 DEGENERATE（拟合器崩了）。**
     r3 的 naive-A/B「被五条判据抓到」，明细全是「提不出 Γ」—— **一个记账截断，记了五次。**

**统一的提取**：对每个 z₀ 的包络，拟合精确的 Bernoulli 闭式

    (A₀/A)² = (1+Q)·e^{2Γt} − Q            ⟸ 由 ż = … 精确解出，不是近似

拿到 (Γ, Q) 两个数。于是五条**零自由参数**预言（P1a/b/c、P3a/b）。
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import CubicSpline
from scipy.optimize import curve_fit, minimize_scalar
from scipy.signal import argrelextrema
from scipy.special import ellipe, ellipk

sys.stdout.reconfigure(encoding="utf-8")
MU0 = 4e-7 * np.pi

# ══════════════════════════════════════════════════════════════════ 设定书 S-2
R_MAG, L_MAG, B_R = 5e-3, 10e-3, 1.30
M_S = B_R / MU0
M_DIP = M_S * np.pi * R_MAG**2 * L_MAG                  # 0.8125 A m²

N, L_COIL = 400, 20e-3
# ★ r2-H9：**同一根线不可能轴向 0.45 mm、径向 0.40 mm。** 六方嵌套：层间距 = d·√3/2。
R_BOB, D_ENAM, N_LAYER = 9.0e-3, 0.45e-3, 9
PITCH_R = D_ENAM * np.sqrt(3) / 2                       # 0.3897 mm
A1 = R_BOB + D_ENAM / 2                                 # 最内层导线中心 9.225 mm
A2 = A1 + (N_LAYER - 1) * PITCH_R                       # 最外层 12.343 mm
A_COIL = (A1 + A2) / 2                                  # 平均半径 10.784 mm
W_COIL = (N_LAYER - 1) * PITCH_R + D_ENAM               # 绕组厚 3.568 mm
WIRE_LEN = N * 2 * np.pi * A_COIL
RHO_CU = 1.72e-8                                        # ★ 和文档一致（标准铜 @20°C）
R_C = RHO_CU * WIRE_LEN / (np.pi * (0.20e-3) ** 2)      # ∅0.40 mm 裸线

M_EFF = 5.89e-3 + 2.0e-3 / 3                            # 6.557 g
OMEGA0 = 2 * np.pi * 3.0
K = M_EFF * OMEGA0**2
GAMMA_OC = 0.0413                                       # 开路本底（含导线涡流 0.0097）
R_TEST = 20.0


# ══════════════════════════════════════════════════════════ ★ Model-2 的 G(z)
#  互易性：λ(z) = (M_s/I)·∫_magnet B_coil,z dV   ⟹   G = dλ/dz
#  **λ 是偶函数 ⟹ G(0) = 0 精确**（与模型无关的对称性）；**G'(0) = d²λ/dz²|₀**。
def _Bz_loop(R, rho, z):
    """半径 R 的单匝环（单位电流）在 (rho, z) 的 B_z。椭圆积分，精确。"""
    d2 = (R + rho) ** 2 + z**2
    k2 = np.clip(4 * R * rho / d2, 0, 1 - 1e-14)
    return (MU0 / (2 * np.pi)) / np.sqrt(d2) * (
        ellipk(k2) + (R**2 - rho**2 - z**2) / ((R - rho) ** 2 + z**2) * ellipe(k2))


def _Bz_coil(rho, z, nr=20, nz=20):
    """厚绕组（匝密度均匀）的 B_z（单位电流）。"""
    rs = A1 + (A2 - A1) * (np.arange(nr) + 0.5) / nr
    zs = -L_COIL / 2 + L_COIL * (np.arange(nz) + 0.5) / nz
    tot = np.zeros_like(np.asarray(rho, float))
    for R in rs:
        for zc in zs:
            tot += (N / (nr * nz)) * _Bz_loop(R, rho, z - zc)
    return tot


def _lam(z, nrho=12, nzm=12):
    """磁通链 λ(z)（磁体中心在 z）。"""
    rr = R_MAG * np.sqrt((np.arange(nrho) + 0.5) / nrho)      # 等面积采样
    zz = z + (-L_MAG / 2 + L_MAG * (np.arange(nzm) + 0.5) / nzm)
    RR, ZZ = np.meshgrid(rr, zz, indexing="ij")
    dV = (np.pi * R_MAG**2 / nrho) * (L_MAG / nzm)
    return M_S * _Bz_coil(RR.ravel(), ZZ.ravel()).sum() * dV


#: ★ 预计算 G(z) 的样条 —— ODE 里每步都要它，双重积分太慢。
_ZG = np.linspace(-32e-3, 32e-3, 321)
_LAM = np.array([_lam(z) for z in _ZG])
_G_SPL = CubicSpline(_ZG, _LAM).derivative(1)


def G_true(z):
    """★ Model-2 的换能系数（有限磁体 + 厚绕组）—— **契约命令 Skill 2 积的就是它。**"""
    return _G_SPL(z)


def G_model0(z):
    """Model-0：点偶极子 + 薄线圈（式 (6)）—— r3 的表用的是**这个**，而契约用上面那个。"""
    c, a2 = L_COIL / 2, A_COIL**2
    return (MU0 * (N / L_COIL) * M_DIP / 2) * a2 * (
        (a2 + (z + c) ** 2) ** -1.5 - (a2 + (z - c) ** 2) ** -1.5)


GP0 = abs(CubicSpline(_ZG, _LAM).derivative(2)(0.0))    # |G'(0)| —— λ 的二阶导
GP0_M0 = abs(-1.5 * MU0 * N * M_DIP * A_COIL**2 * (A_COIL**2 + (L_COIL / 2) ** 2) ** -2.5)

ZPK = abs(minimize_scalar(lambda z: -abs(G_true(z)), bounds=(-0.03, -1e-5),
                          method="bounded", options=dict(xatol=1e-11)).x)
GMAX = abs(G_true(-ZPK))
B_PK = GMAX**2                                          # b(z_pk)·(R+R_c)

# ★★ 契约的 `targets[]` 是 **Model-0 的解析预言**（Skill 2 的**对拍基准** —— Gate 0），
#    而这张表的「★ 正确模型」是 **Model-2**（Skill 2 **真正要积的**）。
#    **这是两件不同的事，别混。** 两者的差 —— 就是 r3 审稿 H9 的余量警告：
#    **P1c 的容差在 Skill 2 还没开跑之前，已经被吃掉一部分了。**
ZPK_M0 = abs(minimize_scalar(lambda z: -abs(G_model0(z)), bounds=(-0.03, -1e-5),
                             method="bounded", options=dict(xatol=1e-11)).x)
GMAX_M0 = abs(G_model0(-ZPK_M0))

C2 = GP0**2 / (2 * M_EFF * (R_TEST + R_C))              # 预言曲率 @ R=20 Ω
C2_SC = GP0**2 / (2 * M_EFF * R_C)                      # 短路

# 线圈在磁体处的 B 场形状（naive-A 用它 —— λ(z) ∝ 它，由互易性）
_BC = CubicSpline(_ZG, _LAM)


# ══════════════════════════════════════════════════════════════════ 六个模型
#  ★ 每一个都必须是「学生真的会写出来的东西」，而且 `why` 必须**和代码一致**
#    （r3-H5：bug-E 列了三个成因，**两个产生不出它**）。
def _mk_models(eps_C=0.30, eps_E=0.10):
    """错误幅度是**参数**，不是硬编码的数 —— ε 要被扫描（P18 ②）。"""
    return {
        "★ 正确 (Model-2)":
            lambda z, R: G_true(z) ** 2 / (R + R_C),
        "naive-A 磁通最大处阻尼最大":
            lambda z, R: (GMAX * _BC(z) / _BC(0.0)) ** 2 / (R + R_C),
        "naive-B 常数阻尼 b=b(z_pk)":
            lambda z, R: B_PK / (R + R_C) + 0 * z,
        "bug-C  β 错 +{:.0%}".format(eps_C):
            lambda z, R: (1 + eps_C) * G_true(z) ** 2 / (R + R_C),
        "bug-D  漏了线圈自阻 R_c":
            lambda z, R: G_true(z) ** 2 / (R + 0.1),
        "★ bug-E 中心阻尼不为零 b₀={:.0%}b_pk".format(eps_E):
            lambda z, R: (G_true(z) ** 2 + eps_E * B_PK) / (R + R_C),
        "★ bug-F 线性化 b≡G(z₀)² 常数":
            lambda z, R: G_true(z) ** 2 / (R + R_C) + 0 * z,   # 见下：z 由外部冻结
    }


WHY = {
    "naive-A 磁通最大处阻尼最大":
        "**最常见的直觉，也是本题的头号陷阱**：磁通在中心最大 ⟹ 阻尼在中心最大。"
        "错在把「磁通 λ」当成了「磁通的**梯度** G = dλ/dz」。**这个错误正是本题的全部内容。**",
    "naive-B 常数阻尼 b=b(z_pk)":
        "**题面自己诱导出来的**：\"the damping\" —— 说「the」就预设了阻尼是**一个数**。"
        "任何把阻尼当成一个标量的模型，都长这样。",
    "bug-C":
        "**最容易犯的实现 bug**：G'(0) 的解析式 (7) 漏一个因子（如那个 3/2），"
        "或者用**标称** B_r（公差 ±5% ⟹ b 偏 ±10%）而不是**实测**的 G。\n"
        "★★ **幅度不是挑出来的 —— 它被扫描，报的是「最小可检测幅度」ε\\***（P18 ②）。",
    "bug-D  漏了线圈自阻 R_c":
        "**naive 电路模型**：b ∝ 1/R，R→0 时发散。（真值：线圈自阻设了天花板 b_max = G²/R_c。）",
    "bug-E":
        "**最难抓的一个**：模型的**形状**全对，但多了一个**经过外电路**的常数偏置 "
        "（∝ 1/(R+R_c)）。\n"
        "★ **成因只有一个：磁体倾斜**（横向 EMF 驱动电流走外电路）。\n"
        "★★ **r3 曾列了三个成因，两个是错的**（r3 审稿 H5）：\n"
        "  · 「骨架涡流」**不经过外电路** ⟹ 与 R 无关 ⟹ 开路时也在 ⟹ **被实测的 γ_oc 整份吸收**；\n"
        "  · 「线圈绕得不对称」只**挪动 G 的零点** ⟹ **被 z_off 完全吸收**。\n"
        "  **说得出理由 ≠ 理由是对的。`why_a_student_writes_it` 是一条断言，不是文案。**\n"
        "★ 它是全表的**试金石**：曲率与正确模型一模一样 —— **只有「顶点值」那条判据看得见它。**",
    "★ bug-F 线性化 b≡G(z₀)² 常数":
        "★★ **A-2 的线性化本身**（「在 z₀ 附近，b 可视为常数 b(z₀)」）—— "
        "**这是学生最会写的那个模型，也是最贴近真相的错模型。**\n"
        "**r3 审稿造出来的**：它的 Γ(z₀) **精确地**落在那条抛物线上 ⟹ "
        "**P1a/P1b/P1c 三条全部放行**，只有 P3a（扫 A₀）看得见它。\n"
        "**⟹ 它证明「表宣称的冗余是虚的」：最贴近真相的错模型，只有一条判据抓得到。**",
}
# id 前缀 → WHY 的键（错误幅度写进 id，但 why 不该跟着变）
_WHY_KEY = {"bug-C": "bug-C", "★ bug-E": "bug-E"}


def _why(mid):
    for pre, key in _WHY_KEY.items():
        if mid.startswith(pre):
            return WHY[key]
    return WHY[mid]


# ═══════════════════════════════════════════════════════ 包络提取（统一的地基）
def envelope(model, z0, A0, R, T, freeze_b_at=None):
    """数值积分 (26)，取包络的峰。`freeze_b_at` 用于 bug-F（b 冻结在 z₀）。"""
    def b_of(z):
        return model(freeze_b_at, R) if freeze_b_at is not None else model(z, R)

    def rhs(t, y):
        z, v = y
        return [v, (-K * (z - z0) - (2 * M_EFF * GAMMA_OC + b_of(z)) * v) / M_EFF]

    sol = solve_ivp(rhs, (0, T), [z0 + A0, 0.0], rtol=1e-10, atol=1e-13,
                    dense_output=True, max_step=2e-3)
    tt = np.linspace(0, T, int(T * 6000))
    u = sol.sol(tt)[0] - z0
    idx = argrelextrema(u, np.greater)[0]
    tp, Ap = tt[idx], u[idx]
    m = Ap > 0.03e-3
    return tp[m], Ap[m]


def fit_bernoulli(model, z0, A0, R, T=None, freeze_b_at=None):
    """★ 统一的提取：拟合 (A₀/A)² = (1+Q)e^{2Γt} − Q，返回 (Γ, Q, ok)。

    ★ `ok=False` ⟹ **DEGENERATE**（提不出 Γ），**不是** CAUGHT。
      **r3 把这两者混在一起**：naive-A/B 的「被五条判据抓到」，明细全是「提不出 Γ」
      —— 一个记账截断，被记了五次（P18 ⑤）。
    """
    if T is None:
        c2 = C2 if R > 1e-9 else C2_SC
        T = min(30.0, max(5.0, 5.0 / (GAMMA_OC + c2 * z0**2)))
    tp, Ap = envelope(model, z0, A0, R, T, freeze_b_at)
    if len(tp) < 6:
        return np.nan, np.nan, False
    y = (A0 / Ap) ** 2
    try:
        (Gam, Q), _ = curve_fit(lambda t, G, Q: (1 + Q) * np.exp(2 * G * t) - Q,
                                tp, y, p0=[0.1, 0.5],
                                bounds=([1e-4, 0.0], [50.0, 1e4]), maxfev=20000)
    except Exception:                                    # noqa: BLE001
        return np.nan, np.nan, False
    return Gam, Q, True


# ══════════════════════════════════════════════════════════════════ 五条判据
#  ★★ 容差**必须有来源**（P18 ①）。r3 的 `< 0.12`/`< 0.20`/`< 0.15` 是**裸数字**，
#     而 §9 说 Γ 只测到 2% —— **一条比误差棒宽 6 倍的判据，抓不到一个 10% 的偏置。**
TOL = {
    "P1a": (2.0, "【结构】判据是**比值** Γ(±4mm)/Γ(0)：\n"
                 "  · 正确模型：**≈ 12**（理论 1 + c₂·(4mm)²/γ_oc = 15，A₀ 的贡献把 Γ(0) 抬高了些）\n"
                 "  · **常数阻尼：≡ 1.00**（严格）；naive-A（中心是极大）：**< 1**\n"
                 "  ⟹ 门槛取 **2** —— **远离两者，离散。**\n"
                 "  ★ 不许用严格的 `Γ(0) < Γ(±4mm)` —— 常数阻尼下两边**严格相等**，"
                 "胜负会由浮点噪声决定，**naive-B 就从判据底下溜过去了**。"),
    "P1b": (0.05, "Γ 的测量误差 2%（§9）+ ±4 mm 区间的拟合系统偏差 1% + 余量 ⟹ **5%**"),
    "P1c": (0.12, "**预言侧主导**：c₂ ∝ G'(0)²，而 G'(0) 由高斯计测（±5%）⟹ c₂ 的预言不确定度 "
                  "**±10%**；加测量 2% ⟹ **12%**。\n"
                  "★★ **⟹ 这条判据分辨不了 10% 的 β 误差**（= 用标称 B_r 而非实测 G 的那个场景）。"
                  "**要抓它，必须用高斯计实测 G'(0)** —— 那把预言的不确定度从 10% 压到 2%。"),
    "P3a": (0.15, "斜率 = c₂(R=0)/(4γ_oc)：G'(0)² 给 ±10%，γ_oc 给 ±2%，拟合给 ±3% ⟹ **15%**"
                  "（与 §9 一致）"),
    "P3b": (0.10, "Γ→γ_oc：γ_oc 的开路实测 ±2% + 长时拟合 ±5% + 余量 ⟹ **10%**"),
}


def _scan_gamma(model, A0=1.0e-3, zmax=4e-3, n=9, delta=0.0, freeze=False):
    """扫 z₀ 取 Γ(z₀)。`delta` = **残余定心误差**（P18 ④ —— §9 说对不准中心）。"""
    zs = np.linspace(-zmax, zmax, n) + delta
    out, ok = [], True
    for z in zs:
        g, _, o = fit_bernoulli(model, z, A0, R_TEST,
                                freeze_b_at=(z if freeze else None))
        out.append(g)
        ok &= o
    return zs - delta, np.array(out), ok         # 报告的 z₀ 是**名义**值（实验读数）


def gamma_early(model, z0, A0, R, freeze=False):
    r"""★ 稳健的 Γ 估计：**前几个峰的对数斜率** —— **不需要 Bernoulli 的 6 个峰。**

    **为什么必须有它**（r3 审稿 H3 / P18 ⑤）：
    naive-A 在中心的阻尼极强 ⟹ 包络一个周期就衰完 ⟹ `fit_bernoulli` 返回「提不出 Γ」。
    r3 于是把它记成「被 P1a/P1b/P1c 三条抓到」——
    **而那不是判据在工作，是拟合器崩了。一个记账截断，记了五次。**

    > **但「磁体在中心一下子就停了」本身就是 P1a 的结论。**
    > **一条判据不该因为拟合器崩了就失明 —— 它该直接去看那件事。**

    ⟹ 衰得太快 ⟹ 返回一个**极大的 Γ**（那是一个测量结果，不是失败）。
    """
    tp, Ap = envelope(model, z0, A0, R, T=4.0,
                      freeze_b_at=(z0 if freeze else None))
    if len(tp) < 2:
        return np.inf                      # 半个周期内就衰完 —— Γ「无穷大」，这是结论
    n = min(len(tp), 5)
    return float(-np.polyfit(tp[:n], np.log(Ap[:n]), 1)[0])


def crit_P1a(model, delta=0.0, freeze=False):
    """【结构】Γ(z₀) 在中心取**极小**（不是极大）。极小 vs 极大 —— 离散。

    ★ 用 `gamma_early`（前几个峰的对数斜率），**不用 Bernoulli 拟合** ——
      否则强阻尼的错模型会以「退化」逃掉，而「它一下子就停了」正是本判据要看的东西。
    """
    zs = np.array([-4e-3, 0.0, 4e-3]) + delta
    g = np.array([gamma_early(model, z, 1.0e-3, R_TEST, freeze) for z in zs])
    if not np.isfinite(g[0]) or not np.isfinite(g[2]):
        return None, "DEGENERATE：连端点都提不出 Γ"
    # ★ 必须是**显著地**极小 —— 常数阻尼给 Γ(±4mm)/Γ(0) ≡ 1.00（严格相等），
    #   而一个严格的 `<` 会被浮点噪声决定胜负 ⟹ **naive-B 从判据底下溜过去。**
    r = min(g[0], g[2]) / g[1] if np.isfinite(g[1]) and g[1] > 0 else 0.0
    mid = f"{g[1]:.4f}" if np.isfinite(g[1]) else "∞（一个周期就衰完）"
    return (bool(r > TOL["P1a"][0]),
            f"Γ(±4mm)/Γ(0) = {r:.2f}   [Γ(0)={mid}, Γ(±4mm)={g[0]:.3f}/{g[2]:.3f}]")


def crit_P1b(model, delta=0.0, freeze=False):
    zs, g, ok = _scan_gamma(model, delta=delta, freeze=freeze)
    if not ok:
        return None, "DEGENERATE：提不出 Γ"
    c, b, a = np.polyfit(zs, g, 2)
    vert = a - b**2 / (4 * c)
    d = vert / GAMMA_OC - 1
    return bool(abs(d) < TOL["P1b"][0]), f"顶点={vert:.4f} (γ_oc={GAMMA_OC:.4f}, {d:+.1%})"


def crit_P1c(model, delta=0.0, freeze=False):
    zs, g, ok = _scan_gamma(model, delta=delta, freeze=freeze)
    if not ok:
        return None, "DEGENERATE：提不出 Γ"
    c = np.polyfit(zs, g, 2)[0]
    d = c / C2 - 1
    return bool(abs(d) < TOL["P1c"][0]), f"c₂={c*1e-6:.4f} (预言 {C2*1e-6:.4f}, {d:+.1%})"


def crit_P3a(model, delta=0.0, freeze=False):
    """★【结构+零参】居中短路：Q(A₀) = c₂A₀²/(4Γ) ⟹ Q ∝ A₀²，斜率零自由参数。"""
    A0s = np.array([2.0, 3.0, 5.0, 8.0]) * 1e-3
    Qs = []
    for A0 in A0s:
        G_, Q_, o = fit_bernoulli(model, delta, A0, 0.0, T=30.0,
                                  freeze_b_at=(delta if freeze else None))
        if not o:
            return None, "DEGENERATE：居中+短路 ⟹ 一个周期就把磁体按死了"
        Qs.append(Q_)
    s, ic = np.polyfit(A0s**2, np.array(Qs), 1)
    pred = C2_SC / (4 * GAMMA_OC)
    d = s / pred - 1
    return (bool(abs(d) < TOL["P3a"][0] and abs(ic) < 0.5),
            f"Q∝A₀² 斜率={s:.4g}(预言{pred:.4g}, {d:+.1%}) 截距={ic:+.2f}")


def crit_P3b(model, delta=0.0, freeze=False):
    """【结构】居中短路，长时衰减率必须回到开路值 γ_oc（b(0)=0 的动力学签名）。"""
    G_, _, o = fit_bernoulli(model, delta, 8e-3, 0.0, T=30.0,
                             freeze_b_at=(delta if freeze else None))
    if not o:
        return None, "DEGENERATE：一个周期就按死了"
    d = G_ / GAMMA_OC - 1
    return bool(abs(d) < TOL["P3b"][0]), f"Γ={G_:.4f} vs γ_oc={GAMMA_OC:.4f} ({d:+.1%})"


CRITS = [("P1a", "中心是极小【结构】", crit_P1a),
         ("P1b", "顶点 = γ_oc【零参】", crit_P1b),
         ("P1c", "曲率 = c₂【零参】", crit_P1c),
         ("P3a", "Q ∝ A₀²【结构+零参】", crit_P3a),
         ("P3b", "长时回到 γ_oc【结构】", crit_P3b)]

BAR = "═" * 100
print(BAR)
print("★★★ r4 · 判据 × 模型 —— 双向表 + P18 的三个新维度")
print(BAR)
print(f"  几何（六方嵌套，r2-H9）：a = {A_COIL*1e3:.4f} mm，w = {W_COIL*1e3:.4f} mm，"
      f"R_c = {R_C:.3f} Ω")
print(f"  ★ 正确模型 = **Model-2**（有限磁体 + 厚绕组）—— 契约命令 Skill 2 积的就是它")
print(f"    |G'(0)| = {GP0:.2f}   （Model-0 给 {GP0_M0:.2f}，差 {GP0/GP0_M0-1:+.1%}）")
print(f"    ⟹ c₂ = {C2*1e-6:.4f} 1/(s mm²)   （用 Model-0 会差 {(GP0/GP0_M0)**2-1:+.1%}）")
print(f"    |G|_max = {GMAX:.4f} Wb/m @ z_pk = {ZPK*1e3:.3f} mm")

MODELS = _mk_models()
FREEZE = {"★ bug-F 线性化 b≡G(z₀)² 常数"}

# ═════════════════════════════════════════ ① 双向表（CAUGHT vs DEGENERATE）
rows = {}
for cid, _, fn in CRITS:
    for m, mf in MODELS.items():
        rows[(cid, m)] = fn(mf, freeze=(m in FREEZE))

print()
print("  " + "─" * 96)
print(f"  {'判据':22}" + "".join(f"{m[:11]:>13}" for m in MODELS))
print("  " + "─" * 96)
for cid, name, _ in CRITS:
    cells = []
    for m in MODELS:
        ok, _ = rows[(cid, m)]
        cells.append("✓ PASS" if ok else ("✗ 抓到" if ok is False else "— 退化"))
    print(f"  {cid + ' ' + name[:16]:22}" + "".join(f"{c:>13}" for c in cells))

bad = False
print("\n  ── 判定（★ 「抓到」必须是判据的**字面逻辑**，退化不算）──")
for m in MODELS:
    res = [rows[(c, m)][0] for c, _, _ in CRITS]
    if m.startswith("★ 正确"):
        good = all(r is True for r in res)
        print(f"  {m:32} 全 PASS？ {'✓ 是（不误杀）' if good else '✗✗ 否 —— 误杀正确模型'}")
        bad |= not good
    else:
        caught = [c for (c, _, _), r in zip(CRITS, res) if r is False]
        degen = [c for (c, _, _), r in zip(CRITS, res) if r is None]
        tail = f"  （另有 {len(degen)} 条退化：{'、'.join(degen)} —— **不计入**）" if degen else ""
        print(f"  {m:32} 被抓到？ "
              f"{'✓ ' + '、'.join(caught) if caught else '✗✗ 漏网！'}{tail}")
        bad |= not caught

# ═════════════════════════════════════════ ② ★ 不误杀：扫残余定心误差 δ（P18 ④）
print()
print("  " + "─" * 96)
print("  ② ★ 「不误杀」扫 **残余定心误差 δ** —— §9 白纸黑字：「**不要试图把磁体对准中心**」")
print("  " + "─" * 96)
correct = MODELS["★ 正确 (Model-2)"]


def _correct_survives(dl):
    """正确模型在残余偏心 δ=dl 下，五条判据**没有一条判死它**（不误杀）。"""
    res = [rows[(c, "★ 正确 (Model-2)")][0] if dl == 0 else fn(correct, delta=dl)[0]
           for c, _, fn in CRITS]
    return all(r is not False for r in res)


def _delta_star(lo, hi, tol=2e-6):
    """★★ r4-H1：**二分**找「第一个判死正确模型的 δ」—— **不再靠网格撞**。

    r4 之前用固定网格 [0, 0.05, 0.10, 0.17, 0.25] mm，从 0.10（过）直接跳到 0.17（判死），
    **跳过了 0.11–0.16 mm** —— 真边界 ≈0.134 mm 就藏在那段里，delta_max 报虚了 30%。
    `eps_star` 早就会二分了，δ 却还在用网格 —— **同一个病，换了个维度**（P18 ④）。
    返回 (boundary, (last_pass, first_fail))；hi 处仍不误杀 ⟹ (None, None)。"""
    if _correct_survives(hi):
        return None, None
    assert _correct_survives(lo), "δ=lo 就误杀正确模型 ⟹ 这是 CRIT-FALSEKILL，不是 robustness"
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if _correct_survives(mid):
            lo = mid
        else:
            hi = mid
    return hi, (lo, hi)


# 展示用的粗扫（只为打印一张人看的表；**边界不从它取**，从二分取）
print(f"  {'δ [mm]':>8}" + "".join(f"{c:>10}" for c, _, _ in CRITS))
for dl in [0.0, 0.05e-3, 0.10e-3, 0.13e-3, 0.14e-3, 0.17e-3, 0.25e-3]:
    res = [rows[(c, "★ 正确 (Model-2)")][0] if dl == 0 else fn(correct, delta=dl)[0]
           for c, _, fn in CRITS]
    mark = "".join(f"{'✓' if r else ('✗✗ 判死' if r is False else '—'):>10}" for r in res)
    print(f"  {dl*1e3:>8.2f}{mark}")

DELTA_SCAN_HI = 0.30e-3                                     # ★ r5-H1：扫描上界必须写进契约
delta_max, delta_bracket = _delta_star(0.0, DELTA_SCAN_HI)  # ★ 二分定边界（非网格）
DELTA_SAFE = 0.10e-3                                        # 协议要求 = §9 视频噪声底 ±0.1 mm
_margin = (delta_max / DELTA_SAFE) if delta_max else float("inf")
print(f"\n  ⟹ **判据的有效窗口：δ < {(delta_max or 1)*1e3:.4f} mm**（**二分定出**，"
      f"括在 [{delta_bracket[0]*1e3:.4f}, {delta_bracket[1]*1e3:.4f}] mm）"
      if delta_max else "\n  ⟹ 扫描范围内都不误杀")
print(f"  ⟹ **协议要求 z_off < {DELTA_SAFE*1e3:.2f} mm ⟹ 安全裕度 {_margin:.2f}×** —— "
      f"**不是网格撞出来的 1.7×，是二分定出来的 {_margin:.1f}×**（r4-H1）。")
print(f"     （§9 的视频噪声预算是 ±0.1 mm —— 一次涨落就能把偏心推到悬崖。）")

# ═════════════════════════════════════════ ③ ★ 扫错误幅度 ε，报 ε*（P18 ②）
print()
print("  " + "─" * 96)
print("  ③ ★★ 扫**错误幅度** ε，报「**最小可检测幅度** ε*」—— 而不是挑一个数说「抓到了」")
print("  " + "─" * 96)


def eps_star(make, crit_ids, lo, hi, tol=0.02):
    """二分：最小的能被 crit_ids 里**任一条**抓到的 ε。"""
    fns = {c: fn for c, _, fn in CRITS}
    if not any(fns[c](make(hi))[0] is False for c in crit_ids):
        return None
    while hi - lo > tol:
        mid = (lo + hi) / 2
        if any(fns[c](make(mid))[0] is False for c in crit_ids):
            hi = mid
        else:
            lo = mid
    return hi


eC = eps_star(lambda e: _mk_models(eps_C=e)["bug-C  β 错 +{:.0%}".format(e)],
              ["P1c", "P3a"], 0.0, 0.60)
eE = eps_star(lambda e: _mk_models(eps_E=e)["★ bug-E 中心阻尼不为零 b₀={:.0%}b_pk".format(e)],
              ["P1b", "P3a", "P3b"], 0.0, 0.30)
print(f"  **bug-C（β 错 ε）**：ε* = **{eC:.0%}** ——「我们的判据能分辨 β 的 {eC:.0%} 偏差」")
print(f"     ★★ 而「用标称 B_r（公差 ±5%）」给的是 **b 偏 ±10%** ⟹ **{'抓不到' if eC > 0.10 else '抓得到'}**。")
print(f"     **r3 把 bug-C 设成 +30% —— 那个当然抓得到。这就是 P18 ② 说的「幅度是挑出来的」。**")
print(f"     ⟹ **实验建议：必须用高斯计实测 G'(0)**（把预言的不确定度从 10% 压到 2%），")
print(f"        否则 P1c 的容差就被预言侧的误差吃光了。")
print(f"  **bug-E（中心偏置 ε·b_pk）**：ε* = **{eE:.0%}**")

# ═════════════════════════════════════════════════════════════════════ 落盘
def _detail(cid, m):
    ok, d = rows[(cid, m)]
    return d


out = {
    "generated_by": "01-criteria/criterion_matrix.py",
    "purpose": ("★★★ 判据 × 模型的**双向**表 + P18 的三个新维度。\n"
                "只跑「正确模型」那一列 = 换了一把新的失明的锁（r2 真实翻车）。\n"
                "**而只跑布尔值，那张表可以被调到全绿（r3 真实翻车 —— 审稿模式 P18）。**"),
    "correct_model": {
        "id": "Model-2（有限磁体 + 厚绕组）",
        "why_this_one": "★ **契约的 (26)+(27) 命令 Skill 2 积的就是它。**\n"
                        f"r3 的表用的是 Model-0（点偶极子 + 薄线圈）⟹ |G'(0)| 差 "
                        f"{GP0/GP0_M0-1:+.1%} ⟹ c₂ 差 {(GP0/GP0_M0)**2-1:+.1%}\n"
                        "⟹ **P1c 的容差在 Skill 2 还没开跑之前就被吃掉 1/3。**"
                        "「不误杀」从没在下游真正要跑的那个模型上验过。",
        "Gp0": round(float(GP0), 3),
        "Gp0_model0": round(float(GP0_M0), 3),
        "c2_per_mm2": round(float(C2 * 1e-6), 5),
    },
    "robustness_scan": {
        "parameter": "δ = 残余定心误差 [m]",
        "why": "★ §9 白纸黑字：「**不要试图「把磁体对准中心」**」—— "
               "而 r3 的 crit_P3/P3b 把 z₀ 钉死在**精确的 0.0**。\n"
               "**「不误杀」必须在协议自己承认的每一项系统误差上各跑一遍**（P18 ④）。\n"
               "★★ r4-H1：边界**必须二分定出**，不能靠网格撞 —— "
               "固定网格会跳过真边界，把 delta_max 报虚（0.17 vs 真值 0.134）。\n"
               "★★ r5-H1：必须报 `scan_upper_bound`（扫到多远）—— 否则 delta_max=None"
               "（「处处稳健」）与「扫描范围太小」不可区分。",
        "scan_upper_bound": round(float(DELTA_SCAN_HI), 7),
        "delta_max": None if delta_max is None else round(float(delta_max), 7),
        "delta_max_bracket": (None if delta_bracket is None else
                              [round(float(delta_bracket[0]), 7),
                               round(float(delta_bracket[1]), 7)]),
        "verdict": (f"判据的有效窗口：**δ < {delta_max*1e3:.3f} mm**（**二分定出**，"
                    f"括在 [{delta_bracket[0]*1e3:.3f}, {delta_bracket[1]*1e3:.3f}] mm）。"
                    f"协议要求 z_off < **{DELTA_SAFE*1e3:.2f} mm** ⟹ 安全裕度 **{_margin:.1f}×** "
                    f"（不是网格撞出的 1.7×）。（§9 视频噪声 ±0.1 mm。）"
                    if delta_max else "在扫描的全部 δ 上都不误杀"),
    },
    "min_detectable": {
        "why": "★★ 一个错模型「被抓到了 ✓」**没有信息量 —— 因为幅度是作者挑的**（P18 ②）。\n"
               "**扫 ε，报「最小可检测幅度」ε\\* —— 那才是判据集的分辨率，"
               "而且它是一条可汇报的物理结论。**",
        "bug-C_beta": {
            "eps_star": round(float(eC), 4),
            "caught_by": ["P1c", "P3a"],
            "note": f"「我们的判据能分辨 β 的 **{eC:.0%}** 偏差」。\n"
                    f"★★ 而「用标称 B_r（公差 ±5%）⟹ b 偏 ±10%」——"
                    f"**{'低于 ε*，抓不到' if eC > 0.10 else '抓得到'}**。\n"
                    "**r3 把 bug-C 设成 +30%，那个当然抓得到。**\n"
                    "⟹ **实验建议：必须用高斯计实测 G'(0)**（预言的不确定度 10% → 2%）。",
        },
        "bug-E_offset": {"eps_star": round(float(eE), 4), "caught_by": ["P1b", "P3a", "P3b"]},
    },
    "wrong_models": [
        {"id": m, "statement": m.split(maxsplit=1)[-1], "why_a_student_writes_it": _why(m)}
        for m in MODELS if not m.startswith("★ 正确")
    ],
    "criteria": [
        {"id": cid,
         "statement": f"{cid} {name}",
         "tolerance": TOL[cid][0],
         "tolerance_source": TOL[cid][1],
         "passes_correct": rows[(cid, "★ 正确 (Model-2)")][0] is True,
         "correct_model_detail": _detail(cid, "★ 正确 (Model-2)"),
         "catches": [
             {"id": m, "detail": _detail(cid, m)}
             for m in MODELS
             if not m.startswith("★ 正确") and rows[(cid, m)][0] is False],
         "degenerate_on": [
             m for m in MODELS
             if not m.startswith("★ 正确") and rows[(cid, m)][0] is None],
         }
        for cid, name, _ in CRITS
    ],
    "verdict": "FAIL" if bad else "PASS",
}
Path(__file__).with_name("matrix.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

print()
print(BAR)
print("✗✗ 有判据失明或误杀 —— **不许交付**" if bad
      else "✓✓ 五条判据双向成立；容差有来源；ε* 与 δ_max 已写进契约")
print(BAR)
print("  → 01-criteria/matrix.json")
sys.exit(1 if bad else 0)
