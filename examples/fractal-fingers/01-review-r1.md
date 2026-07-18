# 审稿报告 · 第 1 轮

**判定**：**MAJOR**
**审稿人视角**：Opponent（fresh context，只读题面 + 设定书 + 台账 + 推导 + 预测 + 判据表；未看任何参考解答）
**被审对象**：`01-analysis.md`（配 `00-problem.md` / `handoff/model-spec.json` / `01-criteria/{criterion_matrix.py,matrix.json}`）
**修订状态**：r1，无 `02-sim/`、无 `model-spec-r{n}.json` 归档 ⟹ **未被 Skill 2 修订过 ⟹ P16 不适用**。

---

## 一句话结论

**这份分析的物理推导（色散关系、$\lambda^\ast$、$k^\ast$、$N$、$\lambda_c$、量纲、极限、文献对拍）我逐条重推、逐格代数、逐点代入，全部对得上——但它的「参数依赖」骨架是自相矛盾的：正文一边（式 13，且加粗强调）钉死「$U$ 由 Marangoni 定、不是自由量」$U=\Delta\gamma h/(\mu_2 R)$，另一边（参数表）又把 $\mu_2$ 和 $U$ 当成两根独立的扫描轴、宣称「扫 $\mu_2$ 让 $\mathrm{Ca}$ 跨一个多量级」。把式 13 代进 $\mathrm{Ca}=\mu_2U/\gamma$，$\mu_2$ 精确抵消：$\mathrm{Ca}=\Delta\gamma h/(R\gamma)$，与 $\mu_2$ 无关。** 于是**稀释漆——题面唯一明确交到手里的旋钮——在这个模型里根本不移动 $\mathrm{Ca}$、也几乎不改 $\lambda^\ast$**，而 F-2 坍缩图「四条独立轴」的说法有两条是虚的。核心指数 $-1/2$ 侥幸活着（它是 Model-0 的代数恒等式，可经 $\Delta\gamma$/$\varphi$ 扫出来），但「几何与动力学如何依赖参数」这件事——**题目的字面主问句**——被答拧了。

---

## 命中的洞

### H1 · [MAJOR] 控制参数不独立：$\mu_2$（稀释）扫描轴是退化的，坍缩图的「独立轴」被高估 — 命中 P3 / P12 / P14

- **位置**：
  - 式 (13)（§6.2，line 261-262，**加粗**）：$U\sim\dfrac{\Delta\gamma\,h}{\mu_2 R}$，并断言「**$U$ 由 Marangoni 定、可实测，不是自由拟合量**」。
  - 参数表（`00-problem.md` line 92）：「漆黏度 $\mu_2$（稀释度）0.02–0.5：$\mathrm{Ca}=\mu_2 U/\gamma$ **随之跨一个多量级**」。
  - F-2（`model-spec.json`）：「不同 $(U,\mu_2,\gamma,h)$ 的指宽坍缩到一条斜率 $-1/2$ 的线」，正文 §4 称其为「本报告杀伤力最大的图」。
- **为什么崩**（数字，全部实算，见 scratchpad/verify.py）：
  把作者自己的式 (13) 代入控制组：
  $$\mathrm{Ca}=\frac{\mu_2 U}{\gamma}=\frac{\mu_2}{\gamma}\cdot\frac{\Delta\gamma h}{\mu_2 R}=\frac{\Delta\gamma\,h}{R\,\gamma}\quad(\mu_2\ \text{精确抵消}).$$
  数值验证——$\mu_2$ 从 0.02 扫到 0.5（25×），$U$ 取 Marangoni 值：

  | $\mu_2$ | $U=\Delta\gamma h/(\mu_2R)$ | $\mathrm{Ca}=\mu_2U/\gamma$ | $\lambda^\ast$ |
  |---|---|---|---|
  | 0.02 | 125 mm/s | **0.5000** | 1.386 mm |
  | 0.10 | 25 mm/s | **0.5000** | 1.343 mm |
  | 0.50 | 5 mm/s | **0.5000** | 1.335 mm |

  $\mathrm{Ca}$ **一动不动**，$\lambda^\ast$ 只因 $(1-r)$ 项变 3.7%。「扫 $\mu_2$ 让 Ca 跨一个多量级」是**假的**。
  - **要么** $U$ 随 $\mu_2$ 浮动（Marangoni），则 $\mathrm{Ca}$ 不动、稀释把你钉在坍缩图的同一个点上；
  - **要么**强行固定 $U$ 扫 $\mu_2$，则需 $\Delta\gamma\propto\mu_2$（25× 量程），而 $\Delta\gamma$ 被醇/水表面张力锁在 $\sim$22–72 mN/m（$\lesssim$5× 量程）——**物理上做不到**。
  两条路都堵死。作者不能同时主张「$U$ 由 Marangoni 定（式 13）」和「$\mu_2$、$U$ 是两根独立轴」——**这是内部矛盾**，正文全文未提。
