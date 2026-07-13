#!/usr/bin/env python3
"""★★ r3 的判据 —— **双向表**（判据 × 模型）。

**统一的提取**：对每个 z₀ 的包络，拟合精确的 Bernoulli 闭式

    (A₀/A)² = (1+Q)·e^{2Γt} − Q            ⟸ 由 ż = ... 精确解出，不是近似

拿到 (Γ, Q) 两个数。于是四条**零自由参数**预言：

    ① Γ(z₀) = γ_oc + c₂·(z₀ − z_off)²      ← 抛物线，**精确**（不再有 A₀² 的污染）
    ②   顶点值 = γ_oc                        ← **这才是 b(0)=0 的检验**
    ③   曲率  = c₂ = G′(0)²/[2·M_eff·(R+R_c)]  ← 高斯计 + 欧姆表
    ④ Q(z₀) = c₂A₀²/(4Γ)                    ← **又一条，白送的**

**六个模型，每个都是学生真的会写出来的东西 —— 不是稻草人。**
"""
import sys

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit, minimize_scalar
from scipy.signal import argrelextrema

sys.stdout.reconfigure(encoding="utf-8")
MU0 = 4e-7 * np.pi

R_MAG, L_MAG = 5e-3, 10e-3
M_DIP = (1.30 / MU0) * np.pi * R_MAG**2 * L_MAG
M_EFF = 5.89e-3 + 2.0e-3 / 3
OMEGA0 = 2 * np.pi * 3.0
K = M_EFF * OMEGA0**2
N, L_COIL, A_COIL, R_C = 400, 20e-3, 10.80e-3, 3.72
C = L_COIL / 2
GAMMA_OC = 0.0413
GP0 = abs(-1.5 * MU0 * N * M_DIP * A_COIL**2 * (A_COIL**2 + C**2) ** -2.5)
BETA = GP0**2 / R_C
R_TEST = 20.0
C2 = GP0**2 / (2 * M_EFF * (R_TEST + R_C))       # 预言曲率 [s⁻¹ m⁻²]
C2_SC = GP0**2 / (2 * M_EFF * R_C)               # 短路（R=0）的 c₂


def G_true(z):
    u1, u2, a2 = z + C, z - C, A_COIL**2
    return (MU0 * (N / L_COIL) * M_DIP / 2) * a2 * (
        (a2 + u1**2) ** -1.5 - (a2 + u2**2) ** -1.5)


def Bcoil(z):
    u1, u2 = z + C, z - C
    return u1 / np.sqrt(A_COIL**2 + u1**2) - u2 / np.sqrt(A_COIL**2 + u2**2)


ZPK = abs(minimize_scalar(lambda z: -abs(G_true(z)), bounds=(-0.05, -1e-5),
                          method="bounded", options=dict(xatol=1e-11)).x)
GMAX = abs(G_true(-ZPK))
B_PK = GMAX**2                                    # b(z_pk)·(R+R_c)

MODELS = {
    "★ 正确": lambda z, R: G_true(z)**2 / (R + R_C),
    "naive-A 磁通最大处阻尼最大": lambda z, R: (GMAX * Bcoil(z) / Bcoil(0.0))**2 / (R + R_C),
    "naive-B 常数阻尼 b=b(z_pk)": lambda z, R: B_PK / (R + R_C) + 0*z,
    "bug-C  β 错 +30%": lambda z, R: 1.30 * G_true(z)**2 / (R + R_C),
    "bug-D  漏了线圈自阻 R_c": lambda z, R: G_true(z)**2 / (R + 0.1),
    "★ bug-E 中心阻尼不为零 b₀=0.1b_pk": lambda z, R: (G_true(z)**2 + 0.10*B_PK) / (R + R_C),
}


def envelope(model, z0, A0, R, T):
    def rhs(t, y):
        z, v = y
        return [v, (-K*(z - z0) - (2*M_EFF*GAMMA_OC + model(z, R))*v) / M_EFF]
    sol = solve_ivp(rhs, (0, T), [z0 + A0, 0.0], rtol=1e-11, atol=1e-14,
                    dense_output=True, max_step=2e-3)
    tt = np.linspace(0, T, int(T*6000))
    u = sol.sol(tt)[0] - z0
    idx = argrelextrema(u, np.greater)[0]
    tp, Ap = tt[idx], u[idx]
    m = Ap > 0.03e-3
    return tp[m], Ap[m]


