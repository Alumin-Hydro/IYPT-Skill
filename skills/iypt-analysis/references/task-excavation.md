# 任务挖掘：题面里的每一个词都是任务的种子

**IYPT 的题面是一段话，不是一张任务清单。** 但真正的任务全藏在那段话的措辞里。

**挖不出来 = 你在答一道自己编的、更容易的题。** 而 Opponent 会拿真正的那道题问你。

---

## 先看两个真实的例子（都来自拿过分的报告）

### 磁铁加速器（IYPT No.8）

**原题**：

> "Fix magnets in pairs onto a metal sheet as shown. If you attach two magnetic discs onto an axle this 'vehicle' will accelerate over the rows of magnets **under certain conditions**. **Investigate** the phenomenon."

**报告挖出来的任务**：

1. **指出磁铁加速过程的物理本质** ← 从 "Investigate the phenomenon"
2. 探究末速度、加速度变化与参数的关系 ← 从 "accelerate"
3. **探究磁铁有效加速的条件** ← 从 **"under certain conditions"**

> **第 3 条是从题面里一个介词短语挖出来的。** 而它往往是**最难、最值钱**的一条——它要求一张**参数空间相图**（哪片区域会加速、哪片不会），而不是一条曲线。

### 磁力牛顿摆（IYPT No.15）

**原题**：

> "Repulsing, non-touching magnets are used instead of colliding balls to make a new type of Newton's cradle. The new cradle **can act in a similar way to a regular cradle**, but **can also exhibit other interesting behaviour**. **Explain and study** the movement of this magnetic cradle."

**报告挖出来的任务**：

1. **探究磁力牛顿摆和传统牛顿摆运动模式之间的异同** ← 从 "similar way to a regular cradle"
2. **探究系统在不同情况下的运动模式** ← 从 **"other interesting behaviour"**

最后落到了 **混沌**、**Lyapunov 指数**、**频谱从离散峰展宽为连续宽带**。

> **而"混沌"这两个字，题面里一个都没有。** 它是从 "other interesting behaviour" 里挖出来的。

---

## 对照表：题面里的词 → 它在要求什么

| 题面里的词 | 它其实在要求 | 挖出来的任务 |
|---|---|---|
| **"Investigate the phenomenon"** | 不是"测几条曲线"，是**解释** | **指出物理本质**：一句话说清能量/机制的转换链条 |
| **"under certain conditions"** / **"can"** / **"in some cases"** | 现象**不总是**发生 | **找出条件边界** —— 参数空间里哪片区域会、哪片不会。**这几乎总是最难、最值钱的一条**，而且它的答案是**一张参数空间相图**，不是一条曲线 |
| **"other interesting behaviour"** / **"various modes"** / **"different regimes"** | 有**多种**行为 | **模式分类** + 模式之间的**转变**（分岔 / 混沌 / 共振 / 锁模） |
| **"relevant parameters"** | "relevant" 本身是个问句 | **哪些参数相关、哪些不相关，都要给理由。** 说一个参数"不相关"和说它"相关"一样需要证据 |
| **"Explain and study"** | 解释 ≠ 拟合 | **机制识别**：证明是这个机制，并**排除**其他候选（机制预算） |
| **"similar to X but also …"** | 题面给了你一个**参照系** | **对照**：与已知系统的异同 —— 哪里像、哪里不像、**为什么** |
| **"Optimize" / "Maximize"** | 一定有权衡 | **权衡关系**：什么增大了、什么**必然**减小 |
| **"Determine X using Y"** | 这是个**测量方法**题 | **误差**：灵敏度、系统误差、精度极限 |
| **"Study the motion / movement"** | 运动学 | **不只是 $x(t)$**：相图、模式、稳定性、吸引子 |
| **"How does it depend on…"** | 依赖关系 | 标度律 + **数据坍缩** |

---

## 两条铁律

### 铁律 1：**因变量不只是"数"，还有"模式"**

