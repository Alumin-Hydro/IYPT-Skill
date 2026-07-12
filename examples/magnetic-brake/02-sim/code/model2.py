#!/usr/bin/env python3
"""Model-2：方程 (15)，有限长磁体 + 有限壁厚。

    F(v) = sigma v ∫_a^{a+w} dr/(2 pi r) ∫_{-inf}^{inf} (dPhi(r,z)/dz)^2 dz

    => b = F/v = sigma ∫_a^{a+w} dr/(2 pi r) ∫_{-inf}^{inf} (dPhi/dz)^2 dz

dPhi/dz 由 field.py 闭式给出（Leibniz 消掉了一层积分），所以这里只剩
一个一维广义积分套一层径向积分 —— 数值上很干净。

数值参数（zmax_factor / epsrel）**全部暴露出来**，因为收敛门（Gate 1）要拧它们：
结果必须与网格/容差/截断无关。截断尤其阴 —— 截短了结果**系统性偏小**，而且偏得
平滑，曲线看起来完全正常，只是每个点都错了一点，于是你的**斜率**是错的。
"""
from __future__ import annotations

import numpy as np
from scipy.integrate import quad

from field import dphi_dz, dphi_dz_dipole


def _z_integral(dfun, r: float, a: float, zmax_factor: float, epsrel: float, limit: int) -> float:
    """∫_{-inf}^{inf} (dPhi/dz)^2 dz。

    被积函数是**偶函数**（dPhi/dz 是奇的），所以 = 2 ∫_0^inf。少一半工作量，
    也少一半出错机会。

    截断长度用**自然尺度的倍数**（zmax_factor * a），不是绝对值 —— 参数扫描时 a 会变，
    绝对截断长度会在扫描的一端悄悄失效。
    """
    v, _ = quad(lambda z: dfun(r, z) ** 2, 0.0, zmax_factor * a,
                limit=limit, epsabs=0.0, epsrel=epsrel)
    return 2.0 * v


def damping(R: float, L: float, Ms: float, a: float, w: float, sigma: float, *,
            thin_wall: bool = False,
            dipole_field: bool = False,
            m_dip: float | None = None,
            zmax_factor: float = 200.0,
            epsrel: float = 1e-10,
            limit: int = 400) -> float:
    """(15) 的阻尼系数 b。

    thin_wall=True   -> 用薄壁近似 w/(2 pi a) 替代径向积分 ∫_a^{a+w} dr/(2 pi r)。
                        **只用来隔离 A-2 这一条假设本身的效应**（见 acceptance.md 的
                        A-2 判读：读法 (a)，两边都用有限长磁体的场）。
    dipole_field=True -> 用点偶极子场替代有限长磁体的场。
                        **只用来做 Gate 0 的对拍和注入式冒烟测试。**
                        拿它冒充 Model-2 正是 AS-9 (must_not) 要抓的东西。
    """
    if dipole_field:
        if m_dip is None:
            raise ValueError("dipole_field=True 时必须给 m_dip")
        dfun = lambda r, z: dphi_dz_dipole(m_dip, r, z)          # noqa: E731
    else:
        dfun = lambda r, z: dphi_dz(R, L, Ms, r, z)              # noqa: E731

    if thin_wall:
        zi = _z_integral(dfun, a, a, zmax_factor, epsrel, limit)
        return sigma * w / (2.0 * np.pi * a) * zi

    outer, _ = quad(lambda r: _z_integral(dfun, r, a, zmax_factor, epsrel, limit) / (2.0 * np.pi * r),
                    a, a + w, limit=limit // 2, epsabs=0.0, epsrel=epsrel)
    return sigma * outer


def vt_model2(R: float, L: float, Ms: float, a: float, w: float, sigma: float,
              M: float, g: float, **kw) -> float:
    """终速 v_t = M g / b。"""
    return M * g / damping(R, L, Ms, a, w, sigma, **kw)