def fit_bernoulli(model, z0, A0, R, T=None):
    """★ 统一的提取：拟合精确闭式 (A₀/A)² = (1+Q)e^{2Γt} − Q，返回 (Γ, Q)。"""
    if T is None:                                 # 自适应：够看到 5 个 e 折就行
        c2 = C2 if R > 1e-9 else C2_SC
        T = min(30.0, max(5.0, 5.0 / (GAMMA_OC + c2 * z0**2)))
    tp, Ap = envelope(model, z0, A0, R, T)
    if len(tp) < 6:
        return np.inf, np.nan                     # 一个周期就衰完了 —— 本身是结论
    y = (A0 / Ap) ** 2

    def f(t, Gam, Q):
        return (1 + Q) * np.exp(2 * Gam * t) - Q
    try:
        (Gam, Q), _ = curve_fit(f, tp, y, p0=[0.1, 0.5],
                                bounds=([1e-4, 0.0], [50.0, 1e4]), maxfev=20000)
    except Exception:
        return np.inf, np.nan
    return Gam, Q


# ══════════════════════════════════════════════════════════ 判据
def _scan(model, A0=1.0e-3, zmax=4e-3, n=9):   # ★ ±4mm：G 在端点非线性 <1%
    zs = np.linspace(-zmax, zmax, n)
    out = np.array([fit_bernoulli(model, z, A0, R_TEST)[0] for z in zs])
    return zs, out


