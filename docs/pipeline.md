# IYPT 流水线：编排、工作区与交接契约

这份文档是四个 skill 的**单一事实源**。任何 skill 想改动产出文件的位置或格式，改这里，然后同步改 skill。

## 1. 四个 skill 与编排顺序

| Skill | 名称 | 职责 | 状态 |
|---|---|---|---|
| 1 | `iypt-analysis` | 补全题目设定 → 假设台账 → 量纲分析 → 机制预算 → 分层推导 → 可证伪预测 | ✅ 已实现 |
| 1R | `iypt-physics-review` | 对抗式物理审稿（Skill 1 内置调用，也可单独调用） | ✅ 已实现 |
| 2 | `iypt-simulation` | 数值解、验证、可视化（Python / JS 动态页面；MATLAB 为带自检的移植） | ✅ 已实现 |
| 3 | `iypt-slides` | 生成 Physics Fight 用的 PPT | 🚧 未实现 |
| 4 | `iypt-design-review` | 可视化与 PPT 的美观度 / 可读性审查（14 条失败模式） | ✅ 已实现 |

编排：

```
        Skill 1 ⇄ Skill 1R        （内置循环，最多 3 轮；不通过则诚实标注 [GAP]）
              ↓  handoff/model-spec.json
        Skill 2 ⇄ Skill 4         （每个图 / 每个动画迭代到通过）
         │    ↓  02-sim/results.json
         │  Skill 3 ⇄ Skill 4     （每版 PPT 迭代到通过）
         │    ↓  03-slides/
         │
         └──► 反向边：数值结果打脸模型时，回送 Skill 1 修订（§5，最多 2 轮）
```

**为什么必须按序**：Skill 2 画什么图不是它自己决定的，是 Skill 1 在 `figures[]` 里指定的（含**预期定性形状**，这既是任务书也是验收标准）。Skill 3 讲什么故事也不是它自己编的，是 Skill 1 的 `targets[]` + `predictions` 决定的。跳过 Skill 1 直接做图，做出来的是"好看的装饰"，不是"论证"。

**为什么需要反向边**：曲线与 `expected_shape` 矛盾时，能改的只有三样东西——代码（合法）、图（**明令禁止**）、模型（是 Skill 1 的产物，Skill 2 无权改）。当极限对拍已经证明代码是对的、曲线却仍然不符，Skill 2 就被逼到墙角了。**一个被逼到墙角又必须交差的 agent 会走那扇焊死的门**，只是走得体面：截掉 x 轴、把偏差说成"数值噪声"、把容差从 5% 放宽到 20%。所以必须给它一条合法的退路——§5。

## 2. 工作区约定

每道题一个工作区，默认建在**当前项目根目录**下：

```
iypt/<problem-slug>/
├── 00-problem.md            # 原题（逐字） + 题型判定 + 设定书 Specification Sheet
├── 01-analysis.md           # ★ Skill 1 主交付物：完整物理分析
├── 01-review-r1.md          # 第 1 轮审稿报告（Skill 1R 产出）
├── 01-review-r2.md          # …每轮一份，保留全部历史，不覆盖
├── handoff/
│   ├── model-spec.json      # ★ Skill 1 → Skill 2 的机器可读契约（始终是当前版本）
│   └── model-spec-r1.json   # 被反向边修订前的历史版本（§5，不覆盖）
├── 02-sim/                  # Skill 2 产出
│   ├── acceptance.md        # ★ 验收断言：expected_shape 的机械可判翻译（写代码前先写它）
│   ├── code/                #   Python 源码 + matlab/（带自检的移植）
│   ├── figures/             #   静态图（PNG/SVG）
│   ├── interactive/         #   JS/HTML/CSS 动态页面（自包含单文件）
│   ├── model-challenge-r1.md #  反向边的证据包（§5，仅在触发时产出）
│   └── results.json         #   ★ Skill 2 → Skill 3 的机器可读契约
└── 03-slides/               # Skill 3 产出
```

