# 验收断言 · electrical-damping（Skill 2 Stage 1）

> **这份文件在写任何求解器代码之前写完。** 每条断言的 `quoted_expectation` 从 `handoff/model-spec.json`
> 逐字抄写（`check_sim.py` 机械校验它是原文子串）。**顺序颠倒，断言就会退化成数值结果的复述。**
>
> **Step 0 补遗（仍在任何求解器代码之前）**：① id 重编号为 `AS-<数字>`（results.schema.json 要求
> `^AS-[0-9]+$`；括号里的助记名仅供人读）；② 补上 Stage 1 漏掉的 Gate 0b/0c 两条断言（它们一直写在
> (26).numerical_notes 里）；③ AS-24(V-3) 从「闭合 <1%」的缩写展开为契约逐字引文（<1e-10）；
> ④ 文末预注册两条 SPEC-DEFECT 候选（纯代数可证，不引用任何仿真数字）。

**判定规则**（写代码前定死）：`limit`(Gate 0) / `must_not` / 收敛门 被违反 ⟹ **FAIL-CODE**；
Gate 0 已过后、Skill 1 承诺的定性形状被违反 ⟹ **FAIL-MODEL**（反向边）。

---

## Gate 0 · 极限对拍（最优先，跑不过一律不许往下走）

### AS-1（G0）· λ₂ 在点偶极子 + 薄线圈极限下回到 λ₀
- **quoted_expectation**（`equations[(26)].numerical_notes`，逐字）：
  > (1) 磁体等比缩小：R_m → ε·R_m，L_m → ε·L_m，M_s → M_s/ε³（**保持 m = M_s·π R_m² L_m 固定**），ε → 0；(2) **同时**：绕组厚度 w → 0（全部匝收缩到平均半径 a）；(3) 则 λ_2(z)（式 (27)）必须回到 λ_0(z)（式 (5)），**最大相对误差 < 0.1%，且误差随 ε 单调趋于 0**（扫 ε = 1, 0.3, 0.1, 0.03, 0.01）。
- **interpretation**：三个尺度一起收缩（R_m、L_m、w）——这是配方自检强调的，magnetic-brake 就是漏了 w/只收一个尺度才收敛到 3.55 而非 1。取 `max_z |λ₂(z;ε) − λ₀(z)| / max_z|λ₀(z)|`，z 扫 [−32,32] mm。
- **assert_kind**：`limit`
- **expect**：`err(ε=0.01) < 0.1%` **且** `err(ε)` 随 ε=1,0.3,0.1,0.03,0.01 单调↓
- **tolerance**：0.1%（配方给定）；单调性无容差（必须逐点下降）
- **verdict_if_violated**：**FAIL-CODE**（纯数学恒等式）。★ 若收敛到一个 ≠1 的稳定值 = 「极限存在但取错了」= `SPEC-DEFECT`（不看仿真数字也能判：配方漏了某个尺度）。

### AS-2（G0-loop）· 单匝环极限（V-1 ⑤，r1 漏了 N=400 的那道门）
- **quoted_expectation**（`model_validation_checks[V-1].independent_checks[4]`，逐字）：
  > 令 ℓ_c → 0，(6) 必须退化为 λ = **N**·μ₀ m a²/[2(a²+z²)^{3/2}] ★ **（r1 漏了这个 N —— 审稿 H6。数值验证：比值精确收敛到 400.00 = N。**
- **assert_kind**：`limit`
- **expect**：`λ₀(z; ℓ_c→0) / (μ₀ m a²/[2(a²+z²)^{3/2}]) → N = 400.00`
- **tolerance**：< 0.1%（ℓ_c → 0 的极限）
- **verdict_if_violated**：**FAIL-CODE**（漏 N ⟹ 错 400 倍）

### AS-3（G0b）· 教科书对拍 —— 只测积分器【Step 0 补遗：Stage 1 漏了这条】
- **quoted_expectation**（`equations[(26)].numerical_notes`，逐字）：
  > ★ **Gate 0b（纯数学，只测积分器）**：把 G 强制为常数、γ_oc = 0、L = 0，则 (26) 必须**精确**重现 (15) 的教科书解 A_0·exp(−γt)·cos(ω_d t)，误差 < 1e-10。
