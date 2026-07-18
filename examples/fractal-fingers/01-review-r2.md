# 审稿报告 · 第 2 轮

**判定**：**MAJOR**
**审稿人视角**：Opponent（fresh context；只读题面 + 设定书 + 台账 + 推导 + 预测 + 判据表 + r1 报告 + 归档 spec；**未读 `02-correspond.md`**——它可能含真实团队解答，读了就污染独立判断，红线禁止）
**被审对象**：`01-analysis.md`（r2 修订版）配 `00-problem.md` / `handoff/model-spec.json` / `handoff/model-spec-r1.json`（归档）/ `01-criteria/{criterion_matrix.py,matrix.json}`
**修订状态**：r2，审稿驱动（**无 `02-sim/`、无 `model-challenge`** ⟹ P16 不是「数值打脸后的 HARKing」，但仍查「新 expected_shape 能否独立推导」——见 P16 行）

---

## 一句话结论

**H1 的物理内核（$U$ 由 Marangoni 定 ⟹ $\mathrm{Ca}=\Delta\gamma h/(R\gamma)$、$\mu_2$ 精确抵消、耦合指数 $\lambda^\ast\propto h^{1/2}$/$N\propto\sqrt{R/h}$、新增 P7）我逐条真算，全部对得上——H4/H3 也干净修好。但修订在拆掉「$\mu_2$ 是 Ca 旋钮」这把失明的锁时，换上了一把**镜像的新瞎锁**：它现在四处（§4、P3、F-2 契约、`00-problem` 扫描表）断言「$h$ 在 $\lambda^\ast/h$-vs-Ca 图上**天然退化**（Ca 里没有 $h$）」——可修订后的 $\mathrm{Ca}=\Delta\gamma h/(R\gamma)$ **分子里就有 $h$**。实算：扫 $h$ 时 $(\mathrm{Ca},\lambda^\ast/h)$ **严格沿 $-1/2$ 线移动**（$0.167,7.75)\to(0.50,4.48)\to(1.67,2.45)$，逐点落在 $\pi\,\mathrm{Ca}^{-1/2}$ 上），$h$ 是**有效杠杆**，而且是最干净的一个（膜厚刮涂直接可测）。这与修订自己的 **P4（$\lambda^\ast\propto h^{1/2}$）当场自相矛盾**：$\lambda^\ast$ 随 $h$ 变，$h$ 就不可能在坍缩图上退化。这正是 H1 判死的**同一个 fixed-$U$ 谬误**——修订替 $\mu_2$ 治好了，却替 $h$（和 $R$）重新犯了一遍。旗舰指数 $-1/2$ 仍活着（$\Delta\gamma$、$\gamma$ 是真杠杆），但「几何/动力学如何依赖参数」——题目字面主问句——**又一次被答窄了**（真杠杆是 $\{\Delta\gamma,\gamma,h,R\}$，契约只认了 2 个）。**赛场上 Opponent 一问「你 P4 说 $\lambda^\ast\propto h^{0.5}$，那 $h$ 明明改指宽，凭什么说它在坍缩图上退化、不能扫？」——Reporter 答不上来。⟹ MAJOR。**

外加两处 r1 洞**未传播到契约**（都是机械门看不见的脱钩）：H2 的修订只落在 §3 散文，`model-spec.json` 的 `A-1.breaks_when` 仍写着被 H2 判死的旧值「$h/\lambda^\ast\to0.5$」；`00-problem.md` S-2 仍写「$N\propto R$」，与修订后的 $N\propto\sqrt{R/h}$ 打架。

---

## 命中的洞

### H1(r2) · [MAJOR] 「$h$ 退化」——修订在 $h$/$R$ 上重犯了 H1 判死的 fixed-$U$ 谬误 — 命中 P12（隐蔽变体）/ P3

- **位置**（同一错误，四处）：
  - `01-analysis.md` §4 line 188：「$h$ 在 $\lambda^\ast/h$-vs-Ca 图上**天然退化**（**Ca 里没有 $h$**）」。
  - `01-analysis.md` §8 P3 line 310：「杠杆只有 $\Delta\gamma(\varphi)$ 与 $\gamma$（H1：$\mu_2$ 相消、$h$ 在此图退化）」。
  - `handoff/model-spec.json` line 564，F-2 `series`：「不同 Δγ(φ)、γ 组合（★ 不是 μ2/h——μ2 相消、**h 退化**，H1）」。
  - `00-problem.md` line 95 / 97：「$h$ 在 $\lambda^\ast/h$-vs-Ca 图上退化」；「$U$/$h$/$\mu_2$ 单独扫……指数被污染或退化，真正沿 Ca 挪的干净旋钮只有 $\Delta\gamma$ 与 $\gamma$」。
