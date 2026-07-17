#!/usr/bin/env python3
r"""G(z) 全家：Model-0 闭式、Model-2 数值（互易性 + 体平均）、以及 V-1 的独立路径。

物理骨架改写自 `01-criteria/criterion_matrix.py`（8 轮审稿验过），三处升级：

1. **numpy 广播重构** —— Gate 0 的 ε 扫描要重建 λ 表 5 次、收敛门还要在双倍网格上重建，
   criterion_matrix 的逐点双循环撑不住。这里把 (z × 磁体采样 × 线圈网格) 一次广播、按 z 分块。
2. **缩放几何构造器** —— Gate 0 的极限配方：R_m→εR_m、L_m→εL_m、M_s→M_s/ε³（保 m 不变）、
   **同时 w→εw**。三个尺度一个不漏（magnetic-brake 的血泪：漏一个，收敛到 3.55 而不是 1）。
3. **V-1 的两条新独立路径** —— ② 互易性（G = m·d(B_coil/I)/dz，不经过磁通链概念）、
   ③ Amperian 面电流 × 离散匝的互感求和。criterion_matrix 只有体平均这一条路。

★ 样条有**定义域护栏**：越界直接抛异常，不许静默三次外推。
  「截断长度写成绝对值」是收敛门在扫描端点要抓的 bug —— 护栏让它响亮地失败。
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from scipy.integrate import quad
from scipy.interpolate import CubicSpline
from scipy.optimize import brentq, minimize_scalar
from scipy.special import ellipe, ellipk

import params as PRM
from params import (A1_BAND, A2_BAND, A_COIL, L_COIL, L_MAG, M_DIP, M_S, MU0,
                    N_TURNS, R_MAG)


# ══════════════════════════════════════════════════════════════ 几何（可缩放）
@dataclass(frozen=True)
class Geometry:
    """磁体 + 线圈的全部空间参数。Gate 0 靠 `scaled()` 生成缩放副本。"""
    R_m: float
    L_m: float
    M_s: float
    N: float
    l_c: float
    a: float
    band_h: float        # 载流带半宽 (A2−A1)/2；w→0 ⟹ band_h→0

    @property
    def m_dip(self) -> float:
        return self.M_s * np.pi * self.R_m**2 * self.L_m

    def scaled(self, eps: float) -> "Geometry":
        """Gate 0 的极限配方：磁体两尺度 + 绕组厚度**一起**收缩，m 保持不变。"""
        return replace(self, R_m=self.R_m * eps, L_m=self.L_m * eps,
                       M_s=self.M_s / eps**3, band_h=self.band_h * eps)


BASE = Geometry(R_m=R_MAG, L_m=L_MAG, M_s=M_S, N=N_TURNS, l_c=L_COIL,
                a=A_COIL, band_h=(A2_BAND - A1_BAND) / 2)
# 契约的 M_s/m 都是圆整过的派生值 ⟹ 一致性只能查到圆整水平（~1e-6），不是 1e-9
assert abs(BASE.m_dip - M_DIP) / M_DIP < 1e-4, "m = M_s·πR_m²L_m 与契约参数不一致"


# ══════════════════════════════════════════════════ 单匝环的 B_z（椭圆积分，精确）
def bz_loop(R, rho, dz):
    """半径 R 的单匝环（单位电流）在 (rho, dz) 的 B_z。全 numpy 广播。"""
    R, rho, dz = np.broadcast_arrays(R, rho, dz)
    d2 = (R + rho) ** 2 + dz**2
    k2 = np.clip(4 * R * rho / d2, 0.0, 1 - 1e-14)
    return (MU0 / (2 * np.pi)) / np.sqrt(d2) * (
        ellipk(k2) + (R**2 - rho**2 - dz**2) / ((R - rho) ** 2 + dz**2) * ellipe(k2))


# ══════════════════════════════════════ Model-2：λ(z) 表（互易性 + 体平均，分块广播）
def _gl(n: int, lo: float, hi: float):
    """[lo, hi] 上的 Gauss–Legendre 节点与**归一化**权重（Σw = 1）。

    ★ 为什么不用中点法：中点法的 O(h²) 离散误差是一个与 Gate 0 的 ε **无关**的地板
    （实测 ~3e-4，把 ε² 信号淹掉，单调性被打破）。GL 对光滑被积函数指数收敛，
    同样 20 个节点地板 ~1e-10 —— 修的是求积器，不是门。"""
    x, w = np.polynomial.legendre.leggauss(n)
    return lo + (hi - lo) * (x + 1) / 2, w / 2


def lambda_table(zgrid: np.ndarray, geom: Geometry = BASE, *,
                 nrho: int = 12, nzm: int = 12, nr: int = 20, nz: int = 20,
                 chunk: int = 16) -> np.ndarray:
    """λ₂(z)：线圈（均匀载流带 [a−h, a+h]）在磁体体积上的 B_z 体平均 × M_s。
    互易性：这就是磁体对线圈的磁通链。四个维度全部 Gauss–Legendre。

    磁体径向用换元 u = (r/R_m)² ⟹ ∫f(r)·2πr dr = πR_m²·∫₀¹ f(R_m√u) du（GL 对 u）。"""
    uu, w_u = _gl(nrho, 0.0, 1.0)
    rr = geom.R_m * np.sqrt(uu)                                      # 磁体径向
    zz, w_zm = _gl(nzm, -geom.L_m / 2, geom.L_m / 2)                 # 磁体轴向
    if geom.band_h > 0:
        rl, w_rl = _gl(nr, geom.a - geom.band_h, geom.a + geom.band_h)
    else:                                                            # w→0：全部匝在 a 上
        rl, w_rl = np.full(1, geom.a), np.full(1, 1.0)
    zc, w_zc = _gl(nz, -geom.l_c / 2, geom.l_c / 2)                  # 线圈轴向

    #: 权重张量（磁体两维 × 线圈两维），已含匝数 N 与磁体体积 πR_m²L_m
    W = (w_u[:, None, None, None] * w_zm[None, :, None, None]
         * w_rl[None, None, :, None] * w_zc[None, None, None, :])
    vol = np.pi * geom.R_m**2 * geom.L_m

    R5 = rl[None, None, None, :, None]
    RHO5 = rr[None, :, None, None, None]
    out = np.empty(len(zgrid))
    for i0 in range(0, len(zgrid), chunk):
        zch = zgrid[i0:i0 + chunk]
        DZ5 = (zch[:, None, None, None, None] + zz[None, None, :, None, None]
               - zc[None, None, None, None, :])
        bz = bz_loop(R5, RHO5, DZ5)                                  # (nchunk,nrho,nzm,nr,nz)
        out[i0:i0 + chunk] = (bz * W[None]).sum(axis=(1, 2, 3, 4))
    return geom.M_s * geom.N * vol * out


class GSpline:
    """λ(z) 的样条 + 一阶导 G(z)。★ 带定义域护栏：越界抛异常，不许静默外推。"""

    def __init__(self, geom: Geometry = BASE, *, zmax: float = 32e-3, n: int = 321,
                 nrho: int = 12, nzm: int = 12, nr: int = 20, nz: int = 20):
        self.geom, self.zmax = geom, zmax
        self.meta = dict(zmax=zmax, n=n, nrho=nrho, nzm=nzm, nr=nr, nz=nz)
        self.zgrid = np.linspace(-zmax, zmax, n)                     # 对称、含精确 0
        self.lam_tab = lambda_table(self.zgrid, geom, nrho=nrho, nzm=nzm, nr=nr, nz=nz)
        self._spl = CubicSpline(self.zgrid, self.lam_tab)
        self._dspl = self._spl.derivative(1)
        self.gp0 = float(abs(self._spl.derivative(2)(0.0)))          # |G'(0)| = |λ''(0)|

    def _guard(self, z):
        z = np.asarray(z, float)
        bad = np.abs(z) > self.zmax
        if np.any(bad):
            raise ValueError(
                f"G 样条定义域越界：|z| 最大 {np.max(np.abs(z))*1e3:.2f} mm > "
                f"zmax = {self.zmax*1e3:.1f} mm —— 截断范围不够（收敛门该抓的 bug）")
        return z

    def lam(self, z):
        return self._spl(self._guard(z))

    def G(self, z):
        return self._dspl(self._guard(z))

    def __call__(self, z):
        return self.G(z)


# ═══════════════════════════════════════════ Model-0 闭式：(5) λ₀、(6) G₀、(7) G₀'(0)
def lam0(z, geom: Geometry = BASE):
    """式 (5)：点偶极子 + 薄螺线管的磁通链（有限长螺线管轴上场 × m，互易性）。"""
    z = np.asarray(z, float)
    c, a = geom.l_c / 2, geom.a
    f = lambda u: u / np.sqrt(a**2 + u**2)                           # noqa: E731
    return (MU0 * geom.N * geom.m_dip / (2 * geom.l_c)) * (f(z + c) - f(z - c))


def G0(z, geom: Geometry = BASE):
    """式 (6)：G₀ = dλ₀/dz。两个「线圈端面项」之差 —— 双峰结构的来源。严格奇函数。"""
    z = np.asarray(z, float)
    c, a2 = geom.l_c / 2, geom.a**2
    return (MU0 * geom.N * geom.m_dip * a2 / (2 * geom.l_c)) * (
        (a2 + (z + c) ** 2) ** -1.5 - (a2 + (z - c) ** 2) ** -1.5)


def Gp0_0(geom: Geometry = BASE) -> float:
    """式 (7)：|G₀'(0)| = 3μ₀Nma²/(2ℓ_c) · … 的闭式（取绝对值）。"""
    a2, c = geom.a**2, geom.l_c / 2
    return abs(-1.5 * MU0 * geom.N * geom.m_dip * a2 * (a2 + c**2) ** -2.5)