- **interpretation**：G ≡ G(z_pk)（任意非零常数皆可，取契约基准），γ = G²/[2·M_eff·(R+R_c)]，ω_d = √(ω₀² − γ²)。积 10 个周期，误差取 max_t |z_num − z_exact| / A₀。初速度取 v(0) = −γ·A₀（使「A₀·exp(−γt)·cos(ω_d t)」恰为精确解——若按 (26) 的 v(0)=0，精确解会多一项 (γ/ω_d)·sin，那就不是引文里的教科书式了）。
- **assert_kind**：`limit`
- **expect**：`max_t |z_num(t) − A₀·exp(−γt)·cos(ω_d t)| / A₀ < 1e-10`
- **tolerance**：1e-10（配方给定）
- **verdict_if_violated**：**FAIL-CODE**（纯数学恒等式，只测积分器）

### AS-4（G0c）· 能量法对拍 —— 只测 (19)–(23) 的代数【Step 0 补遗：Stage 1 漏了这条】
- **quoted_expectation**（`equations[(26)].numerical_notes`，逐字）：
  > ★ **Gate 0c（只测能量法推导）—— r2 重写了容差与对拍点（审稿 H4）**：
把 b(z) 强制为 β z²（即 (18)），数值积分的包络必须重现 (23) 的闭式。
  · **对拍点钉死在 A₀ = 3 mm**（ζ_eff = 0.028）：**误差 < 0.05%**。**这一条是纯数学检验** —— 只测 (19)–(23) 的代数，不测 G(z)、也不测弱阻尼假设。
- **interpretation**：z₀=0、R=0，b(z) 硬编码为 β z²（β 用 (7) 的 G'(0) 闭式），包络取每周期极大值，与 (23) 闭式逐点比取最大相对偏差。**A₀ 扫描下的退化是 A-8 的预期结果（→AS-21），不是这道门。**
- **assert_kind**：`limit`
- **expect**：`max |A_num − A_(23)| / A_(23) < 0.05%` @ A₀=3mm，z₀=0，R=0
- **tolerance**：0.05%（配方给定，对拍点钉死在 A₀ = 3 mm）
- **verdict_if_violated**：**FAIL-CODE**（能量法代数或包络提取错）

---

## Targets · 数值解 vs 解析预测（Gate 3）

> 7 个 target。**先用 Model-0 精确重现 baseline**（重现不了 = 参数/单位读错，先修）。
> `γ/ζ/t*/A_c/c_2` 有闭式；`G_max/z_pk` 无闭式（(6) 数值求极值）。

| id | target | quoted baseline | assert | expect（数值 vs 契约）| tol | 违反 |
|---|---|---|---|---|---|---|
| AS-5 (T1) | `G_max` | `0.8482479` | value | Model-0 \|G\|_max（(6) 极值）= baseline | <0.5% | FAIL-CODE(重现不了)|
| AS-6 (T2) | `z_pk` | `0.0104533` | peak | Model-0 峰位 = baseline ≈ ℓ_c/2，**不是 a/2=5.40mm** | <1% | FAIL-CODE |
| AS-7 (T3) | `γ` | `2.3554174` | deviation | `gamma_oc + G_max²/(2·M_eff·(R+R_c))` = baseline | <1% | FAIL-CODE |
| AS-8 (T4) | `ζ` | `0.1227609` | deviation | `G_max²/(2·√(M_eff·k)·(R+R_c))` = baseline | <1% | FAIL-CODE |
| AS-9 (T5) | `t*` | `1.0082934` | deviation | (23) 的 `4·M_eff/(β·A_0²)`（短路 R=0）= baseline | <1% | FAIL-CODE |
| AS-10 (T6) | `A_c` | `0.0008658` | deviation | `√(8·M_eff·γ_oc/β)` = baseline | <1% | FAIL-CODE |
| AS-11 (T7) | `c_2` | `0.0344832`（r9；r8 曾误写 `0.0345832`，见追加 defect ③） | deviation | `G'(0)²/(2·M_eff·(R+R_c))·1e-6` = baseline | <1% | FAIL-CODE |

> ★ **注意（审稿 H9）**：`targets[]` 是 **Model-0** 的解析预言（Gate-0 对拍基准）。**Skill 2 真正要积的是 Model-2**
> （(26)+(27)）。Model-2 的 c₂≈0.0360（比 Model-0 高 +4.3%）—— **这个偏差是 A-1 崩塌的量度，不是 bug**，记进 `verdict_note`。

