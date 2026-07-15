# 审稿报告 · 第 7 轮

**判定**：**MAJOR**
**审稿人视角**：Opponent
**被审对象**：`01-analysis.md`（r7）、`handoff/model-spec.json`（r7，内嵌 `criterion_matrix`）、`01-criteria/criterion_matrix.py` + `matrix.json`、`00-problem.md`、**`skills/iypt-analysis/scripts/check_analysis.py`（r7 新增 `CRIT-MATRIX-DESYNC` 门 + `systematic_error_budget` 下限 + 元流程钉进文件头）**、**`skills/iypt-analysis/SKILL.md`**
**归档链**：`model-spec-r1..r4.json` → `model-spec.json`（P16 逐版可 diff）
**方法**：第 1.5 步先做（r6 的 H1–H4 逐条独立复核）；P1–P15 + P17 + P18 逐条，P17/P18 先查；P16 必查（归档链存在）。**每个反例都用运行代码证明**——直接 import `check_analysis`、调 `check_criterion_matrix` / `check_matrix_desync` / `check_prose_formula_values`，并把构造的工作区端到端喂进**真的** `check_analysis.py examples/…`。`--selftest` 全过、真实工作区 **0 ERROR**、`criterion_matrix.py` 重跑复现 delta_max=0.1344 mm——**第七轮了，而洞仍然不在物理里、在 r7 新写的机械化里。**

---

## 一句话结论

> **物理第七轮攻不动**（重跑 `criterion_matrix.py` 复现 delta_max=**0.1344 mm**、bracket [0.1328,0.1344]、安全裕度 **1.34×**、ε\*(bug-C)=**13%**、ε\*(bug-E)=**2%**，逐字自洽）。**r6 的四个洞（H1 内嵌脱钩 / H2 scan 无下限 / H3H4 措辞）全部修到位。**
> **但 r7 没收敛——这是 `CLAUDE.md` 教训 15/19/23 的第八次发作，两处 MAJOR：**
>
> **① `budget` 下限门（r6-H2 的修法）自己结构性失明，而且没有任何盲区探针覆盖它（真正的第八次复发）。** 门校验的是 `scan_upper_bound ≥ 3×budget`（**你扫得够不够远**），却**从不校验 `delta_max ≥ budget`（你找到的那道判死悬崖，在不在噪声够不到的地方）**。实测：一个 `delta_max=0.05 mm`（判死悬崖落在 §9 噪声 0.10 mm **以内**、安全裕度 **0.5×**、即**在实操里必然误杀正确模型**）的判据集，配一个合法窄 bracket，**check_analysis 0 ERROR，criterion_matrix.py 自己也 exit 0 报 verdict:PASS**（`bad` 从不读 `_margin`）。这道门守错了那个比值——P18① 的正脸：**那个被 prose 大书特书的「安全裕度 1.34×」，是一个 load-bearing 阈值，而它只活在散文里，没有门。** 而本题**已经贴在 1.34×**，离 1× 悬崖只有一步。
>
> **② `CRIT-MATRIX-DESYNC`（r6-H1 的修法）把「内嵌 ↔ matrix.json」栓住了，却没栓「matrix.json ↔ 源码 criterion_matrix.py 的新鲜输出」。** 实测：把源码 `criterion_matrix.py` **整个删掉** ⟹ 0 ERROR；把源码里 `GAMMA_OC 0.0413→0.0900`（重跑会翻掉整张表）**改掉但不重跑** ⟹ 0 ERROR。门从不读源码。作者把这声明成「已知局限，靠提交前重跑兜底」——但那句「重跑」**全仓库没有任何机械兜底**（无 build / 无 hook / 无 pre-commit，grep 为空），正是铁律「文档里的劝诫会被忽略」。作者把「恶意两处一起改」（确实要 subprocess，贵，可缓）和「**忘了重跑**」（教训 19 的正脸，本项目头号失败模式）**混为一谈**——而后者有一个 r6/r7 都没想到的**廉价机械封口**：把 `sha256(criterion_matrix.py)` 盖进 matrix.json，门重算源码哈希比对（瞬时、确定、不执行、不改文件）。诚实边界对「恶意」成立，对「忘了重跑」**不成立**。

