# Fractal Fingers — 物理分析

> **状态**：DRAFT（待 Stage 8 对抗式审稿）
> **题型**：依赖关系探究型 (dependence)，含机制识别与模式分类内核

---

## 0 · 摘要

一滴低黏、低表面张力的**醇-墨**滴在高黏的**稀释丙烯漆**膜上铺展。醇降低自由面表面张力，形成的 **Marangoni 反差 $\Delta\gamma$ 驱动铺展**，给出前沿速度 $U$。这个「低黏驱替高黏」的推进界面是 **Saffman–Taylor 不稳定**的：界面上任何凸起都把 Darcy 压强梯度聚到尖端（Laplacian 场，如避雷针），尖端跑得更快、凸起长大；**界面张力 $\gamma$ 惩罚短波曲率**，于是有一个**最快增长波长 $\lambda^\ast$** 被选出——它设定指宽。反复的 **tip-splitting** 把这些指长成**自相似的分形**；醇**蒸发**抹平 $\Delta\gamma$、关闭驱动，花样冻结。

**核心结论**：
$$\lambda^\ast = \pi h\sqrt{\dfrac{\gamma}{U(\mu_2-\mu_1)}}\;=\;\pi h\,\big[\mathrm{Ca}\,(1-r)\big]^{-1/2},\qquad \mathrm{Ca}=\dfrac{\mu_2 U}{\gamma},\; r=\dfrac{\mu_1}{\mu_2}$$

即 **$\lambda^\ast/h \propto \mathrm{Ca}^{-1/2}$**。**零自由参数的是「指数 $-1/2$」这一件事**（P1）；**绝对值 $\lambda^\ast$ 不是零参**——它含 $\gamma$，而 $\gamma$ 无表值、需实测（±30%，A-2/S-3），故绝对值是一参预言（P2，H3 订正）。

> **★★ 控制参数不独立（r1 审稿 H1，MAJOR，已订正）**：$U$ 不是自由量，由 Marangoni 定（式 13）$U=\Delta\gamma h/(\mu_2 R)$。代进 $\mathrm{Ca}=\mu_2 U/\gamma$，**$\mu_2$ 精确抵消**：
> $$\boxed{\;\mathrm{Ca}=\dfrac{\Delta\gamma\,h}{R\,\gamma}\;}\qquad(\mu_2\ \text{不进 Ca}).$$
> **⟹ 稀释漆（$\mu_2$，题面唯一明给的旋钮）在固定驱动下根本不移动 Ca、也几乎不改 $\lambda^\ast$。** 真正的 Ca 旋钮是 $\Delta\gamma$（经醇分数 $\varphi$）与 $\gamma$。稀释的**正确**预言是「**固定 Marangoni 驱动下 $\lambda^\ast\approx\pi\sqrt{h\gamma R/\Delta\gamma}$、与 $\mu_2$ 近乎无关**」——它改变的是**失稳存在与否**（$\mu_2>\mu_1$）与**时标**，不是指宽。旗舰指数 $-1/2$ 不受影响（经 $\Delta\gamma$ 扫仍可证伪）。详见 §6.2、§8、§11。

最软的软肋是 **A-2**（醇与水互溶 ⇒ 界面张力 $\gamma$ 是否真的存在、是否足以选出 $\lambda^\ast$）与 **A-3**（丙烯漆剪切变稀）。分形维数 $D\approx1.71$ 是 **DLA 普适类的文献结论**（不是本模型的推导，见 §10）。

---

## 0.5 · 题目任务（挖出来的）

完整挖掘见 `00-problem.md` 的 Stage 0.5。摘要：

| id | 任务 | kind | 从题面哪个词 |
|---|---|---|---|
| T-1 | 指出物理本质（哪种失稳） | essence | "fractal fingering" |
| T-2 | 几何：$\lambda^\ast$、$N$、tip-splitting、分形维数 $D$ | mode-classification | "fractal" / "geometry" |
| T-3 | 几何与动力学如何依赖参数（标度律 + 坍缩） | dependence | "influenced by relevant parameters" |
| T-4 | 动力学：前沿推进、增长、蒸发冻结 | dependence | "dynamics" |
| T-5 | 条件边界（形态相图） | regime-boundary | "can be observed if" / "diluted" |

## 0.6 · 物理本质（一句话）

> 低表面张力的醇-墨滴在高黏漆膜上以 **Marangoni 应力驱动铺展**，低黏流体驱替高黏流体的推进界面在 **Laplacian 增长**下失稳、由**界面张力选出最快波长 $\lambda^\ast$** 并反复 **tip-splitting**，在驱动与界面张力**竞争**中长出**自相似的分形指**；醇的**蒸发**使驱动关闭、花样冻结。

- **系统类型**：界面失稳与花样形成（Laplacian growth / viscous fingering），经 tip-splitting 级联到分形。
- **能量链**：自由面表面能（醇造成的 $\Delta\gamma$）→ 前沿推进的黏性耗散 + 新增界面能；蒸发抹平 $\Delta\gamma$ → 驱动 $\to0$ → 冻结。
- **竞争的效应**：驱动 Marangoni $\Delta\gamma$（设定 $U$） vs 稳定 界面张力 $\gamma$（惩罚短波），比值 $\mathrm{Ca}=\mu_2 U/\gamma$ 选出 $\lambda^\ast$；黏度比 $r=\mu_1/\mu_2$ 决定失稳强度。

> 这句话决定图的骨架：失稳/花样 ⇒ 色散关系 $\sigma(k)$（F-1）+ 形态相图（F-3）；分形 ⇒ 维数 $D$（F-4/F-6）；选出最快波长 ⇒ $\lambda^\ast$ 坍缩（F-2）。

---

## 1 · 符号表

