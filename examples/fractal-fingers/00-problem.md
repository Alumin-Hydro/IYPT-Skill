# Fractal Fingers — 原题、任务挖掘与设定书

## 原题（逐字）

> The effect of fractal fingering can be observed if a droplet of an ink-alcohol mixture is
> deposited onto diluted acrylic paint. How are the geometry and dynamics of the fingers
> influenced by relevant parameters?

（IYPT 2023, Problem 1 "Fractal Fingers"）

## Stage 0 · 题型判定

**依赖关系探究型 (dependence)**，但**带一个很重的「机制识别」内核**。

- 核心问句是 "**How are** the geometry and dynamics of the fingers **influenced by relevant parameters**?" —— 这是标准的依赖关系题：要**标度律、数据坍缩、参数区间划分**。
- 但 "fractal fingering" 里的 "**fractal**" 是一个定量断言（一个维数 $D$），"**can be observed if**" 是一个**条件**（现象不总是发生）—— 这两个限定词把题目同时变成了**机制识别型**（到底是哪种失稳）和**模式分类型**（有哪几类形态、边界在哪）。
- ⇒ 重心：**先说清是什么失稳机制**（Stage 4 机制预算 + Stage 5 Model-0），**再给标度律 + 坍缩**（Stage 3/7），**最后给形态相图**（"can be observed if" 那条任务的答案）。

> 若把它当成纯依赖关系题、只交几条「指宽 vs 参数」的曲线，就漏掉了 "fractal" 和 "can be observed if" 这两条最值钱的任务。

---

## Stage 0.5 · 任务挖掘 + 物理本质

### 自变量归纳（四类过一遍防漏）

| 类 | 本题的 |
|---|---|
| **系统参数** | 漆黏度 $\mu_2$（由稀释度定）、醇墨黏度 $\mu_1$、界面张力 $\gamma$、Marangoni 反差 $\Delta\gamma$、醇质量分数 $\varphi$、醇扩散系数 $D_a$、密度 $\rho$ |
| **构型参数** | 漆膜厚度 $h$、液滴半径 $R$（体积） |
| **初始条件** | 滴落高度/冲击速度、初始醇浓度、液滴与膜的温度 |
| **环境参数** | 温度（控 $\mu_2$、$\gamma$、蒸发率）、湿度、气流、基底浸润性 |

### 因变量归纳（三层——**第三层「模式」是 IYPT 的分水岭**）

| 层 | 本题的 |
|---|---|
| **标量** | 最快波长（指宽）$\lambda^\ast$、指的条数 $N$、分形维数 $D$、前沿速度 $U$、图样冻结时间 $t_{ev}$ |
| **函数** | 色散关系 $\sigma(k)$、$N(t)$、包络半径 $R(t)$、指宽分布 |
| **★ 模式** | **形态类别**：① 光滑圆铺展（不长指）② 少数光滑不分叉的指（Saffman–Taylor 指）③ 密集分叉的**分形**（DLA 类 tip-splitting）④ 完全互溶/无花样。以及它们**随参数的转变边界**。 |

> **第三层是这道题真正的题眼**：新手会去测「指宽随浓度怎么变」（一条曲线）；高分答案回答的是「**有哪几种形态？分形只在哪片参数区里出现？边界在哪？**」——那是一张**参数空间相图**。

### 题目任务（挖出来的）

