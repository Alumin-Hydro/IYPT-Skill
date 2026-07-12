#!/usr/bin/env python3
"""均匀磁化圆柱磁体的磁感应强度 B(r, z)。

安培模型：均匀磁化圆柱 == 半径 R、长 L 的**有限长螺线管**，侧面束缚面电流 K = M_s (A/m)。
于是把它拆成一叠圆环，每个环带电流 dI = M_s dz'，对 z' ∈ [-L/2, L/2] 积分。

单个圆环的场（Simpson 的标准式，只用第一、二类完全椭圆积分）：

    alpha^2 = (R - r)^2 + d^2
    beta^2  = (R + r)^2 + d^2
    k^2     = 1 - alpha^2/beta^2 = 4Rr / beta^2

    B_z = mu0 I / (2 pi alpha^2 beta) * [ (R^2 - r^2 - d^2) E(k^2) + alpha^2 K(k^2) ]
    B_r = mu0 I d / (2 pi alpha^2 beta r) * [ (R^2 + r^2 + d^2) E(k^2) - alpha^2 K(k^2) ]

（scipy 的 ellipk/ellipe 吃的是**参数 m = k^2**，不是模数 k。）

★ 三条独立的对拍（先写预期，再算 —— 这是 Gate 0 的精神）：

  G-A  轴上闭式解：B_z(0,z) = mu0 M_s/2 * [ (z+L/2)/sqrt(R^2+(z+L/2)^2)
                                           - (z-L/2)/sqrt(R^2+(z-L/2)^2) ]
       磁体中心：B_z(0,0) = mu0 M_s (L/2)/sqrt(R^2+L^2/4) = 0.919 T（R = L/2 时是 mu0 M_s/sqrt2）

  G-B  远场必须回到点偶极子（m = M_s pi R^2 L）

  G-C  **B_r 必须等于 -1/(2 pi r) * dPhi/dz** —— 而 dPhi/dz 我们已经有闭式了（field.py）。
       这是两条**完全不同**的路径：一条是"把圆环的场积起来"，一条是"把互感对 z 求导"。
       它们吻合，才说明两边都对。

物理意义：由 Phi = 2 pi r A_phi 与 B_r = -dA_phi/dz 得 B_r = -(1/2 pi r) dPhi/dz。
所以**管壁处的径向磁场 B_r 就是涡流的驱动源**：动生电动势 E = -v dPhi/dz = v * 2 pi a * B_r。
F-5 画的"涡流分布"，其实就是管壁上的 B_r。
"""
from __future__ import annotations

import sys
import warnings

import numpy as np
from scipy.special import ellipk, ellipe

warnings.filterwarnings("ignore")
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

from params import MU0, R_MAG, L_MAG, A_TUBE, W_WALL, M_DIP, MS
from field import dphi_dz


# ---------------------------------------------------------------- 单个圆环的场

def loop_field(R: float, I, r, d):
    """半径 R、电流 I 的圆环，在 (r, d) 处的 (B_r, B_z)。d 是相对环平面的轴向距离。"""
    r = np.asarray(r, float)
    d = np.asarray(d, float)
    r_safe = np.where(r < 1e-12, 1e-12, r)          # 轴上 B_r -> 0，避免 0/0

    a2 = (R - r_safe) ** 2 + d ** 2
    b2 = (R + r_safe) ** 2 + d ** 2
    b = np.sqrt(b2)
    m = 1.0 - a2 / b2                                # = k^2
    m = np.clip(m, 0.0, 1.0 - 1e-15)                 # 电流片上 m -> 1，K 对数发散
    K, E = ellipk(m), ellipe(m)

    c = MU0 * np.asarray(I, float) / (2.0 * np.pi)
    Bz = c / (a2 * b) * ((R ** 2 - r_safe ** 2 - d ** 2) * E + a2 * K)
    Br = c * d / (a2 * b * r_safe) * ((R ** 2 + r_safe ** 2 + d ** 2) * E - a2 * K)
    Br = np.where(r < 1e-12, 0.0, Br)                # 轴对称 -> 轴上 B_r 恒为 0
    return Br, Bz


# ---------------------------------------------------------------- 圆柱磁体的场