- **连带崩掉的**：
  1. **F-2 的「四条独立轴」被高估**：$\mu_2$ 锁在 $U$ 上（不移动 Ca）；$h$ 在 $\lambda^\ast/h$-vs-$\mathrm{Ca}$ 图上**天然退化**（$\mathrm{Ca}=\mu_2U/\gamma$ 里根本没有 $h$）。真正能沿 $-1/2$ 线移动你的只剩 $\Delta\gamma$（伪装成 $U$）与 $\gamma$。而 $\lambda^\ast/h=\pi[\mathrm{Ca}(1-r)]^{-1/2}$ 是 Model-0 的**代数恒等式**（实测：任取 $(U,\mu_2,\gamma,h)$ 组合都精确落线）——**Model-0 输出的坍缩是恒真的、不构成检验**；真正的检验是实验能否沿 Ca 挪、并量到 $-1/2$，而能挪 Ca 的干净旋钮只有 $\Delta\gamma(\varphi)$。
  2. **单变量指数被 $U$-耦合污染**：$\lambda^\ast\propto h^{+1}$（S-1、参数表）与 $N\propto R$（P4）只在**固定 $U$** 下成立。按自然的耦合变化（$U\propto h$、$U\propto1/R$，式 13）：实算 $\lambda^\ast\propto h^{0.500}$（不是 $+1$）、$N\propto\sqrt{R/h}$（不是 $R$）。作者报的 $h$-指数 $+1$ 是「固定 $U$」的产物，而 $h$ 不可能在固定 $U$ 下扫（同上，需 $\Delta\gamma\propto1/h$）。
  3. **T-5 被答拧**：题面 "diluted acrylic paint" 把稀释显式交到手里。模型的**正确**预言其实是「**固定 Marangoni 驱动下，$\lambda^\ast$ 与稀释度 $\mu_2$ 近乎无关**」（因为稀释同时降黏、升 $U$，两者抵消）——与「$\mu_2$ 是 Ca 旋钮」的框架**相反**。稀释真正改变的是失稳存在与否（$\mu_2>\mu_1$，K3）与时标，不是 $\lambda^\ast$。
- **影响**：**不推翻旗舰指数 $-1/2$**（P1 经 $\Delta\gamma$ 扫仍可证伪），但推翻了参数表的一条 load-bearing 陈述、F-2 的轴独立性、两条单变量标度指数（$h$、$R$）、以及对题目字面主问句（稀释/参数依赖）的回答结构。**赛场上 Opponent 一问「你式 13 说 $U\propto1/\mu_2$，那 $\mu_2$ 一约掉、稀释怎么还能扫 Ca？」——Reporter 答不上来。⟹ MAJOR。**
- **可否修**：不必重做 Stage 4。把控制组**改写成真正独立的形式** $\mathrm{Ca}=\dfrac{\Delta\gamma\,h}{R\gamma}$，点名 $\Delta\gamma$（经 $\varphi$）为 Ca 的真旋钮，$\mu_2$-扫改标注为「测失稳存在性/时标，不移动 Ca」，并**补上正确且可证伪的预言**：固定驱动下 $\lambda^\ast$ 与稀释度无关（$\lambda^\ast\approx\pi\sqrt{h\gamma R/\Delta\gamma}$）。F-2 的 $x$ 轴仍是 Ca，但杠杆点要老实标成 $\Delta\gamma$ 与 $\gamma$。