新手会把 "study the movement" 理解成"测 $x(t)$ 然后拟合一条曲线"。

**高分答案回答的是**：

> **有哪几种运动模式？它们怎么随参数转变？边界在哪？**

**这是 IYPT 的分水岭。**

因变量必须分三层列（**第 3 层最容易漏，也最值钱**）：

| 层 | 例 |
|---|---|
| **标量** | 终速、频率、幅度、效率、末速度 |
| **函数** | $x(t)$、$v(x)$、$F(d)$、$U(x)$ |
| **★ 模式** | 周期 / 准周期 / **混沌**；同向模 / 反向模；加速 / 减速 / **卡住**；单稳 / 多稳 |

### 铁律 2：**题面里每一个限定词都要被追问一次**

- "**under certain** conditions" → **哪些**条件？
- "**can also** exhibit" → 还能干**什么**？
- "**in a similar** way" → 哪里**像**？哪里**不像**？
- "**this** vehicle will accelerate" → 换个车呢？

> **漏掉一个限定词 = 漏掉一条任务 = Opponent 的第一个问题。**

---

## 变量归纳（和挖任务同时做）

### 自变量：照这**四类**过一遍，防漏

| 类 | 例（磁铁加速器） |
|---|---|
| **系统参数** | 磁化强度、质量、几何尺寸、材料常数（电导率、磁导率） |
| **构型参数** | 磁铁间距、磁铁数密度、排列方式、板张角、车轴长 |
| **初始条件** | 释放位置、初速度、初始角度 |
| **环境参数** | 温度、介质、重力、外场 |

**四类里空着一类，先问自己"真的没有吗"。**

### 因变量：三层（见铁律 1）

---

## 物理本质：一句话

**在写下任何方程之前，用一句话说清这是个什么系统。**

格式：**「X 通过 Y 转换 / 耦合 / 竞争为 Z 的〈某类〉系统」**

真实的例子（都来自拿过分的报告）：

| 题 | 物理本质 |
|---|---|
| 磁铁加速器 | **"磁势能向动能的非对称转换"** |
| 磁力牛顿摆 | **"在重力约束下、通过非接触磁排斥实现耦合的非线性多体动力系统"** |
| 磁刹车（本 repo 的样例） | **"重力驱动与涡流耗散的平衡；驱动 ∝ 常数，耗散 ∝ v，故必然趋于终速"** |

**这句话的作用不是修辞，是骨架：**

> **它决定了你要画哪些图。**

- "**非对称转换**" ⇒ 必须画 **势能景观 $U(x)$**（看那个"非对称"长什么样）
- "**非线性多体耦合**" ⇒ 必须画 **相图、频谱、Lyapunov**（看"非线性"和"多体"的后果）
- "**驱动与耗散的平衡**" ⇒ 必须画 **力平衡、弛豫时间、标度律**

**说不出这句话 = 你还没懂 = 你不知道该画什么图。**

---

## 产出：`tasks[]`

每条任务写全四项，写进 `handoff/model-spec.json` 的 `tasks[]`：

| 字段 | 内容 |
|---|---|
| `id` | `T-1`, `T-2`, … |
| `statement` | 任务本身 |
| `kind` | `essence` / `dependence` / `regime-boundary` / `mode-classification` / `comparison` / `optimization` / `measurement` |
| **`excavated_from`** | **题面里的哪个词**（逐字引用）。**这一条是防自欺的**——挖不出出处的"任务"，多半是你自己编的 |

**然后：每条任务必须被至少一张图或一个 target 回答**（`figures[].answers_task`）。`check_analysis.py` 机械检查这一条。

**最后（Skill 3 的 PPT 里）：逐条打勾。** 真实报告的最后一页就是：

> 指出磁铁加速过程的**物理本质** ✓
> 探究**末速度、加速度变化与参数的关系** ✓
> 探究磁铁**有效加速的条件** ✓

**答不上来的任务，比没挖出来的任务更糟——但都不如「挖出来了、答上了、还打了勾」。**