`<problem-slug>` 用英文小写连字符，如 `magnetic-brake`、`bouncing-drop`。

**不覆盖原则**：审稿报告、model-spec 的历史版本、challenge 报告，一律按轮次编号累加。**"模型被改了几次、每次改向哪"必须是可见的**——这是 §5 防捏合的物证。

## 3. 交接契约：`handoff/model-spec.json`

Skill 1 → Skill 2 的**唯一**接口。Skill 2 不应该去读 `01-analysis.md` 里的散文来猜要算什么——它读这个 JSON 就够。**如果 JSON 里的信息不够，那是 Skill 1 的缺陷，报 `SPEC-DEFECT`（§5），不是去散文里找补。**

Schema 在 `skills/iypt-analysis/templates/model-spec.schema.json`，顶层字段：

| 字段 | 含义 | 谁消费 |
|---|---|---|
| `problem` | slug、标题、原题、题型 | 2, 3 |
| `symbols[]` | 符号表：符号、含义、SI 单位 | 2, 3 |
| `parameters[]` | 每个参数的基准值、单位、**扫描范围**、来源（`setting` / `literature` / `derived`） | 2 |
| `assumptions[]` | 假设台账：陈述、成立判据（不等式）、分级 `SAFE`/`LOAD-BEARING`/`RISKY` | 2, 3 |
| `equations[]` | 待求解的方程：LaTeX + 可执行形式、初边条件、建议数值方法、**极限对拍配方** | 2 |
| `targets[]` | 目标量：符号、含义、**解析预测值/表达式**（用于对拍数值结果） | 2, 3 |
| `figures[]` | 期望图：x 轴、y 轴、系列、类型、**`expected_shape` 预期定性形状** | 2, 4 |
| `risky_assumption_checks[]` | 每条 `RISKY` 假设对应的数值验证任务 + `pass_criterion` | 2 |
| `open_gaps[]` | Skill 1 未闭合的问题（审稿 3 轮未通过时非空） | 2, 3 |

三条硬约束：

- **每条 `RISKY` 假设必须在 `risky_assumption_checks[]` 里有对应条目。** 这是 `check_analysis.py` 会机械检查的——把"这个简化到底成不成立"从口头承诺变成 Skill 2 必须跑的数值任务。
- **每张图必须写 `expected_shape`。** Skill 2 算出来的曲线如果和它矛盾，不是把图改好看，是回头查模型或查代码。图是用来证伪的，不是用来配色的。
- **`equations[].numerical_notes` 里应当写出一个极限对拍**：数值解在某个极限下必须回到闭式解。这是 Skill 2 的 **Gate 0**——它把"代码对不对"和"物理对不对"解耦。**配方必须完整**：写清楚哪些量趋于什么、哪些量保持固定。

  > 血泪教训：magnetic-brake 的原始配方写的是"令 $L\to0$ 且保持 $m$ 固定（退化为点偶极子）、同时令 $w\to0$"。照做，比值收敛到 **3.55 而不是 1**——因为只让 $L\to0$ 而 $R$ 保持 5 mm，得到的是一个半径 5 mm 的**薄圆盘**，在 $r=a=6$ mm 处它根本不是点偶极子。点偶极子极限要求**整个磁体**相对 $a$ 缩小，$R$ 和 $L$ 必须一起趋于 0。Gate 0 在第一次运行就抓到了这个缺陷。

### `pass_criterion` 里可以（并且应该）预先注册应对动作

`risky_assumption_checks[].pass_criterion` 不只可以写"什么算通过"，还可以写**"如果不通过，该怎么办"**：

> A-1 的实例："若 $|k-4| > 0.3$，则 P5 被数值判定为不可靠，**必须在 `01-analysis.md` 的预测表中把 P5 降级并说明**。"

**这是预注册（pre-registration），是最高标准。** 应对动作在数据出现之前就写死了，因此后续执行它**不构成事后合理化**——见 §5 的 `PRESCRIBED-REVISION`。鼓励 Skill 1 尽量这么写。

