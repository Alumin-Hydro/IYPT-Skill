# Ball on Ferrite Rod — 物理分析

> 独立跑一遍流水线（CUPT 2023 No. 11）。**在本文完成前不读 `example-ppt/` 的参考报告解答**，
> 只用 `00-problem.md` 里逐字抄的题面。设定书（S-n）在 `00-problem.md`，本文只记假设（A-n）与推导。
>
> **[GAP]**：暂无未闭合缺口。若 3 轮审稿后仍有 MAJOR，在此声明。

## 符号表

| 符号 | 含义 | 单位 |
|---|---|---|
| $E,\rho,c$ | 棒杨氏模量 / 密度 / 纵波声速 $c=\sqrt{E/\rho}$ | Pa, kg/m³, m/s |
| $L$ | 棒长 | m |
| $\lambda_s$ | 磁致伸缩饱和应变 | 1 |
| $Q$ | 棒声学品质因数 | 1 |
| $f,\omega$ | 驱动频率 / 角频率 $\omega=2\pi f$ | Hz, rad/s |
| $f_n$ | 棒第 $n$ 纵向本征频率 | Hz |
| $A$ | 棒尖振幅（位移） | m |
| $g$ | 重力加速度 | m/s² |
| $e$ | 球-棒尖恢复系数 | 1 |
| $m$ | 球质量 | kg |
| $u_n$ | 第 $n$ 次落回棒尖的球速率（对地） | m/s |
| $w_n=A\omega\cos\phi_n$ | 第 $n$ 次碰撞时棒尖速度 | m/s |
| $\phi_n$ | 第 $n$ 次碰撞时的驱动相位 | rad |
| $\bar h$ | 稳态平均弹跳高度 | m |
| $\Gamma\equiv A\omega^2/g$ | **无量纲驱动加速度**（主控参数） | 1 |
| $f_{\rm bounce}$ | 弹跳频率 $\approx g/(2u)$ | Hz |

## §2 · 假设台账 (Assumption Ledger)

每条：陈述 / 判据（不等式）/ 代入检查 / 失效边界 / 分级。

### A-1 · 棒的声学边界条件 = **固定-自由**（底端固定、顶端自由） — **RISKY**
- **陈述**：棒竖直放在管底，底端与刚性管底良好耦合 ⟹ 底端位移节点（固定）；顶端放球、面向空气 ⟹ 应力自由端。故 $f_n=(2n{-}1)c/4L$，模式形状 $\xi(x)=\sin\!\big[(2n{-}1)\pi x/2L\big]$，棒尖是**波腹**。
- **判据（不等式）**：底端接触声阻抗 $Z_{\rm base}\gg Z_{\rm rod}=\rho c\,\pi R_{\rm rod}^2$；否则底端趋于自由，退化为**自由-自由** $f_n=nc/2L$。
- **代入检查**：$Z_{\rm rod}=4800\cdot5590\cdot\pi(0.005)^2\approx2.1\times10^3$ kg/s。管底若是金属/石材，$Z_{\rm base}$ 大得多 ⟹ 判据成立；但若只是**轻放**（点接触），底端实为自由 —— **无法先验确定，故 RISKY**。
- **失效边界**：底端从「固定」滑向「自由」，$f_1$ 从 $c/4L=14$ kHz 跳到 $c/2L=28$ kHz。
- **分级**：**RISKY**。★ **退化特征（离散、不连续）**：**基频共振峰的位置** —— 固定-自由给 $c/4L$，自由-自由给 $c/2L$，**两者精确差 2 倍，中间没有过渡值**。这是 Skill 2 识破 BC 取错的钥匙（`risky_assumption_checks` A-1）。