- **为什么崩**（全部实算，见 scratchpad/`verify_r2.py`）：修订把 Ca 重定义为 $\mathrm{Ca}=\Delta\gamma h/(R\gamma)$——**$h$ 就在分子里**。所以「Ca 里没有 $h$」这句用来支撑「$h$ 退化」的理由，在修订后的文档里**自我否定**。真算扫 $h$（$\Delta\gamma,\gamma,R,\mu_2$ 固定）：

  | $h$ (mm) | $\mathrm{Ca}=\Delta\gamma h/(R\gamma)$ | $\lambda^\ast/h$ | $\pi\,\mathrm{Ca}^{-1/2}$ |
  |---|---|---|---|
  | 0.10 | 0.1667 | 7.754 | 7.695 |
  | 0.30 | 0.5000 | 4.477 | 4.443 |
  | 1.00 | 1.6667 | 2.452 | 2.433 |

  $\mathrm{Ca}\propto h$、$\lambda^\ast/h\propto h^{-1/2}$，点**逐个沿 $-1/2$ 线滑动**——$h$ 是有效杠杆，**不退化**。（对照真退化的 $\mu_2$：扫 25× 时 Ca 一动不动、始终 0.50。）$R$ 同理（$\mathrm{Ca}\propto1/R$，也落线）。**能沿 Ca 挪的干净旋钮是 $\{\Delta\gamma,\gamma,h,R\}$，只有 $\mu_2$ 退化**——修订只认了 $\{\Delta\gamma,\gamma\}$，把 $h$、$R$ 错划进退化区。
  - **鉴伪**：为什么「$h$ 在两根轴上都出现」不使它退化？拿一个错模型试金石——若真实 $\lambda^\ast\propto h^1$（naive-A），则 $\lambda^\ast/h=$ 常数、$\mathrm{Ca}\propto h$ ⟹ 扫 $h$ 给**斜率 0**，与正确的 $-1/2$ **离散地不同**。所以扫 $h$（实测 $\lambda^\ast$ 由 FFT）**能证伪模型**，是货真价实的杠杆。「Model-0 恒落线」的恒等式警告对**所有**杠杆（含 $\Delta\gamma$）一视同仁，不构成把 $h$ 单独踢出的理由。
- **与修订自身矛盾**：§6.2 point 2 与 §8 **P4** 白纸黑字写 $\lambda^\ast\propto h^{1/2}$（实算确认：$\lambda^\ast\propto h^{+0.500}$）。$\lambda^\ast$ 随 $h$ 变 $\Rightarrow$ $\lambda^\ast/h\propto h^{-1/2}$、$\mathrm{Ca}\propto h$ $\Rightarrow$ 扫 $h$ 必然沿坍缩线走。**「$\lambda^\ast\propto h^{0.5}$」与「$h$ 退化」不可能同时为真。** 这是 H1 那种「参数独立性内部矛盾」的翻版。
- **影响**：**不推翻旗舰指数 $-1/2$**（$\Delta\gamma$、$\gamma$ 仍是真杠杆，P1 可证伪）。但（a）与 P4 直接自相矛盾；（b）**误导实验方案 §9**——把最干净、最直接可测的杠杆 $h$（连同 $R$）踢出坍缩扫描，命令 Skill 2 只扫 $\Delta\gamma$/$\gamma$；（c）再次答窄了题目主问句（参数依赖）。这与 r1 的 H1 是**同一病灶、同一严重度**（r1 把「轴独立性说错」判 MAJOR，此处「轴独立性说反」按同一标尺也是 MAJOR）。
- **可否修**：不必重做。把四处「$h$ 退化」改成「$h$、$R$ 也沿 Ca 移动、是有效（且干净）杠杆——**只有 $\mu_2$ 退化**」；F-2 `series` 改为「不同 $\Delta\gamma(\varphi),\gamma,h,R$ 组合（$\mu_2$ 相消）」；把「Ca 里没有 $h$」这句删掉（它是 fixed-$U$ 谬误的残留）。**单向棘轮提示**：这是「加回一个被误删的杠杆」，是让预言**变强**——但它变强的是「可证伪面」而非「结论精度」，且有独立推导（上表）撑腰，合法。

