---
name: iypt-slides
description: >-
  把 Skill 2 的 results.json 变成一份 Physics Fight 用的幻灯片 —— 而且是一份**不可能撒谎**的幻灯片。
  核心不是"排版"是"溯源"：PPT 上凡是来自仿真的数字，一律写指针 {{assertions.AS-8.measured|.2f}}，
  **不许手打字面值** —— 渲染时从 results.json 取值代入，于是数字漂移在结构上不可能发生。
  被证伪的断言必须出现在 deck 里（否则 FALSIFIED-DROPPED），status 不是 PASS 必须有「模型边界」一节，
  「这是仿真不是实验」这句话由渲染器写死（作者改不了措辞）。产出自包含 slides.html + 每页 PNG
  （供 iypt-design-review 用眼睛看）+ deck.pdf（上赛场）+ 讲稿。文字溢出/字号/密度在 headless
  浏览器里机械量。当被要求为 IYPT 题目做 PPT/幻灯片/报告，或工作区里已有 02-sim/results.json 时使用。
version: 0.1.0
---

# IYPT 幻灯片

## 这个 skill 到底在解决什么

一份 PPT 有三种腐烂方式，而**三种都不会让任何东西报错**：

1. **数字悄悄漂了。** 仿真重跑，指数从 3.44 变成 3.51 —— PPT 上还写着 3.44。
   **没人会发现，因为没有任何东西把它们绑在一起。**
2. **只报好消息。** 六条断言过了四条，PPT 上讲那四条。
   **剩下两条不是「没讲」，是「被消失」了。** 而 IYPT 的 Opponent 专门找这个。
3. **仿真被讲成了实验。** 一个词的事：「实测」→「实验测得」。
   在 Physics Fight 上，这是学术不端，不是笔误。

**这三样都不是「粗心」—— 它们是一个必须交差的 agent 的最优策略。**

所以对策不能是提醒（劝诫会被忽略），甚至不能只是检查。**只能是「结构上做不到」**：

| 病 | 药 | 为什么它治得住 |
|---|---|---|
| 数字漂移 | **数字不许手打，只许写指针** | `deck.json` 里**根本没有那个数字**。仿真一重跑，幻灯片跟着变 —— **而不是变成一个谎** |
| 选择性汇报 | 被证伪的断言**必须**在 deck 里出现 | `FALSIFIED-DROPPED` 是 ERROR |
| 冒充实验 | 披露语句**由渲染器写死** | 你只能决定它出现在哪一页，**不能决定它说什么** |

> **文档里的劝诫会被忽略；机械检查不会。而「根本没有那个入口」比机械检查还硬。**

---

# 工作流

工作区 `iypt/<problem-slug>/`，产物路径见 `docs/pipeline.md` §2。

## Stage 0 · 读契约，不读散文

**主输入是 `02-sim/results.json`。** 它是自足的 —— 参数、物理本质、假设台账、
任务、断言、图、验证、status，全在里面。

**如果它不够你做出 PPT，那是 `results.json` 的缺陷** —— 回去让 Skill 2 补，
不要跑到 `01-analysis.md` 里找补。（`check_sim.py` 的 `PASSTHROUGH-MISSING`
就是为这个而设的：**去散文里找补，等于替上游掩盖了一个契约漏洞，下一道题它还会犯。**）

`01-analysis.md` 只在一个地方需要：**附录的实验方案**。

读完先打印一份清单：

```
status:                  ← ★ 不是 PASS？那 PPT 里**必须**有 boundary 一节
essence.one_sentence:    ← ★ 定性分析页的核心。**它同时决定了讲故事的骨架**
tasks_answered:      T 条 ← ★ 每条都要有主线页挂在它上面，且总结页逐条打勾
assertions:          N 条（其中 FAIL-MODEL / PRESCRIBED 的有几条？**它们必须上台面**）
risky_checks:        J 条（holds == false 的有几条？**同上**）
figures:             K 张（每张都有 caption —— 那是「这张图**证明了什么**」）
validation_checks:   V 条 ← ★ 中间量验证。**IYPT 的分数在这里**
duration_budget:     720 s（IYPT Reporter = 12 分钟）
```

## Stage 1 · 先定骨架（读 `references/deck-skeleton.md`）

**别一上来就写页。** 先把六节骨架填出来，每节写一句话。

**读 `references/deck-skeleton.md`** —— 它是从 13 份真实 IYPT 报告里抽出来的，
但**第 2 / 4 节必须改名**：这条流水线用数值仿真替代实验（`pipeline.md` §7），
**我们没有「预实验」，也没有「实验探究」**。

## Stage 2 · 写 `03-slides/deck.json`

