#!/usr/bin/env python3
"""有限长均匀磁化圆柱的磁通梯度 dPhi/dz —— **闭式**。

安培模型：均匀磁化圆柱 ≡ 侧面束缚面电流 K = M_s（A/m）。
于是半径 r 的圆环上的磁通是对共轴圆环互感 M(R,r,d) 的积分：

    Phi(r,z) = M_s ∫_{-L/2}^{L/2} M(R, r, z-z') dz'
             = M_s ∫_{z-L/2}^{z+L/2} M(R, r, u) du        （换元 u = z-z'）

**两个积分限都含 z，被积函数不含 z** —— Leibniz 求导，积分整个消失：

    dPhi/dz = M_s [ M(R, r, z+L/2) − M(R, r, z−L/2) ]        ★ 闭式

原本的三重数值积分塌成两次特殊函数求值。**能解析给出的导数，永远不要数值求**
（数值微分是噪声放大器；spec 的 suggested_method 里也这么说）。

**副产品是物理洞察**：这个式子就是「磁体两个端面的等效电流环之差」——它天然是 z 的
奇函数，于是涡流分布必然是**反对称双峰**（前方排斥、后方吸引，两者都阻碍下落）。
这正是 Lenz 定律的样子，也正是 F-5 的 expected_shape 描述的东西。

坑（见 references/numerical-recipes.md）：
  * scipy 的 ellipk(m) 吃的是**参数 m = k^2**，不是模数 k。传错不报错，只给你错的数。
  * scipy **没有**完全第三类椭圆积分。直接照 (15) 的螺线管离轴场硬上会撞墙——
    走互感路线只需第一、二类，绕开了。
"""
from __future__ import annotations

import numpy as np
from scipy.special import ellipk, ellipe

from params import MU0


def mutual(R: float, r, d):
    """共轴圆环互感 M(R, r, d)。半径 R 与 r，轴向间距 d。

        M = mu0 * sqrt(R r) [ (2/k - k) K(k) - (2/k) E(k) ],
        k^2 = 4 R r / ((R+r)^2 + d^2)

    只用第一、二类完全椭圆积分 —— scipy 都有。
    """
    d = np.asarray(d, dtype=float)
    k2 = 4.0 * R * r / ((R + r) ** 2 + d ** 2)
    k = np.sqrt(k2)
    # ellipk / ellipe 的入参是 m = k^2（不是 k！）
    return MU0 * np.sqrt(R * r) * ((2.0 / k - k) * ellipk(k2) - (2.0 / k) * ellipe(k2))


def dphi_dz(R: float, L: float, Ms: float, r: float, z):
    """有限长圆柱：dPhi/dz(r, z)。**闭式**，两次椭圆积分求值。"""
    return Ms * (mutual(R, r, np.asarray(z, float) + L / 2.0)
                 - mutual(R, r, np.asarray(z, float) - L / 2.0))


def dphi_dz_dipole(m: float, r: float, z):
    """点偶极子的 dPhi/dz —— Model-0 用的那个场。

        Phi_dip  =  mu0 m r^2 / (2 (r^2+z^2)^{3/2})
        dPhi/dz  = -3 mu0 m r^2 z / (2 (r^2+z^2)^{5/2})

    只用于对拍与 F-5 的对照曲线。**不要拿它冒充 Model-2 的场**——那正是
    F-2 的 must_not 断言（AS-9）要抓的东西。
    """
    z = np.asarray(z, float)
    return -1.5 * MU0 * m * r ** 2 * z / (r ** 2 + z ** 2) ** 2.5


def peak_z_dipole(a: float) -> float:
    """点偶极子情形下 |dPhi/dz| 的峰位：z = ±a/2。

    由 d/dz [ z (a^2+z^2)^{-5/2} ] = 0  =>  a^2 + z^2 = 5 z^2  =>  z = ±a/2。
    这是 F-5 的 expected_shape 里那个 "±a/2" 的来历 —— 它是**点偶极子**的结果，
    有限长磁体的峰位会被两个端面拉开（见 acceptance.md 的 AS-16 判读）。
    """
    return a / 2.0