---

## Figures · expected_shape（Gate 4；Gate 0 已过后不符 ⟹ FAIL-MODEL）

### AS-12（F1）· G(z) 严格奇函数、双峰、中心精确零点
- **quoted_expectation**（`figures[F-1].expected_shape`，逐字）：
  > **G(z) 是严格的奇函数**（G(−z) = −G(z)，机器精度 < 1e-12），**G(0) = 0 精确**，双峰，峰位 |z| = z_pk = 10.45 mm ≈ ℓ_c/2（**不是** a/2 = 5.40 mm）。
- **assert_kind**：`peak` + 结构（奇对称）
- **expect**：`|G(0)|/|G|_max < 1e-12`；`|G(−z)+G(z)|/|G|_max < 1e-12`；两个峰、峰位 |z|=z_pk
- **tolerance**：奇对称/零点 1e-12（纯对称性）；峰位 <1%
- **verdict_if_violated**：`G(0)≠0` ⟹ **FAIL-CODE**（纯对称性，与模型无关，A-1 章明说）；峰位错 ⟹ FAIL-MODEL

### AS-13（F2）· (16) 的直线：斜率给 G、x 截距给 −R_c
- **quoted_expectation**（`figures[F-2].expected_shape`，逐字）：
  > **严格的直线**（线性拟合 R² > 0.999）。**斜率 = 2·M_eff/G(z_0)² —— 必须与由 (6) 独立算出的 G(z_0) 一致（<10%）。x 截距 = −R_c = −3.71 Ω —— 必须与参数表里的 R_c 一致（<5%）。**
- **interpretation**：直线性在 Model-0 里是代数恒等式、**无证伪力**；证伪力全在斜率+截距的数值。γ 的提取用 A₀ = 1 mm（ν=0.015，线性区干净——A₀=3mm 时 ν=0.133 会给 ⟨b⟩ 引入 6.3% 的系统偏差，吃掉斜率容差的大半）。
- **assert_kind**：`slope` + `value`(截距)
- **expect**：R²>0.999；斜率反推的 G(z_0) vs (6) 的 G(z_0) <10%；x 截距 = −R_c=−3.71Ω，<5%
- **tolerance**：斜率 10%、截距 5%（契约给定）
- **verdict_if_violated**：FAIL-MODEL（斜率/截距偏 ⟹ 电感不可忽略或包络拟合系统误差）

### AS-14（F3）· P3a：Q vs A₀² 过原点直线，零自由参数
- **quoted_expectation**（`figures[F-3].expected_shape`，逐字）：
  > **正确模型**：一条过原点的直线，斜率 = c₂(R=0)/(4γ_oc) —— **零自由参数** · **常数阻尼**：包络是纯指数 ⟹ **Q ≡ 0 ⟹ 一条压在 x 轴上的水平线** **⇒ 必须把这条水平线画在同一张图上。零 vs 非零 —— 离散。**
- **assert_kind**：`slope`（斜率零参）+ `must_not`（常数阻尼对照）
- **expect**：Q vs A₀²（A₀=2/3/5/8mm，居中短路）过原点、斜率 = c₂_sc/(4γ_oc)，偏差<15% 且 |截距|<0.5
- **tolerance**：斜率 15%、截距 0.5（`criteria[P3a]`）
- **verdict_if_violated**：FAIL-MODEL

### AS-15（F3-P3b）· 副面板：长时 Γ 必须回到 γ_oc
- **quoted_expectation**（`figures[F-3]` 副面板 (a)，逐字）：
  > 居中短路，四个 A₀ 的 Γ **必须全部等于开路的 γ_oc**（初始衰减率是它的 13×～86×，而长时衰减率回到它）。
- **assert_kind**：`value`
- **expect**：居中短路、A₀=2/3/5/8mm 的长时 Γ = γ_oc=0.0413；偏差<10%（`criteria[P3b]`）
- **verdict_if_violated**：FAIL-MODEL

### AS-16（F4）· regime map 用 ν（无关阶数），不用一阶判据
- **quoted_expectation**（`figures[F-4].expected_shape`，逐字节选）：
  > z₀ = z_pk、A₀ = 3 mm 时 ν = 0.133 ⟹ 它在这一侧（⟨b⟩ 偏 6.3%），**A₀ = 8 mm 时 ν = 0.70**（⟨b⟩ 偏 31%）。**⇒ 与 F-5 一致了。**