Schema 在 `templates/deck.schema.json`。**你写的是内容 + 溯源指针，不是 HTML。**

### ★★ 铁律：数字不许手打

```json
✗  "text": "有限长磁体给出的指数是 3.44"
✓  "text": "有限长磁体给出的指数是 {{assertions.AS-8.measured|.2f}}"
```

第二种写法里，**3.44 这个数字在 `deck.json` 里根本不存在**。渲染时从 `results.json` 取出来代入。

于是：

- 仿真重跑、数字变了 → 幻灯片**自动跟着变**（而不是变成一个谎）
- 想在 PPT 上写一个 `results.json` 里没有的数 → **你做不到**

`check_slides.py` 的 **`NUM-UNCITED`**：正文里出现任何**带小数点 / 百分号 / 科学计数**的数字，
而没被 `{{}}` 包住 → **ERROR**。

> 整数（`1024/45`、`Model-0`、`12 分钟`、`5 组`）不管 —— 那是**定义或计数**，不是测量。
> **带小数点的数字，你不可能是「随口一说」。**

格式串是 Python 的 format spec，外加两条缩放（`results.json` 里一切都是 SI）：

```
{{parameters.a.value|1e3*.0f}}            -> 6         （m -> mm）
{{targets.v_t.value_numeric|100*.2f}}     -> 5.01      （m/s -> cm/s）
{{targets.v_t.relative_deviation|%+.1f}}  -> +82.7%    （分数 -> 百分数）
```

### 阈值怎么办：**行内引文**

契约里有一类数字**只以散文形式存在**，没有字段可指：

> 「若 |k-4| > **0.3**，则 P5 降级」（在 `pass_criterion` 这句话里）
> 「管壁误差必须 > **50%**」（在 `expect` 里）

只有「取值」一种模式的话，你面对这些数字只有两条路：**手打**（谎的种子），
或者**把它们从文案里删掉**（文案就废了）。**一个逼着人绕过它的机制，最后一定会被绕过。**

所以给一条合法的、但同样堵死了造假的路 —— **写出那个数，但指出它在契约的哪句话里，且必须一字不差**：

```json
"text": "判据是 {{|k-4| > 0.3 @ risky_checks.A-1.quoted_pass_criterion}}"
```

`check_slides.py` 校验 `0.3` 确实是那句话的**逐字子串**。
**它无法被滥用来编造一个数字 —— 编的数字不可能是原文的子串。**

（这就是 `check_sim.py` 的 `quoted_expectation`，做成了行内的。）

### 图注：**不填是最安全的**

```json
"figure": { "figure_id": "F-2" }
```

不写 `caption`，渲染时**整段**取 `results.json` 的 `figures[F-2].caption`。

**`caption` 写的是「这张图证明了什么」，不是「展示了什么」—— Skill 2 已经把最难的那句话写好了。直接用。**

真要缩短可以填，但会校验它是原文的**逐字子串**（`CAPTION-DRIFT`）。
**你只能删字，不能改字** —— 一改字，走样的方向永远是对自己有利的。

### 每页一个 `takeaway`，而且必须是一个**判断**

```
✓ 「v_t ∝ a⁴ 站不住：指数是 {{assertions.AS-8.measured|.2f}}，不是 {{assertions.AS-7.measured|.2f}}」
✗ 「终速的标度律」
```

**说不出这一句 = 这一页不知道自己为什么存在。**
**一页只能有一个 takeaway。有两个 = 该拆成两页。**

## Stage 3 · 构建

```bash
python 03-slides/build.py
```

产出：`slides.html`（自包含）、`png/S-xx.png`（**每页一张**）、`deck.pdf`、`script.md`。

**做不到「一条命令重现整份 PPT」= PPT 和数据已经脱钩了。**

## Stage 4 · 机械检查

```bash
python <skill_dir>/scripts/check_slides.py iypt/<problem-slug>
```

**ERROR 必须清零。**

| 组 | 门 |
|---|---|
| **溯源** | `NUM-UNCITED`（数字手打）、`SRC-DANGLING`（指针解析不到）、`QUOTE-DRIFT` / `INLINE-QUOTE-DRIFT`（引文不是逐字）、`CAPTION-DRIFT` |
| **诚实** | `FALSIFIED-DROPPED`（**选择性汇报**）、`STATUS-HIDDEN`、`DISCLOSURE-MISSING`、`FAKE-EXPERIMENT`、`TASK-UNCOVERED`、`FIG-UNKNOWN` |
| **渲染后** | `OVERFLOW` / `OVERSET`（**在浏览器里量包围盒**）、`TOO-DENSE`、`FONT-SMALL`、`TIME-OVER` |

## Stage 5 · ★ 用眼睛看

```
Read 03-slides/png/S-01.png
Read 03-slides/png/S-02.png
…
```

