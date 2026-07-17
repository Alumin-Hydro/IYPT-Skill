#!/usr/bin/env python3
r"""Model-2：完整数值 —— 式 (26) 的三态 ODE (z, v, I)，加上包络提取与能量审计。

- **三态 vs 二维**：(26) 带电感（刚性比 ~80：L/(R+R_c) = 0.67 ms ≪ 1/ω₀ = 53 ms）。
  A-4 允许消去 I 得二维系统（b(z) = G²/(R+R_c)），两者之差必须 < 1.3%（V-2 ③）。
  三态默认走 Radau（隐式，R=200 Ω 时快时间尺度 12 µs，显式法要 3M 步）；二维走 DOP853。
- **包络/Bernoulli 拟合**沿用 criterion_matrix 的已验实现（(23a) 是 (18) 的精确解）。
- **能量审计（V-3）**：★ 储能必须含 ½LI²、阻尼项系数是 2·M_eff·γ_oc ——
  契约 V-3 ① 原文漏了这两处（acceptance.md Step 0 预注册的 SPEC-DEFECT #1），
  这里两个版本都算：修正版进门（<1e-10），原文版的失配量级作为 defect 的证据。
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import curve_fit
from scipy.signal import argrelextrema

import field as FLD
from params import GAMMA_OC, K_SPRING, L_IND, M_EFF, OMEGA0, R_C


#: 冒烟测试的注入钩子（smoke_test.py 案例 6：力项系数错）。生产值恒为 1.0。
FORCE_GAIN = 1.0


# ══════════════════════════════════════════════════════════════════ 求解器
def simulate3(z0: float, A0: float, R: float, *, Gfun=None, gamma_oc: float = GAMMA_OC,
              L: float = L_IND, T: float = 10.0, rtol: float = 1e-11, atol=None,
              method: str = "Radau", v0: float = 0.0, audit: bool = False,
              M_eff: float = M_EFF, k: float = K_SPRING):
    """式 (26) 的三态积分。audit=True 时增广两个求积状态：
    y[3] = ∫I²(R+R_c)dt（焦耳热）、y[4] = ∫2·M_eff·γ_oc·v²dt（开路本底耗散）。
    M_eff/k 可覆盖 —— F-5 的坍缩图要扫 (M, k, R, z₀) 组合。"""
    G = Gfun if Gfun is not None else FLD.model2().G
    if atol is None:
        atol = [1e-15, 1e-13, 1e-13] + ([1e-16, 1e-16] if audit else [])
    elif np.isscalar(atol):
        atol = [atol] * (5 if audit else 3)

    def rhs(t, y):
        z, v, I = y[0], y[1], y[2]
        g = float(G(z))
        dz = v
        dv = (-k * (z - z0) - 2 * M_eff * gamma_oc * v + I * g * FORCE_GAIN) / M_eff
        dI = (-(R + R_C) * I - g * v) / L
        if not audit:
            return [dz, dv, dI]
        return [dz, dv, dI, I * I * (R + R_C), 2 * M_eff * gamma_oc * v * v]

    y0 = [z0 + A0, v0, 0.0] + ([0.0, 0.0] if audit else [])
    return solve_ivp(rhs, (0, T), y0, method=method, rtol=rtol, atol=atol,
                     dense_output=True, max_step=0.05)


def simulate2(z0: float, A0: float, R: float, *, Gfun=None, bfun=None,
              gamma_oc: float = GAMMA_OC, T: float = 10.0, rtol: float = 1e-10,
              atol: float = 1e-13, v0: float = 0.0, max_step: float = 2e-3,
              M_eff: float = M_EFF, k: float = K_SPRING):
    """A-4 消元后的二维系统：M_eff·v̇ = −k(z−z₀) − [2·M_eff·γ_oc + b(z)]·v。
    `bfun` 显式给出时优先（Gate 0b 的常数 b、Gate 0c 的 βz²、冒烟注入的冻结 b）。"""
    if bfun is None:
        G = Gfun if Gfun is not None else FLD.model2().G
        bfun = lambda z: np.asarray(G(z)) ** 2 / (R + R_C)            # noqa: E731

    def rhs(t, y):
        z, v = y
        return [v, (-k * (z - z0) - (2 * M_eff * gamma_oc + float(bfun(z))) * v)
                / M_eff]

    return solve_ivp(rhs, (0, T), [z0 + A0, v0], method="DOP853", rtol=rtol,
                     atol=atol, dense_output=True, max_step=max_step)


# ══════════════════════════════════════════════════════════ 包络提取与拟合
def envelope_from_sol(sol, z0: float, T: float, *, per_sec: int = 6000,
                      A_cut: float = 0.03e-3):
    """取 u = z − z₀ 的正峰。密采样 6000/s（峰值采样误差 ~1e-6 相对，远小于所有门）。"""
    tt = np.linspace(0, T, max(int(T * per_sec), 2000))
    u = sol.sol(tt)[0] - z0
    idx = argrelextrema(u, np.greater)[0]
    tp, Ap = tt[idx], u[idx]
    m = Ap > A_cut
    return tp[m], Ap[m]


def default_T(z0: float, R: float, gamma_oc: float = GAMMA_OC) -> float:
    """积分时长：~5 个衰减时标，夹在 [5, 30] s（criterion_matrix 的启发式）。"""
    gs = FLD.model2()
    c2 = gs.gp0**2 / (2 * M_EFF * (R + R_C))
    return float(min(30.0, max(5.0, 5.0 / (gamma_oc + c2 * z0**2))))


def envelope(z0: float, A0: float, R: float, *, mode: str = "3state", T: float | None = None,
             Gfun=None, bfun=None, gamma_oc: float = GAMMA_OC, A_cut: float = 0.03e-3,
             **kw):
    """一步到位：积分 + 提峰。返回 (tp, Ap, T)。
    A_cut 可放低（如 R=0 近临界阻尼时峰衰得快 —— rtol 1e-11 下 µm 级的峰仍是干净的）。"""
    if T is None:
        T = default_T(z0, R, gamma_oc)
    if mode == "3state":
        sol = simulate3(z0, A0, R, Gfun=Gfun, gamma_oc=gamma_oc, T=T, **kw)
    else:
        sol = simulate2(z0, A0, R, Gfun=Gfun, bfun=bfun, gamma_oc=gamma_oc, T=T, **kw)
    tp, Ap = envelope_from_sol(sol, z0, T, A_cut=A_cut)
    return tp, Ap, T


def fit_bernoulli(tp, Ap, A0: float):
    """★ 统一的提取：拟合 (A₀/A)² = (1+Q)e^{2Γt} − Q，返回 (Γ, Q, ok)。
    ok=False ⟹ DEGENERATE（提不出 Γ），不是「被抓到」——两者必须分开记账（P18 ⑤）。"""
    if len(tp) < 6:
        return np.nan, np.nan, False
    y = (A0 / Ap) ** 2
    try:
        (Gam, Q), _ = curve_fit(lambda t, G, Q: (1 + Q) * np.exp(2 * G * t) - Q,
                                tp, y, p0=[0.1, 0.5],
                                bounds=([1e-4, 0.0], [50.0, 1e4]), maxfev=20000)
    except Exception:                                    # noqa: BLE001
        return np.nan, np.nan, False
    return float(Gam), float(Q), True


def gamma_early(tp, Ap, n: int = 5) -> float:
    """前几个峰的对数斜率 —— 线性阻尼区的 γ 提取（精确对指数包络，
    不需要 Bernoulli 的 6 个峰）。衰得太快（<2 峰）返回 inf —— 那是测量结果，不是失败。"""
    if len(tp) < 2:
        return np.inf
    k = min(len(tp), n)
    return float(-np.polyfit(tp[:k], np.log(Ap[:k]), 1)[0])


def gamma_first(tp, Ap, A0: float) -> float:
    """★ 初始包络衰减率：从 (t=0, A₀) 到第一个内部峰。**起点本身就是包络点**（v(0)=0）。

    为什么必须有它（F-5 探针实测）：γ≈2 时 argrelextrema 记到第一个峰，振幅已经从
    8mm 衰到 4.4mm —— 最强非线性的那半个摆幅落在「第 −1 个区间」里，gamma_early 对
    「A₀ 这个振幅下的阻尼」系统性失明（理论 −28% 被稀释成 −1.8%）。
    它还顺带修好近临界端（R=0，ζ≈0.7）：那里只剩 1 个内部峰，gamma_early 返回 inf，
    而 1/(inf−γ_oc) = 0.0 是一个**静默的**坏点（不是 nan，拟合照吃）。"""
    if len(tp) < 1:
        return np.inf
    return float(np.log(A0 / Ap[0]) / tp[0])


# ══════════════════════════════════════════════════════════ (23)/(23a) 闭式
def envelope_23(t, A0: float, beta: float, gamma_oc: float = GAMMA_OC):
    """(23)：居中 (z₀=0)、b=βz² 时包络的精确闭式（Bernoulli）。零自由参数。"""
    t_star = 4 * M_EFF / (beta * A0**2)
    q = 1 / (2 * gamma_oc * t_star)
    return A0 / np.sqrt((1 + q) * np.exp(2 * gamma_oc * np.asarray(t)) - q)


def envelope_23a(t, A0: float, Gamma: float, Q: float):
    """(23a)：任意 z₀ 的两参形式。"""
    return A0 / np.sqrt((1 + Q) * np.exp(2 * Gamma * np.asarray(t)) - Q)


# ══════════════════════════════════════════════════════════════ 能量审计（V-3）
def energy_audit(z0: float, A0: float, R: float, *, T: float = 8.0, Gfun=None,
                 rtol: float = 1e-12) -> dict:
    """★ V-3 ①：能量平衡。修正版（含 ½LI²、系数 2·M_eff）必须 < 1e-10；
    「照契约原文」版（无 ½LI²、系数 2M）的失配是 SPEC-DEFECT #1 的证据，一并报告。
    同时报 ③ 单调性：dE_tot/dt ≤ 0 逐时刻（在密采样网格上检查）。"""
    from params import M_MASS
    sol = simulate3(z0, A0, R, Gfun=Gfun, T=T, rtol=rtol,
                    atol=[1e-16, 1e-14, 1e-14, 1e-18, 1e-18], audit=True)

    def E_mech(y):
        return 0.5 * M_EFF * y[1] ** 2 + 0.5 * K_SPRING * (y[0] - z0) ** 2

    y_end = sol.y[:, -1]
    E0, E1 = E_mech(sol.y[:, 0]), E_mech(y_end)
    EL0, EL1 = 0.0, 0.5 * L_IND * y_end[2] ** 2
    joule, diss_oc = y_end[3], y_end[4]

    resid_correct = abs(-( (E1 + EL1) - (E0 + EL0) ) - (joule + diss_oc)) / E0
    diss_oc_aswritten = diss_oc * (M_MASS / M_EFF)       # 原文写 2M 而非 2M_eff
    resid_aswritten = abs(-(E1 - E0) - (joule + diss_oc_aswritten)) / E0

    tt = np.linspace(0, T, 20000)
    Y = sol.sol(tt)
    E_tot = 0.5 * M_EFF * Y[1] ** 2 + 0.5 * K_SPRING * (Y[0] - z0) ** 2 \
        + 0.5 * L_IND * Y[2] ** 2
    dE = np.diff(E_tot)
    monotone_viol = float(max(0.0, dE.max()) / E0)

    k = 5                                                # 序列给 V-3 出图用（降采样）
    return dict(resid_correct=float(resid_correct),
                resid_aswritten=float(resid_aswritten),
                monotone_violation=monotone_viol,
                E0=float(E0), joule=float(joule), diss_oc=float(diss_oc),
                EL_end=float(EL1),
                series=dict(t=tt[::k], E_tot=E_tot[::k],
                            ledger=(E0 - Y[3] - Y[4])[::k],
                            EL=(0.5 * L_IND * Y[2] ** 2)[::k]))


def open_circuit_drift(n_periods: int = 100, A0: float = 3e-3, z0: float = 0.0,
                       rtol: float = 1e-13, atol: float = 1e-17, series: bool = False):
    """★ V-3 ②：开路（I≡0）+ γ_oc=0 ⟹ 纯 SHM，能量必须严格守恒。
    只测积分器（Gate-0 级）。返回 100 个周期内的最大相对漂移（series=True 时带曲线）。"""
    T = n_periods * 2 * np.pi / OMEGA0
    sol = simulate2(z0, A0, 0.0, bfun=lambda z: 0.0, gamma_oc=0.0, T=T,
                    rtol=rtol, atol=atol)
    tt = np.linspace(0, T, 200 * n_periods)
    z, v = sol.sol(tt)
    E = 0.5 * M_EFF * v**2 + 0.5 * K_SPRING * (z - z0) ** 2
    drift = float(np.max(np.abs(E - E[0])) / E[0])
    if series:
        return drift, (tt[::10], np.abs(E / E[0] - 1)[::10])
    return drift


if __name__ == "__main__":
    import time
    print("model2 自检（非门，只看量级）")
    t0 = time.time()
    tp, Ap, T = envelope(0.0, 3e-3, 0.0, mode="2state", T=12.0)
    G_, Q_, ok = fit_bernoulli(tp, Ap, 3e-3)
    print(f"  居中短路 A0=3mm (2-state): Γ={G_:.4f} (γ_oc={GAMMA_OC})  Q={Q_:.2f}  "
          f"峰数={len(tp)}  {time.time()-t0:.1f}s")
    t0 = time.time()
    tp3, Ap3, _ = envelope(0.0, 3e-3, 0.0, mode="3state", T=12.0)
    G3, Q3, ok3 = fit_bernoulli(tp3, Ap3, 3e-3)
    print(f"  同上 (3-state Radau):      Γ={G3:.4f}              Q={Q3:.2f}  "
          f"峰数={len(tp3)}  {time.time()-t0:.1f}s")
    t0 = time.time()
    aud = energy_audit(FLD.zpk_model0()[0], 3e-3, 20.0, T=6.0)
    print(f"  能量审计(z_pk,3mm,R=20): 修正版 {aud['resid_correct']:.2e}  "
          f"原文版 {aud['resid_aswritten']:.2e}  单调破坏 {aud['monotone_violation']:.2e}  "
          f"{time.time()-t0:.1f}s")
    t0 = time.time()
    drift = open_circuit_drift(100)
    print(f"  开路守恒 100 周期: 漂移 {drift:.2e}  {time.time()-t0:.1f}s")
