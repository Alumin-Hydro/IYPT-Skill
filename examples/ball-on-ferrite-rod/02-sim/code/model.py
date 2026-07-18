#!/usr/bin/env python3
r"""物理模型：棒受迫共振 + 球的事件驱动弹跳映射。

Model-0（闭式）：
  · 共振 f_n=(2n-1)c/4L；受迫阻尼响应 A(f)=A_dc·|χ(f)|（Lorentz）
  · 弹跳阈值 Γ=Aω²/g=1；随机相位稳态 h̄=(1+e)/(1-e)(Aω)²/4g
Model-2（数值）：
  · 事件驱动：飞行(自由落体)+碰撞 (5) v_out=(1+e)w+e·u；棒尖 z_tip=A sin(ωt)
  · 相位在碰撞间以 φ→φ+ω·2u/g 演化（敏感依赖⟹有效随机）——确定性混沌表现为随机相位统计稳态
"""
from __future__ import annotations
import math
import numpy as np
from params import G


# ─────────────────────────────────────────── 棒受迫共振（Model-0/Model-2 骨架）
def resonance_A(f, f1, Q, A_dc=1.0):
    """受迫阻尼谐振子的稳态振幅响应（Lorentz），峰在 f1、半带宽 f1/2Q。"""
    f = np.asarray(f, float)
    x = f / f1
    return A_dc / np.sqrt((1 - x**2) ** 2 + (x / Q) ** 2)


# ─────────────────────────────────────────── 弹跳映射（Model-2 核心）
def bounce_series(A, w, e, n=60000, burn=20000, phi0=0.123, g=G):
    """事件驱动弹跳：返回稳态段的落速序列 u[] 与落相 φ[]（确定性混沌相位演化）。

    棒尖位移 μm ≪ 飞行 mm，故飞行时间取 2u/g（Model-2 完整版会含棒尖位移修正，
    量级 A/h̄ ~ 1e-3，进 Model-1）。返回稳态段（burn 之后）。
    """
    u = A * w
    phi = phi0
    us, phis = [], []
    for i in range(n):
        T = 2.0 * u / g
        phi = (phi + w * T) % (2 * math.pi)
        wtip = A * w * math.cos(phi)
        u = abs((1 + e) * wtip + e * u)
        if i >= burn:
            us.append(u); phis.append(phi)
    return np.array(us), np.array(phis)


def hbar(A, w, e, **kw):
    us, _ = bounce_series(A, w, e, **kw)
    return float(np.mean(us**2) / (2 * G))


def hbar_theory(A, w, e, g=G):
    return (1 + e) / (1 - e) * (A * w) ** 2 / (4 * g)


def bounce_cv(A, w, e, **kw):
    """稳态弹高分布变异系数（随机相位⟹宽；锁相⟹~0）。"""
    us, _ = bounce_series(A, w, e, **kw)
    h = us**2 / (2 * G)
    return float(np.std(h) / np.mean(h))


# ─────────────────────────────────────────── Lyapunov（敏感依赖 ⟹ 混沌）
def lyapunov(A, w, e, n=4000, burn=500, d0=1e-9, g=G):
    """两条邻近轨迹的对数发散率（弹跳映射的最大 Lyapunov 指数，单位：每次碰撞）。

    Gate 0：对可积极限（关掉相位演化 = 固定相位）λ 必须落回 ~0。
    """
    def step(u, phi):
        T = 2.0 * u / g
        phi = (phi + w * T) % (2 * math.pi)
        u = abs((1 + e) * A * w * math.cos(phi) + e * u)
        return u, phi
    u1, p1 = A * w, 0.123
    u2, p2 = u1 + d0, p1
    s = 0.0
    for i in range(n):
        u1, p1 = step(u1, p1)
        u2, p2 = step(u2, p2)
        d = abs(u2 - u1) + 1e-30
        if i >= burn:
            s += math.log(d / d0)
        u2 = u1 + (u2 - u1) * d0 / d       # 重正化
        p2 = p1
    return s / (n - burn)


def lyapunov_integrable(A, w, e, n=4000, burn=500, d0=1e-9, g=G):
    """Gate 0 对拍：固定相位（不演化）⟹ 线性映射 u_{n+1}=|e·u+const|，λ=ln e < 0（收缩），
    不是正的混沌 λ。用来证明『正 λ 是真混沌，不是浮点噪声』。"""
    wtip = A * w * math.cos(1.0)          # 固定相位
    u1, u2 = A * w, A * w + d0
    s = 0.0
    for i in range(n):
        u1 = abs((1 + e) * wtip + e * u1)
        u2 = abs((1 + e) * wtip + e * u2)
        d = abs(u2 - u1) + 1e-30
        if i >= burn:
            s += math.log(d / d0)
        u2 = u1 + (u2 - u1) * d0 / d
    return s / (n - burn)


# ─────────────────────────────────────────── 分岔 / regime
def poincare_heights(A, w, e, n=2000, burn=1000, phi0=0.123):
    us, _ = bounce_series(A, w, e, n=n, burn=burn, phi0=phi0)
    return us**2 / (2 * G)


def gamma_of(A, w, g=G):
    return A * w**2 / g