---

### H2(r2) · [MINOR] H2 的修订没传播到契约：`model-spec.json` 的 `A-1.breaks_when` 仍是被判死的旧值 — 契约脱钩 / CLAUDE.md 教训 4/16

- **位置**：`handoff/model-spec.json` line 407，`assumptions[A-1].breaks_when`：「h 增大（扫描上端 h=1mm, **h/λ\*→0.5**）或黏度比很大使 λ\* 变小」——与归档 `model-spec-r1.json` line 402 **逐字相同**（一个字没改）。
- **为什么崩**：r1 的 H2 已证 $h/\lambda^\ast$ 与 $h$ 无关（恒 0.14），永不 $\to0.5$；`01-analysis.md` §3 A-1 line 110 **已正确改成** $h/R\to0.33$。但下游真正读的 `model-spec.json` 里旧的错值「$h/\lambda^\ast\to0.5$」**还活着**。实算：$h=1$ mm 时 $h/\lambda^\ast=0.26$（耦合）或 $0.14$（固定 $U$），$h/R=0.33$——**没有一个是 0.5**。
- **影响**：不改主结论，但这正是 CLAUDE.md 教训 4（修订只落在推导、漏了契约）+ 教训 16（STALE-VALUE）反复强调的脱钩：散文改对了，Skill 2 读的契约仍是错的。机械门 0 ERROR（`check_analysis.py` 抓不到这种散文↔契约脱钩）。
- **可否修**：`A-1.breaks_when` 改为「$h$ 增大：$h/R$（不是 $h/\lambda^\ast$）逼近 0.33，$h\ll R$ 先破」。

---

### H3(r2) · [MINOR] `00-problem.md` S-2 仍写「$N\propto R$」，与修订后的 $N\propto\sqrt{R/h}$ 打架 — 契约脱钩

- **位置**：`00-problem.md` line 80，S-2「结论对它敏感吗」列：「敏感：$N\propto R$」。
- **为什么崩**：修订已把 `targets[N].scaling_law` 与 §8 P4 改成 $N\propto\sqrt{R/h}$（Marangoni 耦合），实算确认 $N\propto R^{+0.500}$（不是 $R^1$）。S-1（line 79）**已同步**改成 $\lambda^\ast\propto h^{1/2}$，但**同一张表的 S-2 漏改**，仍是 fixed-$U$ 的旧指数 $R^1$。
- **影响**：MINOR。设定书自相矛盾（S-1 用耦合指数、S-2 用固定-$U$ 指数），与 §8 P4 也矛盾。
- **可否修**：S-2 改「敏感：$N\propto\sqrt{R/h}$（Marangoni 耦合，H1）」。

---

## r1 洞是否已修（逐条对照）

| r1 洞 | r1 判定 | 修订动作 | 我的复核（真算） | 结论 |
|---|---|---|---|---|
| **H1** 控制参数不独立（$\mu_2$ 从 Ca 相消） | MAJOR | Ca=Δγh/(Rγ)、$\mu_2$ 不进 Ca、耦合指数、新增 P7、契约多处改 | $\mu_2$ 抵消 ✓（Ca 恒 0.50、λ\* 变 3.82%≈报的 3.7%）；$\lambda^\ast\propto h^{0.5}$✓、$N\propto\sqrt{R/h}$✓（实测 $h^{+0.500}/R^{+0.500}$）；P7 λ\*≈π√(hγR/Δγ) 可**独立推导**✓ | **半修好**：$\mu_2$ 方向修对，但**同一 fixed-$U$ 谬误在 $h$/$R$ 上重犯**（H1(r2) MAJOR）——锁换了，新锁也瞎 |
| **H2** $A$-1 失效边界界错量（$h/\lambda^\ast\to0.5$） | MINOR | §3 A-1 改成 $h/R\to0.33$ | 散文 §3 ✓改对；但 **`model-spec.json` A-1.breaks_when 仍是旧的 $h/\lambda^\ast\to0.5$**（逐字未动） | **未传播到契约**（H2(r2) MINOR） |
| **H3** 摘要「零参」把绝对值也算进去 | MINOR | §0 限定「零参」到指数，绝对值标一参 | §0 line 15、§8 P2 均已限定到指数 ✓ | **已修好** |
| **H4** K2 容差推导算术自相矛盾（17% vs 27.5%） | MINOR | K2 tolerance_source 重写为 γ±30% 求和方 | √(10²+15²+5²+5²)=19.4%⟹门槛 20% ✓；γ 不确定度与 §9/robustness 统一到 30% ✓；`criterion_matrix.py` 重跑、sha256=1305f41b… 三处（.py/matrix.json/内嵌）全一致 ✓ | **已修好**（且消除了 r1 指出的 ±15/±30 打架） |
| **H5** 内嵌 criterion_matrix 多一个 `script` 键 | MINOR/良性 | 保留 `script`，论证 `check_analysis` 剥离该键后逐字比对 | 实测：内嵌（剥 `script`）== matrix.json **逐字相等 True** ✓ | **已解决**（scope 论证成立） |