def crit_P1a(model):
    """【结构】Γ(z₀) 在中心取**极小**（不是极大）。极小 vs 极大 —— 离散。"""
    zs, g = _scan(model)
    if not np.all(np.isfinite(g)):
        return False, "包络一个周期就衰完 —— 连 Γ 都提不出来"
    ok = g[len(g)//2] < g[0] and g[len(g)//2] < g[-1]
    return ok, f"Γ(0)={g[len(g)//2]:.3f}  Γ(±4mm)={g[0]:.3f}/{g[-1]:.3f}"


def crit_P1b(model):
    """【零自由参数】抛物线的**顶点值 = γ_oc** ⟸ 这才是 b(0)=0 的检验。"""
    zs, g = _scan(model)
    if not np.all(np.isfinite(g)):
        return False, "提不出 Γ"
    c, b, a = np.polyfit(zs, g, 2)
    vert = a - b**2 / (4*c)
    return abs(vert/GAMMA_OC - 1) < 0.12, f"顶点={vert:.4f} (γ_oc={GAMMA_OC:.4f}, {vert/GAMMA_OC-1:+.0%})"


def crit_P1c(model):
    """【零自由参数】曲率 = c₂ = G′(0)²/[2·M_eff·(R+R_c)]。"""
    zs, g = _scan(model)
    if not np.all(np.isfinite(g)):
        return False, "提不出 Γ"
    c = np.polyfit(zs, g, 2)[0]
    return abs(c/C2 - 1) < 0.12, f"c₂={c*1e-6:.4f} (预言 {C2*1e-6:.4f}, {c/C2-1:+.1%})"


def crit_P3(model):
    """★【结构 + 零自由参数】居中短路：Q(A₀) = c₂A₀²/(4Γ) ⟹ **Q ∝ A₀²**。

    · 正确模型：Q 随 A₀² 线性增长，斜率 = c₂/(4γ_oc)  ← 零自由参数
    · 常数阻尼：b 与 z 无关 ⟹ 包络是**纯指数** ⟹ **Q ≡ 0，与 A₀ 无关**
    **⇒ 斜率零 vs 非零 —— 离散。而且 Q 由包络的头段（t ≲ t*）定，尾巴不主导。**
    """
    A0s = np.array([2.0, 3.0, 5.0, 8.0]) * 1e-3
    Qs, Gs = [], []
    for A0 in A0s:
        Gam, Q = fit_bernoulli(model, 0.0, A0, 0.0, T=30.0)
        if not np.isfinite(Gam):
            return False, "★ 居中+短路 ⟹ **一个周期就把磁体按死了**（这本身就是判据）"
        Qs.append(Q); Gs.append(Gam)
    Qs, Gs = np.array(Qs), np.array(Gs)
    s, ic = np.polyfit(A0s**2, Qs, 1)
    pred = C2_SC / (4 * GAMMA_OC)
    ok = abs(s/pred - 1) < 0.20 and abs(ic) < 0.5
    return ok, (f"Q∝A₀² 斜率={s:.3e}(预言{pred:.3e}, {s/pred-1:+.0%}) "
                f"截距={ic:+.2f}  Γ={Gs.mean():.4f}(γ_oc={GAMMA_OC:.4f})")


def crit_P3b(model):
    """【结构】居中短路，**长时衰减率必须回到开路值 γ_oc**（b(0)=0 的动力学签名）。"""
    Gam, _ = fit_bernoulli(model, 0.0, 8e-3, 0.0, T=30.0)
    if not np.isfinite(Gam):
        return False, "一个周期就按死了"
    return abs(Gam/GAMMA_OC - 1) < 0.15, f"Γ={Gam:.4f} vs γ_oc={GAMMA_OC:.4f} ({Gam/GAMMA_OC-1:+.0%})"


CRITS = [("P1a 中心是极小【结构】", crit_P1a),
         ("P1b 顶点 = γ_oc【零参】", crit_P1b),
         ("P1c 曲率 = c₂【零参】", crit_P1c),
         ("P3a Q ∝ A₀²【结构+零参】", crit_P3),
         ("P3b 长时回到 γ_oc【结构】", crit_P3b)]

print("=" * 112)
print("★★ 判据 × 模型 —— **双向表**（这张表就是 r2 教训的固化）")
print("   正确模型这一列必须全 PASS（**不误杀**）；每个错模型必须至少被一条抓到（**不失明**）。")
print("=" * 112)

rows = {c: {m: f(mf) for m, mf in MODELS.items()} for c, f in CRITS}

print(f"  {'判据':26}" + "".join(f" {m[:13]:>15}" for m in MODELS))
print("  " + "-" * 108)
for c, _ in CRITS:
    print(f"  {c:26}" + "".join(f" {'✓ PASS' if rows[c][m][0] else '✗ FAIL':>15}" for m in MODELS))

print("\n  ── 判定 ──")
bad = False
for m in MODELS:
    ps = [rows[c][m][0] for c, _ in CRITS]
    if m.startswith("★ 正确"):
        print(f"  {m:32} 全部 PASS？ {'✓ 是（不误杀）' if all(ps) else '✗✗ 否 —— 误杀了正确模型'}")
        bad |= not all(ps)
    else:
        hit = [c.split()[0] for (c, _), p in zip(CRITS, ps) if not p]
        print(f"  {m:32} 被抓到？ {'✓ 是  ← ' + '、'.join(hit) if hit else '✗✗ 否 —— 漏网！'}")
        bad |= not hit

print("\n  ── 明细 ──")
for c, _ in CRITS:
    print(f"\n  【{c}】")
    for m in MODELS:
        ok, d = rows[c][m]
        print(f"    {'✓' if ok else '✗'} {m:30} {d}")

# ── 落盘 ───────────────────────────────────────────────────────────────────
#  **契约要引用它，check_analysis.py 要查它，Skill 2 要复现它。**
#  一张只存在于终端输出里的表，等于没有这张表。
import json
from pathlib import Path

WHY = {
    "naive-A 磁通最大处阻尼最大":
        "**最常见的直觉，也是本题的头号陷阱**：磁通在中心最大 ⟹ 阻尼在中心最大。"
        "错在把「磁通 λ」当成了「磁通的**梯度** G = dλ/dz」。**这个错误正是本题的全部内容。**",
    "naive-B 常数阻尼 b=b(z_pk)":
        "**题面自己诱导出来的**：\"the damping\" —— 说「the」就预设了阻尼是**一个数**。"
        "任何把阻尼当成一个标量的模型，都长这样。",
    "bug-C  β 错 +30%":
        "**最容易犯的实现 bug**：G'(0) 的解析式 (7) 漏一个因子（如那个 3/2），"
        "或者用了标称 B_r（公差 ±5% ⟹ b 偏 ±10%）而不是实测的 G。",
    "bug-D  漏了线圈自阻 R_c":
        "**naive 电路模型**：b ∝ 1/R，R→0 时发散。（真值：线圈自阻设了天花板 b_max = G²/R_c。）",
    "★ bug-E 中心阻尼不为零 b₀=0.1b_pk":
        "**最难抓的一个**：模型的**形状**全对，但多了一个常数偏置"
        "（线圈绕得不对称、骨架有涡流、磁体倾斜…）。"
        "**它的曲率和正确模型一模一样 —— 只有「顶点值」那条判据看得见它。**"
        "★ 它就是这张表存在的理由：没有它，P1b 会显得多余。",
}

out = {
    "generated_by": "01-criteria/criterion_matrix.py",
    "purpose": ("★★ 判据 × 模型的**双向**表。"
                "只跑「正确模型」那一列 = 换了一把新的失明的锁（r2 真实翻车）。"),
    "wrong_models": [
        {"id": m,
         "statement": m.split(maxsplit=1)[-1] if " " in m else m,
         "why_a_student_writes_it": WHY[m]}
        for m in MODELS if not m.startswith("★ 正确")
    ],
    "criteria": [
        {"id": c.split()[0],
         "statement": c,
         "passes_correct": bool(rows[c]["★ 正确"][0]),
         "correct_model_detail": rows[c]["★ 正确"][1],
         "catches": [m for m in MODELS
                     if not m.startswith("★ 正确") and not rows[c][m][0]]}
        for c, _ in CRITS
    ],
    "verdict": "FAIL" if bad else "PASS",
}
Path(__file__).with_name("matrix.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("\n  → 写入 01-criteria/matrix.json")

print("\n" + "=" * 112)
print("✗✗ 有判据失明或误杀 —— **不许交付**" if bad else "✓✓ 五条判据全部双向成立 —— 可以写进契约")
print("=" * 112)
sys.exit(1 if bad else 0)