- **assert_kind**：`value` + 一致性（F-4 与 F-5 在 z_pk 处不许给相反断言）
- **expect**：ν(z_pk,3mm)≈0.133、ν(z_pk,8mm)≈0.70；**F-4 与 F-5 在 (z_pk, A₀/z_pk~0.8) 处结论一致**（都判「非线性/坍缩失败」）
- **tolerance**：ν 值 <10%；一致性布尔
- **verdict_if_violated**：**若 F-4 与 F-5 给相反断言 ⟹ FAIL-CODE/SPEC**（这正是 r1 的洞）

### AS-17（F5）· 小振幅坍缩到 y=x；大振幅系统性偏离（是结论不是 bug）
- **quoted_expectation**（`figures[F-5].expected_shape`，逐字）：
  > **小振幅（A_0/z_pk < 0.1）的点必须精确坍缩到 y = x**（斜率 1.000 ± 0.01，截距 0 ± 0.005，相对散布 < 1%）—— 这是式 (15) 的恒等式。**而大振幅（A_0/z_pk ~ 0.8）的点会系统性偏离** … **把坍缩失败当成 bug 去修，就毁掉了这个结论。**
- **assert_kind**：`collapse` + `must_not`(不许把偏离修掉)
- **expect**：小振幅斜率 1.000±0.01、截距 0±0.005、散布<1%；大振幅**必须**偏离（偏离本身是结论）
- **tolerance**：如引文
- **verdict_if_violated**：小振幅不坍缩 ⟹ FAIL-CODE((15) 恒等式)；**大振幅不偏离 ⟹ FAIL-CODE**（说明代码用了常数阻尼/线性化）

### AS-18（F6）· 相图一族螺线，居中 vs 偏心离散地不同
- **quoted_expectation**（`figures[F-6].expected_shape`，逐字）：
  > **必须画一族初始条件（至少 5 条），不是一条。** … **z_0 = 0：螺线在大振幅处收得快、小振幅处收得慢 —— 圈间距比随振幅减小而趋于 1（阻尼 ∝ z² → 0）。** … **若两族螺线看起来一样，说明代码用了常数阻尼。**
- **assert_kind**：`must_not`（结构）
- **expect**：≥5 条初条件；z_0=z_pk 圈间距比恒定；z_0=0 圈间距比随振幅↓→1（离散不同）
- **verdict_if_violated**：两族一样 ⟹ **FAIL-CODE**（常数阻尼）

---

## RISKY 假设的数值验证（Gate 5；每条必跑）

### AS-19（A-1）· 点偶极子（预期通过，误差<15%）
- **quoted_expectation**（`risky_assumption_checks[A-1].pass_criterion`，逐字节选）：
  > **预期通过（误差 < 15%）。** … **无论偏差多大，(i) G(0) = 0 必须仍然成立到机器精度**（|G(0)|/|G|_max < 1e-12）—— 它是纯对称性。**若 G(0) ≠ 0，那是代码错，不是 A-1 崩。**
- **degenerate_signature**（`risky_assumption_checks[A-1].degenerate_signature`，逐字节选）：
  > **must_not：若扫 L_m 时 |G|_max 的相对变化 < 1e-6，说明有限尺寸修正根本没进代码。**
- **assert_kind**：`deviation` + `must_not`(G(0)) + `must_not`(L_m 扫描的结构签名)
- **expect**：Model-2 vs Model-0 的 \|G\|_max 偏差 <15%（实测≈4.5%）；G(0)=0 到 1e-12；固定 m 扫 L_m∈[5,20]mm 时 Model-2 的 \|G\|_max 相对变化 ≥ 1e-6（预期 0.38；Model-0 精确为 0）
- **verdict_if_violated**：偏差>15% ⟹ PRESCRIBED（降级 P2 标定）；G(0)≠0 ⟹ FAIL-CODE；L_m 扫描无变化 ⟹ FAIL-CODE