| 符号 | 含义 | 单位 |
|---|---|---|
| $h$ | 漆膜厚度（Hele-Shaw 有效间隙） | m |
| $\mu_1$ | 醇-墨（入侵相）动力黏度 | Pa·s |
| $\mu_2$ | 稀释丙烯漆（防守相）动力黏度 | Pa·s |
| $r$ | 黏度比 $\mu_1/\mu_2$ | 1 |
| $\gamma$ | 醇墨/漆之间的**界面张力**（稳定短波的那个） | N/m |
| $\Delta\gamma$ | 自由面**表面张力反差**（Marangoni 驱动，与 $\gamma$ 是两个量） | N/m |
| $U$ | 铺展前沿速度 | m/s |
| $R$ | 液滴（图样）半径 | m |
| $k$ | 界面扰动波数 | 1/m |
| $\sigma$ | 扰动的线性增长率（**非电导率**：本题无电磁量） | 1/s |
| $\eta$ | 界面扰动位移（$\eta=\xi\,e^{iky}$，§6.1） | m |
| $\xi$ | 扰动幅度（时间函数 $\xi(t)$，§6.1） | m |
| $\Gamma$ | 界面曲线（Model-2 状态变量，§6.3） | m |
| $\lambda^\ast$ | 最快增长波长 = 指宽 | m |
| $k^\ast$ | 最快增长波数 | 1/m |
| $\lambda_c$ | 临界波长（$\sigma=0$） | m |
| $k_c$ | 临界波数 | 1/m |
| $N$ | 指的条数 | 1 |
| $\mathrm{Ca}$ | 毛细数 $\mu_2 U/\gamma$ | 1 |
| $\mathrm{Pe}$ | Péclet 数 $UR/D_a$ | 1 |
| $\mathrm{Re}$ | Reynolds 数 $\rho U h/\mu_2$ | 1 |
| $\mathrm{Bo}$ | Bond 数 $\rho g h^2/\gamma$ | 1 |
| $D$ | 分形维数 | 1 |
| $D_a$ | 醇在水中的分子扩散系数 | m²/s |
| $\varphi$ | 醇质量分数 | 1 |
| $\rho$ | 液体密度（水基） | kg/m³ |
| $g$ | 重力加速度 | m/s² |
| $p$ | 深度平均压强 | Pa |
| $u$ | 深度平均流速 | m/s |
| $t$ | 时间 | s |
| $t_g$ | 指增长特征时间 $1/\sigma(k^\ast)$ | s |
| $t_s$ | 铺展特征时间 $R/U$ | s |
| $t_{ev}$ | 醇蒸发特征时间 | s |
| $J$ | 醇蒸发质量通量 | kg/(m²·s) |
| $\dot\gamma_c$ | 丙烯漆剪切变稀起始剪切率（**注意**：带点和下标，与界面张力 $\gamma$ 区分） | 1/s |
| $\kappa$ | 界面**全曲率**（Young–Laplace 压跳，§6.3） | 1/m |
| $k_{\rm th}$ | 液体导热系数（A-7 蒸发冷却估计用；**非曲率 $\kappa$、非波数 $k$**） | W/(m·K) |
| $L_v$ | 醇的汽化潜热（A-7） | J/kg |
| $\Pi_1,\Pi_2,\Pi_3$ | 无量纲组 | 1 |

> 一符多义警戒（P13）：$\gamma$（界面张力）vs $\Delta\gamma$（自由面反差，Marangoni）vs $\dot\gamma_c$（剪切率）—— **三个不同的量，刻意用不同修饰区分**。$\sigma$ 在本题是**增长率**，不是电导率（本题无电磁量）。

---

## 2 · 设定书

见 `00-problem.md` 的 Stage 1（S-1 … S-8）与参数扫描范围。设定不在此重复。

---

## 3 · 假设台账 (Assumption Ledger)

每条写全：陈述 / 成立判据（不等式）/ 代入检查 / 失效边界 / 分级 / 若不成立。

### A-1 · 薄膜 Hele-Shaw（Darcy）近似：深度平均流服从达西定律
- **成立判据**：$h \ll \lambda^\ast$ 且 $h \ll R$（面内尺度 ≫ 膜厚，润滑近似成立）
- **代入检查**：$h=0.30$ mm，$\lambda^\ast=2.12$ mm ⇒ $h/\lambda^\ast=0.14$；$h/R=0.10$。两者都 $\approx0.1$——**勉强成立**
- **失效边界**（H2 订正）：$h/\lambda^\ast=0.14$ **与 $h$ 无关**（$\lambda^\ast\propto h$ ⇒ 该比是 $\tfrac1\pi\sqrt{U(\mu_2-\mu_1)/\gamma}$，纹丝不动，扫 $h$ 不经它逼出边界）。真正随 $h$ 长大的是 **$h/R$**：$h=1.0$ mm ⇒ $h/R\to0.33$。大 $h$ 端是 $h\ll R$ 先破，三维流动与竖直方向的压强分布不可再忽略
- **分级**：`LOAD-BEARING`
- **若不成立**：Darcy 定律 (1) 的前因子 $h^2/12$ 失真（自由面还要改成 $h^2/3$，见 (14)），$\lambda^\ast$ 的**绝对值**偏移，但**指数 $-1/2$ 不变**（它来自 $\sigma(k)$ 中 $k$ 与 $k^3$ 的竞争，与前因子无关）。A-1 因此影响 P2（绝对值）不影响 P1（指数）。

### A-2 · 存在锐利、可定义界面张力 $\gamma$ 的两相界面
- **成立判据**：$\mathrm{Pe}=UR/D_a \gg 1$（对流保持前沿锐利，抵抗扩散抹平）**且** 有效界面张力 $\gamma>0$ 足以选出 $\lambda^\ast>$ 观测分辨率
- **代入检查**：$\mathrm{Pe}=10^{-2}\times3\times10^{-3}/10^{-9}=3\times10^{4}\gg1$——**动力学上前沿锐利没问题**。但**醇与水完全互溶**：热力学上醇墨/漆之间未必有真正的界面张力，$\gamma$ 可能只是聚合物分散体给出的一个**很小的有效值**（甚至 Korteweg 应力）。**$\gamma$ 无表值、极不确定**——判据的第二半**无法确认**
- **失效边界**：若两相充分互溶且聚合物不提供有效张力 ⇒ $\gamma_{\rm eff}\to0$ ⇒ (9) 给出 $\lambda^\ast\to0$（无短波截断）
- **分级**：`RISKY`
- **若不成立**：**没有被选出的 $\lambda^\ast$**——不存在特征指宽，图样退化为**无波长选择的纯 Laplacian/DLA 分形**，一直分叉到最小可分辨尺度。P1/P2/P3 全部失去对象；只剩 P6（分形维数）仍有意义。**这是全题最要命的一条**——它决定「有没有指宽」这件事本身。
- **验证任务**：→ `risky_assumption_checks[A-2]`（degenerate signature：色散谱里**有没有一个峰**）