def zpk_model0(geom: Geometry = BASE) -> tuple[float, float]:
    """(6) 数值求极值（契约点名「无闭式」）→ (z_pk, |G|_max)。"""
    r = minimize_scalar(lambda z: -abs(G0(z, geom)), bounds=(1e-6, 0.03),
                        method="bounded", options=dict(xatol=1e-12))
    return float(r.x), float(abs(G0(r.x, geom)))


# ═══════════════════════════════════ V-1 ①：闭式 (6) vs 数值积分（薄线圈 + 点偶极子）
def G_direct_quad(z: float, geom: Geometry = BASE) -> float:
    """点偶极子磁通穿过每一匝的通量公式，对匝分布做自适应求积再对 z 求导（解析地在
    积分号下求导）。与 (6) 的闭式必须 < 1e-10 —— 纯数学恒等式。"""
    a2 = geom.a**2
    n_lin = geom.N / geom.l_c

    def dPhi_dz(zt):                                                  # dΦ_dipole→turn/dz
        d = z - zt
        return -3 * MU0 * geom.m_dip * a2 * d / (2 * (a2 + d**2) ** 2.5)

    val, _ = quad(dPhi_dz, -geom.l_c / 2, geom.l_c / 2, epsabs=1e-16, epsrel=1e-13)
    return n_lin * val


