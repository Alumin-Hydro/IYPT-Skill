# Fractal Fingers — 对账（独立 Skill 1 ⇄ 参考报告）

> **方法**：Skill 1 全程**只读题面**、不看参考解答独立跑完（+ r1 对抗审稿 MAJOR 修订）。**锁定后**才读参考
> 报告 `example-ppt/分形手指打印版.pdf`（CUPT 2023 No.1，南开 liaokq 队）做对账。参考 PDF 几乎全是图 +
> 数学被 pdftotext 打成乱码，故对账基于可提取的**机制词、相位命名、参考文献、维数值**，不逐式比对。

## 一句话

**强收敛于骨架（Marangoni 铺展 + 形态分相 + DLA 分形 D≈1.7 + geometry/dynamics 二分），
但在「指的选择机制」上分道**：**我独立选了 Saffman–Taylor（黏性驱替），参考队选了
Capillary Ridge 的 Plateau–Rayleigh 失稳（Marangoni 铺展指）。** 而**这条分歧，正是我自己
在 A-8 里预先标为 RISKY 的那一条** —— 参考队把它解到了非-ST 的一侧。

## 收敛（骨架几乎一致）

| 维度 | 我（独立 Skill 1） | 参考队（CUPT 2023） | 判 |
|---|---|---|---|
| 驱动 | Marangoni 应力铺展（$\Delta\gamma$ 由醇降表面张力）设定前沿速度 $U$ | Marangoni 铺展（refs [1-3] 全是 Marangoni/表活剂铺展）+ Young–Dupre 铺展系数 $S$ | ✓ 一致 |
| 因变量第三层「模式」 | ① 光滑圆铺展 ② 少数指 ③ 密集分形(DLA) ④ 互溶 | **Spreading Phase → Fingering Phase → Fractal Phase**（三相） | ✓ 一致（都抓了「模式/相」这层） |
| 分形本质 | DLA 普适类，$D\approx1.71$（**文献**，明标弱判别子） | **DLA，实测 $D=1.66\pm0.02$**（盒计数，ref [7] Måløy 1985 多孔介质黏性指分形） | ✓ 一致（1.66 vs 1.71，都在 DLA/黏性指 ~1.7） |
| 题面二分 | 明确 geometry（$\lambda^\ast,N,D$）vs dynamics（$R(t),N(t)$，蒸发冻结） | 明确 **GEOMETRY / DYNAMICS** 两栏组织全文 | ✓ 一致 |
| 验证纪律 | V-1 验 $\sigma(k)$ 峰位（不靠 $D$，$D$ 是弱判别子） | 有实验测 $D$、测时标（TAB.2 时标表）、真实器材（DRAGONLAB 微量移液 0.5–10 μl） | ✓ 都做实测，参考侧更全 |

**这一栏的意义**：一个**没看过参考解答**的 Opus + skill，独立收敛到了参考队的整个骨架
——Marangoni 驱动、三相分类、DLA 分形 D≈1.7、geometry/dynamics 二分。**skill 在全新物理域
（流体/图案，前三题全 E&M）上把「本质→图骨架→模式分层」的机器跑通了。**

## 分歧（一条，但在要害上）—— 指的选择机制

| | 我（独立） | 参考队 |
|---|---|---|
| **失稳机制** | **Saffman–Taylor**：低黏驱替高黏，2D Darcy 界面的 Laplacian 失稳，界面张力选出最快波长 $\lambda^\ast\propto\mathrm{Ca}^{-1/2}$ | **Capillary Ridge 的 Plateau–Rayleigh 失稳**：Marangoni 铺展前沿堆出毛细脊（rim），脊沿横向 Rayleigh 断裂成指（ref [2] Ma et al., *Phys. Fluids* 2020「Fingering instability in Marangoni spreading」） |
| **物理图像** | 压强梯度在尖端聚焦（避雷针），黏度反差驱动 | 铺展前沿的**液脊/液线**被表面张力驱动的 Rayleigh 断裂选出波长 |
| **控制量** | 毛细数 $\mathrm{Ca}=\mu_2U/\gamma$、黏度比 $r$ | 脊的几何（宽/高）+ 表面张力 + Marangoni（脊厚 $\sim$ 铺展动力学定） |