---

### H2 · [MINOR] A-1 失效边界界错了比值：$h/\lambda^\ast$ 与 $h$ 无关，不会「→0.5」 — 命中 P3

- **位置**：A-1「失效边界」（§3）：「$h$ 增大（扫描上端 $h=1.0$ mm，$h/\lambda^\ast\to0.5$）」；参数表：「扫 $h$ … 逼出润滑近似的边界」。
- **为什么崩**：由式 (9) $\lambda^\ast=\pi h\sqrt{\gamma/(U(\mu_2-\mu_1))}\propto h$ ⟹ $h/\lambda^\ast=\dfrac{1}{\pi\sqrt{\gamma/(U(\mu_2-\mu_1))}}$ **与 $h$ 无关**。实算三点：$h=0.1/0.3/1.0$ mm 全都给 $h/\lambda^\ast=0.1413$（不是 0.14→0.5）。随 $h$ 真正长大的是 $h/R$：$0.033\to0.10\to0.33$。所以扫 $h$ **不会**经 $h/\lambda^\ast$「逼出润滑边界」（该比值纹丝不动）；大 $h$ 端真正的隐患是 $h\ll R$ 破了（$h/R\to0.33$）。
- **影响**：不改主结论——Hele-Shaw 的 $h\ll\lambda^\ast$ 在全 $h$ 段**均匀地**是 0.14（既不改善也不恶化）。但台账里写了个错误的失效机制与错误的数（0.5），且误述了 $h$-扫的目的。
- **可否修**：把 A-1 失效边界的比值从 $h/\lambda^\ast$ 改成 $h/R$（$\to0.33$）。

---

### H3 · [MINOR] 摘要「零自由参数」把绝对值 $\lambda^\ast$ 也算进去了，而它需要实测 $\gamma$ — 命中 P2 / P12

- **位置**：§0 摘要（line 12）「**核心结论（零自由参数）**：$\lambda^\ast=\pi h\sqrt{\gamma/(U(\mu_2-\mu_1))}$」。
- **为什么崩**：这个**绝对值**公式含 $\gamma$，而 $\gamma$「无表值、极不确定、必须实测（±30%）」（S-3、A-2）。**真正零自由参数的只有指数 $-1/2$**（P1）；绝对值（P2）是 $\gamma$-limited 的一参预言。§8 P2 与 §9 已老实说清「P2 受限于 $\gamma$」——所以这是**摘要口号 vs 正文**的口径不一致，不是深层错误。
- **影响**：不改结论；但摘要那句会让读者以为 2.12 mm 是零参硬预言。
- **可否修**：摘要把「零自由参数」限定到**指数**，绝对值标为「一参（需实测 $\gamma$）」。

---

### H4 · [MINOR] K2 容差的推导算术自相矛盾（值侥幸对） — 命中 P18 ①

- **位置**：`criterion_matrix.py` `TOL["K2"]` / `matrix.json` criteria[K2].tolerance_source：「$\delta\lambda^\ast/\lambda^\ast=\delta h/h+\tfrac12(\delta\gamma/\gamma+\delta U/U+\delta\mu_2/\mu_2)=10\%+\tfrac12(15+10+10)\%\approx\mathbf{17\%}\Rightarrow$ 门槛 20%」。
- **为什么崩**：把写下的式子照算，$10\%+\tfrac12(35)\% = \mathbf{27.5\%}$（线性最坏），**不是 17%**；而它用 $\gamma\pm15\%$，与 §9/robustness 用的 $\gamma\pm30\%$ **打架**。最终门槛 20% **其实是对的**——但对应的是**另一个**算法：$\gamma\pm30\%$ 的**求和方**（$\sqrt{10^2+15^2+5^2+5^2}=19.4\%\approx20\%$），不是正文展示的那个。
- **影响**：容差值 20% 可辩护，双向表 PASS 不受影响（onset-C 偏 −42.3% 仍被 K2 抓到、$\varepsilon^\ast=20\%$ 仍成立）。但 P18 要求容差**来源**可靠，这里来源是糊的（数与式对不上、$\gamma$ 不确定度前后不一）。
- **可否修**：把 K2 来源重写为「$\gamma\pm30\%$、求和方 $\Rightarrow$ 1σ≈19% $\Rightarrow$ 门槛 20%」，并把 §9 与代码的 $\gamma$ 不确定度统一到 ±30%。