### A-2 · 高频随机相位（碰撞相位在 $[0,2\pi)$ 上均匀） — **LOAD-BEARING**
- **陈述**：$f\gg f_{\rm bounce}$ ⟹ 相邻两次落点之间棒尖振动数百上千次；飞行时间对落速的敏感依赖（$\omega\cdot2u/g\bmod2\pi$）使落相 $\phi_n$ 去相关、等效均匀随机。⟹ 稳态用能量平衡而非确定性映射。
- **判据（不等式）**：$f/f_{\rm bounce}=\Gamma/\pi\gg1$（推导见 §3）。
- **代入检查**：可见弹跳（$\bar h\sim$ mm）对应 $\Gamma\sim10^3$ ⟹ $f/f_{\rm bounce}\sim300$–$900\gg1$ ✓（`/tmp/ferrite_numbers.py` 实算）。
- **失效边界**：$\Gamma\lesssim$ 几（近阈值）⟹ $f/f_{\rm bounce}\sim O(1)$ ⟹ 退回**确定性 bouncing-ball 映射**（周期倍化 / 混沌），但此时 $\bar h\sim$ nm（不可见，见 §5 与 P1）。
- **分级**：**LOAD-BEARING**（在可见工作点成立；近阈值不成立，而近阈值本就不可见）。若不成立 ⟹ §5 的 $\bar h$ 闭式换成确定性映射的分岔结构。

### A-3 · 球 = 刚性点质量，单次接触（无 chattering / 无多点接触） — LOAD-BEARING
- **判据**：接触时间 $\tau_c\ll$ 飞行时间 $T_{\rm bounce}$，且 $\tau_c\ll$ 驱动周期 $1/f$（否则一次「落」里棒尖已换向多次）。Hertz 接触 $\tau_c\sim(m^2/(R_bE_*^2 u))^{1/5}$。
- **代入检查**：钢/玻璃 $\tau_c\sim10\,\mu$s，与驱动周期 $71\,\mu$s 同量级 —— **不是 $\ll$**。⟹ 接触期间棒尖已振动 $\sim1/7$ 周期，碰撞不是瞬时。**列为 Model-1 的修正**（有限接触时间对有效 $e$ 与相位的修正）。
- **分级**：LOAD-BEARING（瞬时碰撞是 Model-0 的骨架；有限 $\tau_c$ 进 Model-1）。

### A-4 · 恢复系数 $e$ 与碰撞速度无关 — **RISKY**
- **判据**：$u<u_{\rm yield}$（低于塑性屈服速度，$e$ 才近常数）；高速下 $e\propto u^{-1/4}$（塑性）。
- **代入检查**：$u\sim0.1$–$0.3$ m/s，玻璃-铁氧体屈服速度 $\sim$ 0.1 m/s ⟹ **勉强，可能进入速度依赖区** ⟹ RISKY。
- **失效边界**：$\bar h$ 的 $(1+e)/(1-e)$ 因子对 $e$ 极敏感（$e{=}0.6{\to}0.7$ 使因子 $4{\to}5.7$）；$e(u)$ 会改变标度律。
- **分级**：**RISKY**。★ **退化特征**：$\bar h$ vs $(A\omega)^2$ 的**斜率**是否恒定 —— 常数 $e$ ⟹ 严格线性（斜率 $=(1+e)/(1-e)/4g$）；速度依赖 $e$ ⟹ 斜率随驱动漂移（`risky_assumption_checks` A-4）。

### A-5 · 单模共振（棒尖运动 = 基频单一正弦，高次模可忽略） — LOAD-BEARING
- **判据**：驱动 $f$ 在 $f_1$ 的半带宽 $f_1/2Q$ 内 ⟹ 基频响应 $\gg$ 高次模；$|f-f_1|\ll|f_3-f_1|$。
- **代入检查**：$Q\sim100$ ⟹ 半带宽 $\sim70$ Hz，$f_3-f_1=2c/4L=28$ kHz ⟹ 靠近 $f_1$ 时高次模被压 $\sim(f_1/(f_3-f_1))^2\sim0.25$… 实际非共振时更小。近共振单模主导 ✓。
- **分级**：LOAD-BEARING。

### A-6 · 球非磁非导 ⟹ 飞行中无直接电磁力 — SAFE（由 S-5 设计保证）
- **判据**：玻璃 $\mu_r\approx1,\sigma\approx0$ ⟹ 磁力、涡流力 $=0$。
- **分级**：SAFE。**这是「排除 confound」的设定选择**，机制预算 M-4/M-6 详述钢球的相反情形。