### AS-20（A-2）· 线性阻尼（预期不通过 —— 这是本题的答案）
- **quoted_expectation**（`risky_assumption_checks[A-2].pass_criterion`，逐字节选）：
  > **预期不通过 —— 而这正是本题的答案。** … (i) **b(z_0=0) / b(z_pk) < 1e-10**（中心处零阻尼）；(ii) 主验收是 P3a（Q ∝ A₀²）… 斜率偏差 **< 15%**、截距 **|ic| < 0.5** ⟹ 通过；(iii) 数值包络与 (23a) 的闭式偏差 < 2%。
- **assert_kind**：`value` + `deviation`
- **expect**：b(0)/b(z_pk)<1e-10；P3a 斜率<15%、|ic|<0.5；数值包络 vs (23a) <2%
- **verdict_if_violated**：FAIL-MODEL（但「不通过」在 z_0=0 处是预期的答案，非灾难）

### AS-21（A-8）· 弱阻尼平均（误差∝ζ_eff²，预注册，不许修）
- **quoted_expectation**（`risky_assumption_checks[A-8].pass_criterion`，逐字节选）：
  > · A₀ = 3 mm：误差 < 0.05%（**这是 Gate 0c 的对拍点**）· A₀ = 8 mm：误差 **预期约 0.46%**，落在 [0.2%, 1.0%] 内即算符合预期 … **★★ 这个误差不是 bug，不许「修」。**
- **degenerate_signature**（`risky_assumption_checks[A-8].degenerate_signature`，逐字节选）：
  > 在 log–log 上拟合「误差 vs ζ_eff」的斜率：**必须是 2.0 ± 0.3**。
- **assert_kind**：`deviation` + `must_not`(不许修)
- **expect**：A₀=3mm 误差<0.05%（纯数学）；A₀=8mm 误差∈[0.2%,1.0%]（≈0.46%）；log-log 斜率 2.0±0.3（离散判别 2 vs 1 vs 0）
- **verdict_if_violated**：A₀=8mm 误差>1% ⟹ PRESCRIBED（收 A₀ 上限到 ζ_eff<0.15）；斜率≈1 或 ≈0 ⟹ FAIL-CODE

---

## 中间量验证（Stage 6.5；任一不过 ⟹ FAIL-CODE）

### AS-22（V-1）· G(z) —— 整条链条的入口，5 条独立路径
- **quoted_expectation**（`V-1.independent_checks`，逐字节选）：① 闭式 (6) vs 数值积分 <1e-10；② **互易性**（不经过磁通链概念）；③ Biot–Savart 直接积分 <0.1%；④ 对称性 G(−z)=−G(z)、G(0)=0 到 1e-12；⑤ 单匝环极限 → N=400.00。
- **assert_kind**：`value`（多路对拍）
- **expect**：① <1e-10；② 互易路径与①吻合 <1e-9；③ <0.1%；④ <1e-12；⑤ →400.00 <0.1%
- **verdict_if_violated**：**FAIL-CODE**（中间量算错）

### AS-23（V-2）· R_c 与 L —— 静态测量 ↔ 动力学反推的交叉验证
- **quoted_expectation**（`model_validation_checks[V-2].independent_checks`，逐字）：
  > ① **解析**：R_c = ρ_Cu · (N · 2πa) / (π (d_wire/2)²) = 3.71 Ω；L 由 Wheeler 近似 = 2.48 mH。
  > ② ★★ **动力学反推**：F-2 直线的 x 截距 = −R_c。**这是从「振子怎么衰减」反推出「线圈的直流电阻是多少」—— 两个毫无关系的物理通道。** 两者必须一致到 < 5%。
  > ③ **电感的自洽**：ω₀L/(R+R_c) 必须 < 1.3%（A-4 的判据）。且带电感的 (26) 与消去电感的二维系统之差必须 < 1.3%。
- **assert_kind**：`value`（多路对拍）
- **expect**：① R_c=3.71Ω、L=2.48mH（复算与契约参数一致 <0.5%）；② F-2 截距反推 R_c <5%；③ ω₀L/R_c<1.3% 且三态 vs 二维之差 <1.3%
- **verdict_if_violated**：**FAIL-CODE**