---

### H5 · [MINOR，良性] 内嵌 `criterion_matrix` ≠ `matrix.json`（多一个 `script` 键） — 契约一致性 / P18 provenance

- **位置**：`handoff/model-spec.json` 的 `criterion_matrix` vs `01-criteria/matrix.json`。
- **为什么崩**：逐键比对，内嵌副本比 `matrix.json` **多一个 `script` 键**（值 `01-criteria/criterion_matrix.py`），而当前 `criterion_matrix.py` 的输出 `out{}` **不产生** `script`（重跑得到的 `matrix.json` 无此键）。所以内嵌副本**不是**当前脚本的逐字重生成，是被**手动加过**的。
- **良性理由**：其余全部键（criteria/tolerances/robustness_scan/min_detectable/verdict）与 `source_sha256`（`6605c226…`，我重算 .py 的 sha256 一致）**都相等**，且 `script` 只是重复了 `generated_by` 的值 ⟹ provenance 实际是**可信的**。
- **影响**：无物理影响。但两点值得记：① 契约里出现了一处**手工触碰**的内嵌数据（流水线最不信任的动作）；② `check_analysis.py` 报 0 ERROR，说明它的 DESYNC 门对「内嵌多一个键」这类差异**放行了**（一个机械门的盲区，属 skill 层面，非本题）。
- **可否修**：删掉内嵌 `script` 键，或让脚本也 emit 它，使内嵌 == matrix.json 逐字成立。

---

## P1–P18 逐条结果