### A-7 · 磁致伸缩是棒的主驱动（vs 端面 Maxwell 应力、vs 涡流） — LOAD-BEARING
- 见机制预算 M-1/M-2/M-3。判据与代入在那里。分级 LOAD-BEARING（若端面 Maxwell 应力可比，驱动的**频率成分**与位置变，但共振结构不变）。

### A-8 · 飞行中空气阻力可忽略 — SAFE
- **判据**：$F_{\rm drag}/mg\ll1$。**代入检查**：$Re\approx40$，Newton 阻力 $/mg\approx2.5\times10^{-4}$（实算）⟹ SAFE。扫描端点：即便 $u\to0.5$ m/s，比值 $\sim10^{-3}$，仍 SAFE。

### A-9 · 球质量负载不失谐棒共振 — LOAD-BEARING
- **判据**：$m\ll M_{\rm rod,eff}=\rho\cdot\pi R_{\rm rod}^2L/2$。**代入**：$M_{\rm rod,eff}=4800\cdot\pi(0.005)^2\cdot0.1/2\approx1.9\times10^{-2}$ kg $=19$ g；$m=0.035$ g ⟹ $m/M_{\rm rod,eff}\approx1.8\times10^{-3}\ll1$ ✓。且球大部分时间在**飞行**、不接触 ⟹ 负载更小。SAFE-ish，记 LOAD-BEARING。

### A-10 · 一维（球不横move、不蹭壁、不自旋耗能） — LOAD-BEARING
- **判据**：棒尖平顶 + 管导向 ⟹ 横向恢复；判据 $A_{\rm lateral}\ll R_{\rm rod}$。RISKY 苗头（真实实验里球常横move / 打转飞出）—— 记 LOAD-BEARING 并在实验方案里要求导向套。

## §3 · 量纲分析与标度律 (Buckingham Π)

**球动力学的相关量**：棒尖驱动幅度 $A$、角频率 $\omega$、重力 $g$、恢复系数 $e$（无量纲）。
$n=4$，量纲只有 $\{L,T\}$（$k=2$）⟹ $n-k=2$ 个无量纲组：

$$\boxed{\ \Pi_1=\Gamma=\frac{A\omega^2}{g}\quad(\text{驱动加速度}/g),\qquad \Pi_2=e\ }\tag{1}$$

- $\Gamma$ = 棒尖峰值加速度 $A\omega^2$ 与 $g$ 之比 —— **决定「能不能弹」和「弹多高」**。
- $e$ = 每次碰撞的能量保留 —— **决定「哪种模式」**。

**认为不相关的量及理由**：球质量 $m$（飞行是自由落体，与 $m$ 无关；碰撞在 $m\ll M_{\rm rod}$ 下也与 $m$ 无关，A-9）；球半径 $R_b$（点质量，A-3，仅经 $e,\tau_c$ 间接进入）；空气（A-8）。

**导出的关键比值 —— 频率比即 $\Gamma$**：飞行时间 $T_{\rm bounce}=2u/g$，稳态 $u\sim A\omega$（§5）⟹
$$\frac{f}{f_{\rm bounce}}=\frac{\omega/2\pi}{g/(2u)}=\frac{\omega u}{\pi g}\;\overset{u=u_{\rm rms}}{=}\;\frac{\Gamma}{\pi}\sqrt{\frac{1+e}{2(1-e)}}.\tag{2}$$
（★ r1 审稿 H6：稳态 $u_{\rm rms}=A\omega\sqrt{(1+e)/2(1-e)}$（由 (7)），故有一个 $O(1)$ 的 $e$ 因子，$e{=}0.6$ 时 $=\sqrt2$。它不改「regime 由 $\Gamma$ 定、边界在 $\Gamma\sim\pi$」这个定性结论，但精确系数带 $e$。）
⟹ **regime 由 $\Gamma$ 自己定**：$\Gamma\lesssim\pi$（近阈值）→ 确定性映射；$\Gamma\gg\pi$（可见弹跳）→ 随机相位。

**数据坍缩预言**（进 `figures[]`）：不同 $(A,\omega)$ 的 $\bar h\cdot g/(A\omega)^2$ 应坍缩成只依赖 $e$ 的一条水平线 $\tfrac14(1+e)/(1-e)$（§5 P2）。

## §4 · 机制预算 (Mechanism Budget)