**本轮实例是干净的**（内嵌 == matrix.json == 我重跑的新鲜输出，全部自洽，物理诚实）。**两处 MAJOR 都是作为 skill 门的失明**——它们要跑遍每一道未来题，由一个没有这段上下文的 Opus 执行。

---

## 第 1.5 步 · r6 的四个洞是否修到位（先做，全部独立复核）

| r6 洞 | 判 | 独立复核（运行代码） |
|---|---|---|
| **H1**（内嵌脱钩：门读内嵌手拷副本、不读 matrix.json，篡改内嵌一处全套门 0 ERROR） | **✓ 已修** | r7 加了 `check_matrix_desync`（L1267）：内嵌（去 `script`）逐字 == `01-criteria/matrix.json`。端到端复核：**把 delta_max=0.17 篡改进内嵌、matrix.json 留 0.135 ⟹ `CRIT-MATRIX-DESYNC` 抓到**（r6-H1 那个「端到端 0 ERROR」的洞封了）。**SKILL.md 的假描述也改对了**：L540 现在写「★ 它**不读** `matrix.json`（r6 审稿 H1：以前这句写反了）—— 内嵌是手工同步进去的一份副本，靠 `CRIT-MATRIX-DESYNC` 校验」。**但只封了「改内嵌一处」，没封「源码脱钩」——见 H2。** |
| **H2**（scan_upper_bound 无下限：0.05mm < 0.10mm 噪声照过） | **✓ 大体已修（残留见 H3）** | r7 加 `systematic_error_budget` 字段 + 门校验 `scan_upper_bound ≥ 3×budget`（L1168–1179）。复核：**None + scan=0.05mm + budget=0.10mm(诚实) ⟹ `CRIT-ROBUSTNESS-COARSE`**（r6-H2 的原样攻击现在被抓）。**但门把 budget 只接进了「None 分支的 scan 距离」，没接进「finite 分支的 delta_max vs 噪声」——那才是新洞 H1。** |
| **H3**（措辞表外的词 `计算得/等于` 落在真 target 上静默漏） | **✓ 已修（改成诚实 scope）** | r7 **回退**扩表冲动，把 `_VALUE_CLAIM`（L1646）明写成**启发式**（docstring L1644–1645：「本表是一个启发式，挡最常见的形态，不追求完备；未覆盖的措辞靠对抗审稿兜底」）。复核：`targets[γ] 的闭式计算得 2.9999`、`targets[γ] 等于 2.9999` ⟹ 门放行（**明写不管**，不再伪装覆盖）；`targets[γ] 公式算出来是 2.9999` ⟹ 仍 `PROSE-FORMULA-GHOST`。**这是对 r6-H3 的正确回应**（r6 自己给的修法就是「明写只认这几个词、列进不管清单」）。 |
| **H4**（`约为/大约` + `parameters[]` 引入误报） | **✓ 已修** | r7 从 `_VALUE_CLAIM` **删掉** `约为/大约/≈`（docstring L1642–1643 记了原因）。复核：`parameters[a] = 10.784 mm 处，中心磁场**约为** 0.3 T` ⟹ **不再误报**（0 ERROR）；`B 场大约为 0.3 T` ⟹ 0 ERROR。误报消了。 |

**⇒ r6 的四个洞全部干净修订。本轮所有命中，全部在 r6 为修 H1/H2 而新写的两道机械门本身留下的**下一层**失明。**

---

## 命中的洞

### H1 · [MAJOR] `budget` 下限门守错了比值：校验「扫得够远」，却不校验「悬崖在噪声外」——判据集在实操里误杀正确模型仍 0 ERROR — 命中 P18① + P17④（第八次复发，**无探针覆盖**）

**这是本轮真正的第八次复发**：r7 为封 r6-H2 引入 `systematic_error_budget`，但把它接错了地方。

**位置**（逐字抄写）。`check_analysis.py` L1156–1212，finite delta_max 分支：