| 模式 | 结果 | 我执行的攻击动作 / 物证 |
|---|---|---|
| **P1 量纲** | 未命中 | 逐式写出 $[M]^a[L]^b[T]^c$：(7) $\to$ 1/s ✓、(9) 宗量无量纲 ✓、(13) $\to$ m/s ✓。独立重推 (1)→(7) 与作者逐行并排，符号/指数/正负号全一致（$\sigma=\frac{k}{\mu_1+\mu_2}[U(\mu_2-\mu_1)-\frac{\gamma h^2}{12}k^2]$）。 |
| **P2 口头忽略** | 未命中 | §5 机制预算给出每个「忽略」的**数值比**（重力 0.13、惯性 $4\times10^{-3}$、扩散 $3\times10^{-5}$、热 Marangoni $8\times10^{-4}$）。A-2 的 $\gamma_{\rm eff}>0$「无法确认」是**明标 RISKY + 验证任务**，不是静默忽略。 |
| **P3 扫描端点** | **命中 → H1, H2** | 逐个把忽略比写成参数函数代端点：Re@端点=0.75（doc 0.75 ✓，且约化 Re$\times(h/\lambda)^2$=0.015 更小）、Bo@$h$=1mm=1.96（✓，$\propto h^2$ 正确）。**但**：A-1 的 $h/\lambda^\ast$ 端点算错（H2）；**更致命**——$\mu_2$-扫在 Marangoni 耦合下不移动 Ca（H1）。 |
| **P4 双重计数** | 未命中 | 线性稳定性，一次动力学条件 (6) 一次运动学条件 (5)，无力/能重复。$\sigma(k)$ 是本征值，不叠加。 |
| **P5 非惯性系漏项** | 未命中 | 无转动/加速系。核运动学条件 $\dot\eta=u_x'$：基态平行 $x$、$u_y^{(0)}\partial_y\eta$ 为二阶 ⟹「无对流修正项」正确。 |
| **P6 边界条件不物理** | 未命中 | (14) 显式讨论：入侵相（低黏）内近等压、压降落防守相、梯度聚尖端；并**明写反向错误**（误把入侵相当高黏 ⟹ 尖端变钝 ⟹ 相反稳定结论）。处理**堪称范本**。 |
| **P7 线性化越界** | 未命中 | 线性 $\lambda^\ast$ 只用于**早期**波长选择（FFT 峰位 V-1）；非线性 $D$/tip-splitting 明确归 Model-2/文献，不外推线性理论。 |
| **P8 公式超适用域** | 未命中 | 主色散关系**自推**（非借用），$\mu_1\ll\mu_2$ 极限退回教科书 $\sigma=Uk-\gamma h^2k^3/(12\mu_2)$（实算一致）。DLA $D$=1.71 明标文献 + 高-Ca 限 + 弱判别子。 |
| **P9 时间尺度矛盾** | 未命中 | $t_g$=52ms、$t_s$=300ms、$t_{ev}\sim10^2$s，序 $t_g\ll t_s\ll t_{ev}$ 自洽（A-4 准定常 $t_g/t_s$=0.17，标 LOAD-BEARING，边界化）。 |
| **P10 耗散符号/热二** | 未命中 | **逐字读** $\sigma(k)$ 符号：$\sigma>0$ 是失稳（释放界面/驱动自由能），非「自发增能」；短波 $-\gamma k^3$ 项稳定（阻尼）✓；$\mu_2>\mu_1$ 才失稳（楞次式「谁推谁」）✓。 |
| **P11 循环论证** | 未命中 | 指数 $-1/2$ 从 $\sigma(k)$ 里 $k$ vs $k^3$ 竞争推出，非「为得到 Ca$^{-1/2}$ 而假设」。A-8 的理由是量级估计（23 Pa），非倒推。 |
| **P12 自由参数掩盖物理** | **命中 → H1, H3** | 数自由参数：指数侧 $N_f=0$（真零参）。**但**「独立可调」这件事本身破了——$U$、$\mu_2$ 被 Marangoni 锁（H1）；且摘要把需实测 $\gamma$ 的绝对值也叫「零自由参数」（H3）。 |
| **P13 符号复用冲突** | 未命中 | 高危字母逐个查：$\sigma$=增长率（明标非电导率）、$\gamma$/$\Delta\gamma$/$\dot\gamma_c$ 三义刻意区分、$k$/$k_{\rm th}$/$\kappa$ 区分、$r$（黏度比）vs $R$（半径）、$D$ vs $D_a$。无冲突。 |
| **P14 RISKY 敏感性未标** | 未命中（但见 H1） | A-2/A-3/A-8 全带 impact_if_false + `risky_assumption_checks` 退化签名 + §8「我什么时候会错」。**范本级**。（H1 是**未被列为 RISKY 的**结构性依赖，故归 P3/P12，不算 P14 漏标。） |
| **P15 文献 vs 自推** | 未命中 | §10 表格逐条分「用了它什么/适用条件」；红线声明 (1)–(13) 自推、$D$=1.71 纯文献且**弱判别子**、不拿它验模型。 |
| **P16 事后合理化** | **不适用** | 无 `02-sim/`、无 `model-spec-r{n}.json` 归档、无 `model-challenge`。此为 r1，从未被 Skill 2 数值修订。 |
| **P17 判据界错了量** | 未命中 | 三动作逐条判据跑：① 量纲——A-1(h/λ,长度比但**是合法的润滑判据** h/L)、A-3(剪切率比)、A-7(界张力反差比=力比)、A-6(Re)、K2(相对偏差) 全是**对的量**，无「耗散用长度比」。② 极值点——无判据含导数在峰/零点求值（K1 是全局拟合斜率、K2 是绝对比值）。③ 写进契约何处——K1→F-2、K2→P2、K3→F-3/P5，各自量对。**无 P17。**（注：H1 是「自变量被锁」，性质近 P17 但更是 P12/独立性问题。） |
| **P18 双向表调绿** | **命中 → H4, H5**（判定不变） | **读了 `criterion_matrix.py` 全源码**，六动作逐个跑：① 容差来源——K1 sourced ✓、K3 boolean ✓、**K2 来源算术矛盾（H4）**。② 错模型幅度谁挑——naive-A/B 指数**离散**(0,−1)、onset-C 偏置=1/√3**物理锁定**、sign-D boolean ⟹ **无 cherry-pick 幅度**，且报了 $\varepsilon^\ast$=20%（诚实）✓。③ 正确模型=契约的 Model-2 吗——$\lambda^\ast$ 是**线性量**，Gate 0 强制 Model-2 线性率 ≡ (7) ⟹ Model-0 λ* ≡ Model-2 λ*，无 electrical-damping 式的 4% 吃容差 ✓。④ 不误杀跑系统误差——扫了 $\delta\gamma/\gamma$（二分定出 44%，budget 30%，裕度 1.47×）✓（**局限**：只扫 γ，未组合 h/U/μ2；但 γ 主导）。⑤ 「被抓」是字面逻辑还是拟合器崩——K1 polyfit 给真斜率、K2 真比值、K3 真 boolean，**无 fitter-crash 虚记** ✓。⑥ why_a_student ↔ 代码——四个错模型逐一核对，函数实现与文案一致 ✓。**onset-C（形状全对、只差 1/√3 常数）试金石在场且被 K2 抓到** ✓。表本身构造得好（学到了 electrical-damping 的教训）；命中仅 H4（容差来源糊）、H5（内嵌副本手工触碰，良性）。 |