### A-3 · 稀释丙烯漆是牛顿流体
- **成立判据**：前沿处剪切率 $\dot\gamma \sim U/h \ll \dot\gamma_c$（剪切变稀起始剪切率）
- **代入检查**：$U/h = 10^{-2}/3\times10^{-4}=33\ \mathrm{s^{-1}}$，而丙烯漆 $\dot\gamma_c\sim5\ \mathrm{s^{-1}}$ ⇒ 比值 $\approx6.7>1$——**判据不满足，剪切变稀已被激活**
- **失效边界**：$U$ 增大（扫描上端 $U=50$ mm/s ⇒ $\dot\gamma=167\ \mathrm{s^{-1}}$）时更严重
- **分级**：`RISKY`
- **若不成立**：指尖（高剪切）处有效黏度低于指身，Darcy 迁移率变成非线性，$\mathrm{Ca}$ 不再是唯一控制组 ⇒ **多参数数据不再坍缩到单条 $\lambda^\ast/h=f(\mathrm{Ca})$ 曲线**。指数 $-1/2$ 会漂移。这直接威胁 P1/P3。
- **验证任务**：→ `risky_assumption_checks[A-3]`（degenerate signature：坍缩**成/不成**——结构性的是/否）

### A-4 · 指增长期间前沿速度 $U$ 准定常
- **成立判据**：$t_g = 1/\sigma(k^\ast) \ll t_s = R/U$（且 $\ll t_{ev}$）
- **代入检查**：$\sigma(k^\ast)\approx19\ \mathrm{s^{-1}}$ ⇒ $t_g\approx0.05$ s；$t_s=R/U=0.30$ s；$t_{ev}\sim10^2$ s。$t_g/t_s\approx0.17$——**成立**（增长比铺展与蒸发都快）
- **失效边界**：接近蒸发末期 $U\to0$ 时，$\lambda^\ast\propto U^{-1/2}\to\infty$，指变粗、停止分叉
- **分级**：`LOAD-BEARING`
- **若不成立**：$\lambda^\ast$ 变成 $U(t)$ 的函数，$N(t)$ 随时间演化（正是 F-5 要展示的动力学）；坍缩要用**瞬时** $U$ 而非平均 $U$，否则散开。

### A-5 · 忽略重力对**面内**失稳的影响
- **成立判据**：基底水平 ⇒ 重力垂直于流动，不进入面内色散；跨膜静水头 $\mathrm{Bo}=\rho g h^2/\gamma \ll 1$ 只影响膜形
- **代入检查**：面内重力分量 $=0$（水平）。$\mathrm{Bo}=10^3\times9.81\times(3\times10^{-4})^2/5\times10^{-3}=0.18$——膜形上重力是表面张力的 18%，但**它不驱动也不抑制面内指**
- **失效边界**：基底倾斜（引入面内重力 ⇒ 密度差驱动的指）；或 $h$ 扫到 1 mm 时 $\mathrm{Bo}\approx2$，膜不再由表面张力定形
- **分级**：`SAFE`（对指宽 $\lambda^\ast$ 的选择而言）

### A-6 · 忽略惯性（蠕动流，$\mathrm{Re}\ll1$）
- **成立判据**：$\mathrm{Re}=\rho U h/\mu_2 \ll 1$
- **代入检查**：$\mathrm{Re}=10^3\times10^{-2}\times3\times10^{-4}/0.1=0.03\ll1$——**宽裕成立**
- **失效边界**：见 §5 扫描端点——高 $U$、低 $\mu_2$ 角落（$U=50$ mm/s，$\mu_2=0.02$）$\mathrm{Re}\to0.75$，蠕动流近似变弱
- **分级**：`SAFE`（基准点），但见 §5 的端点检查

### A-7 · 等温：忽略蒸发冷却驱动的热 Marangoni
- **成立判据**：热 Marangoni 反差 $\ll$ 溶质 Marangoni 反差 $\Delta\gamma$
- **代入检查**：蒸发冷却 $\Delta T\sim J L_v h/k_{\rm th} \approx 3\times10^{-4}\times8.4\times10^{5}\times3\times10^{-4}/0.6\approx0.13$ K；热反差 $|\partial\gamma/\partial T|\Delta T\approx1.5\times10^{-4}\times0.13\approx2\times10^{-5}$ N/m，占 $\Delta\gamma=2.5\times10^{-2}$ 的 $8\times10^{-4}$——**可忽略**
- **失效边界**：强制风冷或高挥发性溶剂使 $\Delta T$ 大时
- **分级**：`SAFE`

### A-8 · 界面张力选择机制是 Saffman–Taylor（黏度反差），Marangoni 只负责设定 $U$
- **成立判据**：Saffman–Taylor 失稳增长率 $\gg$ Marangoni（表面张力梯度）失稳增长率，即驱动主要经「黏度反差 + $U$」而非独立的表面张力梯度失稳
- **代入检查**：界面处黏性压强变动 $\mu_2 U\lambda^\ast/h^2\approx23$ Pa（面内 Darcy），远大于沿前沿方向残余 $\Delta\gamma$ 梯度在指尺度上的变动（$\Delta\gamma$ 主要沿铺展方向、在 $R$ 尺度上耗尽）——**量级上支持**，但 Marangoni 铺展本身也能独立失稳（surfactant fingering），**无法完全排除**
- **失效边界**：极低黏度反差（$r\to1$）时 Saffman–Taylor 关闭，若仍见指 ⇒ 那是 Marangoni 指
- **分级**：`RISKY`
- **若不成立**：$\lambda^\ast$ 的标度不再是 $\mathrm{Ca}^{-1/2}$，而由 Marangoni 铺展的标度定；且在 $r\to1$ 时**指不消失**（Saffman–Taylor 预言消失）
- **验证任务**：→ `risky_assumption_checks[A-8]`（degenerate signature：把 $\mu_1\to\mu_2$，指**消失**（ST）还是**保留**（Marangoni））

---

## 4 · 量纲分析与标度律 (Buckingham Π)

**相关物理量**（对指宽选择）：$\lambda^\ast, h, \mu_1, \mu_2, U, \gamma$。
**明确认为不相关的量及理由**（防漏项的唯一防线）：
- $\rho$（密度）：$\mathrm{Re}\ll1$，惯性不进入 ⇒ $\rho$ 不相关（§5 证）；
- $g$（重力）：水平基底，面内不进入（A-5）；
- $R$（液滴半径）：进入**条数** $N$（=周长/指宽），不进入**局域指宽** $\lambda^\ast$；
- $\Delta\gamma$（Marangoni）：经 $U$ 进入，不再独立（A-8）；
- 时间/蒸发：设定过程**寿命**，不进入瞬时的 $\lambda^\ast$。