```python
dm = rs.get("delta_max"); sub = rs.get("scan_upper_bound"); budget = rs.get("systematic_error_budget")
if not isinstance(sub, (int, float)):            err(... 缺 scan)
elif not (isinstance(budget,(int,float)) and budget>0):  err(... 缺 budget)
elif float(sub) < 3 * float(budget):             err(... 扫得不够远)      # ← budget 只在这里被用
elif dm is None:                                 pass                     # 处处稳健
elif isinstance(dm, (int, float)):
    ...  # 只查 bracket 存在、0≤lo≤dm≤hi≤sub、相对宽<5%
```

**门用 `budget` 只做了一件事：`scan_upper_bound ≥ 3×budget`。** 那回答的是「**你扫得够不够远**」。它**从不比较 `delta_max` 和 `budget`**——也就是**从不回答「你找到的那道判死悬崖 `delta_max`，在不在噪声 `budget` 够得到的地方」**。而那才是判据集**能不能用**的唯一问题。

**运行代码证明（构造 JSON，直接喂 `check_criterion_matrix`）。** budget=1e-4（=§9 噪声 0.10mm）、scan=4e-4（≥3×budget，固定）、bracket 相对宽 0.1%（合法）：

| `delta_max` | 安全裕度 = delta_max/budget | 门判定 |
|---|---|---|
| 0.1344 mm（真值） | **1.34×** | 0 ERROR |
| 0.100 mm | 1.0× | 0 ERROR |
| **0.050 mm** | **0.5×** | **0 ERROR** ← 判死悬崖落在噪声**以内** |
| **0.020 mm** | **0.2×** | **0 ERROR** |
| **0.005 mm** | **0.05×** | **0 ERROR** |
| **0.001 mm** | **0.01×** | **0 ERROR** |

**`delta_max=0.05 mm` 的含义**：残余定心误差一超过 0.05 mm，五条判据里就有一条判死正确模型。而 §9 的视频噪声预算是 **±0.10 mm**——**噪声的一次涨落就把偏心推过悬崖 ⟹ 正确模型被误杀。这套判据在实操里根本不能用。而门 0 ERROR。**

**更糟：`criterion_matrix.py` 自己的自检也瞎。** L400–414 的 `bad` 只从 δ=0 的表（`bad |= not good` / `bad |= not caught`）来；L462 的 `_margin = delta_max/DELTA_SAFE` 只被 **print**（L466/L541），**从不进 `bad`**；L581 `verdict = "FAIL" if bad else "PASS"`。**⟹ 一个 margin=0.5× 的判据集，criterion_matrix.py exit 0、写 `verdict:PASS`，check_analysis 再 0 ERROR。两层机械化，一起对「悬崖在噪声内」失明。**

**为什么这是 P18①（不是别的）。** matrix.json 的 verdict 逐字写着「安全裕度 **1.34×**」、criterion_matrix.py 把它印在最显眼处——**这是一个 load-bearing 的结论阈值**（判据可用 ⟺ 裕度 > 1）。而它**只以散文形式存在，没有任何门**。这正是 r3 翻车（「容差是作者定的裸数字、与正文矛盾」）的同构——只不过这次那个「散文里的数」是**安全裕度本身**。P18① 说「容差是从哪来的、有没有被门守住」；这里连**门该守的那个不等式（margin ≥ 1）压根不存在**。

**为什么这是第八次复发（无探针覆盖）。** 我读了 finite-delta_max 分支的**全部**盲区探针（`--selftest` L1918–1977）：`none+无sub`、`none+ok`、`finite+无sub`、`缺budget`、`scan<3×budget`、`bracket过宽`、`bracket非法`、`手写窄括号(已知局限)`。**没有一个测「finite delta_max < budget、bracket 合法」。** 而且 finite 分支里**没有任何注释声明「我不管 delta_max vs budget」**（None 分支 L1180–1183 倒是诚实声明了它的 scope）——**所以这不是「诚实声明某类不管」，是一处未声明、未探针、未察觉的结构性失明。** 造得出 ⟹ 元流程还缺这一环。