---

## UNCLEAR（我无法判断的）

- **A-2「有效界面张力 $\gamma$ 是否存在」** —— 醇/水互溶体系是否给出足以选出 $\lambda^\ast$ 的有效 $\gamma$（或只是 Korteweg 瞬态应力），是全题成立与否的物理前提。**这不是分析的洞**：作者已明标 RISKY、判为「全题最要命的一条」、给了退化签名验证任务（色散谱有没有峰）、§8 列为「最可能翻」。它需要**真实测 $\gamma$ + 看谱峰**才能判，仿真无法回答。我把它记为 UNCLEAR 而非命中——因为作者**预注册**了这个失效模式与检验，Opponent 无从加罪。
- **$t_{ev}\sim10^2$ s 的来源** —— 冻结时标只给了量级、无代入推导。它不进入瞬时 $\lambda^\ast$（不影响 H1 与主结论），故不追究；但 F-5 动力学若要定量，需补醇蒸发通量 $J$ 的估算链。
- **$\dot\gamma_c\sim5\,\mathrm{s}^{-1}$（丙烯漆剪切变稀起始）** —— 取值无出处。若更低，A-3（已 RISKY）更严重；不改我的判定。

---

## 复核清单（供作者对账）

1. **H1 是头号**：把 $\mathrm{Ca}$ 改写成 $\Delta\gamma h/(R\gamma)$，认领 $\Delta\gamma(\varphi)$ 为真旋钮，$\mu_2$-扫重新定性，补「$\lambda^\ast$ 对稀释近乎无关」这条正确预言，并订正 $\lambda^\ast\propto h^{1/2}$、$N\propto\sqrt{R/h}$（耦合下）与 P4/S-1 的固定-$U$ 指数之间的口径。
2. H2：A-1 失效比值 $h/\lambda^\ast\to h/R$。
3. H3：摘要「零自由参数」限定到指数。
4. H4：K2 容差来源重写（$\gamma\pm30\%$ 求和方），统一 $\gamma$ 不确定度。
5. H5：删内嵌 `script` 键（或脚本 emit 它）。

**总判定：MAJOR**（H1 一条即定）。物理推导与判据双向表的工艺都很扎实；崩的是「参数依赖」的骨架——而那正是题目问的东西。
