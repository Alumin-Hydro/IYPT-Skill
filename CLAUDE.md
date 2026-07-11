# IYPT-Skill

一套 Claude Code skill 流水线，让 Claude 按序完整攻下一道 IYPT 题。远端：https://github.com/Alumin-Hydro/IYPT-Skill（`main`，git 凭据已缓存可直接 push；本机**没有** gh CLI）。

```
Skill 1 (物理分析) ⇄ 审稿  →  Skill 2 (仿真/可视化) ⇄ Skill 4 (美学审查)  →  Skill 3 (PPT) ⇄ Skill 4
```

| Skill | 名称 | 状态 |
|---|---|---|
| 1 | `iypt-analysis` | ✅ |
| 1R | `iypt-physics-review` | ✅ |
| 2 | `iypt-simulation`（数值解、仿真、Python/MATLAB/JS 动态页面，注重美观） | 🚧 **下一个** |
| 3 | `iypt-slides` | 🚧 |
| 4 | `iypt-design-review` | 🚧 |

## 动手前先读

- **`docs/pipeline.md`** —— 工作区约定与四个 skill 的交接契约，**单一事实源**。改产出格式先改它。
- **`skills/iypt-analysis/templates/model-spec.schema.json`** —— Skill 1 → Skill 2 的唯一接口。
- **`examples/magnetic-brake/`** —— 一次真实跑通的完整产出，回归基线。

## 做 Skill 2 时的硬约束

Skill 2 读 `handoff/model-spec.json` 就够了，**不要去读散文猜要算什么**。

- 每张图的 `expected_shape` 是**验收标准**：算出来的曲线与它矛盾时，回头查模型或查代码，**不是把图改好看**。图是用来证伪的。
- 每条 `RISKY` 假设在 `risky_assumption_checks[]` 里都有一个数值验证任务，**必须跑**。
- `equations[].numerical_notes` 里通常写了一个"极限对拍"（数值解在某极限下必须回到闭式解）——**这是验证代码正确性的手段，先跑它再跑别的**。
- 仿真结果**必须标注为仿真**，绝不伪装成实验数据。

## 工程约定

- 输出：中文正文 + 英文物理术语 + LaTeX 公式。
- 联网查文献允许，但必须给引用，并严格区分"文献结论"与"自己推导"。
- 改完 Skill 1 相关的东西，跑 `python skills/iypt-analysis/scripts/check_analysis.py examples/magnetic-brake`，必须零 ERROR。
- Windows 注意：Python 从 stdin 读中文源码会按 GBK 解码而乱码——脚本写成文件再跑；控制台输出中文要 `sys.stdout.reconfigure(encoding="utf-8")`。