代入 S-1..S-9 的具体数值。判定：比值 $\lesssim10^{-2}$ 忽略；$10^{-2}$–$10^{-1}$ correction；$\gtrsim10^{-1}$ dominant。

| ID | 机制 | 表达式 / 数值 | 与主项之比 | 去向 |
|---|---|---|---|---|
| M-1 | **磁致伸缩驱动**（棒纵振） | ★ **r1 审稿 H1**：加 DC/剩磁偏置 $H_b$ ⟹ $\lambda\approx\lambda_s(H_b+H_{ac})^2/H_a^2$ 线性化，力**主导 $1f$**（$\propto 2H_bH_{ac}$）+ $2f$ 泛音 ⟹ **驱动在 $f{=}f_1{=}14$ kHz 直接激发基频**（严格无偏置则力纯 $2f$、须驱动 $7$ kHz）。近共振 $A=Q\varepsilon L\cdot\tfrac{8}{\pi^2}$，$Q{\sim}100,\varepsilon{\sim}10^{-6}\Rightarrow A{\sim}8\,\mu$m ⟹ $\Gamma\sim6\times10^3$ | **主项（驱动）** | **Model-0** |
| M-2 | 端面 Maxwell / 磁阻应力 | $\sigma_M=B^2/2\mu_0$ 作用于两端 → 也激发纵振；与 M-1 同频结构、量级可比或更小 | $\sim O(0.1$–$1)\times$ M-1 | correction（Model-1，不改共振结构） |
| M-3 | 铁氧体涡流 | 铁氧体电阻率 $\rho_e\sim10^{2}$–$10^{6}\,\Omega$m ⟹ 趋肤深度 $\gg R_{\rm rod}$，涡流耗散 $\ll$ | $\lesssim10^{-2}$ | 忽略（正是铁氧体替代金属的原因） |
| M-4 | 球受直接磁力（**玻璃球**） | $\mu_r{=}1,\sigma{=}0\Rightarrow F=0$ | $0$ | **由 S-5 排除** |
| M-5 | 飞行空气阻力 | $Re{\approx}40$，$F_{\rm drag}/mg\approx2.5\times10^{-4}$（实算） | $\sim10^{-4}$ | 忽略（A-8） |
| M-6 | **钢球磁吸（confound，已排除）** | $F_{\rm mag}\sim B_{\rm top}^2A_{\rm ball}/2\mu_0$；$B_{\rm top}{=}10$ mT ⟹ $F_{\rm mag}{\approx}0.28$ mN $\approx$ 重力 $0.35$ mN；$B_{\rm top}{=}50$ mT ⟹ **20×重力，把球按住** | $O(1$–$20)\times mg$ | **换玻璃球彻底去掉** |
| M-7 | 声辐射 / 内耗（定 $Q$） | 铁氧体内耗 + 端面辐射 ⟹ $Q\sim50$–$1000$ | — | 进 Model-1（定共振带宽与 $A$） |
| M-8 | 重力（球的回复） | $mg$ | 主项（飞行） | **Model-0** |
| M-9 | 声辐射压 / 近场声悬浮 | 14 kHz 近场，棒尖辐射对球的时均力；粗估 $\ll mg$（远小于碰撞冲量） | $\lesssim10^{-2}$ | 忽略（记为「考虑过」） |

**考虑过但本题不存在/不主导的**：静电（无带电）、热毛细/表面张力（无液）、浮力（$\rho_{\rm air}/\rho_{\rm ball}\sim5\times10^{-4}$）。

**结论**：主驱动 = M-1 磁致伸缩激发的棒纵共振（**A-7**；M-2 端面应力为同结构 correction，比值 ≈0.3）；球的回复 = M-8 重力；耗散 = 碰撞 $e<1$（略去项/主项比：M-3 涡流 $<10^{-2}$、M-5 空气 $\sim2.5\times10^{-4}$、M-9 声辐射 $<10^{-2}$，均 $\lesssim10^{-2}$ 故忽略）。**非磁非导的玻璃球（A-6）把 M-4/M-6 的电磁 confound 清零 —— 这是本题设计的关键。**

## §5 · 分层推导