**影响**。本轮实例侥幸活着：真值 margin=1.34× > 1。**但只是侥幸**——r6 的 UNCLEAR#1 已经警告「带 ±0.1mm 视频噪声 + Γ 的 2% 后 σ(z_off) 可能 ≳ 0.135mm」，即**本题的有效裕度已经在 1× 悬崖边缘**。作为要跑遍每道题的 skill 门：下一道题只要判据集稍脆（margin 0.8×），两层机械化一起放绿灯，一套**在实操里必然误杀**的判据被送到评委面前。

**可否修**（回填进 skill，都是机械的）：
1. **finite 分支加一条门**：`delta_max ≥ k × systematic_error_budget`（k ≥ 1，本项目 §9 已用 3× 做 scan，用同一个 k 最自洽）。裕度不足 ⟹ `CRIT-ROBUSTNESS-COARSE`（或新码 `CRIT-MARGIN-THIN`）。
2. **criterion_matrix.py 的 `bad` 必须吃 `_margin`**：`bad |= (delta_max is not None and delta_max < k*NOISE_BUDGET)`。自检和门用同一条不等式。
3. **两个方向都钉进 `--selftest` 盲区探针**：`finite delta_max < budget（合法 bracket）⟹ 抓到`、`delta_max ≥ k×budget ⟹ 放行`。

---

### H2 · [MAJOR] `CRIT-MATRIX-DESYNC` 栓了「内嵌↔matrix.json」，没栓「matrix.json↔源码新鲜输出」——源码可删可改而门全程失明；「忘了重跑」这一半有廉价封口没做 — 命中 P17④ + P18（教训 19 正脸）

**先给正面记一功。** r6-H1 的头号 MAJOR（门读内嵌手拷副本、篡改内嵌一处全套门 0 ERROR）**真封死了**：`check_matrix_desync`（L1267）读 `01-criteria/matrix.json`、逐字段 == 内嵌（去 `script`）。我端到端复核：**篡改内嵌 delta_max=0.17、matrix.json 留 0.135 ⟹ `CRIT-MATRIX-DESYNC`**。SKILL.md 的假描述也改对了。**这一层收敛了。**

**但门比的是「内嵌 vs matrix.json」（两份**静态副本**），不是「内嵌 vs `criterion_matrix.py` 的**新鲜**输出」。** 而这整套 DESYNC + CRIT 门存在的**唯一理由**，是保证「门验的那张表 = `criterion_matrix.py` 跑出来的、不是写出来的」。那个不变量，没有门。

**运行代码证明（端到端喂真 `check_analysis.py examples/…` 的临时拷贝）。**

| 我对临时工作区做的事 | 真 `check_analysis.py` 判定 |
|---|---|
| 基线（不动） | 0 ERROR |
| **把 `01-criteria/criterion_matrix.py` 整个删掉** | **0 ERROR** ← 整套门号称要验的源码文件不在了，门无声 |
| **改源码 `GAMMA_OC 0.0413→0.0900` + `P1c 容差 0.12→0.01`（重跑会翻掉整张表），但不重跑** | **0 ERROR** ← matrix.json+内嵌还是旧的、彼此一致，门验的是这份陈旧副本 |

**门从头到尾不打开 `criterion_matrix.py`**（grep `check_analysis.py`：无 `subprocess`/`Popen`/`check_call`；「重跑」只出现在注释里）。而全仓库**也没有任何 build / hook / pre-commit 重跑它**（grep 为空，只有 `settings.local.json` 的 permissions）。**⟹「matrix.json 的新鲜度靠提交前重跑」是一句纯粹的散文劝诫**——正是本项目铁律「文档里的劝诫会被忽略；机械检查不会」要消灭的东西。

**为什么这是 MAJOR 而不是「可接受的诚实局限」。** 任务判据：诚实声明某类不管、**理由成立** = 可接受。作者在 `check_matrix_desync` 的 docstring（L1270–1273）声明了局限，但把两件事混成一件：

