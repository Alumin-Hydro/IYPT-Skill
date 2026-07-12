# IYPT-Skill

一套 Claude Code skill 流水线，让 Claude 按序完整攻下一道 IYPT 题。远端：https://github.com/Alumin-Hydro/IYPT-Skill（`main`，git 凭据已缓存可直接 push；本机**没有** gh CLI）。

```
Skill 1 (物理分析) ⇄ 审稿  →  Skill 2 (仿真/验证/可视化) ⇄ Skill 4 (美学审查)  →  Skill 3 (PPT) ⇄ Skill 4
                       ▲                    │
                       └────────────────────┘  反向边：数值打脸模型时回送修订（docs/pipeline.md §5）
```

| Skill | 名称 | 状态 |
|---|---|---|
| 1 | `iypt-analysis` | ✅ |
| 1R | `iypt-physics-review` | ✅（16 条错误模式） |
| 2 | `iypt-simulation` | ✅ |
| 3 | `iypt-slides` | 🚧 **下一个**（唯一还没做的） |
| 4 | `iypt-design-review` | ✅（14 条设计失败模式） |

## 动手前先读

- **`docs/pipeline.md`** —— 工作区约定、四个 skill 的交接契约、**反向边的五种 status**，**单一事实源**。改产出格式先改它。
- **`skills/iypt-analysis/templates/model-spec.schema.json`** —— Skill 1 → Skill 2 的接口。
- **`skills/iypt-simulation/templates/results.schema.json`** —— Skill 2 → Skill 3 的接口。
- **`examples/magnetic-brake/`** —— 一次真实跑通的完整产出，回归基线。**它把反向边完整走了一遍**：
  r1 运行判 `MODEL-CHALLENGED`（快照 `02-sim/results-r1.json` + `model-challenge-r1.md`）→ Skill 1 按
  **物理理由**修订（r2 修 3 处 SPEC-DEFECT；r3 修 A-2 的一阶系数漏了个 2）→ 重跑，现在是
  `PRESCRIBED-REVISION`（两条 RISKY 假设都**如预期地**不成立 —— 模型边界被正确定位）。
  **归档链 `model-spec-r1/r2.json` 是 P16（事后合理化）审稿的物证。**

## ★ 开发 skill 时的第一条铁律：**改 skill，不要只改这道题**

跑例子时踩到坑，**先问一句**：

> **这个坑是这道题特有的，还是任何题都会踩的？**

是后者 —— **改 skill，不许只在例子里修好就算完。**

**为什么这条必须写在最前面**：实际场景是**一个没有这段开发上下文的 Opus 4.8 + skill**。它不知道你在 magnetic-brake 里踩过什么、修过什么。**你在例子里修好而没回填进 skill 的东西，等于没修——下一道题它会一模一样地再踩一遍。**

每个坑要走完这三步：

1. **例子里修好**（证明修法可行）
2. **回填进 skill**：改 `SKILL.md` / `references/` / `templates/` / schema
3. **加机械检查**（能查就查）—— 写进 `check_analysis.py` / `check_sim.py`。
   > 文档里的劝诫会被忽略；**机械检查不会**。

## 从 13 份真实 IYPT 报告里学到的（`example-ppt/`）

6. **题目任务是「挖」出来的，不是「读」出来的。** 题面里每个限定词都是一条任务的种子：
   `"under certain conditions"` → **条件边界**（答案是**参数空间相图**，不是一条曲线）；
   `"can also exhibit other interesting behaviour"` → **模式分类**（→ 混沌、Lyapunov）。
   **而「混沌」两个字，题面里一个都没有。** 5/13 份报告有专门的「题目任务」页。
7. **因变量有三层，第三层「模式」是分水岭。** 标量 / 函数 / **模式**（周期-准周期-混沌、
   加速-减速-卡住、单稳-多稳）。新手把 "study the movement" 理解成「测 x(t) 然后拟合」。