**数**：$n=6$ 个量（$\lambda^\ast,h,\mu_1,\mu_2,U,\gamma$），量纲 M、L、T（$k=3$）⇒ **$n-k=3$ 个无量纲组**。

| 组 | 表达式 | 物理意义 | 基准值 |
|---|---|---|---|
| $\Pi_1$ | $\lambda^\ast/h$ | 无量纲指宽 | 7.08 |
| $\Pi_2=\mathrm{Ca}$ | $\mu_2 U/\gamma$ | 黏性驱动 / 界面张力 | 0.20 |
| $\Pi_3=r$ | $\mu_1/\mu_2$ | 黏度比（失稳强度） | 0.015 |

**预期标度律**：$\Pi_1 = f(\Pi_2,\Pi_3)$。Model-0（§6）给出闭式 $f=\pi\,[\Pi_2(1-\Pi_3)]^{-1/2}$，即
$$\dfrac{\lambda^\ast}{h}=\pi\,\big[\mathrm{Ca}(1-r)\big]^{-1/2}\;\xrightarrow{r\ll1}\;\pi\,\mathrm{Ca}^{-1/2}.\tag{对应 (9)}$$

**数据坍缩预言**：把实测指宽画成 $\lambda^\ast/h$ vs $\mathrm{Ca}$，**应坍缩到斜率 $-1/2$ 的直线**（log-log，→ F-2）。

> ★★ **杠杆点必须老实标（r1 审稿 H1）**：$\mathrm{Ca}=\mu_2 U/\gamma$ 在 Marangoni 耦合（式 13）下 $=\Delta\gamma h/(R\gamma)$。**能沿 Ca 挪动的干净旋钮只有 $\Delta\gamma$（经醇分数 $\varphi$）与 $\gamma$**——$\mu_2$ **相消**（扫稀释把你钉在坍缩图同一点）、$h$ 在 $\lambda^\ast/h$-vs-Ca 图上**天然退化**（Ca 里没有 $h$）。而且 **Model-0 输出的坍缩是代数恒等式（恒真、不构成检验）**——任取 $(U,\mu_2,\gamma,h)$ 都精确落线。**真正的检验是实验：扫 $\Delta\gamma(\varphi)$ 沿 Ca 挪、看真实系统的斜率是不是 $-1/2$。** 若实验不坍缩或斜率不对，多半是 A-3（剪切变稀，$\mathrm{Ca}$ 不再唯一控制）或 A-2（无 $\gamma$）破了。

> 技巧 3（零自由参数）：$\mathrm{Ca}^{-1/2}$ 里的 **指数 $-1/2$** 不含任何可调参数——测得斜率是 $-0.5$ 还是 $-1$、$0$，直接判 Model-0 的生死（见 P1、criterion K1）。

---

## 5 · 机制预算 (Mechanism Budget)

**硬规则：每一个「忽略」都必须有数字。** 代入基准值（$h=0.3$ mm，$\mu_2=0.1$ Pa·s，$\mu_1=1.5\times10^{-3}$ Pa·s，$U=10^{-2}$ m/s，$\gamma=5\times10^{-3}$ N/m，$R=3$ mm，$\rho=10^3$ kg/m³）。主项取面内黏性压强变动 $\Delta p_{\rm visc}=\mu_2 U\lambda^\ast/h^2\approx23$ Pa。

| 机制 | 表达式 | 代入数值 | 量级 | 与主项之比 | 去向 |
|---|---|---|---|---|---|
| 面内黏性（Darcy） | $\mu_2 U\lambda^\ast/h^2$ | $0.1\cdot0.01\cdot2.1\!\times\!10^{-3}/9\!\times\!10^{-8}$ | $23$ Pa | 1（主项） | **Model-0** |
| 界面张力（选短波） | $\gamma k^{\ast2}h^2/12$ 在 $k^\ast$ | $=U(\mu_2-\mu_1)/3$ | 同量级 | $1/3$ 于驱动 | **Model-0** |
| Marangoni 驱动 | $\Delta\gamma/R$ | $0.025/3\!\times\!10^{-3}$ | $8.3$ Pa | 设定 $U$ | **Model-0（经 $U$）** |
| 重力（跨膜静水头） | $\rho g h$ | $10^3\cdot9.81\cdot3\!\times\!10^{-4}$ | $2.9$ Pa | $0.13$ | 忽略（面内为 0，A-5） |
| 惯性 | $\rho U^2$ | $10^3\cdot(10^{-2})^2$ | $0.1$ Pa | $4\times10^{-3}$ | 忽略（$\mathrm{Re}=0.03$，A-6） |
| 醇扩散（抹平前沿） | $\propto1/\mathrm{Pe}$ | $\mathrm{Pe}=3\times10^{4}$ | — | $3\times10^{-5}$ | 忽略（前沿锐利，A-2） |
| 热 Marangoni | $|\partial_T\gamma|\Delta T$ | $1.5\!\times\!10^{-4}\cdot0.13$ | $2\times10^{-5}$ N/m | $8\times10^{-4}$ | 忽略（A-7） |

**未纳入的机制及理由**（空着不写就是漏项）：
- **蒸发**：不进入瞬时 $\lambda^\ast$，但设定过程**寿命**与最终代数（→ F-5、T-4），单列在动力学里；
- **剪切变稀**（非牛顿）：**不是可忽略项，而是一条 RISKY 假设**（A-3）——基准点就已激活（$\dot\gamma/\dot\gamma_c\approx6.7$）；
- **静电/磁/相变/传导对流**：本题不存在这些机制。

### 扫描端点检查（一端可忽略 ≠ 另一端可忽略）

| 被忽略项 | 比值随参数 | 扫描下端 | 扫描上端 | 全程可忽略？ |
|---|---|---|---|---|
| 惯性 $\mathrm{Re}=\rho U h/\mu_2$ | $\propto U/\mu_2$ | $0.006$（$U$=2 mm/s） | $0.75$（$U$=50 mm/s，$\mu_2$=0.02） | **否**——高 $U$/低 $\mu_2$ 角落 $\mathrm{Re}\to0.75$，蠕动流近似变弱，Model-0 在该角落失效 |
| 重力 $\mathrm{Bo}=\rho g h^2/\gamma$ | $\propto h^2$ | $0.02$（$h$=0.1 mm） | $2.0$（$h$=1 mm） | **否**——厚膜端 $\mathrm{Bo}\approx2$，膜形不再由表面张力定；但仍不驱动面内指 |
| 醇扩散 $1/\mathrm{Pe}$ | $\propto1/(UR)$ | $3\times10^{-5}$ | $1.7\times10^{-4}$（$U$=2 mm/s） | ✓（全程前沿锐利） |