| id | 任务 | kind | 从题面的**哪个词**挖出来 | 由哪张图/target 回答 |
|---|---|---|---|---|
| **T-1** | 指出指状花样的**物理本质**：是哪种界面失稳（Saffman–Taylor 黏性指？Marangoni 铺展指？），驱动、失稳、稳定各由谁承担 | essence | "**fractal fingering**"（现象本身）+ 题目要求先解释 | F-1、V-1、V-2 |
| **T-2** | 定量刻画**几何**：指宽 $\lambda^\ast$、条数 $N$、分叉/tip-splitting，以及 "fractal" 的定量含义——**分形维数 $D$**（怎么测） | mode-classification | "**fractal**" + "**geometry** ... of the fingers" | F-4、F-6、target $\lambda^\ast$/$N$ |
| **T-3** | **几何与动力学如何依赖 relevant parameters**：给出标度律（指宽 $\propto\mathrm{Ca}^{-1/2}$）与**数据坍缩**；并判定哪些参数相关、哪些不相关 | dependence | "**influenced by relevant parameters**" | F-2（坍缩）、target |
| **T-4** | 刻画**动力学**：前沿如何推进、指如何增长、图样如何随醇蒸发而**冻结**（有没有随时间的模式转变） | dependence | "**dynamics** of the fingers" | F-5 |
| **T-5** | **条件边界**：分形指在什么条件下出现、什么条件下不出现（形态相图） | regime-boundary | "**can be observed if**"（现象不总是发生）+ "**diluted**"（为何要稀释） | F-3（相图） |

> **限定词对账（每个都被追问过一次）**：
> "fractal"→T-1/T-2；"fingering"→T-1；"geometry"→T-2；"dynamics"→T-4；
> "influenced by relevant parameters"→T-3；"can be observed if"→T-5；
> "**ink-alcohol**"→醇是活性成分（Marangoni 驱动 + 蒸发，见 T-1/T-4）；
> "**diluted acrylic paint**"→"diluted" 控制 $\mu_2$、把黏度比放进能长指的区间（T-5）。
> **没有一个限定词落空。**

### 物理本质（一句话）

> **本质**：低表面张力的醇-墨滴在高黏漆膜上以 **Marangoni 应力驱动铺展**，低黏流体驱替高黏流体的推进界面在 **Laplacian 增长**下失稳、由**界面张力选出最快波长** $\lambda^\ast$ 并反复 **tip-splitting**，在驱动与界面张力的**竞争**中长出**自相似的分形指**；醇的**蒸发**使驱动关闭、花样冻结。

- **系统类型**：界面失稳与花样形成（Laplacian growth / viscous fingering）—— 经 tip-splitting 级联到分形（DLA 普适类）。
- **能量链**：自由面表面能（醇造成的 $\Delta\gamma$）→ 前沿推进的黏性耗散 + 新增界面的界面能；醇蒸发把 $\Delta\gamma$ 逐渐抹平 → 驱动 $\to 0$ → 冻结。
- **竞争的效应**：驱动（Marangoni $\Delta\gamma$，设定前沿速度 $U$） vs 稳定（界面张力 $\gamma$ 惩罚短波曲率）。比值是**毛细数** $\mathrm{Ca}=\mu_2 U/\gamma$，它选出最快波长 $\lambda^\ast$；黏度比 $\mu_2/\mu_1$ 决定失稳强度。

> **这句话决定要画哪些图**：说了「失稳/花样」就得画色散关系 $\sigma(k)$（F-1）与形态相图（F-3）；说了「分形」就得测维数 $D$（F-4/F-6）；说了「界面张力选出最快波长」就得画 $\lambda^\ast$ 的坍缩（F-2）。

---

## Stage 1 · 设定书 (Specification Sheet)

题目没给的条件，在这里全部显式定死。**设定 (Setting) 是我们自己选的实验条件，选了就没错；假设 (Assumption) 是对物理的简化，可能出错**——两者分开记，本文件只记设定，假设在 `01-analysis.md` 的台账里。