## 4. 交接契约：`02-sim/results.json`

Skill 2 → Skill 3 的**唯一**接口。Schema 在 `skills/iypt-simulation/templates/results.schema.json`。

| 字段 | 含义 |
|---|---|
| `status` | `PASS` / `PRESCRIBED-REVISION` / `MODEL-CHALLENGED` / `SPEC-DEFECT` / `FAIL-CODE`（见 §5） |
| `gates[]` | 每道验证门的记录：Gate 0 极限对拍、收敛门、分层对拍、解析对拍 |
| `assertions[]` | 每条断言：来源（哪个 figure / target / risky check）、`expect`、`measured`、`verdict` |
| `targets[]` | 每个目标量的数值 + 与 `analytical_prediction` 的相对偏差 |
| `figures[]` | 每张图的产出路径 + 对应的断言 id + 判定 |
| `risky_checks[]` | 每条 RISKY 验证任务的结果 + 是否满足 `pass_criterion` |
| `matlab_port` | `{ "verified": false, ... }` —— **诚实标注：移植版未在本机执行** |

硬约束：

- **不许有"未评估"的断言。** 每条断言必须有 `measured` 和 `verdict`。跳过 = 契约违约。
- **每张图必须盖 `SIMULATION` 戳**（§7 的底线）。`check_sim.py` 机械验证这一条。
- **`results.json` 只能由 Python 产生。** MATLAB 是移植版，`verified: false`，附 `verify.m` 供用户在自己机器上自验。

## 5. 反向边：数值结果打脸模型时

Skill 2 跑完，结果分五类。**分类不是自由裁量——判定规则在写代码之前就定死。**

| status | 什么情况 | 谁的问题 | 怎么办 |
|---|---|---|---|
| `PASS` | 全部断言通过，没触发任何预注册分支 | — | 交给 Skill 3 |
| `FAIL-CODE` | **Gate 0 极限对拍不过** / `must_not` 断言被触发（"符得太好"）/ 收敛门不过 | **代码** | 不许交付。回去改代码。 |
| `SPEC-DEFECT` | 契约本身有毛病：极限对拍配方在数学上不可能成立、`expected_shape` 自相矛盾、参数缺单位 | **文档** | 修契约，重跑。**不需要重跑物理审稿**——物理没错，是文档写错了。 |
| `PRESCRIBED-REVISION` | 命中了 Skill 1 在 `pass_criterion` 里**预先注册**的分支 | — （这是好事） | 照它写的动作执行。**不走审稿循环**。 |
| `MODEL-CHALLENGED` | Gate 0 已过（代码被证明对），但某条 Skill 1 承诺过的断言被违反，且**无**预注册应对 | **物理** | 走反向边（下文）。 |

### 5.1 `FAIL-CODE` 与 `MODEL-CHALLENGED` 靠 Gate 0 分开

**Gate 0（极限对拍）是纯数学恒等式，与物理对错无关。** 它不过 → 一定是代码错。它过了 → 代码被证明是对的，此后任何不符都指向物理。

**没有 Gate 0，后面每一个不符都是糊涂账**——你永远不知道该改代码还是改模型，于是你会改图。

### 5.2 `SPEC-DEFECT` 与 `MODEL-CHALLENGED` 靠这条线分开

> **如果你必须引用仿真数字才能说明"契约写错了"，那它就不是 `SPEC-DEFECT`——它是模型被数据打脸了。**

`SPEC-DEFECT` 的门槛：**你能在不看任何仿真结果的情况下证明契约有毛病**（文档自相矛盾、配方在数学上不可能、单位缺失）。

这条线必须画死，否则它就是一个**逃生舱**：任何一个不想面对"我的模型错了"的 agent，都可以把它重新描述成"哦，`expected_shape` 只是措辞不当，我改改措辞"，然后从便宜的门溜走。

