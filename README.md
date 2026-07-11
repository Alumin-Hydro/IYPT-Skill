# IYPT-Skill

一套 Claude Code skill，让 Claude 按流水线完整攻下一道 IYPT（国际青年物理学家锦标赛）题目：

```
物理分析 ⇄ 对抗式审稿  →  仿真/可视化 ⇄ 美学审查  →  PPT ⇄ 美学审查
```

## 它解决什么问题

IYPT 的题目是**故意欠定的**——"Investigate the phenomenon and explain the dependence on relevant parameters"，不给几何、不给材料、不给参数范围。直接让模型"解这道题"，产出的东西通常有三种病：

1. **隐式假设**——用了"均匀磁化""准静态""小角近似"却从没说出口，也没说什么时候它会崩；
2. **口头忽略**——"空气阻力可忽略"，但没给任何数字证明它可忽略；
3. **脆弱结论**——结论其实高度依赖某个没被检验的简化，一旦对手（Opponent）问到就塌。

所以 `iypt-analysis` 的核心不是"解题"，而是**把欠定的题目补全成一个可证伪的物理问题**：先写「设定书」把题目没给的条件显式定死，再用「假设台账」把每条简化连同它的**不等式成立判据**和失效边界一起记账，再用「机制预算」强制每个"忽略"都必须给出数量级数字。写完之后，一个 **fresh-context 的对抗式审稿人**拿着一份具体的物理错误模式清单反复攻击它——不是泛泛地"检查一下对不对"。

## 安装

### 方式一：作为 plugin（推荐）

```
/plugin marketplace add Alumin-Hydro/IYPT-Skill
/plugin install iypt@iypt-skill
```

### 方式二：直接拷贝 skills 目录

```bash
git clone https://github.com/Alumin-Hydro/IYPT-Skill.git
cp -r IYPT-Skill/skills/* ~/.claude/skills/
```

两种方式共用同一份 `skills/` 文件。

## 用法

把题目原文丢给 Claude，让它跑分析：

```
用 iypt-analysis 分析这道题：
"A cylindrical magnet is dropped into a vertical conducting pipe. Investigate the
motion of the magnet and how the terminal velocity depends on relevant parameters."
```

它会在 `iypt/<problem-slug>/` 下产出：

| 文件 | 内容 |
|---|---|
| `00-problem.md` | 原题 + 题型判定 + **设定书**（把题目没给的条件全部定死） |
| `01-analysis.md` | **主交付物**：假设台账、量纲分析、机制预算、分层推导、可证伪预测、实验方案 |
| `01-review-r{n}.md` | 每一轮的对抗式审稿报告 |
| `handoff/model-spec.json` | 交给下游仿真的机器可读契约 |

分析写完后，Skill 1 会**自动**派一个 fresh-context 的审稿人来攻击它，按洞修订，最多 3 轮。3 轮还闭不上的窟窿，它会**诚实地在文首标注 `[GAP]`，而不是假装通过**。

单独复审一份已有的分析：

```
用 iypt-physics-review 审一下 iypt/magnetic-brake/01-analysis.md
```

## 包含的 skill

| Skill | 职责 | 状态 |
|---|---|---|
| `iypt-analysis` | 补全设定 → 假设台账 → 量纲分析 → 机制预算 → 分层推导 → 可证伪预测 | ✅ |
| `iypt-physics-review` | 对抗式物理审稿（15 条具体错误模式） | ✅ |
| `iypt-simulation` | 数值解、仿真、可视化（Python / MATLAB / JS 动态页面） | 🚧 |
| `iypt-slides` | Physics Fight 用的 PPT | 🚧 |
| `iypt-design-review` | 可视化与 PPT 的美观度审查 | 🚧 |

流水线的编排顺序、工作区约定和四个 skill 之间的交接契约见 [`docs/pipeline.md`](docs/pipeline.md)。

## 样例

`examples/magnetic-brake/` 是一次真实跑通的完整产出，可以直接当作参考基线。

## 一个诚实的说明

真实 IYPT 的评分中**实验占很大权重**，且必须真正动手做。这套流水线用**数值仿真**替代实验，两者不是等价物。因此：

- `01-analysis.md` 里仍然会写出**可执行的实验方案**（器材、测量方法、误差来源），供你真的去做；
- 仿真结果在 PPT 中必须**明确标注为仿真**，绝不伪装成实验数据。

## License

MIT