---

## P1–P18 逐条结果

| 模式 | 结果 | 我执行的攻击动作 / 物证 |
|---|---|---|
| **P1 量纲** | 未命中 | 核心式 (7)/(9)/(13) 未改。新耦合式 $\lambda^\ast\approx\pi\sqrt{h\gamma R/\Delta\gamma}$ 量纲：$\sqrt{\mathrm m\cdot(\mathrm N/\mathrm m)\cdot\mathrm m/(\mathrm N/\mathrm m)}=\mathrm m$ ✓。 |
| **P2 口头忽略** | 未命中 | §5 机制预算每个「忽略」带数值比（重力 0.13、惯性 4e-3、扩散 3e-5、热 Marangoni 8e-4），未受修订影响。 |
| **P3 扫描端点** | **命中 → H1(r2), H2(r2)** | 逐端点代入。$\mu_2$-扫已正确重定性；但 $h$-扫被错标「退化」（H1(r2)）；A-1 的 $h$ 端点旧值 $h/\lambda^\ast\to0.5$ 仍活在契约（H2(r2)）。 |
| **P4 双重计数** | 未命中 | 线性稳定性一次动力学 (6) 一次运动学 (5)，无重复；未改。 |
| **P5 非惯性系** | 未命中 | 无转动/加速系；运动学条件无对流修正项论证未改。 |
| **P6 边界条件** | 未命中 | (14) 入侵相近等压、压降落防守相、并明写反向错误——范本级，未改。 |
| **P7 线性化越界** | 未命中 | 线性 $\lambda^\ast$ 只用于早期波长选择；非线性 $D$/tip-splitting 归 Model-2/文献。 |
| **P8 公式超适用域** | 未命中 | 主色散关系自推，$\mu_1\ll\mu_2$ 退回教科书 ST；$D$=1.71 标文献+弱判别子。 |
| **P9 时间尺度** | 未命中 | $t_g\ll t_s\ll t_{ev}$（0.05/0.30/1e2 s）自洽，A-4 边界化，未改。 |
| **P10 耗散符号** | 未命中 | 逐字读 $\sigma(k)$：$\sigma>0$ 释放界面自由能、$-\gamma k^3$ 稳定短波、$\mu_2>\mu_1$ 才失稳，符号全对。 |
| **P11 循环论证** | 未命中 | 指数 $-1/2$ 从 $k$ vs $k^3$ 竞争推出，非倒推；P7 的 λ\*≈π√(hγR/Δγ) 从式(9)代式(13)独立得出，非照抄审稿。 |
| **P12 自由参数掩盖物理（隐蔽变体）** | **命中 → H1(r2)** | 这正是 H1 的落点。$\mu_2$-锁已解，但**镜像新病**：把真能移动 Ca 的 $h$、$R$ 错判为退化（应只有 $\mu_2$ 退化），与 P4 自相矛盾。真杠杆 $\{\Delta\gamma,\gamma,h,R\}$，契约只认 2 个。 |
| **P13 符号复用** | 未命中 | $\gamma$/$\Delta\gamma$/$\dot\gamma_c$、$\sigma$（非电导率）、$r$ vs $R$、$k$/$k_{\rm th}$/$\kappa$ 区分完好，未改。 |
| **P14 RISKY 未标敏感性** | 未命中 | A-2/A-3/A-8 全带 impact_if_false + 退化签名 + §8「我什么时候会错」，未改。 |
| **P15 文献 vs 自推** | 未命中 | §10 逐条分「用了它什么/适用条件」；红线声明 (1)–(13) 自推、$D$=1.71 纯文献且弱判别子，未改。 |
| **P16 事后合理化** | **不适用（但查了独立可推导性）** | 无 `02-sim/`、无 `model-challenge`；此为审稿驱动修订。仍查新 expected_shape：P7（λ\* 对 μ2 近平）与 F-7 的「λ\*-vs-μ2 只因 (1-r) 微降 3.8%」**能从模型独立推导**（实算 (1-r)^(-1/2) 在 μ2 扫 25× 上变 3.8%），不是照数值描的 ⟹ 非 HARKing。 |
| **P17 判据界错了量** | 未命中 | K2 是**绝对值比**（对的量，含 γ 需实测——非零参标注正确）、K1 是全局拟合指数、K3 是布尔符号；H4 重写未引入导数在极值点求值或长度比判耗散。无 P17。 |
| **P18 双向表调绿** | 未命中（判定不变） | 重跑 `criterion_matrix.py`（exit 0，三条双向成立）。① 容差有来源且与正文一致（H4 修好，K2 求和方 19.4%⟹20%）；② $\varepsilon^\ast=20\%$、onset-C 偏 −42.3% 被 K2 抓（试金石在场）；③ 正确模型=线性量 Model-0≡Model-2 λ\*；④ robustness 二分定出 δγ<44%、budget 30%、裕度 1.47×，且 r7-H1 的 margin 门（dg_max≥budget）通过；⑤ 「被抓」是判据字面逻辑（K1 真斜率/K2 真比值/K3 真布尔）；⑥ why_a_student ↔ 代码一致。内嵌==matrix.json（剥 script）逐字相等、sha256 三处一致。**表工艺仍扎实。** |