### 5.3 `MODEL-CHALLENGED` 的处理：自动回环 + 防捏合护栏

**触发条件**：Gate 0 通过 **且** 存在 `FAIL-MODEL` 判定的断言 **且** 无预注册应对。

**动作**：

1. **归档** `handoff/model-spec-r{n}.json`（修订前的版本，不覆盖）
2. **写证据包** `02-sim/model-challenge-r{n}.md`：
   - 哪条断言被违反；Skill 1 **逐字**承诺的是什么；实测是什么
   - **Gate 0 的通过记录**——这是"不是我代码错"的举证责任
   - 收敛门记录——排除"网格太粗"
   - 复现脚本（一条命令重现这个数字）
3. `results.json` 标 `status: MODEL-CHALLENGED`
4. 自动派 agent 调 `iypt-analysis` 修订

**给修订 agent 的铁律（这是护栏的全部）**：

- **修订必须指向一个物理理由**——漏了一项 / 符号错 / 边界条件错 / 某条假设崩得比预想更厉害。**"为了和数值吻合"不是理由。**
- **单向棘轮：修订只能让预测变弱**（加适用条件、缩小适用域、降级），**不能凭空变强**。
- **新的 `expected_shape` 必须能从修订后的模型独立推导出来**，推导要写进 `01-analysis.md`。
  > **若新的 `expected_shape` 恰好就等于数值结果，那它不是预测，是事后拟合。**
- 修订后必须重跑 `check_analysis.py` + **重过 Skill 1R 审稿**，且审稿 prompt 额外告知："**这次修订是被数值结果逼出来的，请重点查 P16（事后合理化）**"。

**上限 2 轮。** （Skill 1 内部已有 3 轮审稿循环，再套 2 轮回环 = 最多 6 轮审稿 + 3 次仿真，够了。）超限 → `01-analysis.md` 文首 `[GAP]` + `model-spec.json` 的 `open_gaps[]` + `results.json` 的 `status: GAP`，照 Skill 1 的 Stage 8.4 诚实弃权。

> **一个知道自己哪里有洞的分析，比一个假装没洞的分析强得多。**

### 5.4 `PRESCRIBED-REVISION`：预注册过的，不算作弊

Skill 1 在 `pass_criterion` 里写死了"若 X 则做 Y"，现在 X 成立了 —— **照做 Y，不走审稿循环**。

**为什么它豁免**：Y 是在数据出现**之前**写下的。执行一条预注册的应对动作，与"看到数据之后编一个应对动作"是完全不同的两件事——前者是临床试验的金标准，后者是 P16。

**但仍然要留痕**：归档 `model-spec-r{n}.json`，并在 `01-analysis.md` 的修订说明里指明"这是 A-x 的 `pass_criterion` 预先注册的动作，触发条件 X 实测为 …"。

## 6. Skill 3/4 的接口预留（未实现，先定死）

- **Skill 3 输入**：`01-analysis.md` + `02-sim/results.json` + `02-sim/figures/`。**输出**：`03-slides/`。
- **Skill 4 输入**：`02-sim/` 或 `03-slides/` 的具体产物。**输出**：`0X-design-review-r{n}.md`，判定 `PASS` / `REVISE` + 逐条问题。它只管**美观度与可读性**，物理正确性归 Skill 1R 管，数值正确性归 Skill 2 的验证阶梯管。

## 7. 与真实 IYPT 的差异（必须诚实标注）

真实 IYPT 的评分里**实验占很大权重**，且要求真实动手实验。这套流水线用**数值仿真**替代实验，这不是等价物：

- Skill 1 产出的 `01-analysis.md` **仍然要写出可执行的实验方案**（器材、测量方法、误差来源），供人真正去做。
- Skill 2 的仿真结果在图上和 PPT 中必须**明确标注为仿真**，不得伪装成实验数据。**这是底线，`check_sim.py` 机械检查它。**

> **仿真验证"方程解对了"，实验验证"方程写对了"。只有实验能证伪模型。**