8. **一句话的物理本质决定图的骨架。** 「磁势能向动能的**非对称转换**」⇒ 必须画势能景观；
   「**非线性多体耦合**」⇒ 必须画相图/频谱/Lyapunov。**说不出本质 = 不知道该画什么图。**
9. **仿真要验证「中间量」，不是验证最终结果。** 真题的做法是**拿高斯计去测 B 场**（链条中间
   的量），不是拿末速度去反证模型。**两个错误可以互相抵消。** 5/13 份报告有专门的模型验证节。

## 已经吃过的亏（别再踩）

1. **零号规则**：验证类 agent 会拿"自己重推的正确版本"替换掉"作者写的字"，从而对公然的错误失明。对策：**逐字抄写**被验对象的原文，并**机械校验引文是原文的子串**（`check_sim.py` 的 `quoted_expectation` 检查）。
2. **`must_not` 必须查「结构」，不能只查「拟合出来的数」。** 只少一个修正的 bug，会让拟合值落在"陷阱值"和"真值"**之间**，从两条断言中间溜走。要找那些在正确/退化模型下**离散地不同**的量（峰位、节点数、对称性）。
3. **收敛门要在扫描端点上做**，不能只在基准点做。绝对截断长度会在扫描的一端悄悄失效，而**斜率已经错了**。
4. **修订必须传播到「结论」和「契约」，不能只落在「推导」上。** 实测：审稿抓到的一个错误，修订只改了正文的推导，**漏掉了预测表和 model-spec.json**——而那两处恰恰是下游真正读的。**目前没有机械检查能发现这种脱钩。**
5. **`SPEC-DEFECT` 是个逃生舱，门槛必须画死**：**要引用仿真数字才能说明"契约写错了"的，一律不是 SPEC-DEFECT**，而是模型被数据打脸了。

## 做 Skill 3 时的硬约束

Skill 3 读 `01-analysis.md` + `02-sim/results.json` + `02-sim/figures/`。

- **`results.json` 里每个数字都有出处**（哪道门、哪条断言、哪次运行）。PPT 上引用的每个数字都必须能追回去。
- **`results.json` 的 `status` 不是 `PASS` 时，PPT 必须诚实反映**——`MODEL-CHALLENGED` 意味着某条结论已被数值证伪，不许当作没发生。
- **仿真结果必须标注为仿真**，绝不伪装成实验数据。这是底线。
- `figures[].caption` 写的是"这张图**证明了什么**"，不是"展示了什么"——直接用它。

## 工程约定

- 输出：中文正文 + 英文物理术语 + LaTeX 公式。**但图上的文字一律英文**（IYPT 是英文赛事，图直接进英文 PPT；而且 DejaVu Sans 没有中文字形，中文会渲染成豆腐块）。
- 联网查文献允许，但必须给引用，并严格区分"文献结论"与"自己推导"。
  **红线：不许去查"答案应该是多少"然后回来调代码去凑**——那是拟合，不是计算。
- 改完 Skill 1/2 相关的东西，跑：
  ```bash
  python skills/iypt-analysis/scripts/check_analysis.py examples/magnetic-brake   # 零 ERROR
  python skills/iypt-simulation/scripts/check_sim.py examples/magnetic-brake      # 零 ERROR
  python examples/magnetic-brake/02-sim/code/run_all.py                           # 一键复现
  python examples/magnetic-brake/02-sim/code/smoke_test.py                        # 四个注入全被抓到
  ```
- 环境：Python 3.12 + numpy/scipy/matplotlib，node v24。**没有 MATLAB/Octave**（所以 MATLAB 只做"带自检的移植"，`matlab_port.verified` 必须是 `false`）。**没有 ffmpeg**（动画走自包含 HTML）。
- Windows 注意：Python 从 stdin 读中文源码会按 GBK 解码而乱码——脚本写成文件再跑；控制台输出中文要 `sys.stdout.reconfigure(encoding="utf-8")`。