> 两条「否」都指向**扫描角落**：高 $U$/低 $\mu_2$ 处惯性抬头、厚膜端重力抬头。正文与 F-2/F-3 必须把这两个角落标为 Model-0 的适用边界，不能把那里的偏差当成模型错。

---

## 6 · 分层推导

### 6.1 Model-0：玩具模型（Saffman–Taylor 线性稳定性，闭式）

**几何**：把薄漆膜当有效间隙 $h$ 的 Hele-Shaw 盒。深度平均流服从达西定律
$$\mathbf u_j = -\dfrac{h^2}{12\mu_j}\nabla p_j,\qquad j=1(\text{醇墨}),\,2(\text{漆}).\tag{1}$$
不可压 $\nabla\!\cdot\!\mathbf u=0$ ⇒
$$\nabla^2 p_j = 0.\tag{2}$$
**基态**：平直界面沿 $x$ 以 $U$ 推进，入侵相 1 在 $x<Ut$、防守相 2 在 $x>Ut$。均匀流 ⇒
$$\dfrac{\mathrm dp_j^0}{\mathrm dx}=-\dfrac{12\mu_j U}{h^2}.\tag{3}$$
**扰动**：界面 $x=Ut+\eta$，$\eta=\xi(t)\,e^{iky}$。满足 (2) 且在各相远处有界的压强扰动为
$$p_1'=A\,e^{+kx}e^{iky},\qquad p_2'=C\,e^{-kx}e^{iky}\quad(k>0).\tag{4}$$
**运动学条件**（界面是物质面，法向速度连续、等于界面速度，基态均匀 ⇒ 无对流修正项）：在 $x\!\approx\!0$，
$$\dot\eta = u_{x,1}' = -\dfrac{h^2}{12\mu_1}\partial_x p_1' = -\dfrac{h^2 k}{12\mu_1}A,\qquad
\dot\eta = u_{x,2}' = +\dfrac{h^2 k}{12\mu_2}C.\tag{5}$$
以 $\dot\eta=\sigma\xi$ 代入 (5) 解出 $A=-\dfrac{12\mu_1\sigma\xi}{h^2k}$、$C=\dfrac{12\mu_2\sigma\xi}{h^2k}$。
**动力学条件**（Young–Laplace，界面张力惩罚面内曲率，扰动曲率 $\approx k^2\eta$）：
$$p_1-p_2\big|_{\rm int}=\gamma k^2\eta.\tag{6}$$
界面处 $p_j=p_j^0(\eta)+p_j'=p_j^0(0)-\dfrac{12\mu_j U}{h^2}\eta+p_j'(0)$。代入 (6)，消去基态常数（平均曲率给的常数压差不影响扰动）：
$$-\dfrac{12U}{h^2}(\mu_1-\mu_2)\xi + (A-C)=\gamma k^2\xi.$$
代入 $A,C$ 并除以 $\xi$：$-\dfrac{12U(\mu_1-\mu_2)}{h^2}-\dfrac{12\sigma(\mu_1+\mu_2)}{h^2k}=\gamma k^2$。解出增长率：
$$\boxed{\;\sigma(k)=\dfrac{k}{\mu_1+\mu_2}\left[U(\mu_2-\mu_1)-\dfrac{\gamma h^2}{12}k^2\right]\;}\tag{7}$$

（量纲核对：$U(\mu_2-\mu_1)$ 与 $\gamma h^2 k^2/12$ 同为 N/m；$k\cdot(\text{N/m})/(\text{Pa·s})=1/\text{s}$ ✓。与文献 Saffman–Taylor 1958 / Homsy 1987 的色散关系在 $\mu_1\!\ll\!\mu_2$ 极限一致：$\sigma\to Uk-\gamma h^2 k^3/(12\mu_2)$，见 §10。）

**失稳条件**：小 $k$ 处 $\sigma>0$ 要求 $\mu_2>\mu_1$（**低黏驱替高黏**）。这是 Saffman–Taylor 的本质，也是 criterion K3。
**最快增长模** $\mathrm d\sigma/\mathrm dk=0$：
$$k^\ast=2\sqrt{\dfrac{U(\mu_2-\mu_1)}{\gamma h^2}},\qquad
\lambda^\ast=\dfrac{2\pi}{k^\ast}=\pi h\sqrt{\dfrac{\gamma}{U(\mu_2-\mu_1)}}.\tag{8,9}$$
**临界模**（$\sigma=0$，稳定与不稳定的分界）：
$$k_c=\sqrt{3}\,k^\ast,\qquad \lambda_c=\dfrac{\lambda^\ast}{\sqrt3}.\tag{10}$$
**条数**（半径 $R$ 的圆前沿，周长 $/$ 指宽）：
$$N=\dfrac{2\pi R}{\lambda^\ast}=\dfrac{2R}{h}\sqrt{\dfrac{U(\mu_2-\mu_1)}{\gamma}}=\dfrac{2R}{h}\sqrt{\mathrm{Ca}(1-r)},\qquad \mathrm{Ca}=\dfrac{\mu_2U}{\gamma}.\tag{11,12}$$

**这个模型的物理图像（一句话）**：低黏推高黏时，界面上任何凸起把 Darcy 压强梯度聚到尖端（Laplacian 场，如避雷针），尖端跑得更快、凸起长大；界面张力对**最尖（最短波）**的凸起惩罚最狠（$\propto k^3$），于是**中间**有一个 $\lambda^\ast$ 长得最快——它就是指宽。$k^\ast$ 处驱动与界面张力之比恰为 $3:1$（见 §5）。

**代入基准值**：$\lambda^\ast=2.12$ mm，$k^\ast=2959\ \mathrm{m^{-1}}$，$N\approx8.9$（$\approx9$ 条指），$\mathrm{Ca}=0.20$，$\sigma(k^\ast)\approx19\ \mathrm{s^{-1}}$（$t_g\approx0.05$ s）。**约 9 条指、指宽约 2 mm**——量级与「一滴墨在漆上炸开成十来根手指」的日常观察一致（§7 反向常识）。

### 6.2 Model-1：修正（有限黏度比、自由面、径向）