### Model-0a · 棒的受迫纵共振（玩具模型，闭式）
一维纵波，固定-自由。本征 $f_n=(2n{-}1)c/4L$ $\tag{3}$，模式形状 $\xi(x)=\sin[(2n{-}1)\pi x/2L]$。近共振**单模主导（A-5）**，棒尖（波腹）振幅被 $Q$ 放大：
$$A(f)=A_0\,\frac{1}{\sqrt{(1-(f/f_1)^2)^2+(f/f_1\,Q)^{-2}\cdots}}\ \xrightarrow{f\to f_1}\ A_{\max}\approx Q\,\varepsilon\,L\cdot\tfrac{8}{\pi^2}.\tag{4}$$
一句话本质：**磁致伸缩把每周期一点点应变，经共振 $Q$ 倍累积成 μm 级棒尖位移** —— 而 $A\omega^2$ 即使 $A$ 只有 nm 也 $\gg g$。

### Model-0b · 弹跳的碰撞映射与随机相位稳态（玩具模型，闭式）
向上为正。球以 $v_{\rm in}=-u_n\ (u_n>0)$ 落回，棒尖速度 $w_n$；恢复系数关系（棒 $\gg$ 球质量）：
$$v_{\rm out}=(1+e)\,w_n+e\,u_n,\qquad u_{n+1}=|v_{\rm out}|.\tag{5}$$
飞行保守 ⟹ 下次以 $-u_{n+1}$ 落回。**阈值**：棒尖峰值加速度 $A\omega^2\ge g$ 时球才可能脱离，即
$$\boxed{\ \Gamma=\frac{A\omega^2}{g}=1\quad\text{（起弹阈值，零自由参数）}\ }\tag{6}$$

**高频随机相位稳态（A-2）**：$\phi_n$ 均匀 ⟹ $w_n=A\omega\cos\phi_n$，$\langle w\rangle{=}0,\ \langle w^2\rangle=\tfrac12(A\omega)^2$。对 (5) 取方差、设 $\langle wu\rangle{=}0$：
$$\langle u^2\rangle_{\rm ss}(1-e^2)=(1+e)^2\langle w^2\rangle\ \Rightarrow\ \langle u^2\rangle_{\rm ss}=\frac{1+e}{1-e}\cdot\frac{(A\omega)^2}{2},$$
$$\boxed{\ \bar h=\frac{\langle u^2\rangle_{\rm ss}}{2g}=\frac{1+e}{1-e}\cdot\frac{(A\omega)^2}{4g}\quad\text{（稳态平均弹跳高度，零自由参数）}\ }\tag{7}$$
一句话本质：**能量以「每次碰撞随机相位的净冲量」泵入、以 $e<1$ 耗散，$\bar h$ 在两者平衡处**。$e\to1$ 发散（无耗散无稳态），$e\to0$ 给 $(A\omega)^2/4g$。

**★ 两个 regime（$\Gamma$ 自己划界，(2)）**：
- $\Gamma\gg\pi$（可见 mm 弹跳，$\Gamma\sim10^3$）：随机相位，(7) 成立，弹跳序列是**敏感依赖的随机过程**（Lyapunov $>0$，观测为弹高的统计分布，不是干净周期倍化）。
- $\Gamma\lesssim\pi$（近阈值，$\bar h\sim$ nm **不可见**）：确定性 bouncing-ball 映射 (5) → 周期-1 锁相 → **Feigenbaum 周期倍化（$\delta{=}4.669$）** → 混沌。
- **★★ 独立发现**：**「教科书的周期倍化混沌」恰好落在 nm 级不可见窗口；肉眼看到的持续弹跳是高频随机相位统计稳态。** 这是本题最容易被讲错的一处 —— 把不可见的近阈值映射当成主答案。

### Model-1 · 修正
有限接触时间 $\tau_c\sim1/7$ 驱动周期（A-3）⟹ 有效 $e,w$ 的相位平均修正；$e(u)$ 速度依赖（A-4）；M-2 端面应力的同频叠加；$Q$ 有限带宽 (4)。