---

## UNCLEAR（我无法判断的）

- **A-2「有效界面张力 $\gamma$ 是否存在」**：同 r1，作者预注册了 RISKY + 退化签名（谱峰有无），Opponent 无从加罪，需实测 $\gamma$ + 看谱峰。修订未动，仍是全题头号物理前提。
- **式 (13) 的 2.5× 量级差**（$U_{\rm Marangoni}=25$ mm/s vs 设定 $U_0=10$ mm/s）：这使「Marangoni 版 Ca=0.50」与「设定版 Ca=$\mu_2U_0/\gamma$=0.20」相差 2.5×。作者在 line 270 已承认式 (13) 是量级估计。**不是新错**，但下游画 F-2 时用哪个 Ca 基准要说清，否则基准点会飘。记为提醒，不进判定。
- **未读 `02-correspond.md`**：该文件可能含真实团队解答，为守住 fresh-Opponent 独立性，本轮**故意不读**。

---

## 复核清单（供作者对账 r3）

1. **H1(r2) 是头号**：四处「$h$ 退化」全部改为「$h$、$R$ 也沿 Ca 移动、是有效杠杆，只有 $\mu_2$ 退化」；删掉「Ca 里没有 $h$」（fixed-$U$ 残留）；F-2 `series` 补上 $h$、$R$。**这与 P4（$\lambda^\ast\propto h^{0.5}$）的自相矛盾必须一并消。**
2. H2(r2)：`model-spec.json` `A-1.breaks_when` 的 $h/\lambda^\ast\to0.5$ 改成 $h/R\to0.33$（散文已改，契约漏了）。
3. H3(r2)：`00-problem.md` S-2 的 $N\propto R$ 改成 $N\propto\sqrt{R/h}$（S-1 已改，S-2 漏了）。

**总判定：MAJOR**（H1(r2) 一条即定）。修订把 H1 的 $\mu_2$ 内核修对了、H3/H4 干净、H5 论证成立、双向表工艺仍扎实——但它在拆锁时按**同一个 fixed-$U$ 谬误**换上了一把镜像新瞎锁（$h$/$R$ 退化），并漏了两处契约传播。**这是 CLAUDE.md 教训 15「拆掉一把失明的锁，换上的新锁多半也瞎」的又一次实证——这次瞎在 $h$ 上。**