| ID | 项目 | 取值 | 理由 | 结论对它敏感吗 |
|---|---|---|---|---|
| **S-1** | 漆膜（防守相） | 稀释丙烯漆，厚度 $h = 0.30$ mm，黏度 $\mu_2 = 0.10$ Pa·s（由稀释度定） | 薄到进入 Hele-Shaw/润滑区、又厚到肉眼可见；黏度取「明显高于醇墨、但仍能流动」 | **敏感**：$\lambda^\ast\propto h$、$\propto\mu_2^{-1/2}$ |
| **S-2** | 液滴（入侵相） | 醇-墨，黏度 $\mu_1 = 1.5\times10^{-3}$ Pa·s，半径 $R = 3.0$ mm | 低黏（醇为主）造成大黏度反差 $\mu_2/\mu_1\approx 67$；$R$ 取常见微升级液滴 | 敏感：$N\propto R$ |
| **S-3** | 界面张力（醇墨/漆之间） | $\gamma = 5\times10^{-3}$ N/m（**估值，不确定度大**） | 两相都含水、互溶性强 ⇒ 有效界面张力小；**无表值**，必须实验独立测 | **极敏感**且**最不确定**：$\lambda^\ast\propto\gamma^{1/2}$（→ robustness scan） |
| **S-4** | Marangoni 反差（自由面） | $\Delta\gamma = 2.5\times10^{-2}$ N/m | 醇滴自由面 $\approx 25$ mN/m vs 漆自由面 $\approx 50$ mN/m；这是**铺展的驱动** | 决定前沿速度 $U$ |
| **S-5** | 前沿速度（观测/导出） | $U = 1.0\times10^{-2}$ m/s（基准，由影像实测） | Marangoni 铺展的典型量级（mm/s–cm/s）；它是 Model-0 的输入，不是自由拟合量 | 敏感：$\lambda^\ast\propto U^{-1/2}$ |
| **S-6** | 醇含量 | 醇质量分数 $\varphi = 0.5$ | 半墨半醇；$\varphi$ 同时控制 $\Delta\gamma$、蒸发率与互溶性 | 敏感（控驱动与寿命） |
| **S-7** | 基底与环境 | 水平玻璃板，$T = 20$ °C，相对湿度 50%，静止空气，$g = 9.81$ m/s² | 常规实验室条件；水平以排除重力铺展 | 温度经 $\mu_2(T)$、蒸发率影响；湿度影响蒸发 |
| **S-8** | 观测量 | 顶视高速影像（$\ge 100$ fps）；由 FFT 峰位提 $\lambda^\ast$、盒计数提 $D$ | 花样是二维的，顶视是自然的观测面 | — |

## 参数扫描范围（这是得分点，认真选）

| 参数 | 扫描范围 | 为什么选这个范围 |
|---|---|---|
| 漆黏度 $\mu_2$（稀释度） | 0.02 – 0.5 Pa·s | 覆盖「黏度比不够、不长指」到「大反差、密集分形」。$\mathrm{Ca}=\mu_2 U/\gamma$ 随之跨一个多量级 —— **能同时展示 T-5 相图的两侧** |
| 前沿速度 $U$（经醇含量/温度调） | 2 – 50 mm/s | $\lambda^\ast\propto U^{-1/2}$ 是**最干净的零自由参数预测**；扫 $U$ 一个十进位 ⇒ $\lambda^\ast$ 变 $\sqrt{10}\approx 3.2$ 倍，足以定斜率 |
| 醇质量分数 $\varphi$ | 0.1 – 0.9 | 同时改 $\Delta\gamma$（驱动）、蒸发率（寿命）、互溶性（界面是否锐利）—— **它是相图 F-3 的一根主轴** |
| 膜厚 $h$ | 0.1 – 1.0 mm | $\lambda^\ast\propto h$，且 $h$ 决定 Hele-Shaw 近似是否成立（$h\ll\lambda^\ast$）；扫它检验线性依赖并逼出润滑近似的边界 |

**范围选择的意图**：$\mu_2$ 与 $\varphi$ 的扫描会把系统从「不长指」推到「密集分形」再推到「完全互溶」，让 F-3 相图上出现**两条形态边界**；而 $U$、$h$ 的扫描给出两条零自由参数标度律（指数 $-1/2$、$+1$）的证伪机会。**一个不知道自己何时失效的模型，在 Physics Fight 上活不过第一轮提问。**