### AS-24（V-3）· 能量审计 —— 机械能损失必须全部现身【Step 0 展开为逐字引文】
- **quoted_expectation**（`model_validation_checks[V-3].independent_checks`，逐字）：
  > ① **能量平衡**：−ΔE_mech = ∫I²(R+R_c)dt + ∫2Mγ_ocż²dt，必须平衡到机器精度（相对误差 < 1e-10）。
  > ② **开路守恒**：令 R → ∞ 且 γ_oc = 0，则 E 必须**严格守恒**（相对漂移 < 1e-10 over 100 个周期）。**这是 Gate-0 级的纯数学检验 —— 它只测积分器。**
  > ③ **单调性**：dE/dt ≤ 0 在每个时刻都成立（耗散系统）。
- **interpretation**：★ ① 照原文在三态模型上**不可能**到 1e-10 —— 由 (26) 推能量定理，左边必须是 E_mech + ½LI²（见文末 SPEC-DEFECT 预注册 #1），且阻尼项系数是 2M_eff 不是 2M。实现用**完整恒等式** −Δ(E_mech+½LI²) = ∫I²(R+R_c)dt + ∫2M_eff·γ_oc·ż²dt < 1e-10，同时把「照原文」的失配量级（~1e-3）算出来作为 defect 的证据。③ 的 E 取 E_mech+½LI²（总储能），对耗散系统逐时刻单调。
- **assert_kind**：`value`（守恒审计）
- **expect**：①(修正后) 相对误差 <1e-10；② 100 周期漂移 <1e-10；③ dE/dt≤0 逐时刻
- **verdict_if_violated**：**FAIL-CODE**（符号/系数错——"力和电流的符号搞反、或系数差一个 2" 正是 V-3 要抓的）

### AS-25（must_not-c₂）· Model-2 的 c₂ 不许回到 Model-0 的值
- **quoted_expectation**（`assumptions[A-1].impact_if_false`，逐字节选）：
  > c₂ 偏 **+4.3%**（0.0345 → 0.0360）
- **assert_kind**：`must_not`
- **expect**：|c₂(Model-2)/c₂(Model-0) − 1| ≥ 2%（预期 +4.3%；若 <2% = 有限磁体修正没进 Model-2 的代码）
- **tolerance**：门槛 2%（真值 4.3% 的一半，离散地区分「修正在」与「修正不在」；配合 AS-19 的 L_m 结构签名双保险）
- **verdict_if_violated**：**FAIL-CODE**（Model-2 退化成了 Model-0——「符得太好」）

---

## must_not 清单（「太好了 = 可疑」——各条落点）
- **AS-25**：Model-2 若给出 Model-0 的 c₂=0.0345（而非 ≈0.0360）⟹ 有限磁体修正没进代码。
- **AS-13**：Model-2 若给出**弯的**线 ⟹ 电感没忽略对/包络拟合系统误差。
- **AS-14**：常数阻尼对照必须给 **Q≡0 水平线**（离散对照，不是稻草人截距线）。
- **AS-17 / AS-18**：大振幅**必须**偏离 y=x、两族螺线**必须**不同 —— 不偏离/相同 = 代码用了常数阻尼。
- **AS-19**：L_m 扫描时 Model-2 的 |G|_max 必须动（≥1e-6；Model-0 精确不动）。
- **AS-21**：A₀=8mm 的 0.46% 误差**不许修**（是 (23) 的截断误差）。

---

## ★ Step 0 预注册：两条 SPEC-DEFECT 候选（纯代数可证，不引用任何仿真数字）

> `SPEC-DEFECT` 的硬门槛：**不看任何仿真结果**就能证明契约有毛病。这两条都满足——证明只用契约自己的方程。

1. **V-3 ① 漏了 ½LI²（且写 2M 而非 2M_eff）。** 由契约自己的 (26) 推能量定理：
   对 M_eff·v̇ = −k(z−z₀) − 2M_eff·γ_oc·v + I·G 乘 v，对 L·İ = −(R+R_c)I − G·v 乘 I，相加：
   d/dt[½M_eff v² + ½k(z−z₀)² + **½LI²**] = −2**M_eff**·γ_oc·v² − (R+R_c)I²。
   V-3 ① 的原文「−ΔE_mech = ∫I²(R+R_c)dt + ∫2**M**γ_ocż²dt」左边没有 ½LI²、右边用 M——
   在它自己要求的 1e-10 精度上**代数地不可能成立**（½LI²/E_mech ~ 5e-4，M/M_eff 差 10%）。
   **处理**：实现用完整恒等式；results.spec_defects 记录 + proof_without_simulation（上面这段推导）。