- **恶意路径**（「内嵌 + matrix.json 两处**一起**手改成一致的假值」）：确实要 subprocess 重跑源码才能抓，而重跑 `criterion_matrix.py` **实测 > 120 秒**（我重跑计过时）、且会覆写 matrix.json。**punt 到对抗审稿，理由成立。** ✓
- **疏忽路径**（「改了源码、**忘了重跑**」）：这是**教训 19 的正脸**（「而『忘了改』的定义，就是『值没变』」）、是本项目反复强调的**头号失败模式**（「修订必须传播」）。它**有一个 r6/r7 都没想到的廉价机械封口**：`criterion_matrix.py` 生成时把 **`sha256(自己的源码文件)`** 写进 matrix.json；门重算 `sha256(01-criteria/criterion_matrix.py)` 比对。**瞬时、确定、不执行任何代码、不改任何文件。** 源码一改 ⟹ 哈希对不上 ⟹ 抓到 ⟹ 逼你重跑。**这一半的「理由（要贵 subprocess）」不成立。**

**teeth**：一个学生修了 `criterion_matrix.py` 里的物理 bug（重跑会让某条判据翻成 `passes_correct=False` 或某个错模型 `UNCAUGHT`），**忘了重跑** ⟹ 陈旧的全绿 matrix.json + 内嵌照旧一致 ⟹ `CRIT-FALSEKILL`/`CRIT-MODEL-UNCAUGHT` 验的是陈旧副本、全过 ⟹ 0 ERROR。**四道 CRIT 门的全部价值，被一次「忘了重跑」清零。** 而 CRIT-FALSEKILL 只查 δ=0 那一格，看不见这个。

**可否修**（回填）：
1. **廉价封口（堵疏忽路径）**：`criterion_matrix.py` 落盘时加 `out["source_sha256"] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()`；`check_matrix_desync` 读 matrix.json 的 `source_sha256`、重算 `01-criteria/criterion_matrix.py` 的哈希、不符即 `CRIT-MATRIX-DESYNC`（或新码 `CRIT-MATRIX-STALE-SOURCE`）。**~7 行，把「改源码不重跑」从疏忽变成硬错。**
2. 恶意路径（两处一起改）继续靠对抗审稿——但 docstring 要**把两半拆开写**：疏忽半靠源码哈希（已机械封），恶意半靠 subprocess/审稿（诚实局限）。**别再用「都要贵 subprocess」把可廉价封的那半也 punt 掉。**

---

### H3 · [MINOR] `budget` 是作者报的数，可假报到荒谬地小——逃生舱从「无下限」挪成「相对一个可假报的数」 — 命中 P18②（逃生舱 narrow 了但没 seal，理由**部分**成立）

**位置**：L1168–1175，门自己声明「budget 是作者报的数，门只保证 `scan_upper_bound ≥ 3×budget`；budget 本身诚不诚实（对比 §9）靠人读/审稿（诚实 scope）」。

**运行代码证明**：`delta_max=None` + `budget=1e-9`（假报，真噪声 1e-4）+ `scan=1e-8`（≥3×budget） ⟹ **0 ERROR**。「在 [0, 10 nm] 上处处稳健」是**真话，但一个 10 纳米的稳健窗口毫无意义**。

**为什么这算 MINOR 不算 MAJOR**（与 H1/H2 不同）：
- budget 的诚实性**本质上不可机械自证**——你把 §9 的「±0.1mm」结构化成字段，那个字段**同样是作者报的数**，无穷回退。到某一层必须信一个人报的数，然后靠对抗审稿去对物理。**这个诚实 scope 的理由，成立。**
- 而且这个逃生舱**自曝**：假报小 budget ⟹ 稳健窗口塌成纳米级 ⟹ verdict 散文里白纸黑字写「稳健窗口 10 nm」，**审稿一眼就看穿**（对比 H2 的陈旧副本长得和正常的一模一样，无 tell）。
- 且 r6-H2 的**原样攻击**（scan 太短、budget 诚实）**已经被封**（见第 1.5 步）。残留只是「budget 不诚实」这一薄壳。

**⇒ 逃生舱被 narrow 了（从「完全无下限」到「相对一个自曝的数」），没 seal，但理由部分成立、且 exploit 自曝 ⟹ MINOR。**

---

## ★★★ 头号攻击面的结论（任务第 2 步）