# ══════════════════════════ V-1 ②：互易性路径 —— G = m·d(B_coil,axis/I)/dz，不经磁通链
def B_axis_per_amp(z, geom: Geometry = BASE):
    """线圈（均匀载流带）在轴上 (0, z) 的 B_z / I。
    对轴向的积分有闭式（有限螺线管公式），只剩径向一维求积。"""
    z = np.asarray(z, float)
    c = geom.l_c / 2

    def sheet(R):                                                     # 半径 R 的薄螺线管
        return (MU0 * geom.N / (2 * geom.l_c)) * (
            (z + c) / np.sqrt(R**2 + (z + c) ** 2) - (z - c) / np.sqrt(R**2 + (z - c) ** 2))

    if geom.band_h <= 0:
        return sheet(geom.a)
    lo, hi = geom.a - geom.band_h, geom.a + geom.band_h
    out = np.zeros_like(z)
    for i, _ in np.ndenumerate(z):
        out[i] = quad(lambda R, zz=z[i]: float(
            (MU0 * geom.N / (2 * geom.l_c)) * (
                (zz + c) / np.sqrt(R**2 + (zz + c) ** 2)
                - (zz - c) / np.sqrt(R**2 + (zz - c) ** 2))) / (hi - lo),
            lo, hi, epsabs=1e-16, epsrel=1e-13)[0]
    return out


def G_reciprocity(z, geom: Geometry = BASE, h: float = 1e-5):
    """★ V-1 ②：G(z) = m · d(B_coil,z/I)/dz —— 先算线圈每安培的轴上场，再数值求导，
    再乘 m。这条路**不经过磁通链的概念**（四阶中心差分，截断+舍入 ≲ 1e-12 相对）。"""
    z = np.asarray(z, float)
    B = lambda u: B_axis_per_amp(u, geom)                             # noqa: E731
    dB = (B(z - 2 * h) - 8 * B(z - h) + 8 * B(z + h) - B(z + 2 * h)) / (12 * h)
    return geom.m_dip * dB


# ════════════════ V-1 ③：Amperian 面电流 × 离散匝 —— 互感求和（与 ①② 完全不同的分解）
def mutual_loops(Ra, Rb, dz):
    """两共轴圆环的互感（诺伊曼公式的椭圆积分形式）。"""
    Ra, Rb, dz = np.broadcast_arrays(Ra, Rb, dz)
    k2 = np.clip(4 * Ra * Rb / ((Ra + Rb) ** 2 + dz**2), 1e-30, 1 - 1e-14)
    k = np.sqrt(k2)
    return MU0 * np.sqrt(Ra * Rb) * ((2 / k - k) * ellipk(k2) - (2 / k) * ellipe(k2))