1. **有限黏度比**：(9) 已保留 $\mu_2-\mu_1$ 与 $\mu_1+\mu_2$，$r=0.015$ 使修正 $<1\%$——本题 $r\ll1$，修正可略。
2. **自由面迁移率**：漆膜上表面是自由面（非 Hele-Shaw 双无滑移壁），深度平均迁移率应为 $h^2/3\mu$ 而非 $h^2/12\mu$（一处无滑移 + 一处零切应力）。这把 (1) 的前因子改 4 倍 ⇒ $\lambda^\ast$ **绝对值** $\times\sqrt{12/3}=2$，**指数不变**。本文以 Hele-Shaw 的 $h^2/12$ 为参照写 (7)–(11)，把自由面修正记为 LOAD-BEARING（A-1）：它只搬动 P2 的绝对值，不动 P1 的指数。
3. **径向增长**：液滴是圆的、$R(t)$ 在长大。局域指宽仍由 (9) 定；但每根指变得太宽（宽度 $>\lambda^\ast$）时会 **tip-split**，使 $N(t)$ 随 $R$ 增长 $N(t)\approx2\pi R(t)/\lambda^\ast$——这就是 tip-splitting 级联，是分形长出来的机制。
4. **Marangoni 设定 $U$**：铺展前沿速度由 Marangoni 应力与黏性阻力平衡估出
$$U\sim\dfrac{\Delta\gamma\,h}{\mu_2 R}\quad(\text{量级})\;\Rightarrow\;\dfrac{0.025\times3\times10^{-4}}{0.1\times3\times10^{-3}}=2.5\times10^{-2}\ \mathrm{m/s},\tag{13}$$
与设定的 $U=10^{-2}$ m/s 同量级（$\Delta\gamma$、$h/R$ 的量级不确定度足以覆盖 2.5 倍差异）。**$U$ 由 Marangoni 定、可实测，不是自由拟合量。**

> ★★ **这条关系锁死了控制参数的独立性（r1 审稿 H1，MAJOR，本轮订正的头号洞）。** 把 (13) 代进 $\mathrm{Ca}=\mu_2 U/\gamma$，**$\mu_2$ 精确抵消**：$\mathrm{Ca}=\Delta\gamma h/(R\gamma)$。三条连带后果：
> 1. **$\mu_2$（稀释）不进 Ca**：固定驱动下扫 $\mu_2$ 不移动 Ca，$\lambda^\ast$ 只因 $(1-r)$ 项变几个百分点（$\mu_2$ 扫 25× ⟹ $\lambda^\ast$ 变 3.7%）。**故参数表原先「扫 $\mu_2$ 让 Ca 跨量级」是错的。**
> 2. **单变量指数被 $U$-耦合污染**：把 (13) 代进 (9)，$r\ll1$ ⟹ $\lambda^\ast\approx\pi\sqrt{h\gamma R/\Delta\gamma}$。于是**自然耦合下** $\lambda^\ast\propto h^{1/2}$（不是 (9) 表面的 $h^{1}$）、$\propto R^{1/2}$，$N=2\pi R/\lambda^\ast\propto\sqrt{R/h}$（不是 (12) 表面的 $R^{1}$）。表面的 $h^1$/$R^1$ 只在**固定 $U$** 下成立，而 $U$ 不能在固定下扫 $h$/$R$（同样需 $\Delta\gamma$ 反向补偿，物理做不到）。
> 3. **能沿 Ca 挪的干净旋钮只有 $\Delta\gamma$（经醇分数 $\varphi$）与 $\gamma$**。这**不弱化旗舰指数** $-1/2$（$\lambda^\ast/h\propto\mathrm{Ca}^{-1/2}$ 是恒等式，经 $\Delta\gamma$ 扫仍可证伪），但改写了「几何/动力学如何依赖参数」的骨架、以及 T-5（稀释）的答案——见 §8 P3/P4/P7、§11。

### 6.3 Model-2：完整模型（数值 → 移交 Skill 2）

**待解**：二维 Laplacian 增长（Hele-Shaw 自由边界问题）。在两相各解 $\nabla^2 p=0$ (2)，界面上 Young–Laplace 压跳 (6) 的完整非线性形式 $[p]=\gamma\kappa$（$\kappa$ 全曲率），法向速度 $v_n=-\frac{h^2}{12\mu}\partial_n p$：
$$\nabla^2 p_j=0\ (j=1,2),\qquad [p]_{\rm int}=\gamma\kappa,\qquad v_n=-\dfrac{h^2}{12\mu}\partial_n p.\tag{14}$$
- **状态变量**：界面曲线 $\Gamma(t)$（边界积分/相场法表示）。
- **初始条件**：半径 $R_0$ 的圆 + 小白噪声扰动。
- **边界条件**：远场 $p\to$ 基态；界面 $[p]=\gamma\kappa$、$v_n$ 连续。**边界条件的物理含义**：入侵相内准均匀压（低黏 ⇒ 指内近等压），压降几乎全落在防守相——这正是 Laplacian 场把梯度聚到尖端的原因。（边界条件错是最隐蔽的错误 P6：若误把入侵相当高黏、压降落在指内，尖端反而变钝，得到相反的稳定结论。）
- **建议数值方法**：相场法（Cahn–Hilliard + Darcy）或边界积分（共形映射）；$\gamma\to$ 可调以扫 $\mathrm{Ca}$。
- **与 Model-0 对拍（Gate 0）**：**播一个单一波数 $k$、小振幅的正弦扰动，量初始指数增长率 $\sigma_{\rm num}(k)$，必须逐点等于 (7)，且峰位在 $k^\ast=2\sqrt{U(\mu_2-\mu_1)/(\gamma h^2)}$（(8)），误差 $<0.1\%$，并随振幅 $\to0$ 单调收敛**。这是纯线性代数恒等式，把「代码对不对」与「物理对不对」解耦。

---

## 7 · 自洽性检验 (Sanity Battery)