### Model-2 · 完整数值（交 Skill 2）
1. **棒**：受迫阻尼波动方程（或集中参数共振子）→ 共振曲线 $A(f)$、$f_n$。
2. **球**：事件驱动仿真 —— 飞行（$\ddot z=-g$）+ 碰撞 (5)，棒尖 $z_{\rm tip}=A\sin\omega t$。扫 $\Gamma$ 与 $e$ ⟹ 弹高分布、$\bar h(\Gamma,e)$、Poincaré、Lyapunov、（低 $\Gamma$）分岔图、regime-map。
3. **极限对拍（Gate 0）**：① $e\to1,\Gamma\ \text{固定}$ ⟹ $\bar h\to\infty$（单调）；② 关掉驱动 $A\to0$ ⟹ 球静止在棒尖（$\bar h\to0$）；③ 单次碰撞、$w$ 固定 ⟹ (5) 解析可验；④ 低 $\Gamma$ 确定性映射的周期-1 不动点解析可验（$u^*=(1+e)/(1-e)\cdot|w|$）。

## §6 · 自洽性检验
1. **量纲**：(1)(6)(7) 逐项齐次 ✓（$\Gamma,e$ 无量纲；$\bar h$ 为长度）。
2. **极限**：$e\to0\Rightarrow\bar h\to(A\omega)^2/4g$（有限）；$e\to1\Rightarrow\bar h\to\infty$（无耗散，物理上对）；$A\to0\Rightarrow\bar h\to0,\Gamma\to0$（不弹）✓。
3. **对称守恒**：无驱动时 $dE/dt<0$（碰撞耗散）✓；驱动注入 = 耗散时达稳态。
4. **数值可信**：$\bar h=(1{+}0.6)/(1{-}0.6)\cdot(0.2)^2/(4\cdot9.81)=4\cdot0.00102=4$ mm —— 与「mm 级可见弹跳」同量级 ✓（不是 μm 也不是 m）。
5. **已知特例**：$\Gamma\lesssim\pi$ 退回标准 bouncing-ball map（Tufillaro/Pieranski 的周期倍化）✓。
6. **反向常识**：「14 kHz 的棒尖只振 μm，却把球抛到 mm 高」—— 因为 $A\omega^2\sim10^3g$，加速度巨大而位移微小，念着不别扭 ✓。

## §7 · 可证伪预测 + 交接

**零自由参数预测（分数所在）**：
- **P1 · 起弹阈值** $\Gamma=A\omega^2/g=1$（棒尖峰值加速度 $=g$）。★ 但可见弹跳需 $\Gamma\gg1$；**P1 的可证伪版**：临界处弹高 $\to0$（nm 级），$\Gamma$ 稍增弹高按 (7) 平方涨。
- **P2 · 稳态弹高** $\bar h=\frac{1+e}{1-e}\frac{(A\omega)^2}{4g}$ —— 给定实测 $A,\omega,e$，**无拟合参数**。可证伪：$\bar h$ vs $(A\omega)^2$ 严格线性、斜率 $=(1+e)/[4g(1-e)]$。
- **P3 · 本征频率** $f_n=(2n{-}1)c/4L$（固定-自由）—— 由 $E,\rho,L$ 零参给出；峰位是 A-1 的退化特征（vs 自由-自由 $nc/2L$，差 2×）。
- **P4 · 数据坍缩**：$\bar h\,g/(A\omega)^2$ 对不同 $(A,\omega)$ 坍缩成只依赖 $e$ 的水平线 $\tfrac14(1+e)/(1-e)$。
- **P5 · regime 边界**：$f/f_{\rm bounce}=\Gamma/\pi$ ⟹ 混沌映射区（$\Gamma\lesssim\pi$，不可见）与随机相位区（$\Gamma\gg\pi$，可见）的边界在 $\Gamma\sim\pi$；低 $\Gamma$ 区若能测（干涉仪）应见 Feigenbaum $\delta=4.669$。

**我什么时候会错**：A-1（BC）错 ⟹ P3 峰位差 2×；A-2（随机相位）在近阈值不成立 ⟹ P2 换成映射分岔；A-4（$e$ 速度依赖）⟹ P2 斜率漂移。