def cylinder_field(r, z, *, R=R_MAG, L=L_MAG, Ms=MS, n_gauss: int = 400):
    """有限长均匀磁化圆柱的 (B_r, B_z)。

    对侧面电流片做 Gauss-Legendre 求积（n_gauss 个节点，向量化到整个网格）。
    n_gauss 是收敛门要拧的参数。
    """
    r = np.asarray(r, float)
    z = np.asarray(z, float)
    x, w = np.polynomial.legendre.leggauss(n_gauss)
    zp = 0.5 * L * x                                  # z' ∈ [-L/2, L/2]
    wt = 0.5 * L * w * Ms                             # dI = M_s dz'

    Br = np.zeros_like(r, dtype=float)
    Bz = np.zeros_like(r, dtype=float)
    for zpi, wi in zip(zp, wt):
        br, bz = loop_field(R, wi, r, z - zpi)
        Br += br
        Bz += bz
    return Br, Bz


# ---------------------------------------------------------------- 参照解

def onaxis_exact(z, *, R=R_MAG, L=L_MAG, Ms=MS):
    """G-A：有限长螺线管的**轴上闭式解**（教科书结果）。"""
    z = np.asarray(z, float)
    zp, zm = z + L / 2, z - L / 2
    return 0.5 * MU0 * Ms * (zp / np.sqrt(R ** 2 + zp ** 2) - zm / np.sqrt(R ** 2 + zm ** 2))


def dipole_field(r, z, *, m=M_DIP):
    """G-B：点偶极子的场（m 沿 z）。"""
    r = np.asarray(r, float)
    z = np.asarray(z, float)
    s2 = r ** 2 + z ** 2
    s2 = np.where(s2 < 1e-18, 1e-18, s2)
    s5 = s2 ** 2.5
    c = MU0 * m / (4.0 * np.pi)
    Br = c * 3.0 * z * r / s5
    Bz = c * (2.0 * z ** 2 - r ** 2) / s5
    return Br, Bz


def Br_from_flux(r, z, *, R=R_MAG, L=L_MAG, Ms=MS):
    """G-C：B_r = -(1/2 pi r) dPhi/dz —— **完全不同的一条路**（互感对 z 求导）。"""
    r = np.asarray(r, float)
    return -dphi_dz(R, L, Ms, r, z) / (2.0 * np.pi * r)


# ---------------------------------------------------------------- 验证门