| 检验 | 做法 | 结果 |
|---|---|---|
| **量纲齐次性** | 逐式 (1)–(13) | ✓ 全部齐次（(7) 已核） |
| **极限行为** | $\gamma\to0$：(9) ⇒ $\lambda^\ast\to0$（无短波截断，纯分形，与 A-2 失效图像一致）✓；$\gamma\to\infty$：$\lambda^\ast\to\infty>2\pi R$ ⇒ 不长指（光滑铺展）✓；$\mu_2\to\mu_1$：$\lambda^\ast\to\infty$、$\sigma\to0$ ⇒ 失稳关闭 ✓ | ✓ |
| **对称性/守恒** | (7) 对 $\mu_1\!\leftrightarrow\!\mu_2$ 反号：交换驱替方向，失稳↔稳定，符号正确（楞次式的「谁推谁」）✓ | ✓ 符号正确 |
| **数值可信度** | 代入基准值：$\lambda^\ast=2.12$ mm，$N\approx9$，$t_g\approx0.05$ s | ✓ 「一滴墨炸成十来根 2 mm 手指、在零点几秒内成形」——与日常观察一致 |
| **已知特例** | $\mu_1\ll\mu_2$ 极限 (7) 退回教科书 Saffman–Taylor 色散 $\sigma=Uk-\gamma h^2k^3/(12\mu_2)$ | ✓（§10 文献对拍） |
| **反向常识** | 「漆越黏（$\mu_2\uparrow$）指越细（$\lambda^\ast\downarrow$）」「铺展越快（$U\uparrow$）指越细」 | ✓ 越使劲挤、越细的手指，符合直觉 |

---

## 8 · 可证伪预测

**这一节是分数所在。** 全部零自由参数（除 P6 是文献普适类）。

| 预测 | 内容 | 怎么证伪 |
|---|---|---|
| **P1** | $\lambda^\ast/h\propto\mathrm{Ca}^{-1/2}$，**指数 $=-0.50$，零自由参数** | 扫 **$\Delta\gamma$（经醇分数 $\varphi$）**——**不是 $\mu_2$**（H1：$\mu_2$ 相消、不移动 Ca），FFT 提 $\lambda^\ast$，测 $\log\lambda^\ast$–$\log\mathrm{Ca}$ 斜率。测得 $-1$ ⇒ naive-B（毛细平衡）；$0$ ⇒ naive-A（只由 $h$ 定）。模型死。（criterion K1） |
| **P2** | $\lambda^\ast=\pi h\sqrt{\gamma/(U(\mu_2-\mu_1))}=2.12$ mm（给定独立测的 $U$ 与 $\gamma$）⇒ $N\approx9$ | 数指的条数。偏 $1/\sqrt3$（$\approx-42\%$）⇒ 把临界波长当了指宽（onset-C）。（criterion K2）**（一参预言，非零参：$\gamma$ 需实测）** |
| **P3** | 坍缩：$\lambda^\ast/h$ vs $\mathrm{Ca}$ **落在斜率 $-1/2$ 的线上**——**杠杆只有 $\Delta\gamma(\varphi)$ 与 $\gamma$**（H1：$\mu_2$ 相消、$h$ 在此图退化） | 扫 $\Delta\gamma$ 画坍缩图。不坍缩 ⇒ 漏了一个组（A-3 剪切变稀，或 A-2 无 $\gamma$）。**注意 Model-0 输出恒落线（恒等式），真检验在实验。**（F-2） |
| **P4** | **自然耦合下**（$U$ 由 Marangoni 定，式 13）$N\propto\sqrt{R/h}$、$\lambda^\ast\propto h^{1/2}R^{1/2}$（**不是**固定-$U$ 的 $N\propto R$、$\lambda^\ast\propto h^1$，H1 订正） | 扫 $R$、$h$，数 $N$。测得 $N\propto R^1$ 而非 $\sqrt{R/h}$ ⇒ $U$ 其实不随 Marangoni 耦合（外加驱动？）⇒ 查 A-8/驱动机制 |
| **P5** | **失稳需 $\mu_2>\mu_1$**：防守相更黏才长指；反之光滑铺展 | 换低黏「漆」/高黏「墨」（$r>1$）⇒ 应**不长指**。若仍长指 ⇒ 那不是 Saffman–Taylor（sign-D 或 A-8）。（criterion K3、F-3） |
| **P6** | 高-$\mathrm{Ca}$、多代 tip-splitting 极限下，图样落入 **DLA 普适类，$D\approx1.71$**（**文献**，非本模型推导） | 盒计数测 $D$。**注意：$D\approx1.7$ 是普适的、对模型细节不敏感 ⇒ 它是弱判别子**（很多错模型也给 1.7）。**验证要靠 $\sigma(k)$ 的峰位（V-1），不是靠 $D$。** |
| **★ P7** | **稀释（$\mu_2$）在固定驱动下几乎不改指宽**（H1 补的正确预言，回答题面 "diluted acrylic paint"）：$\lambda^\ast\approx\pi\sqrt{h\gamma R/\Delta\gamma}$，与 $\mu_2$ 无关。稀释真正改变的是**失稳存在性**（$\mu_2>\mu_1$）与**时标**（$U\propto1/\mu_2$，稀漆铺得快），不是 $\lambda^\ast$ | 固定 $\varphi$（即固定 $\Delta\gamma$）扫稀释度 $\mu_2$，测 $\lambda^\ast$。若 $\lambda^\ast$ 随 $\mu_2$ 显著变（尤其 $\propto\mu_2^{-1/2}$）⇒ $U$ 不是 Marangoni 锁定的（外部驱动？）或另有机制。这是最直接检验 H1 那条耦合的实验 |

**我什么时候会错（结论对 RISKY 假设的敏感性，P14）**：
- **A-2 破**（醇墨/漆互溶、无有效 $\gamma$）⇒ **没有被选出的 $\lambda^\ast$**，P1/P2/P3/P4 全部失去对象，只剩 P6；图样是无波长选择的纯分形。**这是最可能翻的一条。**
- **A-3 破**（剪切变稀）⇒ P1 指数从 $-1/2$ 漂移，P3 坍缩散开。
- **A-8 破**（Marangoni 指而非 Saffman–Taylor）⇒ P1 标度改变，且 $r\to1$ 时指**不消失**（与 P5 相反）。
- **A-1/自由面** ⇒ P2 绝对值 $\times2$，但 P1 指数不动。

---

## 9 · 实验方案（给人做的，不是给仿真做的）

> **仿真不能替代实验。** 仿真验证「方程解对了」，实验验证「方程写对了」。只有真实验能证伪模型。

