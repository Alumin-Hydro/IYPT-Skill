# IYPT 流水线：编排、工作区与交接契约

这份文档是四个 skill 的**单一事实源**。任何 skill 想改动产出文件的位置或格式，改这里，然后同步改 skill。

## 1. 四个 skill 与编排顺序

| Skill | 名称 | 职责 | 状态 |
|---|---|---|---|
| 1 | `iypt-analysis` | 补全题目设定 → 假设台账 → 量纲分析 → 机制预算 → 分层推导 → 可证伪预测 | ✅ 已实现 |
| 1R | `iypt-physics-review` | 对抗式物理审稿（Skill 1 内置调用，也可单独调用） | ✅ 已实现 |
| 2 | `iypt-simulation` | 数值解、仿真、可视化（Python / MATLAB / JS+HTML+CSS 动态页面） | 🚧 未实现 |
| 3 | `iypt-slides` | 生成 Physics Fight 用的 PPT | 🚧 未实现 |
| 4 | `iypt-design-review` | 可视化与 PPT 的美观度 / 可读性审查 | 🚧 未实现 |

编排：

```
Skill 1 ⇄ Skill 1R   （内置循环，最多 3 轮；不通过则诚实标注 [GAP]）
        ↓  handoff/model-spec.json
Skill 2 ⇄ Skill 4    （每个图 / 每个动画迭代到通过）
        ↓  02-sim/
Skill 3 ⇄ Skill 4    （每版 PPT 迭代到通过）
        ↓  03-slides/
```

**为什么必须按序**：Skill 2 画什么图不是它自己决定的，是 Skill 1 在 `figures[]` 里指定的（含**预期定性形状**，这既是任务书也是验收标准）。Skill 3 讲什么故事也不是它自己编的，是 Skill 1 的 `targets[]` + `predictions` 决定的。跳过 Skill 1 直接做图，做出来的是"好看的装饰"，不是"论证"。

## 2. 工作区约定

每道题一个工作区，默认建在**当前项目根目录**下：

```
iypt/<problem-slug>/
├── 00-problem.md            # 原题（逐字） + 题型判定 + 设定书 Specification Sheet
├── 01-analysis.md           # ★ Skill 1 主交付物：完整物理分析
├── 01-review-r1.md          # 第 1 轮审稿报告（Skill 1R 产出）
├── 01-review-r2.md          # …每轮一份，保留全部历史，不覆盖
├── handoff/
│   └── model-spec.json      # ★ Skill 1 → Skill 2 的机器可读契约
├── 02-sim/                  # Skill 2 产出
│   ├── code/                #   Python / MATLAB 源码
│   ├── figures/             #   静态图（PNG/SVG）
│   ├── interactive/         #   JS/HTML/CSS 动态页面
│   └── results.json         #   数值结果，回填给 Skill 3 引用
└── 03-slides/               # Skill 3 产出
```

`<problem-slug>` 用英文小写连字符，如 `magnetic-brake`、`bouncing-drop`。

## 3. 交接契约：`handoff/model-spec.json`

Skill 1 → Skill 2 的**唯一**接口。Skill 2 不应该去读 `01-analysis.md` 里的散文来猜要算什么——它读这个 JSON 就够。

Schema 在 `skills/iypt-analysis/templates/model-spec.schema.json`，顶层字段：

| 字段 | 含义 | 谁消费 |
|---|---|---|
| `problem` | slug、标题、原题、题型 | 2, 3 |
| `symbols[]` | 符号表：符号、含义、SI 单位 | 2, 3 |
| `parameters[]` | 每个参数的基准值、单位、**扫描范围**、来源（`setting` / `literature` / `derived`） | 2 |
| `assumptions[]` | 假设台账：陈述、成立判据（不等式）、分级 `SAFE`/`LOAD-BEARING`/`RISKY` | 2, 3 |
| `equations[]` | 待求解的方程：LaTeX + 可执行形式、初边条件、建议数值方法 | 2 |
| `targets[]` | 目标量：符号、含义、**解析预测值/表达式**（用于对拍数值结果） | 2, 3 |
| `figures[]` | 期望图：x 轴、y 轴、系列、类型、**`expected_shape` 预期定性形状** | 2, 4 |
| `risky_assumption_checks[]` | 每条 `RISKY` 假设对应的数值验证任务 | 2 |
| `open_gaps[]` | Skill 1 未闭合的问题（审稿 3 轮未通过时非空） | 2, 3 |

两条硬约束：

- **每条 `RISKY` 假设必须在 `risky_assumption_checks[]` 里有对应条目。** 这是 `check_analysis.py` 会机械检查的——把"这个简化到底成不成立"从口头承诺变成 Skill 2 必须跑的数值任务。
- **每张图必须写 `expected_shape`。** Skill 2 算出来的曲线如果和它矛盾，不是把图改好看，是回头查模型或查代码。图是用来证伪的，不是用来配色的。

## 4. Skill 2/3/4 的接口预留（未实现，先定死）

- **Skill 2 输入**：`handoff/model-spec.json`。**输出**：`02-sim/`，并写 `02-sim/results.json`（每个 `target` 的数值结果 + 与解析预测的相对偏差 + 每个 `figure` 的产出路径）。
- **Skill 3 输入**：`01-analysis.md` + `02-sim/results.json` + `02-sim/figures/`。**输出**：`03-slides/`。
- **Skill 4 输入**：`02-sim/` 或 `03-slides/` 的具体产物。**输出**：`0X-design-review-r{n}.md`，判定 `PASS` / `REVISE` + 逐条问题。它只管**美观度与可读性**，物理正确性归 Skill 1R 管。

## 5. 与真实 IYPT 的差异（必须诚实标注）

真实 IYPT 的评分里**实验占很大权重**，且要求真实动手实验。这套流水线用**数值仿真**替代实验，这不是等价物：

- Skill 1 产出的 `01-analysis.md` **仍然要写出可执行的实验方案**（器材、测量方法、误差来源），供人真正去做。
- Skill 2 的仿真结果在 PPT 中必须**明确标注为仿真**，不得伪装成实验数据。这是底线。