**1. `CRIT-MATRIX-DESYNC` 瞎不瞎？**
- 对「改内嵌一处」：**不瞎**（真封了 r6-H1，端到端复现抓到）。
- 对「matrix.json ↔ 源码新鲜输出」：**瞎**（删源码 / 改源码不重跑，全 0 ERROR）。作者声明为已知局限，但**声明的理由（都要贵 subprocess）对「忘了重跑」这半不成立**——有 `source_sha256` 廉价封口没做。**⟹ 诚实边界对「恶意两处一起改」站得住，对「忘了重跑」站不住 ⟹ H2 = MAJOR。**
- **有没有 build 步骤能真堵而 r7 没做？** 有两个：① 贵的（subprocess 重跑比对输出，r6 已提，>120s，可缓）；② **廉价的（源码哈希戳，r6/r7 都没想到，~7 行，直接堵死疏忽路径）**。r7 一个都没做。

**2. `budget` 下限是不是真锁？**
- 对「r6-H2 的原样攻击（scan 太短）」：**是真锁**（budget 诚实时 scan=0.05mm 被抓）。
- 对「budget 假报小」：不是锁，但逃生舱自曝（纳米窗口）+ 诚实性不可机械自证 ⟹ 可接受（H3 = MINOR）。
- **但 budget 被接错了地方**：它进了「None 分支的 scan 距离」，**没进「finite 分支的 delta_max vs 噪声」**——那才是判据可用性的命门，而那里**没有任何门**（H1 = MAJOR）。**逃生舱不是被挪了个位置，是**换了个更深、更没 tell 的维度**：从「scan 无下限」变成「找到的悬崖可以落在噪声里而无人过问」。**

**3. 元流程收不收敛？——我，就是那个 fresh 审稿。**
- 跑 `--selftest`：全过（每道门后都有盲区探针，写死不 regress）。
- **我构造出了一个让 `budget` 门结构性失明、而它的盲区探针没覆盖的输入**（H1：finite delta_max < budget，合法 bracket）。它**不在任何探针里**，finite 分支里**也没有诚实声明**它不管。**⟹ 造得出 ⟹ 元流程还缺这一环 ⟹ 第八次复发。**
- 这**正面印证**了文件头 L36–40 和教训 23 那句话：「每一轮我都以为够了，每一轮审稿都构造出新的失明。收敛不靠更完美的门，靠流程：探针挡已知 + 对抗审稿挖未知。」**这一轮，探针挡住了 r5/r6 的已知坑（我复核全绿），对抗审稿挖出了下一个未知坑（H1）。元流程本身在起作用——但它的必然推论就是「还没收敛」。**

> **⇒ r7 **没有**收敛。** 物理是磐石，r6 的四个门洞真修好了，但**修 r6-H2 时新引入的 budget 门守错了比值（H1，第八次复发、无探针）**，**修 r6-H1 时的 DESYNC 门把可廉价封的疏忽路径也 punt 掉了（H2）**。**这不是失败——这是元流程按设计在跑：下一把锁又是瞎的，而我把它拆了。**

---

## 我独立复算 / 构造的关键量