def gates(verbose=True) -> dict:
    out = {}

    # ---- G-A：轴上闭式解
    zz = np.linspace(-6 * L_MAG, 6 * L_MAG, 241)
    _, bz_num = cylinder_field(np.zeros_like(zz), zz)
    bz_exact = onaxis_exact(zz)
    err_a = float(np.max(np.abs(bz_num - bz_exact)) / np.max(np.abs(bz_exact)))
    b_center = float(onaxis_exact(0.0))
    b_center_pred = MU0 * MS * (L_MAG / 2) / np.sqrt(R_MAG ** 2 + (L_MAG / 2) ** 2)
    out["G-A"] = dict(err=err_a, passed=err_a < 1e-10,
                      b_center=b_center, b_center_pred=float(b_center_pred))

    # ---- G-B：远场 -> 点偶极子
    rows_b = []
    for f in (2, 5, 10, 20, 50):
        s = f * L_MAG
        # 取 45 度方向的一点
        rr, zz1 = s / np.sqrt(2), s / np.sqrt(2)
        br, bz = cylinder_field(np.array([rr]), np.array([zz1]))
        brd, bzd = dipole_field(np.array([rr]), np.array([zz1]))
        bmag = np.hypot(br, bz)[0]
        bmagd = np.hypot(brd, bzd)[0]
        rows_b.append(dict(s_over_L=f, B=float(bmag), B_dip=float(bmagd),
                           err=float(abs(bmag - bmagd) / bmagd)))
    out["G-B"] = dict(rows=rows_b, passed=rows_b[-1]["err"] < 1e-3)

    # ---- G-C：B_r 的两条独立路径
    rr = np.linspace(1.2 * R_MAG, 4 * A_TUBE, 97)
    zz2 = np.linspace(-3 * L_MAG, 3 * L_MAG, 97)
    Rg, Zg = np.meshgrid(rr, zz2, indexing="ij")
    br_loop, _ = cylinder_field(Rg, Zg)
    br_flux = Br_from_flux(Rg, Zg)
    scale = np.max(np.abs(br_loop))
    err_c = float(np.max(np.abs(br_loop - br_flux)) / scale)
    out["G-C"] = dict(err=err_c, passed=err_c < 1e-9)

    # ---- 收敛门：Gauss 节点数翻倍
    r1 = np.array([A_TUBE]); z1 = np.array([L_MAG / 2])
    b_400 = np.hypot(*cylinder_field(r1, z1, n_gauss=400))[0]
    b_800 = np.hypot(*cylinder_field(r1, z1, n_gauss=800))[0]
    d_conv = float(abs(b_800 - b_400) / b_400)
    out["conv"] = dict(err=d_conv, passed=d_conv < 1e-6)

    if verbose:
        print("=" * 76)
        print("B 场的验证门 —— 三条**独立**路径必须互相对上")
        print("=" * 76)
        print()
        print(f"  G-A · 轴上闭式解  (数值积分 vs 教科书的有限长螺线管公式)")
        print(f"        最大相对误差 = {err_a:.3e}      {'PASS' if out['G-A']['passed'] else '**FAIL**'}")
        print(f"        磁体中心 B_z(0,0) = {b_center:.4f} T")
        print(f"        算前的预言        = {b_center_pred:.4f} T   "
              f"(= mu0*M_s/sqrt(2)，因 R = L/2)")
        print()
        print(f"  G-B · 远场 -> 点偶极子  (45° 方向)")
        print(f"        {'s/L':>6} {'|B| 精确':>14} {'|B| 偶极子':>14} {'相对偏差':>12}")
        for r_ in rows_b:
            print(f"        {r_['s_over_L']:>6} {r_['B']:>14.4e} {r_['B_dip']:>14.4e} "
                  f"{r_['err']*100:>11.4f}%")
        print(f"        {'PASS' if out['G-B']['passed'] else '**FAIL**'}  "
              f"(s = 50L 处偏差 {rows_b[-1]['err']*100:.5f}%)")
        print()
        print(f"  G-C · B_r 的两条独立路径  (圆环场积分  vs  -1/(2πr)·∂Φ/∂z 的闭式)")
        print(f"        最大相对误差 = {err_c:.3e}      {'PASS' if out['G-C']['passed'] else '**FAIL**'}")
        print(f"        ** 这两条路完全不同：一条把圆环的场积起来，一条把互感对 z 求导。**")
        print(f"        ** 它们吻合到 {err_c:.0e}，说明两边都对。 **")
        print()
        print(f"  收敛门 · Gauss 节点 400 -> 800")
        print(f"        相对变化 = {d_conv:.3e}      {'PASS' if out['conv']['passed'] else '**FAIL**'}")
        print()

    return out


# ---------------------------------------------------------------- 偶极子近似的误差

def dipole_error_at(r, z) -> float:
    """点偶极子近似在 (r,z) 处的相对误差 |B_exact - B_dip| / |B_exact|。"""
    br, bz = cylinder_field(np.asarray(r), np.asarray(z))
    brd, bzd = dipole_field(np.asarray(r), np.asarray(z))
    return float(np.hypot(br - brd, bz - bzd) / np.hypot(br, bz))


if __name__ == "__main__":
    from params import banner
    banner()
    g = gates()

    print("=" * 76)
    print("点偶极子近似在**管壁上**错得有多离谱？")
    print("=" * 76)
    print()
    print(f"  管内壁 r = a = {A_TUBE*1e3:.1f} mm   (a/L = {A_TUBE/L_MAG:.2f}，"
          f"判据 a >> L **根本不满足**)")
    print()
    print(f"  {'z (mm)':>9} {'|B| 精确 (T)':>14} {'|B| 偶极子 (T)':>15} {'相对误差':>12}")
    for zmm in (0, 2, 5, 8, 12, 20, 40):
        e = dipole_error_at(A_TUBE, zmm * 1e-3)
        br, bz = cylinder_field(np.array([A_TUBE]), np.array([zmm * 1e-3]))
        brd, bzd = dipole_field(np.array([A_TUBE]), np.array([zmm * 1e-3]))
        print(f"  {zmm:>9} {np.hypot(br,bz)[0]:>14.5f} {np.hypot(brd,bzd)[0]:>15.5f} "
              f"{e*100:>11.1f}%")
    print()
    print(f"  管外壁 r = a+w = {(A_TUBE+W_WALL)*1e3:.1f} mm, z = 0:  "
          f"误差 {dipole_error_at(A_TUBE+W_WALL, 0.0)*100:.1f}%")