**实验方案**（给人做，仿真不能替代）：
- **测棒尖振幅 $A$（中间量！）**：激光多普勒测振仪 / 迈克尔逊干涉（nm–μm 分辨）—— **不是**拿弹高反推 $A$，而是独立测 $A$ 再代进 (7) 验证。这是「验中间量」的关键。
- **测共振曲线 $A(f)$**：扫 $f$，定 $f_1$ 与 $Q$；比对 P3 的 $c/4L$ vs $c/2L$ 判 BC。
- **测弹高分布**：高速相机（$\ge1$ kHz）测球轨迹 ⟹ $\bar h$、弹高分布、Lyapunov（近阈值需干涉级分辨）。
- **测 $e$**：静态落球测恢复系数，代进 P2。
- **误差来源**：横向move（A-10，用导向套）、$e(u)$（A-4）、棒尖非平顶、温漂 $E(T)$。

**交接**：`handoff/model-spec.json`（Skill 2 唯一输入契约）。

## §9 · 修订记录（r1 审稿 → 修订）

fresh `iypt-physics-review` r1 判 **MAJOR**（报告 `01-review-r1.md`）。球动力学骨架（碰撞映射 eq.5/7、能量平衡 ⟨wu⟩=0、regime 分界、nm 不可见混沌窗口、P17 全清、零参预言）**全部扛住**；MAJOR 来自驱动/共振半边。已修：

- **H1（MAJOR，驱动频率记账）**：无偏置磁致伸缩力纯在 $2\omega$，要激发 $f_1$ 须驱动 $f_1/2{=}7$ kHz，且 $2f{=}28$ kHz 撞自由-自由模。**修：加 DC/剩磁偏置 ⟹ 力主导 $1f$，驱动在 $f{=}f_1{=}14$ kHz 直接激发**（S-7、M-1、A-7）。这正是参考报告用剩磁偏置（$1f{+}2f$）避开的坑 —— 独立分析漏了偏置这一步。
- **H4（设定书 $f_1$ 自相矛盾）**：S-2 曾写 $c/2L{=}28$ kHz，与 S-3/A-1 的 $c/4L{=}14$ kHz 冲突。**修：统一到 $c/4L{=}14$ kHz（固定-自由）**。
- **H6（eq.2 丢 $e$ 因子）**：$f/f_{\rm bounce}=\dfrac{\Gamma}{\pi}\sqrt{\dfrac{1+e}{2(1-e)}}$，补回 $O(1)$ 的 $e$ 因子。
- **H2（交接契约缺席）**：`handoff/model-spec.json` + `01-criteria/criterion_matrix.py`（判据×模型双向表，5 错模型全抓、4 判据全不瞎、robustness margin 1.47、$\varepsilon^*$）**已补齐**，`check_analysis` 零 ERROR。归档 `model-spec-r1.json`。
- **H3/H5/H7（MINOR）**：M-2 端面应力比实算 ≈0.3（已入 A-7/§4）；A-3 接触时间 $\tau_c/T\approx0.16$–$0.20$ 对 eq.7 斜率的 ~20% 影响、M-9 声辐射高驱动端 $\sim1.2\times10^{-2}$ —— 记为 Model-1 的量化项（本轮未逐一收口）。
- **UNCLEAR**：BC（固定-自由 vs 自由-自由）与偏置强度，都要一张**实测共振谱**才能定 —— 正是 V-1/T-3 与 A-1 双向表要验的。

> **r2 复审未跑**（本轮到此）。这一次已完整演示了流水线核心回路：**独立推导 → fresh 对抗审稿抓出真 bug（H1）→ 按洞修订 + 归档**。而 H1 恰好印证了 `02-correspond.md`：真实团队靠偏置避开的那一步，无上下文的独立分析确实会漏 —— 审稿把它逼了出来。

## §8 · 文献
- 弹跳球映射与周期倍化：Tufillaro, Abbott & Reilly, *An Experimental Approach to Nonlinear Dynamics and Chaos* (1992)；Pieranski, *J. Physique* 44 (1983) 573.
- 高频振动下颗粒的随机相位/统计稳态：Kanellopoulos & Kroy 等振动床文献（定性，标度自行推导）。
- 磁致伸缩换能器：Engdahl (ed.), *Handbook of Giant Magnetostrictive Materials* (2000)。
> **文献给思路与参数；(6)(7) 的闭式为自推**（P15：严格区分）。