**一页一页看。** 这是 `iypt-design-review` 的**铁律 0**：

> **你会脑补出一份比实际渲染出来的更好看的幻灯片。读代码猜排版 = 没审。**

机械检查查得了溢出、字号、密度。**它查不了「哪个元素压住了哪个数据」。**

> **实测（就在做这份 skill 的时候）**：F-5 的静态图，第一版两个标注框的箭头**全指向空白处**
> —— 因为我"知道"峰在哪儿，所以看图时看见的是"数据 + 两个有用的框"，
> 而不是"两个框，底下什么都没有"。**第二版又把两个标签叠成了一团糊字。**
>
> **同一个坑，一天之内，在同一张图上踩了三次 —— 而每一次都是靠「真的看了一眼」才发现的。**

然后走 `iypt-design-review`（D1–D16 + S1–S10），迭代到 PASS。**最多 3 轮。**

## Stage 6 · 注入式冒烟测试

**你怎么知道你那些门不是摆设？** 往 `deck.json` 里**故意注入错误**，看抓不抓得到：

```bash
python 03-slides/smoke_test.py
```

| 注入 | 应该被哪道门抓到 |
|---|---|
| 手打一个数（3.44 → 3.5） | `NUM-UNCITED` |
| 指针指向不存在的断言 | `SRC-DANGLING` |
| **悄悄删掉「A-1 崩了」那一页（只报好消息）** | **`FALSIFIED-DROPPED`** |
| 图注改一个词 | `CAPTION-DRIFT` |
| 往某页塞 300 字 | `OVERSET` / `TOO-DENSE` |
| 夹带一张不在 results.json 里的图 | `FIG-UNKNOWN` |
| 把「仿真」写成「实验测得」 | `FAKE-EXPERIMENT` |

**任何一个没被抓到，那道门就是摆设，必须重新设计。**
**顺带必须验证：基线（无注入）不被任何门误报。会误报的门比没有门更糟。**

---

## 完成的标准

不是"PPT 很好看"，是这九件事都做到了：

1. **★ PPT 上没有一个手打的数字。** 每个数字要么是指针，要么是契约原文的逐字子串。
2. **★ 被证伪 / 被降级的东西，全部在主线里出现过。** 没有一条被"消失"。
3. **★ 有一页明确声明「这是仿真，不是实验」**，而且措辞不是你写的。
4. **★ 每张图都是 `results.json` 里的图** —— 没有夹带任何"好看的示意图"。
5. **★ 每条 task 都有主线页挂着**，且总结页**逐条打勾**（真实报告的最后一页就是这张表）。
6. **`status` 不是 `PASS` 时，有 `boundary` 一节**，而且讲清了**边界在哪**。
7. **主线讲得完** —— `duration_s` 之和 ≤ 12 分钟。
8. **一条命令能重现整份 PPT。**
9. **★ 每一页你都真的用眼睛看过**，并且过了 `iypt-design-review`。

## 常见的自我背叛

- **★ 手打数字，然后"事后核对一遍"。** 你不会核的。**而且核对是弱的：写指针才是强的 ——
  它让漂移在结构上不可能发生。**
- **★ 只讲通过了的断言。** 一份只报好消息的 PPT，读起来和一份全部通过的 PPT **一模一样** ——
  **这就是它危险的原因。** 而 Opponent 专门找这个，一找一个准。
- **★ 把 `PRESCRIBED` / `MODEL-CHALLENGED` 当成"没发生"。** 恰恰相反：
  **一个标出了 RISKY 假设、并且用数值把它打崩了的报告，说明模型边界被正确定位了 —— 这是加分项。**
  **藏起来的 RISKY 才是被一击致命的那个。**
- **★ 把仿真说成实验。** 「实测」可以（这是"数值上测到的"），「**实验测得**」不行。
  **仿真验证「方程解对了」，实验验证「方程写对了」。只有实验能证伪模型。**
- **★ 把 `figures[].caption` 重写一遍。** 那句话是 Skill 2 花了最大力气写的
  （「这张图**证明了什么**」）。**你一改，就只会更弱、更含糊、更对自己有利。**
- **takeaway 写成名词。** 「终速的标度律」不是一句话，是一个题目。
  **说不出判断，就是还没想清楚这一页要干什么。**
- **一页塞三个论点。** 观众只能带走一个。**你不选，他们就随机选一个。**
- **12 分钟讲 40 页。** 每页 18 秒 —— **结论页永远讲不到。**
- **★ 只跑了 `check_slides.py` 就交付。** 它查得了溢出和字号，**查不了「哪个框压住了哪个峰」**。
  **必须 Read 每一页 PNG，用眼睛看。**