### 谁更对？——大概率是参考队

这题是**一滴液体在膜上自由铺展**（不是把流体注进受限的 Hele-Shaw 盒）。对 **Marangoni 驱动的
铺展前沿**，成熟的失稳机制正是**毛细脊/接触线的 Plateau–Rayleigh 型失稳**（Troian–Cazabat 系、
refs [1-3] 全是这一路）。我的 Saffman–Taylor 把它当成**受限驱替**问题——是教科书最有名的黏性指机制，
但对**自由面铺展滴**未必最贴切。**⟹ 参考队的机制选择大概率更合物理。**

### ★★ 而这条分歧，我自己在 A-8 里预标了 RISKY

我的 `A-8`（RISKY）逐字写着：「波长选择机制是 Saffman–Taylor（黏度反差），Marangoni 只负责设定 $U$」，
退化签名「$r\to1$ 时指**消失**（ST）vs **保留**（Marangoni）」。**参考队正是把这条解到了「保留」一侧
（Marangoni 铺展指，非 ST）。** 我的分析**诚实地把要害标成了 RISKY**，只是**正文承诺了 ST 为主**，而参考
显示 RISKY 的那一支才是真相。

### ★★★ 而它又正好解释了 r1 审稿的 H1

r1 审稿 MAJOR（H1）：ST 框架下 $\mathrm{Ca}=\mu_2U/\gamma$ 代入 Marangoni $U\propto1/\mu_2$ ⟹ **$\mu_2$ 相消、
扫稀释不动 Ca**。**这本身就是「ST 机制在这个系统里被拧着用」的症状**——黏度反差旋钮 $\mu_2$ 从指的控制里
掉出去，恰恰暗示**指不是黏度反差驱替选出来的**（那就该由脊几何 + 表面张力选，即 Plateau–Rayleigh）。
**H1（审稿抓到）+ 对账（参考显示）合起来，强烈指向 A-8 破、机制是 Capillary-Ridge/Plateau–Rayleigh。**

## ★ 元教训（这次对账真正的收获）

**对抗式审稿抓到了 H1（ST 框架的**后果**），但结构性地**无法**质疑 ST 机制的**选择**本身**——因为 A-8
（ST vs Marangoni）被诚实地预注册成 RISKY，而审稿人的纪律是「对预注册的失效模式**无从加罪**」（r1 报告
原话：把 A-2 判 UNCLEAR 同理）。**是对账（比对真实报告）揭示了机制分歧——审稿够不到的那一层。**

> **⟹ 「practice + correspond」是独立于对抗审稿的一层验证：当分析诚实地把某个机制标成 RISKY，
> 审稿人不能给它定罪，但参考报告 / 真实实验能证明 RISKY 的那一支才是真相。** 这正印证了
> [[iypt-correspond-validation]]，也是「Stage 7 必须写『哪些结论仍需真实实验确认』」那条纪律的兑现——
> **A-8 就是那条「仿真判不了、必须真实验（换低黏漆看指消不消失）」的假设，而它是全题的机制要害。**

## 结论

- **收敛**：骨架（Marangoni + 三相 + DLA D≈1.7 + geometry/dynamics）几乎逐项吻合 —— skill 在流体新域成立。
- **分歧**：一条，在机制选择（ST vs Plateau–Rayleigh 毛细脊），而**我已在 A-8 把它标成 RISKY**、审稿把
  它的后果（H1）抓了出来、对账把它的答案（参考选非-ST）补齐。**三层各司其职，没有互相掩盖。**
- **若继续**：把 essence 从「ST 选 $\lambda^\ast$」改成「机制待定：ST vs Marangoni 毛细脊，A-8 是判别实验」，
  并把 Plateau–Rayleigh 的波长选择作为**并列 Model-0'** 推一遍（$\lambda\sim$ 脊宽 $\sim\sqrt{\nu t}$ 类），
  用「$r\to1$ 指消不消失」的实验判生死 —— 但这已超出「practice+correspond」的范围，记在此备查。