| 量 | 我的方法 | 我的值 | 契约/代码 | 判 |
|---|---|---|---|---|
| δ 判死边界（重跑源码） | 后台重跑 `criterion_matrix.py`，`_delta_star` 二分 | **0.1344 mm，bracket [0.1328,0.1344]** | 0.0001344 / 同 | ✓ 本轮实例诚实 |
| 安全裕度 | 0.1344/0.10 | **1.34×** | 1.34× | ✓（但**门不校验它 ≥1**——H1） |
| ε\*(bug-C) / ε\*(bug-E) | 重跑复现 | **13% / 2%** | 0.1312 / 0.0187 | ✓ 诚实（10%<13% 抓不到，作者认） |
| r6-H1：篡改内嵌 0.17、matrix.json 留 0.135 | 端到端喂真 check_analysis | **CRIT-MATRIX-DESYNC 抓到** | — | ✓ **r6-H1 封了** |
| r6-H2：None+scan0.05mm+budget0.10mm | 喂门函数 | **CRIT-ROBUSTNESS-COARSE** | — | ✓ **r6-H2 封了** |
| r6-H4：`parameters[a] 磁场约为 0.3 T` | 喂门函数 | **不误报** | — | ✓ **r6-H4 封了** |
| **finite delta_max=0.05mm（margin 0.5×）+合法窄bracket** | 喂门函数 | **0 ERROR** | — | **✗✗ H1** |
| **同上 margin 0.01×（delta_max=1μm）** | 喂门函数 | **0 ERROR** | — | **✗✗ H1** |
| **删掉 `criterion_matrix.py` 源码** | 端到端喂真 check_analysis | **0 ERROR** | — | **✗✗ H2** |
| **改源码 GAMMA_OC 0.0413→0.0900 不重跑** | 端到端喂真 check_analysis | **0 ERROR** | — | **✗✗ H2** |
| **None+budget=1e-9(假)+scan=1e-8** | 喂门函数 | **0 ERROR**（10nm 稳健窗口） | — | ✗ H3（自曝，MINOR） |

> **我最想打穿的物理（Model-2 的 `G`、能量法、ν 无关阶、δ 二分边界、ε\* 扫幅度、bug-E/bug-F 试金石）—— 第七轮全部打空。** 重跑复现 delta_max=0.1344、ε\*=13%/2%，逐字自洽。**本轮所有命中都在「r7 新写/重写的机械化」上，不在物理上。**

---

## 18 条模式的逐条结果（P1–P15 + P17 + P18；被审稿修订过，加查 P16）

| 模式 | 结果 | 我做了什么检查 |
|---|---|---|
| **P1 量纲/单位** | 未命中 | (1)–(27) 齐次（前六轮硬验）；重跑数字复现。 |
| **P2 口头忽略** | 未命中 | 每个「忽略」都是功率比/力比（r1 长度比 non sequitur 早改）。 |
| **P3 忽略/门只在扫描一端** | **命中 → H1** | δ 二分定边界（0.1344，重跑复现）✓；**但 finite 分支门只校验 scan≥3×budget，不校验 delta_max≥budget ⟹ 悬崖落在噪声内仍 0 ERROR。** |
| **P4 双重计数** | 未命中 | 力/能量互补。 |
| **P5 非惯性系** | 未命中 | 全文实验室系。 |
| **P6 边界条件** | 未命中 | (26)/(27) 边界显式。 |
| **P7 线性化越界** | 未命中 | ν 无关阶数（bug-F 探针证明扫 A₀ 抓得到线性化）。 |
| **P8 公式超域** | 未命中 | 点偶极子 RISKY 已量化；趋肤深度作适用条件。 |
| **P9 时间尺度** | 未命中 | $L/(R{+}R_c)\ll1/\omega_0$。 |
| **P10 耗散符号/热二** | 未命中（零号规则：逐字抄 (26)） | 两处质量都 $M_{\rm eff}$；$\dot E\le0$。 |
| **P11 循环论证** | 未命中 | $k=Mg/\Delta x$ 弹簧自重抵消。 |
| **P12 自由参数** | 未命中 | $N_f=0$。 |
| **P13 符号复用** | MINOR（未升级） | 0 ERROR；$Q$ 双义已记。 |
| **P14 RISKY 敏感** | 未命中 | 逐条 impact_if_false + 预注册应对。 |
| **P15 文献替代推导** | 未命中 | 抽查通过。 |
| **P16 事后合理化** | 未命中 HARKing | 归档链 r1→r4 全齐，逐版 diff 可做；r7 的每处改动（DESYNC 门、budget 字段、措辞回退）都由 r6 审稿驱动、是**变严/更诚实**，非照数值倒推（`02-sim/` 不存在）。无 HARKing。 |
| **P17 判据界错了量** | **命中 → H1/H2** | ①②③ 物理侧全过；**④「换上的新锁也瞎」——budget 门守错比值（H1）、DESYNC 门不栓源码（H2）。** |
| **P18 双向表是自评** | **命中 → H1（守表的门自己瞎）** | 六维度复核：容差有来源✓、ε\* 扫幅度且诚实✓、正确模型=Model-2✓、不误杀二分✓、CAUGHT≠DEGENERATE✓、bug-E/F 试金石✓。**表本身（matrix.json）是真的，我重跑复现。塌的是守它的两道门：①「安全裕度」这个 load-bearing 阈值只活在散文里、门不守（H1，P18① 正脸）；② 门验的副本和源码之间没机械栓（H2）。** |

