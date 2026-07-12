#!/usr/bin/env python3
"""Model-0：点偶极子 + 薄壁的闭式解。**这是地面真值。**

    (10)  b   = (45/1024) * mu0^2 m^2 sigma w / a^4
    (11)  v_t = (1024/45) * M g a^4 / (mu0^2 m^2 sigma w)
    (12)  v(t) = v_t (1 - exp(-t/tau)),   tau = M/b = v_t/g

Model-0 必须**精确**重现 targets[].baseline_value。重现不了 = 参数读错或单位错，
先修这个，别往下走（Gate 2）。
"""
from __future__ import annotations

import numpy as np

from params import MU0, G, M_MASS


def b_model0(m: float, a, w, sigma) -> float:
    """(10) 阻尼系数。"""
    return 45.0 * MU0 ** 2 * m ** 2 * sigma * w / (1024.0 * np.asarray(a, float) ** 4)


def vt_model0(m: float, a, w, sigma, M: float = None) -> float:
    """(11) 终速。"""
    M = M_MASS if M is None else M
    return M * G / b_model0(m, a, w, sigma)


def tau_model0(vt) -> float:
    """(12) 时间常数 tau = M/b = v_t/g。"""
    return np.asarray(vt, float) / G


def v_of_t(t, vt: float, tau: float):
    """(12) 的闭式解。"""
    return vt * (1.0 - np.exp(-np.asarray(t, float) / tau))


def x_of_t(t, vt: float, tau: float):
    """位移：x(t) = ∫v dt = v_t [ t - tau (1 - e^{-t/tau}) ]"""
    t = np.asarray(t, float)
    return vt * (t - tau * (1.0 - np.exp(-t / tau)))


def distance_to_fraction(frac: float, vt: float, tau: float) -> float:
    """v/v_t 达到 frac 时的下落距离。

        v/v_t = frac  =>  e^{-t/tau} = 1-frac  =>  t = -tau ln(1-frac)
        x = v_t tau [ -ln(1-frac) - frac ]

    **注意 -frac 那一项。** 漏掉它就是 01-review-r1.md 抓到的那个"错误捷径"
    （x ≈ 4.6 v_t tau），系统性高估 27%。model-spec.json 的 F-3 expected_shape
    里存的正是那个错误值 0.35 mm（正确值 0.277 mm）—— 见 acceptance.md 的 SD-2。
    """
    return vt * tau * (-np.log(1.0 - frac) - frac)


PI1_THEORY = 1024.0 / 45.0     # = 22.7556，F-4 的水平渐近线


def pi1(vt, m: float, a, w, sigma, M: float = None) -> float:
    """无量纲终速 Pi_1 = v_t mu0^2 m^2 sigma w / (M g a^4)。

    Model-0 下它恒等于 1024/45 —— 与所有参数无关。**这是恒等式，不是巧合**，
    也正是 F-4 里 Model-0 的点必须精确坍缩的原因（AS-12）。
    """
    M = M_MASS if M is None else M
    return (np.asarray(vt, float) * MU0 ** 2 * m ** 2 * sigma * w
            / (M * G * np.asarray(a, float) ** 4))


def pi2(w, a) -> float:
    """薄壁参数 Pi_2 = w/a。"""
    return np.asarray(w, float) / np.asarray(a, float)
