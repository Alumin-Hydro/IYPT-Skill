# Ball on Ferrite Rod — 验收断言（Stage 1，写在求解器之前）

> **顺序即纪律**：这份断言在写任何求解器之前定死。每条 `quoted_expectation` **逐字**从
> `handoff/model-spec.json` 的对应字段抄来（`check_sim` 机械校验是子串）。容差在此定死，不许事后放宽。
> 机械实现见 `code/acceptance.py`（run() 计算 measured + verdict）。

## 判定规则（写代码之前就定）

| 被违反的断言 | 判定 |
|---|---|
| `limit`（Gate 0 极限对拍） | **FAIL-CODE**（纯数学恒等式） |
| `must_not`（退化特征） | **FAIL-CODE / FAIL-MODEL**（结构性退化） |
| 收敛门 | **FAIL-CODE** |
| Skill 1 承诺的形状（Gate 0 已过） | **FAIL-MODEL**（走反向边） |

## 断言表

| ID | 源 | assert_kind | 期望（逐字引文来源） | 容差 | 违反判 |
|---|---|---|---|---|---|
| **AS-1** | target k_h | `limit` | Gate 0：单碰撞解析精确、A→0⟹h̄→0（单调）、e→1⟹h̄→∞（单调）、可积极限 λ=ln e<0 | single<1e-12；λ 偏 ln e<0.05 | FAIL-CODE |
| **AS-2** | figure F-1 | `peak` | 共振峰在 f₁=c/4L（固定-自由） | <5% | FAIL-CODE |
| **AS-3** | figure F-3 | `slope` | h̄ vs (Aω)² 过原点直线，斜率=k_h=(1+e)/[4g(1-e)]（零参） | <5% | FAIL-MODEL |
| **AS-4** | target k_h | `deviation` | 基准点 h̄ = 理论闭式 | <5% | FAIL-MODEL |
| **AS-5** | figure F-4 | `must_not` | 弹高**不许**是单值锁相（忽略能量泵入的退化模型）——分布必须宽 | CV>0.3 | FAIL-CODE |
| **AS-6** | figure F-6 | `value` | 混沌 λ>0，且可积极限 λ<0（证明正 λ 是真混沌不是噪声） | λ_c>0 且 λ_i<0 | FAIL-CODE |
| **AS-7** | figure F-5 | `value` | regime 由 Γ 定，f/f_bounce=Γ/π·√((1+e)/2(1-e))，工作点在随机相位区（>>1） | f/f_bounce>>1 | FAIL-MODEL |
| **AS-8** | risky A-1 | `must_not` | 共振峰**不许**落在 c/2L（自由-自由）——落在 c/2L 说明 BC 退化 | 离 c/2L 远、离 c/4L<5% | FAIL-MODEL |
| **AS-9** | risky A-4 | `must_not` | h̄ vs (Aω)² 斜率**不许**随扫描系统性漂移——漂移则 e(u) 速度依赖 | 漂移<10% | PRESCRIBED |
| **AS-10** | figure V-1 | `peak` | 中间量：棒尖振幅 A(f) 峰位独立验证（不由弹高反推） | <5% | FAIL-CODE |

### 双向性（"符得太好"也是失败）
- **AS-5（must_not）**：若弹高分布 CV→0（单值锁相），说明代码退化成「球被抛到峰值棒尖速度 Aω 对应高度」的
  单值模型，忽略了多次随机碰撞的能量泵入。**CV 宽是随机相位统计稳态的结构签名。**
- **AS-8（must_not）**：峰位落在 c/2L = 用了自由-自由 BC（退化）。**峰位是结构量（本征值），不是拟合值。**
  ★ **诚实局限（r2-H1'）**：加 1f+2f 偏置后 14 kHz 处**两种 BC 都有峰**，峰位单读数不足以定 BC——
  本断言只验「无谐波理想扫频」下的峰位；真实定 BC 需模式形状 / 多点测振。**不假装此断言覆盖了它。**

### Gate 0（极限对拍，最先跑，纯数学）
配方逐字见 `equations[(7)].numerical_notes`：① 单碰撞 v_out=(1+e)w+e·u 解析精确；② A→0 扫一串单调趋 0（∝A²）；
③ e→1 扫一串单调增；④ Lyapunov 可积对拍（固定相位 λ=ln e<0 vs 真混沌 λ>0）。**扫一串看单调**，不取单点。

### 收敛门（在扫描端点上做）
样本 n×2 + 换初相 φ0，在扫描端点 A_low / A_high 各测 h̄ 漂移 <5%。**不只在基准点。**