---

## UNCLEAR（我无法判断的）

1. **有噪声下 $\sigma(z_{\rm off})$**（r3–r6 同判，本轮更紧迫）：无噪声仿真给 ~0.03mm，悬崖在 **0.1344mm、裕度仅 1.34×**。**H1 让这从「UNCLEAR」变成「门本该抓、却抓不到」**：若带 ±0.1mm 视频噪声 + Γ 的 2% 后有效裕度掉到 <1×，判据在实操里误杀正确模型——而 finite 分支的门（和 criterion_matrix.py 的自检）**都不会响**。作者必须把「带噪声的有效裕度」算出来，并把 `delta_max ≥ k×budget` 变成一道门（H1 的修法）。
2. **bug-E 的 `why` 与 catches 轻微不符**（MINOR 提示，不改判定）：`why_a_student_writes_it` 写「曲率与正确模型一模一样 —— **只有「顶点值」那条判据看得见它**」，而 matrix.json 显示 bug-E（eps_E=10%）被 **P1b + P3a + P3b 三条**抓到（只有曲率 P1c 对它退化）。散文「只有顶点值看得见」相对数据**略微夸大**（准确说法应是「只有 P1c 对它失明」）。这不影响 P18 完备性试金石（bug-E 作为「形状全对+常数偏置」的模型**确被抓到**），但 prose 与 data 有一处该对齐。

---

## ★ 给 skill 的回填建议（**任何题都会踩的坑**）

### 1. ★★★ 门要守「悬崖在噪声外」，不是只守「扫得够远」（H1）
> 教训 11「门的容差要在扫描端点上定」被 r7 用在了「scan 距离」上，**却没用在「delta_max vs 噪声」上**——而后者才是判据可用性的命门。「安全裕度」是一个 load-bearing 阈值，r7 把它算出来、印出来、写进 verdict 散文，**唯独没给它一道门**（P18① 正脸）。
> **⇒ finite 分支加 `delta_max ≥ k×systematic_error_budget`（k 与 scan 用同一个，本项目 3×）；criterion_matrix.py 的 `bad` 也吃这条不等式；正反两向钉进探针。**

### 2. ★★★ 门验的那份数据，要和「源码本身」有机械栓——而且疏忽路径可以廉价封（H2）
> `CRIT-MATRIX-DESYNC` 栓了「内嵌↔matrix.json」，没栓「matrix.json↔源码」。删源码 / 改源码不重跑，全 0 ERROR。「靠提交前重跑」全仓库无任何机械兜底（铁律「文档里的劝诫会被忽略」）。**别把「恶意两处一起改（要贵 subprocess）」和「忘了重跑（教训 19 正脸）」混为一谈**——后者有廉价封口。
> **⇒ `criterion_matrix.py` 落盘时戳 `source_sha256`（自己源码的哈希）；门重算源码哈希比对，不符即报。~7 行，把「改源码不重跑」从疏忽变硬错。恶意半继续靠对抗审稿，但 docstring 要把两半拆开写。**

### 3. ★★ 每加/改一道门，盲区探针要覆盖「门守的那个不等式被绕过」的方向
> H1 证明：r7 给 budget 门加了一堆探针（缺 budget、scan 太短、bracket 过宽…），**唯独没有「门用 budget 做的那个比较，可以对另一个更该比的量失明」**。探针挡住了「字段缺失/格式」，没挡住「比对了错的量」。
> **⇒ 探针纪律要升一层：不只测「该抓的抓、诚实的放」，还要测「门用来判定的每一个不等式，把它两边换成**该比而没比**的量，会不会放行」。而这一层，最终只能靠 fresh 对抗审稿去逼（本轮已印证）。**