- **器材**：稀释丙烯漆 + 醇-墨（乙醇/墨水，$\varphi$ 可调）；水平玻璃板；刮涂器控膜厚 $h$；高速相机（$\ge100$ fps，顶视）；**悬滴/吊片张力仪独立测醇墨/漆界面张力 $\gamma$**（关键）；**流变仪测 $\mu_2(\dot\gamma)$**（查 A-3）；轮廓仪/干涉测 $h$；控温控湿箱。
- **测量方法**：$\lambda^\ast$——早期界面的**空间 FFT 峰位**（比数指客观）；$N$——数条数；$D$——**盒计数**；$U$——前沿轨迹 $R(t)$ 求导；$\gamma$——独立测（不能反推）。
- **需要的精度**：区分 P1 的斜率 $-0.5$ 与 $-1$，$\mathrm{Ca}$ 扫一个十进位、$\lambda^\ast$ 测到 $\sim10\%$（即 $\ge$ 数十条指或干净 FFT）即可。**而 P2（绝对值）受限于 $\gamma$**：$\lambda^\ast\propto\gamma^{1/2}$，判据 K2 只容 $\pm44\%$ 的 $\gamma$ 误差（criterion matrix robustness），而 $\gamma$ 只能测到 $\pm30\%$——**裕度仅 1.5×，所以 $\gamma$ 必须独立实测，不能取表值。**
- **误差来源**：**系统——$\gamma$ 的不确定度（主导）**、蒸发使 $U$、$\varphi$、$\gamma$ 随时间漂移（A-4）、膜厚不均、剪切变稀（A-3）；**随机**——液滴体积、滴落冲击。
- **哪些结论仍需真实实验确认**：(i) A-2——**醇墨/漆之间到底有没有有效界面张力**（决定「有没有指宽」这件事本身，仿真无法回答，必须实测 $\gamma$ 与看谱峰）；(ii) A-8——$r\to1$ 时指消不消失（Saffman–Taylor vs Marangoni）；(iii) $D$ 的真实值与 Ca 的关系。

---

## 10 · 文献

**严格区分「文献结论」与「自己推导」（P15）。**

| 用途 | 出处 | 我们用了它的什么 | 适用条件核对 |
|---|---|---|---|
| Saffman–Taylor 失稳与色散关系 | Saffman & Taylor, *Proc. R. Soc. A* **245**, 312 (1958)；Homsy, *Ann. Rev. Fluid Mech.* **19**, 271 (1987) | **只用来核对**我们独立推导的 (7)：在 $\mu_1\ll\mu_2$ 极限二者一致（$\sigma=Uk-\gamma h^2k^3/12\mu_2$）。**(1)–(11) 是自己推的。** | ✓ 我们的 Hele-Shaw + 达西前提与之相同 |
| 黏性指 = DLA、分形维数 | Daccord, Nittmann & Stanley, *PRL* **56**, 336 (1986)：径向黏性指 $D=1.70\pm0.05$；Witten & Sander, *PRL* **47**, 1400 (1981)：DLA $D\approx1.71$ | **P6 的 $D\approx1.71$ 完全是文献结论**，本模型**不独立推导** $D$——它是非线性 tip-splitting 级联的涌现性质，超出线性稳定性 | ✓ 高-Ca、多代分叉极限；低-Ca 时 $D$ 会更接近 2（更致密） |
| Marangoni 铺展驱动 | 表面张力反差 $\Delta\gamma$（乙醇 $\approx22$ mN/m vs 水 $\approx72$ mN/m）驱动铺展（tears-of-wine 类） | (13) 的 $U$ 量级估计 | ✓ 溶质 Marangoni 主导（热 Marangoni 见 A-7，$8\times10^{-4}$） |

> 红线：本文**没有**去查「分形维数答案应该是多少」再回调模型。(1)–(13) 是从达西定律与 Young–Laplace 独立推出的；$D\approx1.71$ 明确标为文献普适类，且明说它是**弱判别子**——不拿它去「验证」模型。

---

## 11 · 修订记录 + 交接

### r1 审稿（MAJOR）→ 本轮修订（逐条列出改了哪几处，供审稿人 r2 对账）

- **H1（MAJOR，控制参数不独立）**：$U$ 由 Marangoni 定（式 13）⟹ 代进 $\mathrm{Ca}=\mu_2U/\gamma$ 后 **$\mu_2$ 相消**，$\mathrm{Ca}=\Delta\gamma h/(R\gamma)$。改了 **6 处**：① §0 摘要加 boxed 结论 + 稀释正确预言；② §4 坍缩预言的杠杆点（$\Delta\gamma/\gamma$，非 $\mu_2/h$）+「Model-0 坍缩是恒等式、真检验在实验」；③ §6.2 (13) 后加三条连带后果（$\mu_2$ 不进 Ca、耦合指数 $\lambda^\ast\propto h^{1/2}$/$N\propto\sqrt{R/h}$、干净旋钮）；④ §8 P1（扫 $\Delta\gamma$ 非 $\mu_2$）、P3（杠杆）、P4（耦合指数）；⑤ §8 新增 **P7**（稀释近乎不改 $\lambda^\ast$，回答题面 "diluted"）；⑥ 契约 `parameters`（$\mu_2$ 扫描重定性、$\varphi$/$\Delta\gamma$ 认领 Ca 旋钮）、`targets` scaling_law、`tasks[T-5]`、`figures[F-2]` + 新增 `figures[F-7]`（$\lambda^\ast$-vs-$\mu_2$ 近平）。**旗舰指数 $-1/2$ 不变**（单向棘轮：只削弱/加限定，不凭空变强）。
- **H2（MINOR）**：§3 A-1 失效边界 $h/\lambda^\ast$（与 $h$ 无关，恒 0.14）→ **$h/R$**（$\to0.33$）。
- **H3（MINOR）**：§0 摘要「零自由参数」限定到**指数**；绝对值 $\lambda^\ast$ 标为一参（需实测 $\gamma$）。§8 P2 同步。
- **H4（MINOR）**：`criterion_matrix.py` 的 K2 `tolerance_source` 重写为「$\gamma\pm30\%$ 求和方 ⟹ 1σ≈19% ⟹ 门槛 20%」，$\gamma$ 不确定度与 §9 统一到 ±30%。
- **H5（MINOR，良性）**：内嵌 `criterion_matrix` 的手加 `script` 键——见下（DESYNC 门设计上剥离 `script` 再比对，故 provenance 仍可信；本轮保留，另在 skill 层评估门是否该更严）。
- **UNCLEAR/A-2**：审稿判「无从加罪」（已预注册 RISKY + 退化签名），不改；仍是全题头号物理前提，靠实测 $\gamma$ + 看谱峰定。

### 交接

→ `handoff/model-spec.json`（Skill 2 的输入契约；修订前已归档 `model-spec-r1.json`）；`01-criteria/criterion_matrix.py` → `matrix.json`（判据双向表，已内嵌进契约的 `criterion_matrix`）。