def lam_amperian(z, geom: Geometry = BASE, *, n_ring: int = 60,
                 n_layer: int | None = None, per_layer: int | None = None):
    """把磁体拆成侧面束缚电流环（K = M_s ⟹ 每环 dI = M_s·L_m/n_ring），把线圈拆成
    离散匝（n_layer 层 × per_layer 匝）。λ(z) = ΣΣ M(环, 匝)·dI。"""
    z = np.asarray(z, float)
    nl = n_layer or PRM.N_LAYER
    pl = per_layer or int(round(geom.N / nl))
    r_lay = (np.linspace(geom.a - geom.band_h, geom.a + geom.band_h, nl)
             if geom.band_h > 0 else np.full(1, geom.a))
    if geom.band_h <= 0:
        nl = 1
    z_turn = -geom.l_c / 2 + geom.l_c * (np.arange(pl) + 0.5) / pl
    w_turn = geom.N / (nl * pl)                                      # 匝数守恒（Σ = N）
    z_ring = -geom.L_m / 2 + geom.L_m * (np.arange(n_ring) + 0.5) / n_ring
    dI = geom.M_s * geom.L_m / n_ring

    out = np.zeros_like(z)
    for i, zi in np.ndenumerate(z):
        DZ = (zi + z_ring[:, None, None]) - z_turn[None, None, :]    # 环(磁体系) − 匝
        M = mutual_loops(geom.R_m, r_lay[None, :, None], DZ)
        out[i] = w_turn * dI * M.sum()
    return out


# ══════════════════════════════════════════════════════ 派生标量（Model-2 / Model-0）
def A_lin(gs: GSpline, tol: float = 0.10) -> float:
    """G 的线性化上限：|G(A)/(G'(0)·A) − 1| = tol 处（symbols[A_lin] 的定义）。"""
    gp0 = gs.gp0
    f = lambda A: abs(abs(gs.G(A)) / (gp0 * A) - 1) - tol             # noqa: E731
    return brentq(f, 1e-4, 0.02, xtol=1e-9)


def nu(gs, z0: float, A: float, n: int = 401) -> float:
    """A-2 的非线性度 ν(z₀,A) = max_{|u|≤A} |G(z₀+u) − G(z₀)| / |G(z₀)|（无关阶数）。"""
    u = np.linspace(-A, A, n)
    Gz0 = gs.G(np.array([z0]))[0] if isinstance(gs, GSpline) else gs(z0)
    Gu = gs.G(z0 + u) if isinstance(gs, GSpline) else gs(z0 + u)
    denom = abs(Gz0)
    if denom == 0:
        return np.inf
    return float(np.max(np.abs(Gu - Gz0)) / denom)


# ════════════════════════════════════════════════════════════════ 模块级缓存
_G2: GSpline | None = None


def model2(**kw) -> GSpline:
    """默认网格的 Model-2 样条（模块级缓存 —— run_all 里到处要用）。"""
    global _G2
    if _G2 is None or kw:
        gs = GSpline(**kw) if kw else GSpline()
        if not kw:
            _G2 = gs
        return gs
    return _G2


if __name__ == "__main__":
    import time
    t0 = time.time()
    gs = model2()
    print(f"Model-2 样条：{gs.meta}，耗时 {time.time()-t0:.1f} s")
    zpk0, gmax0 = zpk_model0()
    r = minimize_scalar(lambda z: -abs(gs.G(z)), bounds=(1e-6, 0.03),
                        method="bounded", options=dict(xatol=1e-12))
    print(f"Model-0: z_pk={zpk0*1e3:.4f} mm  |G|max={gmax0:.7f}  |G'(0)|={Gp0_0():.3f}")
    print(f"Model-2: z_pk={float(r.x)*1e3:.4f} mm  |G|max={abs(gs.G(r.x)):.7f}  "
          f"|G'(0)|={gs.gp0:.3f}")
    print(f"对称性: |G(0)|/|G|max = {abs(gs.G(0.0))/abs(gs.G(r.x)):.2e}")
    z = np.linspace(1e-3, 20e-3, 8)
    print(f"奇对称: max|G(z)+G(-z)|/|G|max = "
          f"{np.max(np.abs(gs.G(z)+gs.G(-z)))/abs(gs.G(r.x)):.2e}")