2. **F-5 的 x 轴公式与 targets[ζ] 自相矛盾。** `figures[F-5].x` 写「ζ = G(z_0)² / [2·sqrt(M k)·(R + R_c)]」，
   而 `targets[ζ].analytical_prediction` 写「\zeta = G(z_0)^2/[2\sqrt{M_{\rm eff}k}\,(R+R_c)]」。
   同一个 ζ，两个公式，差 √(M_eff/M) − 1 ≈ 5% —— **大于 F-5 自己要求的 1% 坍缩容差**。
   两者不可能同时成立，与任何仿真无关。（(26) 的质量是 M_eff ⟹ 正确的是 targets 版。）
   **处理**：实现一律用 M_eff；results.spec_defects 记录。

### 执行中追加的两条（发现于跑的过程中，但**证明不引用任何仿真数字**——只用契约自己的数）

3. **targets[c₂].baseline_value 与它自己的 closed_form 不自洽（数位笔误）。**
   按 closed_form「(1.5*mu_0*N*m*a**2*(a**2 + ell_c**2/4)**-2.5)**2/(2*M_eff*(R + R_c)) * 1e-6」
   用契约参数复算 = **0.0344832**，而 baseline_value 写的是 **0.0345832** —— 第四位数字 4→5，偏 +0.29%。
   同源的 t*、A_c 都与 G'(0)=103.55 精确一致（<0.01%），只有 c₂ 这一个数错位 ⟹ 笔误，不是模型分歧。
   **这正是教训 19（SPEC-SELFCONTRADICT）该抓的东西** —— check_analysis 的那道门没响（容差没按存储精度定标），回填候选。
   **处理**：AS-11 以 <1% 容差通过（−0.29%）；results.spec_defects 记录。
   **r9 后记（闭环）**：回填已落地 —— `SPEC-SELFCONTRADICT` 的容差改为按 baseline 字面量的
   有效位数定标（6 位 ⟹ 1e-5，`--selftest` 钉了本案例 + 盲区探针），收紧后的门在 r8 契约上
   **机械复现了本条**；契约已修（`0.0345832 → 0.0344832`，归档 `model-spec-r8.json`，
   `01-analysis.md` §11·r9），AS-11 自此按 r9 值验收（复算偏差 ~2e-7）。

4. **★ V-2 ③ 的「三态 vs 二维之差 < 1.3%」在 R=0 端点上代数地不可能成立 —— A-4 的判据界错了量（P17，又一次）。**
   对 L·İ = −(R+R_c)I − G·v 做准静态展开：I ≈ −Gv/R_tot + (L/R_tot)·d(Gv/R_tot)/dt ⟹
   力 F = IG 里出现 **+(LG²/R_tot²)·v̇ —— 一项有效质量修正** ΔM_eff = −LG²/R_tot²。
   ⟹ δγ/γ = LG²/(R_tot²·M_eff) = **2ζ_el·(ω₀L/R_tot)** —— A-4 只界住了 ω₀L/R_tot（1.26%），
   **漏了 2ζ_el 的放大**。用契约自己的数（ζ(R=0, z_pk) = 0.785）：2×0.785×1.26% = **1.98% > 1.3%**。
   阻尼系数本身的改变确实是 O((ωL/R_tot)²)=1.6e-4（A-4 说对了那一半）——**界错的是「γ 之差」这个观测量**。
   **处理**：V-2 ③ 的检查改为「γ 差与准静态预言 2ζ_el·ω₀L/R_tot 吻合（<0.3%）且在基准点 R=20 处原判据成立（<1.3%）」；
   R=0 处按原文的失败量级作为证据记入 spec_defects。**这不是把容差放宽 —— 是把界回到它该界的量上，且新界更紧。**

---

## 复用已存在的物理（不重造）

`01-criteria/criterion_matrix.py` 已实现并被 8 轮审稿验过：**Model-2 的 `G_true`（椭圆积分+面电流片+样条）、
`G_model0`（(6) 闭式）、`envelope`/`fit_bernoulli`（(23a) 包络提取）、五条判据、ε* 二分**。
Skill 2 的 `model0.py`/`model2.py`/`field.py` 直接改写自它 —— 但 **Gate 0 / 收敛门 / V-1 的独立路径**是新的（criterion_matrix 没做极限对拍，也没做互易性那条独立路径）。
