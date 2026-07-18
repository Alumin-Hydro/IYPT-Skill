#!/usr/bin/env python3
"""IYPT 分析的机械检查器。

只做**确定性可判**的检查——不做物理判断。物理判断是 iypt-physics-review 的活。
先跑这个把机械错修掉，再去叫审稿人，别浪费审稿轮次。

用法:
    python check_analysis.py iypt/magnetic-brake

退出码: 0 = 无 error（可能有 warning）；1 = 有 error；2 = 用不了（文件缺失等）

★★★ 盲区探针（BLINDNESS PROBES）—— 本文件最贵的一条纪律（第六次复发才逼出来）
────────────────────────────────────────────────────────────────────────────
一道门的 `--selftest` **本身也是一份自评**（P18「双向表是自评」再上一层楼）。
「它在诚实实例上判得对、`--selftest` 全绿」**不算验证** —— 那只跑了两种用例：
「该抓的 → 抓到」「诚实的 → 放行」，**从没跑「它号称要挡、但换个形状 → 该抓却放行」。**

**实测（electrical-damping r5，真实翻车）**：`CRIT-ROBUSTNESS-COARSE` 和
`PROSE-FORMULA-GHOST` 两道门 `--selftest` 全绿、真实工作区 0 ERROR，而审稿一构造就穿：
`delta_max=None` 整道门被跳过、手写窄括号复活虚报值、非-target 的公式幽灵漏网……
**更糟：`none_ok` 用例亲手把「None ⟹ 放行」钉成了「预期行为」，给盲区盖了章。**

**⟹ 每加一道门（或改一道门），`--selftest` 必须包含「盲区探针」：**
  ① **造出让门失明的输入。造不出 = 你还没理解它守的是什么。**
  ② 能修的 → 修（探针从「放行」翻成「抓到」）；
  ③ **修不了的（如「非 spec 量的幽灵」「provenance 靠重跑保证」）→ 明写「已知局限」**
     —— 探针断言「它放行」并注明为什么，**而不是假装门覆盖了它**（诚实 scope 胜过虚假安全感）。
本文件的 `selftest()` 里，每道门后都跟着一组这样的探针（搜 `盲区探针` / `BLINDNESS`）。

★★★ 而「盲区探针」本身也不完备 —— 这是最后一层（r6 审稿，第七次复发）
────────────────────────────────────────────────────────────────────────────
r6 审稿又构造出两个盲区（`CRIT-MATRIX-DESYNC` 之前的内嵌脱钩、`PROSE` 门措辞表外的词），
**两个都不在当轮的探针集里**。**「列几个探针」= r3 那张「全绿表」在探针层的翻版 —— 它证明不了
自己穷尽了。** 这正是 P18「你怎么知道判据集完备」的同一个未解问题，只是又升了一层楼。

**⟹ 机械门（含它的探针）无法机械地证明自己完备。收敛不靠更完美的门，靠**流程**：**
  · **探针挡**已知**盲区**（写死在 selftest，不会 regress）；
  · **对抗审稿挖**未知**盲区**（每改一道门 / 每加一道门 → 派一次 fresh 的 `iypt-physics-review`，
    让它专门构造「让这道门失明」的输入）。**缺一不可。**
七次复发是这件事的经验证明：每一轮我都以为「这次的门/探针够了」，每一轮审稿都构造出新的失明。

★ 一个能让盲区探针**更系统**的工具（r7 审稿 ③ —— wrong-quantity 元探针）
────────────────────────────────────────────────────────────────────────────
**对一道门用来判定的**每一个不等式**，探一次：把「它**该**比、却**没**比的那个量」换进去，门放不放行。**
这正是「找 P17-at-gate-level」（判据/门界错了量）的系统方法。
**实测（r7-H1）**：budget 门查的是 `scan_upper_bound ≥ 3×budget`（δ 扫多远），
**却从没查那个 load-bearing 的量 `margin = delta_max/budget`**（判死悬崖在不在噪声外）——
`delta_max=0.05mm < budget` 照过，正确模型在实操里被自己的判据误杀。**我审稿时抓 P17 抓过无数次，
自己写门照样把门界在了错的量上。** ⟹ 每加一道带不等式的门，先跑一遍这个元探针。
"""

import hashlib
import json
import re
import sys
import textwrap
from pathlib import Path

# Windows 控制台默认 GBK，中文报告和 ✓/✗ 会直接抛 UnicodeEncodeError
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(code: str, msg: str) -> None:
    ERRORS.append(f"[{code}] {msg}")


def warn(code: str, msg: str) -> None:
    WARNINGS.append(f"[{code}] {msg}")


def _as_list(v) -> list:
    """契约里「一个或多个」的字段，统一归一化成 list。

    ★ **为什么需要它**：`answers_task` 这类字段天然是「一个或多个」——
    一张图答一条任务，写字符串很自然；一张 regime-map 同时答两条任务，写数组也很自然。
    契约同时接受两种形式（见 model-spec.schema.json 的 `oneOf`）。

    **血泪教训**：`check_analysis.py` 原本假定它**只可能是字符串**，把它直接塞进 set ——
    换一道题，遇到数组就是 `TypeError: unhashable type: 'list'`，**整个检查器当场崩溃**。

    > **一个崩溃的检查器，比一个漏报的检查器更糟：它什么信息都不给。**

    **凡是「一个或多个」的字段，都从这里过一遍。** 类型不对时不崩，而是报错。
    """
    if v is None or v == "":
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, (list, tuple, set)):
        return [x for x in v if x]
    err("FIELD-TYPE", f"字段的类型不对：期望 string 或 list，拿到 {type(v).__name__}（{v!r}）")
    return []


# ---------------------------------------------------------------- 载入

def load(workspace: Path):
    analysis = workspace / "01-analysis.md"
    problem = workspace / "00-problem.md"
    spec_path = workspace / "handoff" / "model-spec.json"

    if not analysis.is_file():
        print(f"找不到 {analysis}", file=sys.stderr)
        sys.exit(2)
    md = analysis.read_text(encoding="utf-8")

    # 设定书 (S-n) 住在 00-problem.md，假设台账 (A-n) 住在 01-analysis.md
    if problem.is_file():
        problem_md = problem.read_text(encoding="utf-8")
    else:
        problem_md = ""
        err("PROBLEM-MISSING", "00-problem.md 不存在——原题和设定书没有落盘")

    spec, spec_raw = None, ""
    if spec_path.is_file():
        # spec_raw 是**文件原文** —— SPEC-SELFCONTRADICT 要从 baseline_value 的
        # 字面量数有效位数（json.dumps 重排会把 0.0350 吞成 0.035，尾零就是精度声明）。
        spec_raw = spec_path.read_text(encoding="utf-8")
        try:
            spec = json.loads(spec_raw)
        except json.JSONDecodeError as e:
            err("SPEC-PARSE", f"model-spec.json 不是合法 JSON: {e}")
    else:
        err("SPEC-MISSING", "handoff/model-spec.json 不存在——Skill 2 没有输入，流水线断了")

    return md, problem_md, spec, spec_raw


# ---------------------------------------------------------------- 任务挖掘

#: 题面里的「任务种子」—— 每一个都藏着一条任务。
#: 漏掉一个限定词 = 漏掉一条任务 = Opponent 的第一个问题。
_TASK_SEEDS: list[tuple[str, str]] = [
    (r"under (?:certain|some|specific|the right) conditions?",
     "★ **条件边界**（regime-boundary）—— 现象**不总是**发生。答案是一张**参数空间相图**"
     "（哪片区域会、哪片不会），不是一条曲线。**这往往是最难、最值钱的一条。**"),
    (r"in (?:certain|some) cases",
     "★ 条件边界（regime-boundary）—— 参数空间相图"),
    (r"can also\b",
     "★ **模式分类**（mode-classification）—— 「还能干什么？」通常通向分岔 / 混沌"),
    (r"other (?:interesting )?behaviou?rs?",
     "★ **模式分类** —— 真题里这句话最后落到了**混沌**和 **Lyapunov 指数**，"
     "而「混沌」两个字题面里一个都没有"),
    (r"(?:various|different|several) (?:modes|regimes|behaviou?rs|patterns)",
     "★ 模式分类 + 模式之间的转变"),
    (r"relevant parameters?",
     "「relevant」本身是个问句：**哪些参数相关、哪些不相关，都要给理由**。"
     "说一个参数「不相关」和说它「相关」一样需要证据"),
    (r"\binvestigate\b",
     "★ **指出物理本质**（essence）—— 不是「测几条曲线」，是**解释**"),
    (r"\bexplain\b",
     "**机制识别**：证明是这个机制，并**排除**其他候选（机制预算）"),
    (r"similar (?:to|way|manner)",
     "**对照**：与已知系统的异同 —— 哪里像、哪里不像、**为什么**"),
    (r"\b(?:optimi[sz]e|maximi[sz]e|minimi[sz]e)\b",
     "**权衡关系**：什么增大了、什么**必然**减小"),
    (r"\bdetermine\b[^.]{0,60}\busing\b",
     "**误差分析**：灵敏度、系统误差、精度极限"),
    (r"how (?:does|do)[^.]{0,60}depend",
     "标度律 + **数据坍缩**"),
    (r"(?:study|investigate|analy[sz]e|describe) the (?:motion|movement|dynamics|behaviou?r)",
     "★ **不只是 x(t)**：相图、模式、稳定性、吸引子。"
     "**因变量的第三层「模式」是 IYPT 的分水岭。**"),
]

#: 物理本质里的词 -> 必须有的图。essence 决定图的骨架。
_ESSENCE_TO_KIND: list[tuple[str, set[str], str]] = [
    (r"非对称|势能驱动|势能.{0,6}(?:转换|下降|梯度)",
     {"potential-landscape"}, "势能景观 U(x) —— 那个「非对称」长什么样？势阱在哪？会卡在哪？"),
    (r"非线性",
     {"phase-portrait", "spectrum", "bifurcation", "lyapunov-map", "poincare"},
     "相图 / FFT 频谱（离散峰 vs 连续宽带）"),
    (r"多体|耦合",
     {"mode-shape", "spectrum", "phase-portrait"}, "简正模 / 频谱"),
    (r"混沌|不规律|chaos|chaotic",
     {"lyapunov-map", "poincare", "bifurcation", "spectrum"},
     "Lyapunov 指数 / Poincaré 截面 / 分岔图"),
    (r"多稳|双稳|bistab|multistab",
     {"basin"}, "吸引域 (basin)"),
]


def check_tasks(spec: dict) -> None:
    """★ 任务挖掘的机械检查（Stage 0.5）。"""
    if not spec:
        return

    tasks = spec.get("tasks") or []
    if not tasks:
        err("NO-TASKS",
            "model-spec.json 里没有 tasks[] —— **题面不是任务书，任务要挖**。\n"
            "        \"Investigate the phenomenon\" 不是一条任务，它是**三条**任务的种子。\n"
            "        见 references/task-excavation.md。")
        return

    for t in tasks:
        tid = t.get("id", "?")
        if not t.get("excavated_from"):
            err("TASK-NOSRC",
                f"{tid} 没有 excavated_from（题面里的**哪个词**）。\n"
                f"        **这一条是防自欺的**：挖不出出处的「任务」，多半是你自己编的。")

    # ---- ★ 题面里的限定词，有没有被漏掉？
    stmt = (spec.get("problem") or {}).get("statement", "")
    cited = " ".join((t.get("excavated_from") or "") for t in tasks).lower()
    for pat, hint in _TASK_SEEDS:
        m = re.search(pat, stmt, re.I)
        if not m:
            continue
        phrase = m.group(0)
        # 引用里出现了这个词（或它的核心词）就算引用过
        core = re.sub(r"\\b|[\\()?:]", "", pat).split("|")[0][:12].strip()
        if phrase.lower() in cited or (core and core.lower() in cited):
            continue
        warn("TASK-MISSED",
             f"题面里有 “**{phrase}**”，但**没有任何一条 task 引用它**。\n"
             f"        这多半是你漏掉的一条任务：{hint}\n"
             f"        **题面里每一个限定词都要被追问一次。**")

    # ---- 每条任务必须被至少一张图或一个 target 回答
    #
    #  ★ answers_task 可以是**字符串**（一张图答一条任务）或**数组**（答多条）。
    #
    #  **血泪教训（electrical-damping 的第一次运行，checker 当场崩溃）**：
    #  这里原本写的是 `{f.get("answers_task") for f in ...}` —— 把值直接塞进 set。
    #  magnetic-brake 的 9 张图**恰好每张只答一条任务**（全是字符串），所以它一直活着。
    #  换一道题，一张 (z_0, A_0) 平面上的 regime-map **同时**答「哪些因素」和「有哪些模式」，
    #  写成数组 —— **`TypeError: unhashable type: 'list'`，整个检查器崩了。**
    #
    #  > **一个崩溃的检查器比一个漏报的检查器更糟：它什么信息都不给。**
    #
    #  **两条回填**：① schema 改成接受 string | array；② 这里统一归一化。
    #  **而抓到它的是「第二道题」本身** —— 一个只在一道题上跑过的检查器，
    #  它的每一个隐式假设都还没被证伪过。
    answered: set[str] = set()
    for f in spec.get("figures", []):
        for tid in _as_list(f.get("answers_task")):
            answered.add(tid)

    for t in tasks:
        tid = t.get("id")
        if tid not in answered:
            err("TASK-UNANSWERED",
                f"{tid}（{(t.get('statement') or '')[:40]}）**没有任何一张图回答它**。\n"
                f"        没有图回答的任务 = 空头支票。给它安排一张图"
                f"（figures[].answers_task 里加上 {tid}）。")

    # ---- 反向：没有任务归属的图 = 装饰
    for f in spec.get("figures", []):
        if not _as_list(f.get("answers_task")):
            warn("FIG-NOTASK",
                 f"图 {f.get('id')} 没有 answers_task —— **没有任务归属的图是装饰**")


def check_essence(spec: dict) -> None:
    """★ 物理本质：一句话。它决定图的骨架。"""
    if not spec:
        return
    ess = spec.get("essence") or {}
    one = (ess.get("one_sentence") or "").strip()

    if not one:
        err("NO-ESSENCE",
            "没有 essence.one_sentence —— **在写下任何方程之前，用一句话说清这是个什么系统**。\n"
            "        格式：「X 通过 Y 转换/耦合/竞争为 Z 的〈某类〉系统」。\n"
            "        真题：「磁势能向动能的**非对称转换**」、"
            "「在重力约束下、通过非接触磁排斥实现耦合的**非线性多体动力系统**」。\n"
            "        **这句话不是修辞，是骨架 —— 它决定了你要画哪些图。说不出来 = 你还没懂。**")
        return

    # 「研究 XX 的运动」不是本质，那是题目
    if re.match(r"^(?:研究|探究|分析|study|investigate)", one) or len(one) < 8:
        warn("ESSENCE-VAGUE",
             f"essence.one_sentence = “{one[:40]}” —— 这读起来像**题目**，不像**本质**。\n"
             f"        本质要说清**机制/能量的转换或竞争**：「重力驱动与涡流耗散的**平衡**」、"
             f"「磁势能向动能的**非对称转换**」。")

    # ---- ★ 本质里的关键词 -> 必须有对应的图
    #
    #  注意否定：「线性一阶弛豫，**无**振荡、**无**多稳、**无**混沌」里的「混沌」「多稳」
    #  是在**排除**这些行为，不是在断言它们。断言「不会混沌」不需要画 Lyapunov 图。
    #  （这个 bug 是本检查第一次跑就撞到的。）
    kinds = {f.get("kind") for f in spec.get("figures", [])}
    blob = one + " " + (ess.get("system_type") or "") + " " + (ess.get("competing_effects") or "")
    NEG = r"(?:无|非|不|没有|排除|不会|不存在|no |not |non-)\s*$"
    for pat, need, what in _ESSENCE_TO_KIND:
        m = re.search(pat, blob, re.I)
        if not m:
            continue
        if re.search(NEG, blob[max(0, m.start() - 6):m.start()]):
            continue                                # 否定语境 —— 它在说「不会」，放行
        if kinds & need:
            continue
        err("ESSENCE-NOFIG",
            f"物理本质里说了「{m.group(0)}」，"
            f"但 figures[] 里**没有任何一张 {'/'.join(sorted(need))}**。\n"
            f"        说了这个词，就必须画：**{what}**。\n"
            f"        **essence 决定图的骨架 —— 说了却不画，那句话就是修辞。**")

    # ---- 题面有 "under certain conditions" -> 必须有参数空间相图
    stmt = (spec.get("problem") or {}).get("statement", "")
    if re.search(r"under (?:certain|some|specific) conditions?|in (?:certain|some) cases",
                 stmt, re.I) and "regime-map" not in kinds:
        err("NO-REGIME-MAP",
            "题面里有 “under certain conditions”（现象**不总是**发生），"
            "但 figures[] 里**没有 regime-map（参数空间相图）**。\n"
            "        「什么时候会、什么时候不会」的答案是**一张参数平面上按模式上色的图**，"
            "不是一条曲线。\n"
            "        **这是 IYPT 报告里最值钱的一张图。**")


def check_model_validation(spec: dict) -> None:
    """★ 中间量的独立验证。「最终结果对了」不代表「模型对了」。"""
    if not spec:
        return
    mv = spec.get("model_validation_checks") or []
    if not mv:
        warn("NO-MODEL-VALIDATION",
             "没有 model_validation_checks[] —— **你打算只用「最终结果吻合」来证明模型对吗？**\n"
             "        **两个错误可以互相抵消。** 真题的做法是拿**高斯计去测 B 场**"
             "（模型链条中间的那个量），\n"
             "        而不是拿末速度去反证模型。挑一个可以**独立验证**的中间量："
             "场分布 / 势能景观 / 力曲线 / 本征频率 / 守恒量。")
        return
    for v in mv:
        vid = v.get("id", "?")
        paths = v.get("independent_checks") or []
        if len(paths) < 2:
            err("MV-ONEPATH",
                f"{vid}（{v.get('intermediate_quantity','?')}）只有 {len(paths)} 条验证路径 —— "
                f"**至少要两条互不依赖的**。\n"
                f"        只有一条路 = 没有交叉验证。（如：① 轴上闭式解；② 远场极限；"
                f"③ 对称性；④ 实测。）")
        if not v.get("why_it_can_fail_silently"):
            warn("MV-NOSILENT",
                 f"{vid} 没写 why_it_can_fail_silently —— "
                 f"**它错了而最终结果仍然「对」，是哪两个错误在抵消？**")


# ---------------------------------------------------------------- 自相矛盾的门槛

#: criterion_check 里的**误差估计**（"一阶修正 O(w/a)≈17%"）
_EST = re.compile(r"(?:≈|~|约|大约|approx\.?|~=)\s*([0-9]+(?:\.[0-9]+)?)\s*%")
#: pass_criterion 里的**通过门槛**（"相对偏差 < 15% 则 A-2 站得住"）
_THR = re.compile(r"[<＜]\s*([0-9]+(?:\.[0-9]+)?)\s*%")
#: 承认"预期不通过"的措辞 —— 有它就不算矛盾，而是诚实
_KNOWN_FAIL = re.compile(r"预期不?通过|预期(?:会)?失败|预期(?:会)?不成立|注定|预计不满足|"
                         r"expected to fail|will not hold|expected NOT")


def _check_threshold_vs_estimate(aid: str, chk: dict, asm: dict) -> None:
    """★ pass_criterion 的通过门槛，不能比 criterion_check 里你自己给的误差估计还严。

    **那不是"严格"，那是自相矛盾**：按你自己的估计，这条假设注定通不过。
    而这个矛盾在写下的那一刻就存在了 —— 不需要跑任何数值就能看出来。

    真实案例（magnetic-brake 的 A-2）：
        criterion_check : "一阶修正 O(w/a) ≈ **17%**"
        pass_criterion  : "相对偏差 **< 15%** 则 A-2 在基准点站得住"
    按作者自己的估计，17% > 15%，**它注定不通过**。（实测 23.4%，比两个数都大。）

    逃生口：如果你**明说**"预期不通过"，那不是矛盾，是诚实 —— 放行。
    """
    cc = asm.get("criterion_check") or ""
    pc = chk.get("pass_criterion") or ""
    if not cc or not pc:
        return

    est = _EST.search(cc)
    thr = _THR.search(pc)
    if not (est and thr):
        return

    e, t = float(est.group(1)), float(thr.group(1))
    if t >= e:
        return
    if _KNOWN_FAIL.search(pc) or _KNOWN_FAIL.search(cc):
        return                                   # 明说了"预期不通过" —— 诚实，放行

    err("PASS-CRIT-CONTRADICTION",
        f"{aid} 的通过门槛比你**自己的估计**还严 —— 这是自相矛盾，不是严格。\n"
        f"        criterion_check 说：误差 ≈ {e:g}%\n"
        f"        pass_criterion  说：< {t:g}% 才算通过\n"
        f"        **按你自己的估计，这条假设注定通不过。** 而这个矛盾在写下的那一刻就存在了——\n"
        f"        不需要跑任何数值就能看出来。三条出路，选一条：\n"
        f"          (a) 估计错了 -> 重估（{e:g}% 是怎么来的？系数对吗？）\n"
        f"          (b) 门槛太苛 -> 放宽，并说清这个精度为什么够用\n"
        f"          (c) 它**确实**注定不通过 -> 在 pass_criterion 里**明说「预期不通过」**，\n"
        f"              把任务从「判定通过」改成「量化它有多糟，并据此收窄结论的适用域」")


# ---------------------------------------------------------------- 契约检查

def check_contract(spec: dict) -> None:
    """model-spec.json 的硬约束。schema 能表达的用 schema，表达不了的在这里。"""
    if not spec:
        return

    required_top = ["problem", "symbols", "parameters", "assumptions",
                    "equations", "targets", "figures", "risky_assumption_checks"]
    for key in required_top:
        if key not in spec:
            err("SPEC-FIELD", f"model-spec.json 缺少必填字段 `{key}`")

    # 参数：单位、来源
    for p in spec.get("parameters", []):
        sym = p.get("symbol", "?")
        if not p.get("unit"):
            err("PARAM-UNIT", f"参数 {sym} 没有单位——对 Skill 2 是无意义的数字（无量纲量请写 unit: \"1\"）")
        if p.get("source") == "literature" and not p.get("ref"):
            err("PARAM-REF", f"参数 {sym} 标为 literature 但没给 ref（联网查来的必须给引用）")

    # 假设：分级、判据、RISKY 的验证任务
    checked = {c.get("assumption_id") for c in spec.get("risky_assumption_checks", [])}
    for a in spec.get("assumptions", []):
        aid = a.get("id", "?")
        grade = a.get("grade")

        crit = a.get("criterion", "")
        if not crit:
            err("ASM-CRIT", f"{aid} 没有成立判据")
        elif not re.search(r"[<>≪≫≤≥]|\\ll|\\gg|\\leq|\\geq", crit):
            err("ASM-CRIT-INEQ", f"{aid} 的判据不是不等式形式: \"{crit}\" —— "
                                 f"判据必须能代入数字验证，\"通常成立\"等于没写")

        if grade in ("LOAD-BEARING", "RISKY") and not a.get("impact_if_false"):
            err("ASM-IMPACT", f"{aid} 分级为 {grade} 但没写 impact_if_false"
                              f"（结论依赖它，就必须说清它不成立时结论会怎样——审稿模式 P14）")

        if grade == "RISKY" and aid not in checked:
            err("ASM-RISKY-NOCHECK", f"{aid} 标为 RISKY 但 risky_assumption_checks 里没有对应的数值验证任务"
                                     f"——契约硬约束：RISKY 必须交给 Skill 2 去验")

    # 反向：验证任务指向的假设必须存在
    known = {a.get("id") for a in spec.get("assumptions", [])}
    ledger = {a.get("id"): a for a in spec.get("assumptions", [])}
    for c in spec.get("risky_assumption_checks", []):
        aid = c.get("assumption_id")
        if aid not in known:
            err("CHECK-ORPHAN", f"risky_assumption_checks 引用了不存在的假设 {aid}")
        if not c.get("pass_criterion"):
            err("CHECK-CRIT", f"{aid} 的验证任务没有 pass_criterion——Skill 2 不知道什么结果算通过")

        # ---- 退化特征：Skill 2 唯一能识破"代码偷懒"的手段
        if not c.get("degenerate_signature"):
            err("CHECK-NODEGEN",
                f"{aid} 的验证任务没有 degenerate_signature —— "
                f"**如果代码根本没实现这条修正（偷偷退化回玩具模型），会出现什么「结构性」特征？**\n"
                f"        必须是一个在「正确模型」和「退化模型」下取**离散地不同**值的量"
                f"（峰位、节点数、对称性、解析可证的幂次），**不能是一个拟合出来的数**。\n"
                f"        血泪教训：只写「若斜率也给出 4.00 则代码错」，被「只少一个修正」的 bug "
                f"以斜率 3.79 从两条断言之间溜走了。拟合值是连续的，可以落到任何地方。")
        elif re.search(r"斜率|指数|拟合|slope|exponent|fit",
                       c.get("degenerate_signature", "")) \
                and not re.search(
                    # 结构性的量：离散、可解析确定、不会平滑漂移
                    r"峰|节点|零点|对称|解析|位置|个数|常数|恒为|恒等|不变|单调|结构|离散|"
                    r"peak|node|symmetr|analytic|position|count|constant|invariant|"
                    r"monoton|structur|discrete",
                    c.get("degenerate_signature", "")):
            warn("CHECK-DEGEN-WEAK",
                 f"{aid} 的 degenerate_signature 看起来是在查「拟合出来的数」（斜率/指数）。\n"
                 f"        **拟合值是连续的** —— 只少一个修正的 bug 会让它落在陷阱值和真值**之间**，"
                 f"从断言中间溜走。\n"
                 f"        找一个**结构性**的量：峰位、节点数、对称性、解析可证的幂次。\n"
                 f"        自问：「把这个修正项整个删掉，哪个量会**跳变**（而不是平滑漂移）？」")

        # ---- ★ pass_criterion 的门槛不能比 criterion_check 自己的估计还严
        _check_threshold_vs_estimate(aid, c, ledger.get(aid) or {})

    # 图：expected_shape 是验收标准
    for f in spec.get("figures", []):
        fid = f.get("id", "?")
        shape = (f.get("expected_shape") or "").strip()
        if not shape:
            err("FIG-SHAPE", f"图 {fid} 没有 expected_shape——图是用来证伪的，没有预期就没有验收标准")
        purpose = (f.get("purpose") or "").strip()
        if purpose in ("展示结果", "show results", "结果", ""):
            warn("FIG-PURPOSE", f"图 {fid} 的 purpose 是\"{purpose}\"——说清它要证明什么，不然它只是装饰")

    # 目标量：至少要有一个零自由参数的预测
    if spec.get("targets") and not any(t.get("scaling_law") for t in spec["targets"]):
        warn("NO-SCALING", "没有任何 target 给出 scaling_law——幂律指数是零自由参数的预测，"
                           "是最有说服力的可证伪点，缺了它模型很难被证伪（审稿模式 P12）")

    # 未闭合的洞
    gaps = spec.get("open_gaps") or []
    if gaps:
        warn("OPEN-GAPS", f"model-spec.json 声明了 {len(gaps)} 个未闭合的 [GAP]——"
                          f"确认 01-analysis.md 文首也声明了它们，且下游知情")


# ---------------------------------------------------------------- 正文检查

def _tag_defn_nums(md: str) -> list:
    r"""从 \tag{...} 里抽出**定义**的公式号。

    ★ 教训 12（「正则写死一种排版」第四次）：旧正则 `\\tag\{\(?(\d+)\)?\}` 只认单个号，
    对一行定义多式的 `\tag{8,9}`、`\tag{11, 12}` **整条不匹配** ⟹ 8/9/11/12 全被误报为「缺」。
    而「一行给出 k* 与 λ* 两式、共一个 \tag{8,9}」是**极常见**的排版。

    规则：body **完全是数字列表**（数字/逗号/括号/空白）才算「定义」，逐个抽出其中的数字：
      · `\tag{7}` / `\tag{(7)}` → [7]      · `\tag{8,9}` / `\tag{11, 12}` → [8,9] / [11,12]
    body 含**其它文字**的是「引用」，跳过（否则会把它里的号**重复计数**，假报 EQ-DUP）：
      · `\tag{对应 (9)}` / `\tag{cf. 3}` → []   —— 「见式 (9)」这种再引用不是新定义。

    ★ 诚实的已知局限（钉进 selftest 盲区探针）：字母子式 `\tag{7a}` 也被当引用**跳过**
      —— 若某号**只**以 `7a` 出现、`7` 没单独出现，EQ-GAP 会假报缺 7（WARNING 级）。
      字母编号的 EQ 连续性本就歧义（7a 算不算「7」？在 7 和 8 之间？），不在本门 scope 内。"""
    nums: list = []
    for body in re.findall(r"\\tag\{([^}]*)\}", md):
        if re.fullmatch(r"[\s\d,()]+", body):
            nums += [int(n) for n in re.findall(r"\d+", body)]
    return nums


def check_equations(md: str) -> None:
    r"""公式编号连续、无重复。`\tag{8,9}` 一行多式、`\tag{对应 (9)}` 引用都要正确处理。"""
    nums = _tag_defn_nums(md)
    if not nums:
        warn("EQ-NONE", "正文里没有找到 \\tag{n} 编号公式——推导应当给公式编号，审稿人要靠它定位")
        return

    dupes = {n for n in nums if nums.count(n) > 1}
    if dupes:
        err("EQ-DUP", f"公式编号重复: {sorted(dupes)}")

    expected = set(range(1, max(nums) + 1))
    missing = sorted(expected - set(nums))
    if missing:
        warn("EQ-GAP", f"公式编号不连续，缺: {missing}")


#: markdown 的强调标记。ID 写成 `| **S-1** |` 或 `### **A-1**` 都是**完全正常**的写法。
#
#  **血泪教训（electrical-damping）**：这两条正则原本写死成 `\|\s*(S-\d+)\s*\|` ——
#  只认**裸的** `| S-1 |`。我在设定书表格里给 ID 加了粗（`| **S-1** |`），
#  于是 7 条设定**一条都没被认出来**，检查器报 `NO-SPEC-SHEET`：「你没写设定书」。
#
#  **它就在那儿，写了整整一张表。**
#
#  magnetic-brake 的 ID 恰好都没加粗，所以这条正则一直活着。
#  > **正则写死一种排版，等于在契约里偷偷加了一条没人知道的格式规定。**
_EMPH = r"(?:\*\*|__|\*|`)?"

#  ★ 血泪教训 2（electrical-damping 真实发生）：ID 是 `A-6a` / `A-6b`。
#
#  原正则是 `(A-\d+)`，于是：
#    · 正文的 `### A-6a` 被读成 **A-6**
#    · 契约里是 A-6a / A-6b
#    ⟹ **两个方向同时报错**：「A-6 在正文里有、契约里没有」+「A-6a 在契约里有、正文里没有」。
#    ⟹ 一次**正确的修订**（把一条假设拆成两条），被检查器当成三个 ERROR 骂回来。
#
#  **而「把一条假设拆成两条」正是修订最常做的动作。** 任何题、任何一轮审稿都会撞上。
#  ⇒ ID 必须允许字母后缀，而且**必须锚死尾部**（否则 A-6 仍会从 A-6a 里被抠出来）。
_AID = r"A-\d+[a-z]?"
_SID = r"S-\d+[a-z]?"

#  ★ 第三次栽在「正则写死一种排版」上（--selftest 当场抓到的）：
#  实际写出来的行是  `| **S-8** ★ | 利兹线 |` —— ID 后面跟了个星号。
#  `{_EMPH}\s*\|` 要求 ID 之后**紧接着**就是竖线，于是 **S-8 整行对检查器隐形**。
#  ⇒ ID 只需**占住单元格的开头**；这个单元格里剩下什么，不关它的事。
_SROW = rf"\|\s*{_EMPH}({_SID}){_EMPH}[^|\n]*\|"

#  「这一项**不可忽略**」是全文最负责任的一句话 —— 不许骂它。（→ check_silent_neglect）
#  桥上的字必须是只可能出现在「否定 + 忽略」结构里的那些。
#  **绝不能放宽成 `[^。]{0,8}`** ——「这一项很小，不影响结论，忽略」也会被放行，
#  而那正是这条检查要抓的东西。（CLAUDE.md 教训 11：为消误报而削弱检查，最贵。）
_BRIDGE = r"[\s被是为算作能得容可当成属于「」“”\"'*`]{0,5}"
_NEGATED_NEGLECT = re.compile(
    r"(?:non-?negligible|not\s+negligible)"                       # 本身就是完整的否定
    r"|(?:不|无法|不能|绝不|决不|并非|而非|cannot|can't|must\s+not)"
    + _BRIDGE + r"(?:忽略|略去|neglect|ignor)",
    re.I)


def check_ids(md: str, problem_md: str, spec: dict) -> None:
    """S-n / A-n：定义了就要被引用；台账要和 spec 对齐。"""
    defined_s = set(re.findall(_SROW, problem_md))
    defined_a = set(re.findall(rf"###\s*{_EMPH}({_AID}){_EMPH}(?![0-9a-z])", md))

    if not defined_s:
        err("NO-SPEC-SHEET", "00-problem.md 里没有设定书条目（S-n）——IYPT 题目是欠定的，"
                             "补全题目设定是 Stage 1 的核心产出，不能跳过")
    if not defined_a:
        err("NO-LEDGER", "01-analysis.md 里没有假设台账条目（A-n）——没有一条简化被记账，"
                         "这在物理上是不可能的：你一定用了假设，只是没说出口")

    # 假设定义了却从不被引用，是真可疑的（要么是废话，要么是你忘了它用在哪）。
    # 设定 (S-n) 不查这个——设定是通过「数值」进入模型的，不是通过 ID 引用；
    # 而且有些设定本来就不该进入模型（管长不影响终速），要求它被引用是官僚主义。
    both = problem_md + "\n" + md
    for aid in sorted(defined_a):
        # (?![0-9a-z]) —— 否则 "A-6" 会在 "A-6a" 里被数到，一条从没被引用的 A-6 会假装被引用了
        if len(re.findall(rf"\b{re.escape(aid)}(?![0-9a-z])", both)) < 2:
            warn("ID-UNUSED", f"{aid} 定义之后再也没被引用过——它真的在推导里起作用吗？"
                              f"（一条从不被引用的假设，要么是废话，要么是你忘了它在哪里被用到）")

    # 台账 vs spec 对齐
    if spec:
        spec_a = {a.get("id") for a in spec.get("assumptions", [])}
        for aid in sorted(defined_a - spec_a):
            err("ASM-NOT-IN-SPEC", f"{aid} 在 01-analysis.md 里有，但 model-spec.json 的 assumptions 里没有"
                                   f"——下游看不到这条假设")
        for aid in sorted(spec_a - defined_a):
            err("ASM-NOT-IN-MD", f"{aid} 在 model-spec.json 里有，但正文里没有对应的 `### {aid}` 条目")


def check_silent_neglect(md: str) -> None:
    """口头忽略：说了'忽略'但同一行/同一句里没有任何数字。审稿模式 P2 的机械版。"""
    kw = re.compile(r"忽略|略去|可略|negligible|neglect|ignor", re.I)

    # 不能只查"有没有数字"——$\tfrac12\rho v^2$ 里的 12 和 2 都是数字，
    # 但它是个「表达式」，不是「量级」。要找的是真正的数量级陈述。
    has_magnitude = re.compile(
        r"\d+\.\d"                      # 小数：3.5、0.167
        r"|10\s*\^|10\s*\{"             # 科学计数法：10^{-8}
        r"|\\times\s*10"                # \times 10^{-7}
        r"|\d\s*[eE][+-]?\d"            # 2e-4
        r"|\d\s*%"                      # 百分比
        r"|(?:^|\|)\s*0\s*(?:\||$)"     # 表格里独立的 0（如"无接触，比值恰为 0"）
    )
    # ★★ **否定**：「这**不可忽略**」是最负责任的一句话 —— 而它被这条检查判成了「口头忽略」。
    #
    #  **血泪教训（electrical-damping）**：A-5 的台账里写「地磁力矩 4.1e-5 N·m，
    #  这**不可忽略**（它会让磁体缓慢转向）⟹ 必须机械约束」——
    #  **一句把「不能忽略」明确说出口的话，被判成了「你忽略了却没给数」。**
    #
    #  这和 `check_essence` 里那个「**无**混沌不需要画 Lyapunov 图」是**同一个病**：
    #  > **正则看得见关键词，看不见否定。**
    #  那里修过一次；**这里没有。同一课，只学了一半。**
    #  ★ 第三次栽在同一个病上（electrical-damping 真实发生）。被误报的那一行是：
    #
    #      「**它不是「可忽略」的 —— 它被吸收进 $M_{\rm eff}$**」
    #
    #  —— 全文**最负责任**的一句话，被这条检查骂了。
    #  原正则要求否定词**紧挨着**「忽略」（中间只许一个「被」），
    #  于是「不**是「可**忽略」的」中间隔了 `是「可` 三个字，就漏了。
    #
    #  ⇒ 允许一小段「桥」——**但桥上的字必须是只可能出现在「否定+忽略」结构里的那些**。
    #  **绝不能放宽成 `[^。]{0,8}`**：那样「这一项很小，不影响结论，忽略」也会被放行，
    #  而那正是这条检查要抓的东西。
    #  **（CLAUDE.md 血泪教训 11：为了消误报而削弱一条检查，是最容易犯、也最贵的错。）**
    negated = _NEGATED_NEGLECT

    # 这些行谈的是"忽略"这件事本身，不是在做一次忽略决策：
    #   标题行、引用块、失效边界的描述、表头单元格、以及规则条文本身
    skip = re.compile(r"^\s*#"                       # 标题
                      r"|^\s*>"                      # 引用块
                      r"|失效边界|breaks_when"        # 假设台账里描述"何时会崩"
                      r"|全程可忽略|一端可忽略"        # 端点检查表的表头
                      r"|被忽略项"                    # 端点检查表的表头（列名）
                      r"|硬规则|口头忽略|未纳入的机制")  # 规则条文/小节名)

    for i, line in enumerate(md.splitlines(), 1):
        if not kw.search(line):
            continue
        if skip.search(line):
            continue
        if negated.search(line):
            continue                                  # ★ 它在说「不能忽略」—— 放行
        if not has_magnitude.search(line):
            warn("SILENT-NEGLECT", f"L{i}: 提到\"忽略\"但这一行没有给出任何量级 —— "
                                   f"每个忽略都要给出「被略去项/主项」的数值比（审稿模式 P2）：\n"
                                   f"        {line.strip()[:90]}")


#: 这几个 LaTeX 宏**按压倒性的惯例是「算符」或「单位」，不是物理符号**。
#
#  \Delta  —— 差量算符（ΔE、ΔT、ΔR_c）。**它不是一个量，它是「……的变化」。**
#  \Omega  —— 欧姆（单位）。`R_c = 3.72\ \Omega` 里的 Ω 是单位，不是符号。
#
#  **血泪教训（electrical-damping）**：一篇有电阻（Ω）、有能量审计（ΔE）的分析里，
#  这条检查会对着每一个 ΔE 和每一个 Ω 喊「你没声明这个符号」——
#  **而作者能做的只有：要么在符号表里给「变化量」和「欧姆」编个词条（荒谬），
#  要么学会无视这条警告（更糟 —— 它会连带训练人无视所有警告）。**
#
#  > **一个总是响的警报，等于没有警报。**
#
#  （真要把 Ω 当符号用——立体角、角速度——照常在符号表里声明它就是了，这里只是不再唠叨。）
_NOT_SYMBOLS = {"Delta", "Omega"}


#  ★ 排版差异 ≠ 符号差异（electrical-damping 真实发生）。
#  契约里写 `A_{cs}`，正文里写 `A_{\rm cs}` —— **同一个符号**，而朴素的子串匹配说「没出现」。
#  于是 6 条 SYM-UNUSED 假警报，把真正的漏声符号淹掉。
#  **而「契约里写裸下标、正文里写 \rm 下标」是所有人都会做的事。**
#  ⇒ 比较之前先把**纯排版**的东西剥掉：\rm / \mathrm / \mathbf / \text、空格、单字符外的花括号。
#  **只剥排版，不剥语义** —— `G'` 与 `G` 仍然是两个符号，`\Pi_4` 与 `\Pi` 仍然是两个符号。
_TYPO = re.compile(r"\\(?:rm|mathrm|mathbf|mathit|text|bm|boldsymbol)\s*")


def _norm_sym(s: str) -> str:
    s = _TYPO.sub("", s)
    s = re.sub(r"\{(\w)\}", r"\1", s)      # {c} -> c（单字符的花括号是排版，不是语义）
    return re.sub(r"[\s{}]", "", s)


def check_symbols(md: str, spec: dict) -> None:
    """符号表双向闭合。"""
    if not spec or not spec.get("symbols"):
        err("NO-SYMBOLS", "model-spec.json 没有符号表")
        return

    table = {s.get("symbol", "").strip() for s in spec["symbols"]}
    body = md
    body_n = _norm_sym(body)

    # 表里有，正文没用
    for sym in sorted(table):
        if not sym:
            continue
        if sym not in body and _norm_sym(sym) not in body_n:
            warn("SYM-UNUSED", f"符号表里的 ${sym}$ 在正文里没出现")

    # 正文有，表里没有：只查希腊字母（误报率低、且正是一符多义的高危区）
    greek = set(re.findall(r"\\(alpha|beta|gamma|delta|epsilon|zeta|eta|theta|kappa|lambda"
                           r"|mu|nu|xi|rho|sigma|tau|phi|chi|psi|omega|Gamma|Delta|Theta"
                           r"|Lambda|Xi|Pi|Sigma|Phi|Psi|Omega)\b", body))
    for g in sorted(greek - _NOT_SYMBOLS):
        if not any(g in s for s in table):
            warn("SYM-UNDECLARED", f"正文用了 \\{g} 但符号表里没有——"
                                    f"注意一符多义：ρ(密度/电阻率)、σ(电导率/表面张力)、μ(磁导率/黏度)")


#: "0.35 mm" / "$0.28$ mm" / "2.74 cm/s" / "2.80 ms" …
#: ★ `(?![eE][-+]?[0-9])` —— **拒绝科学计数法的尾数。**
#
#  **血泪教训（electrical-damping）**：正文里写 `B_E ≈ 5e-5 T`（地磁），
#  这条正则读出来是 **`5 T`** —— **静默地错了 10⁵ 倍**，然后拿去和契约对质，
#  报出一个完全莫名其妙的 NUM-NOT-IN-PROSE。
#
#  magnetic-brake 全篇用 `5\times10^{-5}` 的 LaTeX 写法（那种恰好不匹配），
#  所以这个 bug 一直没被看见。**换一种同样合法的写法，它就炸了。**
#
#  > **一个把 5e-5 读成 5 的数字提取器，比没有数字提取器更危险 ——
#  > 它会用一个凭空捏造的数字去指控你。**
#  科学计数法要挡**两头**（第一版只挡了一头，被自检当场抓住）：
#    · `(?![eE][-+]?[0-9])` —— 挡**尾数**：`5e-5 T` 里的头一个 `5`
#    · `(?<![0-9.eE])(?<![eE][-+])` —— 挡**指数**：`5e-5 T` 里的**第二个** `5`
#      （只挡尾数是不够的：正则会往后挪，从指数里再抠一个 `5` 出来配上 ` T`。
#       `1.2e-3 mm` 更离谱 —— 它读出来是 `3 mm`。）
_NUMUNIT = re.compile(
    r"(?<![0-9.eE])(?<![eE][-+])"
    r"([0-9]+(?:\.[0-9]+)?)(?![eE][-+]?[0-9])"
    r"\s*\$?\s*(?:\\[,; ])?\s*(?:\\mathrm\{)?"
    r"(cm/s|m/s|mm|cm|km|ms|mT|kHz|Hz|[mT])(?:\})?(?![A-Za-z0-9])"
)

#: 宽松版：只用来扫**契约**，回答「这个数在契约里出现过吗」。
#  契约里常把数写在括号/区间里：`[0.73, 8.64] mm`、`A ∈ [A_c, A_lin] = [0.73, 8.64] mm`。
#  严格版要求数和单位紧挨着，于是 `8.64` 被判成「只在正文里出现的野数」—— 假 NUM-DESYNC。
_NUMUNIT_LOOSE = re.compile(
    r"(?<![0-9.eE])(?<![eE][-+])"
    r"([0-9]+(?:\.[0-9]+)?)(?![eE][-+]?[0-9])"
    r"[^A-Za-z0-9]{0,8}?(?:\\mathrm\{)?"
    r"(cm/s|m/s|mm|cm|km|ms|mT|kHz|Hz|[mT])(?![A-Za-z0-9])"
)

#: ★★ **这条检查分辨不了「同一个量的两个版本」和「两个不同的量」。**
#
#  它的代理是「同单位 + 数值接近」。而在一篇有十几个毫米量的分析里
#  （a/2、线性化上限、阻尼峰位、初振幅、间隙、线径、绕组厚度、定位误差……），
#  两两之间到处都是 1.1–1.4 的比值 —— **代理没有分辨力。**
#
#  **我试过加一条「同单位的数太多就闭嘴」的守卫。结果：
#  它把 magnetic-brake 那个真实的脱钩（契约 0.35 mm / 正文 0.277 mm）也一起放走了。**
#  （——被注入式回归当场抓住。**为了消误报而削弱一条检查，是最容易犯、也最贵的错。**）
#
#  所以：**不削弱它，而是让它承认自己的局限**，把裁决权交给人。
#  这条是 WARNING，不是 ERROR —— 它的职责是**指出来**，不是**判定**。
_DESYNC_NOTE = (
    "**这条检查分辨不了「同一个量的两个版本」和「两个不同的量」—— 请人工核一遍。**"
    "  若确是两个不同的量（如「线径 0.4 mm」vs「定位误差 0.5 mm」），忽略本条。"
)

#: 换算到 SI —— 用来和 model-spec 的 parameters（SI）比对
_SI = {"mm": 1e-3, "cm": 1e-2, "m": 1.0, "km": 1e3,
       "ms": 1e-3, "s": 1.0, "cm/s": 1e-2, "m/s": 1.0,
       "mT": 1e-3, "T": 1.0, "Hz": 1.0, "kHz": 1e3}


def check_number_desync(md: str, spec: dict) -> None:
    """★ 契约里的数字，正文里是不是**同时**存在另一个"接近但不等"的值？

    **修订只改了推导、没改预测表和契约 —— 这是流水线里最阴的一种脱钩，
    因为没有任何东西会发现它。**

    真实案例（magnetic-brake）：审稿人 r1 抓到"达到终速的距离用了错误捷径，
    高估 27%，精确值 0.28 mm"。作者改了 §6.2 的**推导**，但漏了：
      · 01-analysis.md 的**预测表 P7**（还写着 0.35 mm）
      · handoff/model-spec.json 的 **F-3**（还写着 0.35 mm）
    **而这两处恰恰是下游真正读的东西。** 这个 bug 一路活到 Skill 2 手里。

    这个检查抓的就是"正文里 0.28 和 0.35 并存，而契约用的是 0.35"。
    """
    if not spec:
        return

    prose = {}                                    # unit -> {value}
    for v, u in _NUMUNIT.findall(md):
        prose.setdefault(u, set()).add(float(v))

    # 契约里"故意不同"的数：基准值 + 扫描端点。**扫描端点本来就是两个不同的数**，
    # 不是脱钩。不排除它们，这个检查会被自己的噪声淹掉。
    legit_si = set()
    for p in spec.get("parameters", []):
        for x in ([p.get("value")] + list(p.get("sweep_range") or [])):
            if isinstance(x, (int, float)):
                legit_si.add(float(x))

    def is_legit(v: float, unit: str) -> bool:
        si = v * _SI.get(unit, 1.0)
        return any(abs(si - L) <= 0.01 * max(abs(si), abs(L)) for L in legit_si if L)

    # ★ `json.dumps` 会把反斜杠**再转义一遍**：契约里的 `4\ \mathrm{mm}`
    #   在 dumps 之后变成 `4\\ \\mathrm{mm}`，于是下面「这个数在契约里也出现过吗」
    #   的正则（它认的是**单个**反斜杠）**永远匹配不上** ——
    #   结果：契约里明明白白写着的数，被当成「只在正文里出现的野数」，
    #   于是 NUM-DESYNC 疯狂误报。
    #
    #   **实测（electrical-damping）**：5 条 NUM-DESYNC 里 4 条是这么来的。
    #   **一个总是响的警报，等于没有警报 —— 而且它会训练人无视所有警报。**
    spec_txt = json.dumps(spec, ensure_ascii=False).replace("\\\\", "\\")

    spec_nums = {}
    #: 契约里**所有**出现过的「数 + 单位」—— 用来判断「另一个值是不是也是契约里的量」。
    #  只扫 expected_shape / criterion_check 是不够的：一个数可能定义在 A-5 的 criterion 里、
    #  被 F-1 的 expected_shape 引用。**扫全文，而且用宽松的正则**
    #  （契约里常写成 `[0.73, 8.64] mm`、`(35%, 45%)` —— 数和单位之间隔着标点）。
    spec_all: dict[str, set[float]] = {}
    for v, u in _NUMUNIT_LOOSE.findall(spec_txt):
        spec_all.setdefault(u, set()).add(float(v))

    for f in spec.get("figures", []):
        for v, u in _NUMUNIT.findall(f.get("expected_shape", "") or ""):
            spec_nums.setdefault(u, set()).add((float(v), f.get("id", "?")))
    for a in spec.get("assumptions", []):
        for v, u in _NUMUNIT.findall(a.get("criterion_check", "") or ""):
            spec_nums.setdefault(u, set()).add((float(v), a.get("id", "?")))

    for unit, entries in spec_nums.items():
        for val, src in entries:
            if is_legit(val, unit):
                continue                          # 它就是某个参数/扫描端点
            others = prose.get(unit, set())
            # 舍入不算脱钩：契约写 0.277 mm、正文写 0.28 mm，是同一个数
            near = [o for o in others if abs(o - val) <= 0.02 * max(abs(o), abs(val))]
            if not near:
                # ★ **这一条才是主力。** magnetic-brake 的真实脱钩（契约 0.35 mm、
                #   正文修订成 0.277 mm）正是被它抓到的：**契约里的数，正文里根本找不到。**
                warn("NUM-NOT-IN-PROSE",
                     f"契约里 {src} 用的 `{val:g} {unit}`，在 01-analysis.md 里找不到 —— "
                     f"正文与契约可能已脱钩")
                continue

            for o in others:
                if o in near or is_legit(o, unit):
                    continue
                # ★ 另一个值**也在契约里** ⟹ 它是**另一个量**，不是同一个数的两个版本。
                #
                #   实测（electrical-damping）：正文里同时有 `10.46 mm`（阻尼峰位）、
                #   `8.64 mm`（线性化上限）、`5.4 mm`（a/2）、`4 mm`（磁体到线圈的间隙）……
                #   **一篇有很多毫米量的分析里，「同单位 + 数值接近」这个代理彻底失效。**
                #   ——除非先把「两个都在契约里声明过」的对子排掉。
                if any(abs(o - s) <= 0.01 * max(abs(o), abs(s))
                       for s in spec_all.get(unit, set())):
                    continue
                # ★ 窗口收紧到 (1.05, 1.4)。
                #
                #   这条检查瞄准的是**一种很具体的失败**：「修订漏了一个修正因子」。
                #   magnetic-brake 的真实案例：0.35 mm（漏减了 0.99 项）vs 0.277 mm（真值）——
                #   **比值 1.26**。这类遗漏的比值几乎总在 1.1–1.3。
                #
                #   而 1.8 的上限会把**两个毫不相干的量**扫进来：
                #   electrical-damping 里同时有 5.4 mm（a/2）、8.64 mm（线性化上限）、
                #   6 mm（初振幅）、4 mm（磁体到线圈的间隙）…… 两两之间到处都是 1.1–1.8。
                #   **在一篇有很多同单位长度的分析里，「同单位 + 数值接近」这个代理彻底失效。**
                r = max(o, val) / min(o, val) if min(o, val) > 0 else 99
                if not (1.05 < r < 1.4):
                    continue
                warn("NUM-DESYNC",
                     f"正文里**同时**存在 `{val:g} {unit}` 和 `{o:g} {unit}`"
                     f"（相差 {(r-1)*100:.0f}%），而契约（{src}）用的是 `{val:g} {unit}`，\n"
                     f"        **且 `{o:g} {unit}` 在契约里根本没出现过。**\n"
                     f"        **修订可能只改了一处。** 一个数通常住在四个地方：推导、机制预算表、\n"
                     f"        **预测表**、**model-spec.json** —— 后两处才是下游真正读的东西。\n"
                     f"        改一个数，grep 整个工作区。\n"
                     f"        {_DESYNC_NOTE}")


# ---------------------------------------------------------------- ★★ 修订传播
#
#  `CLAUDE.md` 血泪教训 4 白纸黑字写着：
#
#     「修订必须传播到「结论」和「契约」，不能只落在「推导」上。
#       **目前没有机械检查能发现这种脱钩。**」
#
#  **这两道门就是那个「没有」。**
#
#  它们之所以**可能**，是因为归档链 `handoff/model-spec-r{n}.json` 是强制的 ——
#  **旧值是有物证的。** 于是「修订有没有传播」这件事，从「靠人读」变成「拿旧值 grep 新文档」。
#
#  **实测（electrical-damping r2）**：一次审稿抓出 **13 处** r1 旧值还活着 ——
#  包括 `targets[]` 的三个 baseline、`(26).latex` 里**同一个方程 LHS 用 M、阻尼项用 M_eff**、
#  以及一个改名后无人认领的孤儿符号 `\gamma_0`。**而 checker 报的是零 ERROR。**

def _spec_values(spec: dict) -> dict[str, tuple[float, str]]:
    """契约里所有「有名字的数」：(值, 单位)。**单位是必须的** —— 它是 STALE-VALUE 消误报的唯一手段。"""
    out: dict[str, tuple[float, str]] = {}
    for p in spec.get("parameters", []):
        v = p.get("value")
        if isinstance(v, (int, float)) and p.get("symbol"):
            out[p["symbol"]] = (float(v), str(p.get("unit") or ""))
    for t in spec.get("targets", []):
        v = t.get("baseline_value")
        if isinstance(v, (int, float)) and t.get("symbol"):
            out["target:" + t["symbol"]] = (float(v), str(t.get("unit") or ""))
    return out


#: 契约存 SI（0.000765 m），正文写工程单位（0.765 mm）。同一个数，两种写法。
_SCALE_BY_UNIT: dict[str, list[float]] = {
    "m": [1.0, 1e3, 1e2],          # m / mm / cm
    "kg": [1.0, 1e3],              # kg / g
    "s": [1.0, 1e3],               # s / ms
    "H": [1.0, 1e3],               # H / mH
    "T": [1.0, 1e3],               # T / mT
}


def _literals(v: float, unit: str = "") -> set[str]:
    """一个数在正文里可能被写成的样子。

    ★ **只生成 3–5 位有效数字。绝不生成 2 位。**
      `0.1361` 在 2 位下是 `0.14` —— 而 `0.14 s`、`0.14 mm` 满世界都是。
      **一个总是响的警报，等于没有警报，而且它会训练人无视所有警报。**
      3 位起步就没有这个问题：`0.136` 只可能是那个数。

    ★ 同时按单位做换算：契约存 SI，正文写工程单位。
    """
    out: set[str] = set()
    for scale in _SCALE_BY_UNIT.get(unit.strip(), [1.0]):
        x = v * scale
        if x == 0 or abs(x) < 1e-6 or abs(x) > 1e7:
            continue
        for sig in (3, 4, 5):
            s = f"{x:.{sig}g}"
            if "e" in s or "E" in s:
                continue
            if len(s.lstrip("-0.")) >= 3:      # ★ 至少三位有效数字
                out.add(s)
    return out


def _cited(lines: list[str], i: int, tag: str) -> bool:
    """第 i 行（1-based）引用旧值时，**点名版本了吗**？

    ★ 点名可以出现在三个地方 —— 这三条都不是宽容，是**为了不和「零号规则」打架**：

      ① **行内**：`r1 报的是 0.765 mm`
      ② **上文三行内**：`r1 的验收方式是（逐字）：` 后面跟一个 blockquote。
         **逐字引文里不许塞任何标记**（那会污染引文，而引文必须是原文的子串），
         所以标记只能落在引导句上。
      ③ **节标题里**：`## 11 · r1 → r2 修订记录` —— 整节都在谈旧值，这是它的职责。

    ⟹ **「我在修订记录里引用旧值」合法，「我忘了改」不合法 —— 两者在语法上被区分开了。**
    """
    if tag in lines[i - 1]:
        return True
    for j in range(max(0, i - 4), i - 1):                      # 上文三行
        if tag in lines[j]:
            return True
    # 往上走，**沿途每一级标题都算** —— 子标题继承父节的豁免。
    # （`## 11 · r1 → r2 修订记录` 下面的 `### 三条被改动的结论`，当然还在修订记录里。）
    for j in range(i - 1, -1, -1):
        m = re.match(r"(#{1,6})\s", lines[j])
        if not m:
            continue
        if tag in lines[j]:
            return True
        if len(m.group(1)) <= 2:                               # 走到 h2/h1 就到顶了
            return False
    return False


def check_stale_values(ws: Path, md: str, problem_md: str, spec: dict) -> None:
    """★★ 拿归档里的**旧值**，去 grep 新文档。还搜得到 = 修订没传播干净。"""
    if not spec:
        return
    archives = sorted((ws / "handoff").glob("model-spec-r*.json"))
    if not archives:
        return

    new = _spec_values(spec)
    spec_txt = json.dumps(spec, ensure_ascii=False, indent=2)
    docs = [("01-analysis.md", md.splitlines()),
            ("00-problem.md", problem_md.splitlines()),
            ("handoff/model-spec.json", spec_txt.splitlines())]

    for arc in archives:
        m = re.search(r"model-spec-(r\d+)\.json", arc.name)
        if not m:
            continue
        tag = m.group(1)                                   # "r1"
        try:
            old_spec = json.loads(arc.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        old = _spec_values(old_spec)

        # ---- ① 值变了，但旧值还在文档里
        for sym, (ov, unit) in old.items():
            if sym not in new:
                continue                                   # 符号没了 —— 归 ② 管
            nv = new[sym][0]
            if abs(ov - nv) <= 1e-12 * max(abs(ov), 1.0):
                continue
            #: ★ 有**物理单位**的量（长度/质量/时间…），不可能写成一个百分数。
            #  实测误报：`w = 3.6 mm` 的字面量 `3.6`，撞上了正文里的
            #  「涡流占本底的 **3.6%**」—— 那是一个完全无关的百分比。
            #  **这不是放宽**：一个以 mm 为单位的长度，写成 `3.6%` 是没有意义的。
            #  （而无量纲量 `unit: "1"` 不吃这条豁免 —— 它**可以**是百分数。）
            tail = r"(?![0-9])(?!\s*[%％])" if unit.strip() in _SCALE_BY_UNIT else r"(?![0-9])"
            for lit in _literals(ov, unit):
                if lit in _literals(nv, unit):
                    continue                               # 舍入后撞车，不算
                pat = re.compile(rf"(?<![0-9.]){re.escape(lit)}{tail}")
                for fname, lines in docs:
                    for i, line in enumerate(lines, 1):
                        if not pat.search(line):
                            continue
                        if _cited(lines, i, tag):
                            continue                       # ★ 点了名的引用 —— 放行
                        err("STALE-VALUE",
                            f"{fname}:{i} 还写着 `{lit}` —— 那是 **{tag} 的 {sym}**"
                            f"（{tag}: {ov:g} → 现在: {nv:g}）。\n"
                            f"        **修订没传播到这里。** 一个数住在四个地方：推导 / 机制预算表 / "
                            f"**预测表** / **model-spec.json** —— 后两处才是下游真正读的。\n"
                            f"        若这一行是**故意**引用旧值（修订记录里对比新旧），"
                            f"**在同一行里写上 `{tag}`** —— 引用必须点名版本。\n"
                            f"        > {line.strip()[:100]}")

        # ---- ② ★ 符号被改名了，但旧名字还在（孤儿符号）
        gone = {s for s in old if not s.startswith("target:")} - {
            s for s in new if not s.startswith("target:")}
        for sym in sorted(gone):
            if len(sym) < 3:
                continue
            for fname, lines in docs:
                for i, line in enumerate(lines, 1):
                    if sym not in line or _cited(lines, i, tag):
                        continue
                    err("STALE-SYMBOL",
                        f"{fname}:{i} 还在用 `{sym}` —— 它在 {tag} 里存在，"
                        f"**在当前契约的 symbols/parameters 里已经没有了**。\n"
                        f"        改名（如 γ_0 → γ_oc）必须**全文**传播。"
                        f"一个无人认领的孤儿符号，下游会当成一个新的量去找它的定义。\n"
                        f"        > {line.strip()[:100]}")


# ---------------------------------------------------------------- ★★ 判据不许失明
#
#  **r2 的血泪教训（这一条是全套 skill 里最贵的一课）**：
#
#  r1 的一条判据在极值点**结构性失明**（一阶判据用在 |G| 的峰上 ⟹ 分子恒为零
#  ⟹ 对任何振幅都报「线性 ✓」）。审稿抓到了，我把它拆了 —— **然后换上了三把新的失明的锁。**
#
#  **为什么没发现？因为我只跑了一个方向。**
#  我验证了「新判据在**正确模型**上通过」（R² = 1.000000，看着真漂亮），
#  **从没验证「它在**错的模型**上会不会照样通过」。**
#
#  > **一条判据，只在正确模型上跑过 —— 那不叫验证，那叫「换了一把新的失明的锁」。**
#
#  ⟹ 契约必须带一张 `criterion_matrix`（判据 × 模型），而且它必须是**跑出来的**，不是写出来的。

def _catch_ids(c: dict) -> list[str]:
    """`catches` 可以是 `[id]`，也可以是 `[{id, detail}]`（后者带「抓到时偏了多少」）。

    ★ **非空 ≠ 有效** —— id 必须能解析回 `wrong_models`（CLAUDE.md 教训 6）。
    """
    out: list[str] = []
    for x in _as_list(c.get("catches")):
        if isinstance(x, dict) and x.get("id"):
            out.append(str(x["id"]))
        elif isinstance(x, str):
            out.append(x)
    return out


def check_criterion_matrix(spec: dict) -> None:
    """★★ 判据 × 模型的双向表 + **P18 的三个新维度**（r3 审稿逼出来的）。"""
    if not spec:
        return
    cm = spec.get("criterion_matrix")
    if not cm:
        err("CRIT-MATRIX-MISSING",
            "契约里没有 `criterion_matrix` —— **每一条可证伪判据都必须双向跑过**：\n"
            "        ① 在**正确模型**上：它会不会**误杀**？\n"
            "        ② 在几个**错模型**上：它抓不抓得到？\n"
            "        **只跑第①个方向 = 换了一把新的失明的锁。**（这是 r2 真实翻车的地方。）\n"
            "        错模型必须是「学生真的会写出来的东西」，不是稻草人。\n"
            "        见 SKILL.md「Stage 8.5 · 判据的双向验证」。")
        return

    wrong = {w.get("id") for w in cm.get("wrong_models", []) if w.get("id")}
    crits = cm.get("criteria", [])
    if len(wrong) < 3:
        err("CRIT-TOO-FEW-MODELS",
            f"只列了 {len(wrong)} 个错模型 —— **至少 3 个**，而且每个都得是"
            f"「学生真的会写出来的东西」（如「磁通最大处阻尼最大」、「常数阻尼」、"
            f"「某个系数错 30%」），**不是稻草人**。\n"
            f"        （r2 真实翻车：我给的对照模型是个稻草人，它和正确模型给出**相同**的截距。）")
    if not crits:
        err("CRIT-MATRIX-EMPTY", "criterion_matrix.criteria 是空的")
        return

    # ── ① 每个错模型必须被**判据的字面逻辑**抓到（★ 退化不算 —— P18 ⑤）
    for w in sorted(wrong):
        if any(w in _catch_ids(c) for c in crits):
            continue
        degen = [c.get("id", "?") for c in crits if w in _as_list(c.get("degenerate_on"))]
        extra = (f"\n        ★★ 它在 {'、'.join(degen)} 上是 **DEGENERATE**（提取失败）—— "
                 f"**那不是「被抓到」，那是拟合器崩了。**\n"
                 f"        （r3 真实翻车：naive-A 的「被五条判据抓到」，明细全是「提不出 Γ」"
                 f"—— **一个记账截断，被记了五次。**）\n"
                 f"        **判据必须去看那件事本身**（如「它一下子就停了」），"
                 f"而不是依赖一个恰好会崩的拟合器。" if degen else "")
        err("CRIT-MODEL-UNCAUGHT",
            f"错模型 `{w}` **没有任何一条判据抓得到它** —— 它会一路走到评委面前。{extra}")

    for c in crits:
        cid = c.get("id", "?")
        if not c.get("passes_correct"):
            err("CRIT-FALSEKILL",
                f"判据 `{cid}` 在**正确模型**上不通过 —— **它会误杀一个正确的模型。**\n"
                f"        （r1/r2 各翻车一次：P1 的原判据被 ±0.5 mm 定位误差判死；"
                f"r2 的抛物线顶点判据被 G 的非线性判死 +17.5%。）\n"
                f"        **判据的适用区间由物理定**（如「G 的线性度 <1% 的那段 z₀」），"
                f"**不是随手画的。**")
        caught = _catch_ids(c)
        if not caught:
            err("CRIT-BLIND",
                f"判据 `{cid}` **在所有错模型上都通过** —— **它是一把失明的锁。**\n"
                f"        一条从来抓不到任何东西的判据，和一条**不存在**的判据，行为上完全一样。\n"
                f"        **要么找到它真能判别的东西，要么删掉它。**")
        for w in caught:
            if w not in wrong:
                err("CRIT-CATCH-DANGLING",
                    f"判据 `{cid}` 声称抓得到 `{w}`，但 wrong_models 里没有这个 id —— "
                    f"**编出来的 id 是非空的。**")

        # ── ② ★ 容差必须有来源（P18 ①）
        if not str(c.get("tolerance_source") or "").strip():
            err("CRIT-TOLERANCE-UNSOURCED",
                f"判据 `{cid}` 没有 `tolerance_source` —— **它的容差是一个裸数字。**\n"
                f"        **容差不是随手定的**：它必须由**测量误差 + 预言侧的不确定度**算出来。\n"
                f"        （r3 真实翻车：源码里 `< 0.12` / `< 0.20` / `< 0.15`，"
                f"而正文写的是 15% —— **两处矛盾，而且两条判据的阈值只活在 `.py` 里**。\n"
                f"        §9 说 Γ 只测到 2% —— **一条比误差棒宽 6 倍的判据，"
                f"抓不到一个 10% 的偏置。**）")

    # ── ③ ★★ 「不误杀」必须在协议自己承认的系统误差上跑过（P18 ④）
    rs = cm.get("robustness_scan")
    if not (isinstance(rs, dict) and rs.get("parameter")):
        err("CRIT-NO-ROBUSTNESS",
            "`criterion_matrix` 没有 `robustness_scan` —— "
            "**「不误杀」那一列只在理想点上跑过。**\n"
            "        **判据必须在协议自己列出的每一项系统误差的量级上各跑一遍**，"
            "并报出它的**有效窗口**。\n"
            "        （r3 真实翻车：`crit_P3` 把 z₀ 钉死在**精确的 0.0**，"
            "而同一份分析的 §9 写着「**不要试图把磁体对准中心**」——\n"
            "        实算：**残余偏心就判死正确模型**，而噪声预算是 ±0.1 mm。）\n"
            "        字段：`{parameter, why, scan_upper_bound, delta_max, delta_max_bracket, verdict}`。")
    else:
        # ★★★ r5 审稿 H1：这道门原来挂在 `elif isinstance(delta_max,(int,float))` 上 ——
        #   **`delta_max=None` 时整道门被静默跳过。** 而「扫描范围太小」恰好产出 None
        #   （`criterion_matrix` 的 `_delta_star`：扫描上界 hi < 真边界 ⟹ `return None`）
        #   ⟹「作者挑的扫描端点」这个病从「网格间距」（r4）升到了「扫描上界」（r5），门又瞎。
        #   **更糟：我的 `--selftest` 里 `none_ok` 用例把这个跳过钉成了「预期行为」，给盲区盖了章**
        #   —— 见文件头「★ 盲区探针」：一道门的 selftest 本身也是自评。
        #   ⟹ `delta_max=None` 不再是逃生舱：**必须报 `scan_upper_bound`**，否则「处处稳健」不可证伪。
        dm = rs.get("delta_max")
        sub = rs.get("scan_upper_bound")
        budget = rs.get("systematic_error_budget")   # ★ r6-H2：scan_upper_bound 的下限参照
        if not isinstance(sub, (int, float)):
            err("CRIT-ROBUSTNESS-COARSE",
                "`robustness_scan` 缺 `scan_upper_bound`（δ 到底扫了多远）—— "
                "**没有它，`delta_max=None`（「处处稳健」）不可证伪。**\n"
                "        「扫描范围太小 ⟹ 没撞到边界 ⟹ `delta_max=None`」与「真的处处稳健」"
                "编码成了同一个 `None`。\n"
                "        （r5 真实翻车：门挂在 `elif delta_max is number` 上，None 时整道门被跳过，"
                "而 selftest 把这个跳过钉成「预期行为」——盲区被写进了自检。）\n"
                "        必须报 `scan_upper_bound`；「处处稳健」= 在 `[0, scan_upper_bound]` 上不误杀。")
        elif not (isinstance(budget, (int, float)) and budget > 0):
            err("CRIT-ROBUSTNESS-COARSE",
                "`robustness_scan` 缺 `systematic_error_budget`（协议自报的系统误差量级，如 §9 噪声预算）——\n"
                "        **没有它，`scan_upper_bound` 够不够远无法机械判定**"
                "（r6-H2：`scan_upper_bound=0.05mm` < 0.10mm 噪声预算，照样报「处处稳健」）。\n"
                "        ★ budget 是作者报的数，门只保证 `scan_upper_bound ≥ 3×budget`；"
                "**budget 本身诚不诚实（对比 §9）靠人读/审稿**（诚实 scope）。")
        elif float(sub) < 3 * float(budget):
            err("CRIT-ROBUSTNESS-COARSE",
                f"`scan_upper_bound={sub:g}` < 3×`systematic_error_budget={budget:g}` —— "
                f"**δ 扫得不够远，「处处稳健 / 有效窗口」不足信**（r6-H2）。\n"
                f"        扫到 ≥ 3× 系统误差，边界才在噪声够不到的地方。")
        elif dm is None:
            # 「处处稳健」：门已保证 scan_upper_bound 写出来了（上面查过）。
            # 「扫得够不够远」（对比噪声预算）是**物理判断** —— 门不冒充能判它（诚实 scope）。
            pass
        elif isinstance(dm, (int, float)):
            # ★★ r4-H1：有边界 ⟹ 必须**二分定出**（暴露窄 bracket），不能靠网格撞。
            dm = float(dm)
            br = rs.get("delta_max_bracket")
            if not (isinstance(br, (list, tuple)) and len(br) == 2
                    and all(isinstance(x, (int, float)) for x in br)):
                err("CRIT-ROBUSTNESS-COARSE",
                    f"`robustness_scan.delta_max = {dm:g}` 有值，却**没有 `delta_max_bracket`** —— "
                    f"没法证明这个边界是二分定出来的（r4：网格 0.10→0.17 跳过真边界 0.135）。\n"
                    f"        像 `eps_star` 那样二分，暴露 `delta_max_bracket = [last_pass, first_fail]`。")
            elif not (0 <= float(br[0]) <= dm <= float(br[1]) <= float(sub)):
                err("CRIT-ROBUSTNESS-COARSE",
                    f"`delta_max_bracket = [{br[0]:g}, {br[1]:g}]` 不合法 —— 必须 "
                    f"`0 ≤ last_pass ≤ delta_max ≤ first_fail ≤ scan_upper_bound`"
                    f"（delta_max={dm:g}, scan_upper_bound={sub:g}）。")
            elif (float(br[1]) - float(br[0])) > 0.05 * float(br[1]):
                lo, hi = float(br[0]), float(br[1])
                err("CRIT-ROBUSTNESS-COARSE",
                    f"`robustness_scan` 的边界**太粗**：括号 [{lo:g}, {hi:g}] 相对宽 "
                    f"**{(hi-lo)/hi:.0%}**（门槛 5%）—— 网格撞的，不是二分定的。\n"
                    f"        （r4-H1：网格报 0.17，二分定出真值 0.135 —— 虚高 30%，裕度 1.3→谎报 1.7 倍。）\n"
                    f"        二分到 `last_pass` 与 `first_fail` 相邻（像 `eps_star`）。")
            # ★ 诚实 scope（r5-H1②）：宽度检查只证 bracket **自洽**，**证不了它真是二分跑出来的** ——
            #   手写一个窄括号（把 r4 判死的虚报值 0.17 配上 [0.169,0.170]）照样过。
            #   **provenance 靠「先跑 `criterion_matrix.py` 重新生成 `matrix.json`」保证，不靠这道门。**
            #   （所以这条盲区探针在 selftest 里是**记录在案的已知局限**，不是「已修好」。）
            #
            # ★★★ r7 审稿 H1（P17 长在门里）：上面查的全是「bracket 是不是二分定的」，
            #   **却从没查那个 load-bearing 的量：margin = delta_max / budget**（悬崖在不在噪声外）。
            #   实测：delta_max=0.05mm < budget=0.10mm（裕度 0.5×）—— 噪声一涨就把残余偏心推过悬崖、
            #   **正确模型被自己的判据误杀**，而门 0 ERROR。散文大书特书的「安全裕度 1.34×」**没有门**。
            #   ⟹ 硬地板 `delta_max ≥ budget`（悬崖至少在噪声外）。薄裕度（1–3×）靠散文披露（人读/审稿）。
            if dm < float(budget):
                err("CRIT-ROBUSTNESS-COARSE",
                    f"`delta_max={dm:g}` < `systematic_error_budget={budget:g}` —— "
                    f"**判死悬崖落在噪声里（裕度 {dm/float(budget):.2f}× < 1）**：噪声一涨就把残余偏心"
                    f"推过悬崖，**正确模型被自己的判据误杀**。\n"
                    f"        （r7-H1：**P17 长在门里** —— budget 门查的是 `scan_upper_bound`（扫多远），"
                    f"而 load-bearing 的量是 `margin = delta_max/budget`。散文里的「安全裕度」必须有门。）\n"
                    f"        ★ 硬地板 = margin ≥ 1（悬崖至少在噪声外）；薄裕度（1–3×）本门放行、靠散文披露。")
        else:
            err("CRIT-ROBUSTNESS-COARSE",
                f"`robustness_scan.delta_max` 类型非法（{type(dm).__name__}）—— 只能是数或 `null`。")

    # ── ④ ★★ 错模型的「错误幅度」不许是挑出来的 —— 扫 ε，报 ε*（P18 ②）
    md = cm.get("min_detectable")
    if not (isinstance(md, dict) and any(
            isinstance(v, dict) and "eps_star" in v for v in md.values())):
        err("CRIT-NO-MIN-DETECTABLE",
            "`criterion_matrix` 没有 `min_detectable` —— "
            "**「这个错模型被抓到了 ✓」这句话没有信息量，因为幅度是你自己挑的。**\n"
            "        **必须扫错误幅度 ε，报「最小可检测幅度」ε\\*** ——\n"
            "        ε\\* 是判据集的**分辨率**，而且它是一条**可汇报的物理结论**：\n"
            "        「我们的判据能分辨 β 的 X% 偏差」是一句真话；"
            "「bug-C 被抓到了」不是。\n"
            "        （r3 真实翻车：`bug-C` 设成「β 错 **+30%**」，被 12% 的容差抓到 ✓ ——\n"
            "        **而作者自己在 `why_a_student_writes_it` 里写着**"
            "「标称 B_r 公差 ±5% ⟹ **b 偏 ±10%**」。\n"
            "        **10% < 12% ⟹ 他亲手描述的那个真实场景，五条判据一条都抓不到。**）\n"
            "        字段：`{<错模型>: {eps_star, caught_by, note}}`。")


# ------------------------------------------------------- ★★★ 内嵌副本 vs matrix.json 脱钩
#
#  **教训（electrical-damping r6 审稿，真实发生 —— 第七次复发的真 MAJOR）**：
#  上面 `check_criterion_matrix` 读的是 `model-spec.json` **内嵌**的 `criterion_matrix`
#  （一份**手拷**副本），而它能和 `01-criteria/matrix.json`（`criterion_matrix.py` 的真输出）
#  **静默脱钩**。实测：把 `delta_max=0.17`（r4 判死的虚报值）+ 手写窄括号塞进**内嵌**副本、
#  `matrix.json` 留 0.1348 不动，端到端喂真 `check_analysis.py` ⟹ **0 ERROR，两份差 26%。**
#
#  > **r5/r6 那句「provenance 靠重跑 matrix.json 保证」是一张空标签 —— 重跑碰不到门消费的数据。**
#  > **而 `SKILL.md` 还谎称门会把 matrix.json 读进 model-spec。文档里的劝诫会被忽略；这道门不会。**


def _first_json_diff(a, b, path: str = "") -> str:
    """两个 JSON 结构的第一处差异（给 DESYNC 一个可定位的消息）。相等 ⟹ 空串。"""
    if type(a) is not type(b):
        return f"{path or '根'}：类型 {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                return f"{path}.{k}：matrix.json 有、内嵌无"
            if k not in b:
                return f"{path}.{k}：内嵌有、matrix.json 无"
            if d := _first_json_diff(a[k], b[k], f"{path}.{k}"):
                return d
        return ""
    if isinstance(a, list):
        if len(a) != len(b):
            return f"{path}：长度 {len(a)} vs {len(b)}"
        for i, (x, y) in enumerate(zip(a, b)):
            if d := _first_json_diff(x, y, f"{path}[{i}]"):
                return d
        return ""
    return "" if a == b else f"{path}：{a!r} vs {b!r}"


def check_matrix_desync(spec: dict, workspace: Path) -> None:
    """★★★ 内嵌 `criterion_matrix`（去掉 `script`）必须**逐字 == `01-criteria/matrix.json`**。

    ★ 诚实 scope：这把「只改内嵌一处」的攻击**堵死了**（等式检查，不是启发式）。它**证不了
      `matrix.json` 本身是不是 `criterion_matrix.py` 的新鲜输出**（「内嵌+matrix.json 两处一起改」
      仍能骗过）—— 那要 build 步骤 subprocess 重跑源码再比。**本门只保证「内嵌 == matrix.json」；
      matrix.json 的新鲜度靠「提交前先重跑 criterion_matrix.py」+ 对抗审稿兜底。**（见文件头「盲区探针」。）
    """
    if not spec:
        return
    cm = spec.get("criterion_matrix")
    if not isinstance(cm, dict):
        return                                     # 缺失归 CRIT-MATRIX-MISSING
    mp = workspace / "01-criteria" / "matrix.json"
    if not mp.exists():
        err("CRIT-MATRIX-DESYNC",
            f"内嵌 `criterion_matrix` 存在，但找不到源 `01-criteria/matrix.json` —— "
            f"**无法校验内嵌副本是不是 `criterion_matrix.py` 跑出来的。**\n"
            f"        先 `python 01-criteria/criterion_matrix.py` 生成，再同步进契约。")
        return
    try:
        mat = json.loads(mp.read_text(encoding="utf-8"))
    except Exception as e:                         # noqa: BLE001
        err("CRIT-MATRIX-DESYNC", f"`01-criteria/matrix.json` 解析失败：{type(e).__name__}: {e}")
        return
    embedded = {k: v for k, v in cm.items() if k != "script"}
    if embedded != mat:
        err("CRIT-MATRIX-DESYNC",
            f"**契约内嵌的 `criterion_matrix` 与 `01-criteria/matrix.json` 对不上** "
            f"（第一处：{_first_json_diff(embedded, mat)}）。\n"
            f"        （r6 真实翻车：门读**内嵌手拷副本**、不读 matrix.json —— 有人把 delta_max 篡改进内嵌、"
            f"matrix.json 不动，全套门 0 ERROR。这道门补那个洞。）\n"
            f"        **重跑 `criterion_matrix.py`，再把 matrix.json 逐字同步进 "
            f"`model-spec.criterion_matrix`（保留 `script`）。**")

    # ★★★ r7 审稿 H2：内嵌 == matrix.json 还不够 —— matrix.json 自己可能不是源码的**新鲜**输出。
    #   实测：删掉 / 改 `criterion_matrix.py` 而不重跑 ⟹ matrix.json 不变 ⟹ 门 0 ERROR。
    #   「忘了重跑」是教训 19 的正脸、头号失败模式 —— 有廉价封口：源码 sha256 戳进 matrix.json、门重算比对。
    #   （★ 诚实边界：这堵「改源码忘重跑」；「手改 matrix.json + 内嵌对上、源码不动」仍要 subprocess 重跑，未做。）
    sp = workspace / "01-criteria" / "criterion_matrix.py"
    stamped = mat.get("source_sha256")
    if not isinstance(stamped, str):
        err("CRIT-MATRIX-DESYNC",
            "`matrix.json` 没有 `source_sha256` 戳 —— **无法校验它是不是 `criterion_matrix.py` 的新鲜输出**"
            "（改源码忘重跑，门看不见）。\n"
            "        `criterion_matrix.py` 结尾把 `sha256(自己)` 写进 matrix.json（见 electrical-damping 实现）。")
    elif not sp.exists():
        err("CRIT-MATRIX-DESYNC",
            "`matrix.json` 有 `source_sha256`，但源 `01-criteria/criterion_matrix.py` **不存在** —— "
            "删了源码也是脱钩（r7-H2 实测：删源码，门 0 ERROR）。")
    elif (actual := hashlib.sha256(
            sp.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
          ).hexdigest()) != stamped:
        err("CRIT-MATRIX-DESYNC",
            f"`matrix.json.source_sha256` 与当前 `criterion_matrix.py` 的 sha256 **对不上** —— "
            f"**源码改了、没重跑**（教训 19 正脸：「忘了改/忘了跑」）。\n"
            f"        stamped={stamped[:12]}… vs actual={actual[:12]}…\n"
            f"        重跑 `python 01-criteria/criterion_matrix.py` 再同步进契约。")


# ---------------------------------------------------------------- ★★ 闭式里的孤儿
#
#  **教训（electrical-damping r3 审稿，真实发生）**：`STALE-VALUE` 这道门只在
#  「值**变了**，但旧值还在别处躺着」时触发（`if abs(ov-nv) <= 1e-12: continue`）。
#
#  > **而「忘了改」的定义，就是「值没变」。**
#
#  于是 `(16)/(23)/(25).closed_form` 里的 `gamma0` —— 一个在 r2 就被改名成 `\gamma_{oc}`、
#  **在当前契约的 symbols/parameters 里根本不存在**的标识符 —— 三代原封不动地活着，
#  而 `STALE-SYMBOL` 也抓不到它（它查的是**正文**，不是 `closed_form` 里的**代码**）。
#
#  **一个下游 agent 拿 `closed_form` 去 eval，用 `parameters[].symbol` 建符号表 ⟹ NameError。**
#  **而这道门只需要解析，不需要求值。**

_MATH_NAMES = {
    "sqrt", "exp", "log", "log10", "ln", "sin", "cos", "tan", "arctan", "atan",
    "sinh", "cosh", "tanh", "abs", "min", "max", "pi", "inf", "sign", "erf",
    "sum", "int", "d", "dt", "dz",                     # 微分记号
    "True", "False", "None", "and", "or", "not", "if", "else", "for", "in",
}

_IDENT = re.compile(r"(?<![\w.])([A-Za-z_]\w*)")
#: `tau = M/b = 2.80 ms` —— 数字 + 空格 + 字母 ⟹ 那是**单位**，不是标识符。
_UNIT_AFTER_NUM = re.compile(r"\d\s+([A-Za-z_]\w*)")
#: `Bz_coil(z)` / `G(z0)` —— 后面跟 `(` 的是**函数**，它可以是数值定义的。
_CALLED = re.compile(r"([A-Za-z_]\w*)\s*\(")
#: ★ **只有「单个标识符（可带形参）」的左边才是一次定义。**
#
#   **这道门第一版就栽在这里**（而且是它自己要抓的那个 bug）：
#   `(16).closed_form` 是 `1/(gamma - gamma0) = 2*M_eff*(R+R_c)/G(z0)**2` ——
#   左边是一个**表达式**，不是定义。第一版把 LHS 里所有标识符都当成「已定义」，
#   于是 **`gamma0` 把自己定义了，门对它彻底失明。**
#
#   > **我建的新门，在它该响的地方没响 —— 而我差一点就交付了。**
#   > **这就是本轮的全部内容：拆掉一把瞎锁，换上的新锁多半也是瞎的。**
#   > **⟹ 反向用例（`(16)` 这一行）已经钉进 `--selftest`。**
_DEF_LHS = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:\(([^)]*)\))?\s*$")


def _ascii_variants(sym: str) -> set[str]:
    r"""一个契约符号（LaTeX）在 `closed_form` 里可能被写成的**标识符**。

    契约写 `\mu_0`，代码写 `mu0` —— **这是两种合法的记法，不是错误。**
    但 `\gamma_{oc}` 的变体是 `gamma_oc` / `gammaoc` —— **`gamma0` 不在里面。**

    > **⟹ 记法变体放行，而真正不存在的标识符仍然被抓住。**
    > 这正是零号规则：**不许因为「我知道他的意思」就放过。**
    > `gamma0` 和 `gamma_oc` 是两个不同的标识符，而前者在契约里**不存在**。
    """
    out: set[str] = {sym}
    for ell_as in ("ell", "l"):                          # `\ell_c` 写成 ell_c 或 l_c 都常见
        s = re.sub(r"\\(?:rm|mathrm|text|mathbf|operatorname)\b\s*", "", sym)
        s = s.replace(r"\ell", ell_as)
        s = s.replace("\\", "")                          # \max → max、\gamma → gamma、\mu → mu
        s = s.replace("^*", "_star").replace("*", "_star")   # t^* → t_star
        s = s.replace("^", "_").replace("'", "p")        # G' → Gp、R_c' → R_cp
        s = re.sub(r"\W+", "_", s).strip("_")
        s = re.sub(r"__+", "_", s)
        if s:
            out.add(s)
            out.add(s.replace("_", ""))                  # mu_0 → mu0、A_0 → A0
    return out


def _clauses(cf: str) -> list[str]:
    return [c for c in re.split(r"[;\n]|,\s+(?=[A-Za-z_]\w*\s*=)", cf) if c.strip()]


def _defs_in(cf: str) -> tuple[set[str], set[str]]:
    """(这份闭式定义的名字, 它的函数形参)。**LHS 是表达式的，一个名字都不定义。**"""
    names: set[str] = set()
    params: set[str] = set()
    for clause in _clauses(cf):
        if "==" in clause or "=" not in clause:
            continue
        m = _DEF_LHS.match(clause.split("=", 1)[0])
        if not m:
            continue                                   # ★ `1/(gamma - gamma0) = …` —— 不是定义
        names.add(m.group(1))
        if m.group(2):
            params |= {p.strip() for p in m.group(2).split(",") if p.strip()}
    return names, params


def check_closed_forms(spec: dict) -> None:
    """★★ `equations[].closed_form` 里的每个自由标识符，必须在契约里存在。"""
    if not spec:
        return
    eqs = [e for e in spec.get("equations", []) if isinstance(e.get("closed_form"), str)]
    if not eqs:
        return

    known: set[str] = set()
    for grp in ("parameters", "symbols", "targets"):
        for it in spec.get(grp, []):
            if isinstance(it, dict) and it.get("symbol"):
                known |= _ascii_variants(str(it["symbol"]))

    # ★ 跨方程引用是合法的：(23) 用的 Gp0 由 (7) 定义。
    defined: set[str] = set()
    for e in eqs:
        defined |= _defs_in(e["closed_form"])[0]

    for e in eqs:
        cf, eid = e["closed_form"], e.get("id", "?")
        local = _defs_in(cf)[1]                        # 形参只在**本式**内有效
        units = {m.group(1) for m in _UNIT_AFTER_NUM.finditer(cf)}
        called = {m.group(1) for m in _CALLED.finditer(cf)}
        free = {m.group(1) for m in _IDENT.finditer(cf)}
        for o in sorted(free - known - defined - local - _MATH_NAMES - units - called):
            err("CLOSED-FORM-ORPHAN",
                f"`equations[{eid}].closed_form` 用了标识符 `{o}` —— "
                f"**它不在契约的 parameters / symbols / targets 里。**\n"
                f"        下游拿 `closed_form` 去求值、用 `symbol` 建符号表 ⟹ **NameError**。\n"
                f"        **改名必须传播到代码，不只是正文**（`STALE-SYMBOL` 只查正文）。\n"
                f"        > {cf[:90]}")


# ---------------------------------------------------------------- ★★★ 契约自相矛盾
#
#  **这道门是 r3 审稿最贵的一条产出。**
#
#  `STALE-VALUE` 拿归档的旧值 grep 新文档 —— 但它第 960 行写着：
#
#      if abs(ov - nv) <= 1e-12 * max(abs(ov), 1.0):
#          continue                      # ← 值**没变** ⟹ 跳过
#
#  > **而「忘了改」的定义，就是「值没变」。**
#
#  **实测**：`targets[\gamma].baseline_value = 2.5978` 在 r1 / r2 / r3 **三代一字未动**，
#  而它自己的 `analytical_prediction` 算出来是 **2.3454**（偏 +10.8%）。
#  r2 审稿逐字点过它。r3 的 §11 写着「全部清掉」。**而两道 STALE-* 门都看不见它** ——
#  因为 `old == new`，门根本没往下走。
#
#  > **⟹ 一个「值从没改过」的错值，只能靠「它和自己的公式对不上」来抓。**
#  > **这是 P17 ④ 升了一层楼：这次瞎掉的不是物理判据，是「用来查判据的那道机械门」。**
#
#  ★ **顺带的收获**：`t^*` 和 `A_c` 的 baseline 是在**短路**（R=0）下算的，而 `\gamma`/`c_2`
#  是在 R=20 Ω 下算的。**这件事以前只活在作者的脑子里。** 一个 baseline 复算不出来，
#  **第一嫌疑不是「值错了」，而是「它的基准条件从来没被写下来」。**

_MATH_ENV = {k: getattr(__import__("math"), k) for k in
             ("sqrt", "exp", "log", "log10", "sin", "cos", "tan", "atan", "pi", "sinh", "cosh")}
_MATH_ENV["abs"] = abs


def _spec_env(spec: dict) -> dict:
    """契约的符号表：parameters 的 value + targets 的 baseline_value，按 ASCII 变体展开。"""
    env = dict(_MATH_ENV)
    for p in spec.get("parameters", []):
        if isinstance(p.get("value"), (int, float)) and p.get("symbol"):
            for v in _ascii_variants(str(p["symbol"])):
                if v.isidentifier():
                    env[v] = float(p["value"])
    for t in spec.get("targets", []):
        if isinstance(t.get("baseline_value"), (int, float)) and t.get("symbol"):
            for v in _ascii_variants(str(t["symbol"])):
                if v.isidentifier():
                    env.setdefault(v, float(t["baseline_value"]))   # parameters 优先
    return env


def _sig_figs(lit: str) -> int:
    """字面量的有效位数。尾零**算**有效（写出来就是精度声明：0.0350 是 3 位）。"""
    m = re.match(r"-?(\d*)\.?(\d*)(?:[eE][-+]?\d+)?$", lit.strip())
    if not m:
        return 0
    digits = (m.group(1) + m.group(2)).lstrip("0")
    return len(digits)


def _baseline_literals(spec_raw: str) -> list:
    """按 targets 顺序取每个 baseline_value 在**文件原文**里的字面量。

    用 parse_float/parse_int 钩子做第二次受控解析 —— 和 json.loads 用同一个解析器，
    转义、字段顺序、criterion_matrix 里的同名字段全都不用自己对齐。
    （正则全局 findall 的对齐是猜的；猜错时门会安静地看错行 —— 那是一把新瞎锁。）
    """
    class _Lit(float):
        def __new__(cls, s):
            o = super().__new__(cls, s)
            o._lit = s
            return o

    try:
        d = json.loads(spec_raw, parse_float=_Lit, parse_int=_Lit)
    except (json.JSONDecodeError, ValueError):
        return []
    return [getattr(t.get("baseline_value"), "_lit", None)
            for t in d.get("targets", []) if isinstance(t, dict)]


def check_spec_selfcontradict(spec: dict, spec_raw: str = "") -> None:
    """★★★ 每个 `targets[].baseline_value`，必须能由它自己的 `closed_form` 复算出来。

    容差**按字面量的有效位数定标**：s 位 ⟹ tol = 10^(1-s)（clamp 到 [5e-13, 1e-2]）。
    固定 1% 的旧门槛抓不到「一位数字的笔误」—— 实测 electrical-damping 的
    `targets[c_2]` 第 4 位 4→5（偏 +0.29%）从 1% 门下溜走，三代未响。
    合法的存储舍入 ≤ 0.5 ulp ≪ 10^(1-s)，不会误报；写得越精，管得越严 ——
    **baseline 的书写精度本身就是一份声明，门按声明执行。**
    没有原文（spec_raw 为空）时退回 1% —— 没有字面量就没有精度声明（已知局限，
    selftest 盲区探针记录在案）。
    """
    if not spec:
        return
    targets = spec.get("targets", [])
    if not targets:
        return
    env = _spec_env(spec)
    lits = _baseline_literals(spec_raw) if spec_raw else []
    if len(lits) != len(targets):                    # 原文与 dict 对不上 ⟹ 不猜
        lits = [None] * len(targets)

    for t, lit in zip(targets, lits):
        sym = t.get("symbol", "?")
        bl = t.get("baseline_value")
        cf = t.get("closed_form")
        if not isinstance(bl, (int, float)):
            continue

        if not isinstance(cf, str) or not cf.strip():
            if not str(t.get("numerical_recipe") or "").strip():
                err("TARGET-NO-RECIPE",
                    f"`targets[{sym}].baseline_value = {bl:g}` **既没有可执行的 `closed_form`，"
                    f"也没有 `numerical_recipe`。**\n"
                    f"        ⟹ 这个数**没有任何机械校验**。它可以三代原封不动地错下去"
                    f"（`targets[\\gamma] = 2.5978` 就是这么活过来的 —— 真值 2.3454）。\n"
                    f"        **二选一**：① 写 `closed_form`（Python 表达式，"
                    f"只用 `parameters[].symbol` 和其他 `targets[].symbol`）；\n"
                    f"        ② 若它只能数值求解（如「(6) 的极值」），写 `numerical_recipe` "
                    f"**显式声明**它无闭式。**不许沉默地跳过。**")
            continue

        try:
            got = eval(cf, {"__builtins__": {}}, env)              # noqa: S307
        except Exception as e:                                     # noqa: BLE001
            err("TARGET-CF-BROKEN",
                f"`targets[{sym}].closed_form` **求不出值**：{type(e).__name__}: {e}\n"
                f"        > {cf[:90]}\n"
                f"        它必须是一个**可执行的 Python 表达式**，"
                f"只用 `parameters[].symbol` / `targets[].symbol`（LaTeX 会被自动归一化成标识符）。")
            continue

        if not isinstance(got, (int, float)) or bl == 0:
            continue
        s = _sig_figs(lit) if lit else 0
        tol = max(min(10.0 ** (1 - s), 1e-2), 5e-13) if s > 0 else 1e-2
        dev = got / bl - 1
        if abs(dev) > tol:
            src = (f"{s} 位有效数字（字面量 `{lit}`）⟹ 门槛 {tol:.0e}" if s > 0
                   else "无字面量可读 ⟹ 退回 1%")
            err("SPEC-SELFCONTRADICT",
                f"★★ `targets[{sym}]` **和它自己的公式对不上**：\n"
                f"        `baseline_value` = **{bl:.8g}**，而 `closed_form` 算出 **{got:.8g}** "
                f"（偏 **{dev:+.2%}**；容差按存储精度定标：{src}）。\n"
                f"        > {cf[:90]}\n"
                f"        **这是下游会直接撞上的一个伪失败** —— Skill 2 拿 baseline 对质，"
                f"然后去「修」一段本来正确的代码。\n"
                f"        **三个嫌疑，按顺序查**：\n"
                f"        **① 一位数字的笔误**（实测：`targets[c_2]` 第 4 位 4→5，偏 +0.29% —— "
                f"固定 1% 的旧门放它三代未响）。\n"
                f"        **② 值整个是旧的**（`STALE-VALUE` 对它结构性失明："
                f"`old == new` ⟹ 那道门根本不响）。\n"
                f"        **③ 基准条件没写进公式**（如 `t^*` 是**短路** R=0 算的，"
                f"而 `\\gamma` 是 R=20 Ω —— **这件事以前只活在作者脑子里**）。")


# ---------------------------------------------------------------- ★★ 幽灵引文
#
#  **教训（真实发生，而且受害者是 `CLAUDE.md` 本身）**：
#  作者写「**r2 审稿的实测：正确模型偏 +27.7%**」。
#  **而 `01-review-r2.md` 里 "27.7" 出现 0 次 —— 它逐字写的是 17.5%（出现 8 次）。**
#
#  那个凭记忆填出来的数字，一路活到了 `CLAUDE.md` 的「教训 15」、
#  `physics-failure-patterns.md` 的弹药表、以及 `check_analysis.py` 自己的错误消息里。
#  **下一道题的模型会读到它，并且相信它。**
#
#  > **零号规则通常说：审稿人不许拿自己的推导替换作者的字。**
#  > **这是它的镜像：作者不许拿自己的记忆替换审稿人的字。**
#
#  **这和 Skill 3 的「行内引文必须是原文的子串」是同一道门** —— **编的数字不可能是原文的子串。**

#: 一行里「点名了 r{n}」+「给了一个百分数」⟹ 那个百分数必须在 01-review-r{n}.md 里。
_PCT = re.compile(r"[-+]?\d+(?:\.\d+)?(?=\s*\\?%)")
_RTAG = re.compile(r"\br([1-9])\b")
#: 豁免：这一行**自己声明了另一个来源**（本文算的，不是从审稿报告抄的）。
_OWN_SOURCE = re.compile(
    r"本文|本表|本节|本轮|我复现|复现|重算|重跑|自己算|"
    r"\d+\s*点|01-review-r\d|matrix\.json|criterion_matrix")


def _own_source_near(lines: list[str], i: int) -> bool:
    """第 i 行（1-based）的数，**在附近声明了自己的来源**吗？

    ★ 窗口是**双向**的（上下各 3 行）—— 因为一张表的说明常常在表**下面**：

        | ±6 mm（r2 用的） | 1.1% | +16.2% |        ← 数在这里
        > ★ 这里的 +16.2% 是**本表**的 9 点扫描。      ← 来源在下一行

    **这不是宽容，是和 `_cited` 同构的一条语法**：
    **模糊的归属必须被显式化 —— 「我自己算的」和「我从 r2 抄的」，在语法上被区分开。**
    """
    for j in range(max(0, i - 4), min(len(lines), i + 3)):
        if _OWN_SOURCE.search(lines[j]):
            return True
    for j in range(i - 1, -1, -1):                     # 节标题（子标题继承父节）
        m = re.match(r"(#{1,6})\s", lines[j])
        if not m:
            continue
        if _OWN_SOURCE.search(lines[j]):
            return True
        if len(m.group(1)) <= 2:
            return False
    return False


def check_review_citations(ws: Path, md: str) -> None:
    """★★ 凡是把一个数归给「r{n} 审稿」的，那个数必须能在 `01-review-r{n}.md` 里 grep 到。"""
    reports: dict[str, str] = {}
    for p in sorted(ws.glob("01-review-r*.md")):
        m = re.search(r"01-review-(r\d+)\.md", p.name)
        if m:
            reports[m.group(1)] = p.read_text(encoding="utf-8", errors="replace")
    if not reports:
        return

    lines = md.splitlines()
    for i, line in enumerate(lines, 1):
        pcts = _PCT.findall(line)
        if not pcts:
            continue
        tags = {f"r{d}" for d in _RTAG.findall(line)} & reports.keys()
        if not tags or _own_source_near(lines, i):
            continue
        for lit in pcts:
            # ★ 一行里可以同时点名 r1 和 r2（「r1 死于定位，r2 死于非线性 +17.5%」）。
            #   机械上无法判断哪个数属于哪一版 —— **但「它在任何一份被点名的报告里都查无此数」
            #   已经足够抓住那个病：你是凭记忆编的。**
            #   （放宽的是「归属」，**没有放宽「存在」** —— 后者才是这道门的全部内容。）
            if any(lit.lstrip("+-") in reports[t] for t in tags):
                continue
            err("REVIEW-CITE-GHOST",
                f"01-analysis.md:{i} 把 `{lit}%` 归给了 **{'/'.join(sorted(tags))}**，"
                f"但那些审稿报告里**根本没有这个数**。\n"
                f"        **这是一个幽灵数字 —— 你拿自己的记忆替换了审稿人的字。**\n"
                f"        （真实后果：一个编出来的 `+27.7%` 进了 `CLAUDE.md` 的教训表、"
                f"审稿人的弹药库、和本检查器自己的错误消息 —— **下一道题的模型会相信它**。）\n"
                f"        修法二选一：**① 改成报告里真有的那个数**；\n"
                f"        **② 若这个数是你自己算的**，在附近点名来源"
                f"（`本表` / `本文` / `9 点` / `01-review-r2.md L123`）——\n"
                f"        **引用必须点名出处。编出来的数字，不可能是原文的子串。**\n"
                f"        > {line.strip()[:100]}")


# ---------------------------------------------------------------- ★★ 散文里的「公式幽灵」
#
#  **教训（electrical-damping r4 审稿，真实发生 —— 出现在最讽刺的地方）**：
#  §11 那一节的标题是「我为查错值造的门自己也是瞎的」，它在讲怎么消灭一个三代未动的
#  错值 `targets[γ] = 2.5978`。**而就在那段散文里，作者自己手打了一个幽灵：**
#
#  > 「`targets[\gamma]` … 而它自己的**公式算出来是 2.3454**」——
#  > **公式实际算出来是 2.3554**（契约里就是 2.3554，`SPEC-SELFCONTRADICT` 已验）。
#  > `2.3454` 是 r3 审稿在**旧几何**下手算的数，被逐字搬进正文、没随重标定重算。
#
#  **为什么现有的门都看不见它**：
#  - `SPEC-SELFCONTRADICT` 查的是**契约字段** baseline↔closed_form（都是 2.3554，对）；
#  - `REVIEW-CITE-GHOST` 查「归给 r{n} 审稿的数」（而 2.3454 **确实**在 r3 报告里，放行）。
#  - **没有门去查「散文里归给『公式/真值』的数，代回那个 target 对不对」。**
#
#  > **零号规则的镜像第三次**（r3 是 +27.7% 归给审稿；r4 是 2.3454 归给「公式」）。
#
#  ★ **一个坑（差点又建一把瞎锁）**：幽灵 2.3454 与真值 2.3554 只差 **0.42%** ——
#  **审稿建议的「相对容差 1%」会漏掉它自己要抓的那个 bug。**
#  ∴ 必须在**散文写出的那个精度**上比（ULP）：`2.3454` 写到小数点后 4 位，
#  它与 2.3554 在第 4 位上差了 100 个单位 —— **那不是四舍五入，是另一个数。**

_GREEK_TEX2U = {r"\alpha": "α", r"\beta": "β", r"\gamma": "γ", r"\delta": "δ",
                r"\epsilon": "ε", r"\zeta": "ζ", r"\eta": "η", r"\theta": "θ",
                r"\kappa": "κ", r"\lambda": "λ", r"\mu": "μ", r"\nu": "ν",
                r"\rho": "ρ", r"\sigma": "σ", r"\tau": "τ", r"\phi": "φ",
                r"\omega": "ω", r"\Gamma": "Γ", r"\Delta": "Δ", r"\Omega": "Ω"}

#: 「这个数是某个量的**计算 / 真实值**」的措辞。**present-tense —— 无版本豁免**：
#  说「公式算出来是 N」就是断言「**现在**的公式给出 N」，它必须等于**现在**的 baseline / value。
#  （想引旧值？把它归给 r{n}（走 `REVIEW-CITE-GHOST`），不能归给「公式」。）
#  ★ r6 审稿 H4：r6 加的「约为 / 大约 / ≈」**引入了误报**（`parameters[a] … 磁场约为 0.3 T`
#    把 0.3 硬套给 a=10.784mm）—— 太泛的措辞抓到的是**别的量**的数。**r7 回退它们。**
#  ★★ r6 审稿 H3：措辞表怎么扩都不全（`计算得/等于/求得` 仍漏）——「同一个病换更大的有限数」。
#    ⟹ **本表是一个启发式**（挡最常见的形态），**不追求完备；未覆盖的措辞靠对抗审稿兜底**（见文件头）。
_VALUE_CLAIM = re.compile(
    r"(公式算出来|闭式算出来|公式给出|闭式给出|真值|正确值)"
    r"[^0-9\n]{0,10}?([-+]?\d+(?:\.\d+)?)")


def _quantity_prose_refs(sym: str, prefix: str) -> set[str]:
    """一个具名量在正文里 `prefix[...]` 的写法（LaTeX / ASCII / 希腊 unicode）。
    `prefix` ∈ {`targets`, `parameters`}。"""
    out: set[str] = set()
    for form in {sym} | _ascii_variants(sym):
        out.add(f"{prefix}[{form}]")
    for tex, uni in _GREEK_TEX2U.items():
        if sym == tex:
            out.add(f"{prefix}[{uni}]")
        elif sym.startswith(tex) and (len(sym) == len(tex) or not sym[len(tex)].isalpha()):
            out.add(f"{prefix}[{uni}{sym[len(tex):]}]")   # \gamma_{oc} → γ_{oc}
            out.add(f"{prefix}[{uni}]")
    return out


def check_prose_formula_values(md: str, spec: dict) -> None:
    r"""★★ 正文里归给「公式 / 真值」、且锚定 `targets[X]` / `parameters[X]` 的数，
    必须 = 那个量的 baseline / value（在**散文写出的精度**上比，ULP，不是相对容差 ——
    幽灵 2.3454 与真值 2.3554 只差 0.42%，相对容差 1% 会漏，ULP 在第 4 位上抓得到）。

    ★★★ **诚实 scope（r5 审稿 H2 —— 这道门守的是「一类」，不是「所有幽灵」）**：
      · **管**：`targets[X]` / `parameters[X]` 显式锚 + 值断言措辞（`_VALUE_CLAIM`），数字在锚**之后**。
      · **★ 不管（需人读 / 靠对抗审稿）—— 明写出来，不冒充「幽灵数都归我管」**：
        - **纯散文派生量**（`|G'(0)|`、A-1 的孤立角峰值 `0.8083`）—— **契约里没有它们的「正确值」，无从比**；
          这正是 r5-H4 那个 live stale 活着的地方，**本门对它结构性失明，且我认这一点。**
        - **裸赋值** `targets[X] = N`（不带值断言词）—— 契约侧归 `SPEC-SELFCONTRADICT`，散文侧需人读；
        - **数字写在锚**之前** 的措辞**（`N 就是 X 的真值`）。
      **⟹ 把这些当「已知局限」钉进 `--selftest` 的盲区探针（该抓的抓、抓不到的记录在案），
        而不是假装门覆盖了它们 —— 这是本轮（第六次复发）的元教训。**
    ★ **按位置归属**：一行里若同时出现两个锚，「真值 N」归给它**前面最近**的那个 —— 不硬套给全行。
    """
    if not spec:
        return
    tmap: dict[str, tuple[str, float]] = {}
    for t in spec.get("targets", []):
        sym, bl = t.get("symbol"), t.get("baseline_value")
        if sym and isinstance(bl, (int, float)) and bl != 0:
            for ref in _quantity_prose_refs(str(sym), "targets"):
                tmap.setdefault(ref, (f"targets[{sym}]", float(bl)))
    for p in spec.get("parameters", []):
        sym, v = p.get("symbol"), p.get("value")
        if sym and isinstance(v, (int, float)) and v != 0:
            for ref in _quantity_prose_refs(str(sym), "parameters"):
                tmap.setdefault(ref, (f"parameters[{sym}]", float(v)))
    if not tmap:
        return

    lines = md.splitlines()
    for i, line in enumerate(lines):
        window = line + ("\n" + lines[i + 1] if i + 1 < len(lines) else "")
        anchors: list[tuple[int, str, float]] = []          # (end_pos, label, value)
        for ref, (label, val) in tmap.items():
            start = 0
            while (k := window.find(ref, start)) >= 0:
                anchors.append((k + len(ref), label, val))
                start = k + 1
        if not anchors:
            continue
        anchors.sort()
        for m in _VALUE_CLAIM.finditer(window):
            cand = [a for a in anchors if a[0] <= m.start()]     # 前面最近的锚
            if not cand:
                continue
            _, label, val = cand[-1]
            num = m.group(2)
            n = float(num)
            dp = len(num.split(".")[1]) if "." in num else 0
            if abs(n - val) > 10.0 ** (-dp):                     # ★ ULP，不是相对容差
                err("PROSE-FORMULA-GHOST",
                    f"01-analysis.md:{i+1} 把 `{num}` 说成 `{label}` 的"
                    f"「{m.group(1)}」，但它的记录值 = `{val:.6g}`。\n"
                    f"        **归给「公式 / 真值」的散文数，必须等于那个量的 baseline / value**"
                    f"（`SPEC-SELFCONTRADICT` 已保证 target 的 baseline = closed_form 的输出）。\n"
                    f"        （r4 真实翻车：§11「消灭错值」那段自己手打了幽灵 `2.3454`，"
                    f"而公式算出来是 `2.3554` —— **零号规则的镜像第三次**。）\n"
                    f"        > {line.strip()[:90]}")
                break


def check_residue(md: str) -> None:
    """TODO / [GAP] 残留：允许存在，但必须在文首声明。"""
    head = md[:1500]

    for m in re.finditer(r"\bTODO\b|\bFIXME\b|\bXXX\b", md):
        line_no = md[:m.start()].count("\n") + 1
        err("TODO", f"L{line_no}: 残留 {m.group()} —— 分析交付前不该有未完成标记")

    gaps = [m for m in re.finditer(r"\[GAP\]", md)]
    if gaps:
        # 文首的 [GAP] 声明区不算
        body_gaps = [m for m in gaps if m.start() > 1500]
        declared = "[GAP]" in head
        if body_gaps and not declared:
            err("GAP-UNDECLARED", f"正文里有 {len(body_gaps)} 处 [GAP] 但文首没有声明 —— "
                                  f"未闭合的洞必须写在文首，不许藏在正文里")


def check_sections(md: str) -> None:
    """几个不能缺的 stage。缺了说明流程被跳步了。"""
    required = {
        "量纲": ("量纲分析|Buckingham|无量纲组", "Stage 3 量纲分析"),
        "预算": ("机制预算|Mechanism Budget", "Stage 4 机制预算"),
        "自洽": ("自洽性检验|极限行为|Sanity", "Stage 6 自洽性检验"),
        "预测": ("可证伪预测|证伪", "Stage 7 可证伪预测"),
        "实验": ("实验方案|实验设计", "实验方案（仿真不能替代实验）"),
    }
    for _, (pattern, name) in required.items():
        if not re.search(pattern, md):
            err("STAGE-MISSING", f"正文里找不到「{name}」—— 这一步被跳过了")


# ---------------------------------------------------------------- 自检

def selftest() -> int:
    """★ 把这个检查器**自己的**解析逻辑钉死。

        python check_analysis.py --selftest

    ## 为什么需要它

    这个检查器里全是**正则**，而正则是**照着一道题的排版写出来的**。
    换一道题，同样合法的另一种写法就能让它：

      · **崩溃**（`answers_task` 是数组 → `TypeError: unhashable type: 'list'`）
      · **假报错**（ID 加了粗 `| **S-1** |` → 「你没写设定书」—— 它就在那儿，写了整整一张表）
      · **静默地读错一个数**（`5e-5 T` → 读成 `5 T`，**错 10⁵ 倍**，然后拿这个捏造的数去指控你）

    **上面三条全是 electrical-damping 第一次运行时真的发生的。**
    而 magnetic-brake 跑了几十次，一条都没暴露 —— 因为它的排版恰好都是正则认得的那一种。

    > **一个只在一道题上跑过的检查器，它的每一个隐式假设都还没有被证伪过。**

    这个自检把**已知的坑**钉死。它拦不住下一个未知的坑 ——
    **拦下一个坑的，是「在第二道题上真的跑一遍」。**
    """
    global ERRORS, WARNINGS               # ← 必须在**任何**使用之前声明
    fails: list[str] = []

    def eq(name: str, got, want):
        if got != want:
            fails.append(f"  ✗ {name}\n      得到 {got!r}\n      期望 {want!r}")
        else:
            print(f"  ✓ {name}")

    print("=" * 72)
    print("① _as_list：`一个或多个` 的字段，字符串和数组都必须收得住")
    print("=" * 72)
    eq("字符串",     _as_list("T-1"),               ["T-1"])
    eq("数组",       _as_list(["T-2", "T-4"]),      ["T-2", "T-4"])
    eq("空",         _as_list(None),                [])
    eq("空串",       _as_list(""),                  [])

    print()
    print("=" * 72)
    print("② ID 的正则：markdown 加粗 / 斜体 / 反引号 都必须认得")
    print("=" * 72)
    for raw, want in [
        ("| S-1 | 磁体 |",        {"S-1"}),
        ("| **S-1** | 磁体 |",    {"S-1"}),       # ← electrical-damping 踩的
        ("| *S-2* | 线圈 |",      {"S-2"}),
        ("| `S-3` | 弹簧 |",      {"S-3"}),
        ("| **S-8** ★ | 利兹线 |", {"S-8"}),
    ]:
        eq(f"设定书 {raw!r}",
           set(re.findall(_SROW, raw)), want)
    for raw, want in [
        ("### A-1 · 点偶极子",      {"A-1"}),
        ("### **A-2** · 线性阻尼",  {"A-2"}),
        # ★★ electrical-damping 踩的：修订把一条假设**拆成两条** ⟹ ID 变成 A-6a / A-6b。
        #    旧正则 (A-\d+) 会从 `### A-6a` 里抠出 **A-6**，于是两个方向同时报 ERROR ——
        #    **一次正确的修订，被检查器当成三个错误骂回来。**
        #    而「拆假设」正是修订最常做的动作。
        ("### A-6a · 磁体内涡流",   {"A-6a"}),
        ("### A-6b · 导线涡流",     {"A-6b"}),
        ("### **A-6b** · 导线涡流", {"A-6b"}),
    ]:
        eq(f"台账 {raw!r}",
           set(re.findall(rf"###\s*{_EMPH}({_AID}){_EMPH}(?![0-9a-z])", raw)), want)
    # ★ 引用计数也必须锚死：A-6 不许从 A-6a 里被数出来
    eq("A-6 不会被 A-6a 冒名顶替",
       len(re.findall(r"\bA-6(?![0-9a-z])", "见 A-6a 与 A-6b，另见 A-6a。")), 0)

    print()
    print("=" * 72)
    print("②a-eq EQ 编号（教训 12 第四次）：\\tag{8,9} 一行多式要收得住；\\tag{对应 (9)} 引用不许重复计数")
    print("=" * 72)
    eq(r"单式 \tag{7}",          _tag_defn_nums(r"x=1\tag{7}"),          [7])
    eq(r"带括号 \tag{(7)}",       _tag_defn_nums(r"x=1\tag{(7)}"),        [7])
    # ★ fractal-fingers 真实踩的：一行给 k* 与 λ* 两式共 \tag{8,9}，旧正则整条不匹配 ⟹ 假报缺 8,9
    eq(r"一行两式 \tag{8,9}",     _tag_defn_nums(r"k=..,\lam=..\tag{8,9}"),   [8, 9])
    eq(r"带空格 \tag{11, 12}",    _tag_defn_nums(r"N=..\tag{11, 12}"),        [11, 12])
    # ★★ 盲区探针：引用 tag（body 含文字）**不是定义**，跳过——否则和真定义 (9) 撞成假 EQ-DUP
    eq(r"引用 \tag{对应 (9)} 跳过", _tag_defn_nums(r"\lam/h=..\tag{对应 (9)}"),  [])
    eq(r"引用 \tag{cf. 3} 跳过",    _tag_defn_nums(r"\tag{cf. 3}"),         [])
    # ★★ 端到端：8,9 与「对应 (9)」共存时，9 只数一次（无 EQ-DUP）—— fractal-fingers 的真实排版
    eq(r"组合 + 引用：9 不重复计数",
       sorted(_tag_defn_nums(r"a\tag{8,9} b\lam/h\tag{对应 (9)}")),        [8, 9])
    # ★ 已知局限（记录在案，非「已修好」）：字母子式 \tag{7a} 被当引用跳过 —— body 含 'a' 非纯数字列表。
    #   若某号只以 7a 出现、7 没单独出现，EQ-GAP 会假报缺 7（WARNING 级）。字母编号连续性本就歧义，不在 scope。
    eq(r"已知局限：\tag{7a} 跳过（body 非纯数字列表）", _tag_defn_nums(r"\tag{7a}"), [])

    print()
    print("=" * 72)
    print("②b ★★ STALE-VALUE：拿归档的旧值 grep 新文档（教训 4 的机械化）")
    print("=" * 72)
    # ★ 3 位有效数字起步 —— 2 位会让 0.1361 生成 "0.14"，而 `0.14 s`/`0.14 mm` 满世界都是。
    #   **一个总是响的警报，等于没有警报，而且它会训练人无视所有警报。**
    eq("0.03217 (1/s) → 生成 '0.0322'",   "0.0322" in _literals(0.03217, "1/s"), True)
    eq("0.1361 (1) → **不**生成 '0.14'",  "0.14" in _literals(0.1361, "1"),      False)
    eq("0.1361 (1) → 生成 '0.136'",       "0.136" in _literals(0.1361, "1"),     True)
    eq("0.000765 m → 生成 '0.765'（mm）",  "0.765" in _literals(0.000765, "m"),   True)
    eq("0.00589 kg → 生成 '5.89'（g）",    "5.89" in _literals(0.00589, "kg"),    True)
    # ★ 引用旧值必须**点名版本** —— 三种点名方式（行内 / 上文三行 / 节标题）
    _L = ["## 11 · r1 → r2 修订记录", "", "值从 0.0322 改到 0.0413", "",
          "## 12 · 别的", "", "γ_oc = 0.0322", "",
          "r1 报的是（逐字）：", "", "> γ_0 = 0.0322", ""]
    eq("节标题里点名 r1 ⟹ 放行",        _cited(_L, 3, "r1"), True)
    eq("★ 换了一节，没点名 ⟹ **抓住**",  _cited(_L, 7, "r1"), False)
    eq("上文三行内点名 ⟹ 放行（逐字引文里不许塞标记）", _cited(_L, 11, "r1"), True)

    print()
    print("=" * 72)
    print("②c ★★ CRIT-BLIND / CRIT-FALSEKILL：判据不许失明，也不许误杀")
    print("=" * 72)

    def _crit(spec):
        ERRORS.clear()
        check_criterion_matrix(spec)
        return [e.split("]")[0].lstrip("[") for e in ERRORS]

    _SRC = "测量误差 2%（§9）+ 预言侧 10% ⟹ 12%"
    good = {"criterion_matrix": {
        "wrong_models": [{"id": "n-A"}, {"id": "n-B"}, {"id": "bug-C"}],
        "criteria": [
            {"id": "K1", "passes_correct": True, "tolerance_source": _SRC,
             "catches": [{"id": "n-A", "detail": "k=2.1"}, {"id": "n-B", "detail": "k=1.0"}]},
            {"id": "K2", "passes_correct": True, "tolerance_source": _SRC,
             "catches": ["bug-C"]}],                     # ★ 旧格式 [str] 必须仍然收得住
        "robustness_scan": {"parameter": "δ = 残余定心误差", "scan_upper_bound": 4.0e-4,
                            "systematic_error_budget": 1.0e-4,   # ★ r6-H2：scan ≥ 3×budget
                            "delta_max": 1.35e-4, "delta_max_bracket": [1.34e-4, 1.35e-4]},
        "min_detectable": {"bug-C": {"eps_star": 0.13, "caught_by": ["K2"]}},
        "verdict": "PASS"}}
    eq("合格的表（catches 新旧两种格式混用）⟹ 无 ERROR", _crit(good), [])

    import copy
    blind = copy.deepcopy(good)
    blind["criterion_matrix"]["criteria"][1]["catches"] = []
    # ★ 一条判据失明，会**连带**让它本该抓的那个错模型漏网 —— 两个 ERROR 一起报才是对的
    eq("★ 判据失明 ⟹ CRIT-BLIND（+ 连带 MODEL-UNCAUGHT）",
       sorted(_crit(blind)), ["CRIT-BLIND", "CRIT-MODEL-UNCAUGHT"])

    fk = copy.deepcopy(good)
    fk["criterion_matrix"]["criteria"][0]["passes_correct"] = False
    eq("★ 判据误杀正确模型 ⟹ CRIT-FALSEKILL", _crit(fk), ["CRIT-FALSEKILL"])

    uncaught = copy.deepcopy(good)
    uncaught["criterion_matrix"]["wrong_models"].append({"id": "bug-D"})
    eq("★ 一个错模型没人抓 ⟹ CRIT-MODEL-UNCAUGHT", _crit(uncaught), ["CRIT-MODEL-UNCAUGHT"])

    dang = copy.deepcopy(good)
    dang["criterion_matrix"]["criteria"][0]["catches"] = ["编出来的-id"]
    # ★ 一个**编出来的** id 是「非空」的 —— 它同时掩盖了「n-A / n-B 没人抓」这个更糟的事实
    eq("★ 编出来的 id ⟹ CRIT-CATCH-DANGLING（非空 ≠ 有效）",
       sorted(_crit(dang)),
       ["CRIT-CATCH-DANGLING", "CRIT-MODEL-UNCAUGHT", "CRIT-MODEL-UNCAUGHT"])

    # ★★★ P18 ⑤ —— r3 真实翻车：naive-A 的「被五条判据抓到」，明细全是「提不出 Γ」。
    #     **一个记账截断，被记了五次。** 退化 ≠ 被抓到。
    degen = copy.deepcopy(good)
    degen["criterion_matrix"]["criteria"][0]["catches"] = [{"id": "n-A", "detail": "k=2.1"}]
    degen["criterion_matrix"]["criteria"][0]["degenerate_on"] = ["n-B"]
    eq("★★★ 只在 degenerate_on 里出现（拟合器崩了）⟹ **不算被抓到** ⟹ CRIT-MODEL-UNCAUGHT",
       _crit(degen), ["CRIT-MODEL-UNCAUGHT"])

    # ★★ P18 ① —— 容差是裸数字
    nosrc = copy.deepcopy(good)
    del nosrc["criterion_matrix"]["criteria"][0]["tolerance_source"]
    eq("★★ 容差没有来源 ⟹ CRIT-TOLERANCE-UNSOURCED", _crit(nosrc),
       ["CRIT-TOLERANCE-UNSOURCED"])

    # ★★ P18 ④ —— 「不误杀」只在理想点上跑过
    norob = copy.deepcopy(good)
    del norob["criterion_matrix"]["robustness_scan"]
    eq("★★ 没有 robustness_scan ⟹ CRIT-NO-ROBUSTNESS", _crit(norob), ["CRIT-NO-ROBUSTNESS"])

    # ★★★ r4-H1 —— 边界必须**二分**定出，不能靠网格撞（新锁：CRIT-ROBUSTNESS-COARSE）
    coarse_nobr = copy.deepcopy(good)
    del coarse_nobr["criterion_matrix"]["robustness_scan"]["delta_max_bracket"]
    eq("★★★ 有 delta_max 却没 bracket ⟹ CRIT-ROBUSTNESS-COARSE（证明不了是二分）",
       _crit(coarse_nobr), ["CRIT-ROBUSTNESS-COARSE"])

    coarse_wide = copy.deepcopy(good)
    coarse_wide["criterion_matrix"]["robustness_scan"]["delta_max"] = 1.7e-4
    coarse_wide["criterion_matrix"]["robustness_scan"]["delta_max_bracket"] = [1.0e-4, 1.7e-4]
    eq("★★★ 网格撞的宽括号 [0.10,0.17]（宽 41%）⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(coarse_wide), ["CRIT-ROBUSTNESS-COARSE"])

    coarse_bad = copy.deepcopy(good)
    coarse_bad["criterion_matrix"]["robustness_scan"]["delta_max_bracket"] = [2e-4, 3e-4]
    eq("★ delta_max 不在 bracket 内（1.35e-4 ∉ [2e-4,3e-4]）⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(coarse_bad), ["CRIT-ROBUSTNESS-COARSE"])

    # ═══════════ ★★★ r5 审稿 H1 —— 盲区探针（BLINDNESS PROBES）═══════════
    #  上一版这里只写「delta_max=None ⟹ 不报」——**亲手把盲区钉成了「预期行为」，给它盖了章**。
    #  **一道门的 `--selftest` 本身也是一份自评（P18 再上一层）**：只测「该抓的→抓到、诚实的→放行」
    #  不算验证；必须**造出让门失明的输入**去探它。造不出 = 你还没理解它守的是什么。
    none_blind = copy.deepcopy(good)
    none_blind["criterion_matrix"]["robustness_scan"] = {"parameter": "δ", "delta_max": None}
    eq("★★★ 探针：delta_max=None 却没 scan_upper_bound（可能没扫够远）⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(none_blind), ["CRIT-ROBUSTNESS-COARSE"])

    none_ok = copy.deepcopy(good)
    none_ok["criterion_matrix"]["robustness_scan"] = {
        "parameter": "δ", "delta_max": None, "scan_upper_bound": 5e-4,
        "systematic_error_budget": 1e-4}      # 5e-4 ≥ 3×1e-4 ✓
    eq("★ delta_max=None + scan_upper_bound 且 ≥3×budget（诚实的「处处稳健」）⟹ 不报",
       _crit(none_ok), [])

    nosub = copy.deepcopy(good)
    del nosub["criterion_matrix"]["robustness_scan"]["scan_upper_bound"]
    eq("★★ 探针：有限 delta_max 但缺 scan_upper_bound ⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(nosub), ["CRIT-ROBUSTNESS-COARSE"])

    # ★★ r6 审稿 H2 探针 —— scan_upper_bound 必须有下限（否则 None 逃生舱没真堵死）
    nobudget = copy.deepcopy(good)
    del nobudget["criterion_matrix"]["robustness_scan"]["systematic_error_budget"]
    eq("★★ 探针（r6-H2）：缺 systematic_error_budget ⟹ scan 无下限 ⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(nobudget), ["CRIT-ROBUSTNESS-COARSE"])

    shallow = copy.deepcopy(good)
    shallow["criterion_matrix"]["robustness_scan"]["scan_upper_bound"] = 2.0e-4  # < 3×budget(3e-4)
    eq("★★ 探针（r6-H2）：scan=2e-4 < 3×budget(3e-4) ⟹ 扫得不够远 ⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(shallow), ["CRIT-ROBUSTNESS-COARSE"])

    # ★★ r5-H1② 探针（**记录在案的已知局限**，不是「已修好」）：手写一个窄括号，把 r4 判死的
    #    虚报值 0.17 塞回来。门只查自洽性（宽度），**证不了它是二分跑出来的** ⟹ **它照样过**。
    #    provenance 靠「先重跑 `criterion_matrix.py` 再 check」保证，不靠这道门。**探针断言「它过」——
    #    明写这是局限，而不是假装门修好了它。**（诚实 scope 胜过虚假安全感。）
    handwritten = copy.deepcopy(good)
    handwritten["criterion_matrix"]["robustness_scan"] = {
        "parameter": "δ", "scan_upper_bound": 4e-4, "systematic_error_budget": 1e-4,
        "delta_max": 1.7e-4, "delta_max_bracket": [1.69e-4, 1.70e-4]}
    eq("★★ 探针（已知局限）：手写窄括号复活虚报值 0.17 ⟹ 门放行"
       "（r6-H1 起：CRIT-MATRIX-DESYNC 现在抓「内嵌≠matrix.json」，但**两处一起改**仍靠重跑+审稿）",
       _crit(handwritten), [])

    # ★★★ r7 审稿 H1 探针 —— **元探针 ③（wrong-quantity）**：门查了 bracket（该量），
    #    却没查那个 load-bearing 的量 margin=delta_max/budget。把「该比而没比的量」换进去 → 该抓。
    thin_margin = copy.deepcopy(good)
    thin_margin["criterion_matrix"]["robustness_scan"]["delta_max"] = 0.5e-4      # < budget 1e-4
    thin_margin["criterion_matrix"]["robustness_scan"]["delta_max_bracket"] = [0.49e-4, 0.5e-4]
    eq("★★★ 探针(r7-H1)：delta_max=0.5e-4 < budget(1e-4)（悬崖在噪声内，裕度 0.5×，必误杀）⟹ CRIT-ROBUSTNESS-COARSE",
       _crit(thin_margin), ["CRIT-ROBUSTNESS-COARSE"])

    # ★★ P18 ② —— 错误幅度是挑出来的
    nomin = copy.deepcopy(good)
    del nomin["criterion_matrix"]["min_detectable"]
    eq("★★ 没有 min_detectable（ε*）⟹ CRIT-NO-MIN-DETECTABLE", _crit(nomin),
       ["CRIT-NO-MIN-DETECTABLE"])

    eq("契约里没有 criterion_matrix ⟹ CRIT-MATRIX-MISSING",
       _crit({"tasks": [{"id": "T-1"}]}), ["CRIT-MATRIX-MISSING"])
    ERRORS.clear()

    print()
    print("=" * 72)
    print("②c″ ★★★ CRIT-MATRIX-DESYNC（r6 审稿 H1）：门读内嵌手拷副本，它必须 == matrix.json")
    print("=" * 72)
    import os as _os
    import tempfile as _tf
    _SRC = b"# criterion_matrix.py source"
    _SRCH = hashlib.sha256(_SRC).hexdigest()

    def _desync(emb_delta, mat_delta, *, write_matrix=True, write_source=True, stamp=_SRCH):
        # emb_delta / mat_delta = 内嵌 / matrix.json 里的 robustness_scan.delta_max（构造脱钩用）
        with _tf.TemporaryDirectory() as d:
            cdir = _os.path.join(d, "01-criteria")
            _os.makedirs(cdir)
            if write_source:
                with open(_os.path.join(cdir, "criterion_matrix.py"), "wb") as f:
                    f.write(_SRC)
            mat = {"verdict": "PASS", "robustness_scan": {"delta_max": mat_delta}}
            emb = {"verdict": "PASS", "robustness_scan": {"delta_max": emb_delta}, "script": "x.py"}
            if stamp is not None:
                mat["source_sha256"] = stamp
                emb["source_sha256"] = stamp
            if write_matrix:
                with open(_os.path.join(cdir, "matrix.json"), "w", encoding="utf-8") as f:
                    json.dump(mat, f, ensure_ascii=False)
            ERRORS.clear()
            check_matrix_desync({"criterion_matrix": emb}, Path(d))
            return [e.split("]")[0].lstrip("[") for e in ERRORS]

    eq("内嵌（去 script）== matrix.json + 源码戳对得上 ⟹ 不报", _desync(1.35e-4, 1.35e-4), [])
    # ★★★ r6-H1 探针：把 r4 判死的 0.17 篡改进内嵌、matrix.json 留 0.135 ⟹ 抓到（端到端 0 ERROR 的那个洞）
    eq("★★★ 探针(r6-H1)：内嵌 delta_max 篡改为 0.17、matrix.json 留 0.135 ⟹ CRIT-MATRIX-DESYNC",
       _desync(1.7e-4, 1.35e-4), ["CRIT-MATRIX-DESYNC"])
    eq("★ 探针（已知局限）：内嵌+matrix.json 两处一起改成 0.17（源码不动）⟹ 门放行（本门只保证两份一致）",
       _desync(1.7e-4, 1.7e-4), [])
    eq("★ matrix.json 缺失 ⟹ CRIT-MATRIX-DESYNC", _desync(1.35e-4, 1.35e-4, write_matrix=False),
       ["CRIT-MATRIX-DESYNC"])
    # ★★★ r7-H2 探针 —— 源码新鲜度（内嵌==matrix.json 还不够）
    eq("★★★ 探针(r7-H2)：改源码不重跑（戳对不上）⟹ CRIT-MATRIX-DESYNC",
       _desync(1.35e-4, 1.35e-4, stamp="dead" * 16), ["CRIT-MATRIX-DESYNC"])
    eq("★★★ 探针(r7-H2)：删掉源码 criterion_matrix.py ⟹ CRIT-MATRIX-DESYNC",
       _desync(1.35e-4, 1.35e-4, write_source=False), ["CRIT-MATRIX-DESYNC"])
    eq("★ 探针：matrix.json 没有 source_sha256 戳 ⟹ CRIT-MATRIX-DESYNC",
       _desync(1.35e-4, 1.35e-4, stamp=None), ["CRIT-MATRIX-DESYNC"])
    ERRORS.clear()

    print()
    print("=" * 72)
    print("②c′ ★★★ SPEC-SELFCONTRADICT：抓「值**压根没改过**」——STALE-VALUE 看不见的那一半")
    print("=" * 72)

    def _sc(spec, txt=""):
        ERRORS.clear()
        check_spec_selfcontradict(spec, txt)
        return [e.split("]")[0].lstrip("[") for e in ERRORS]

    _P = [{"symbol": r"\gamma_{oc}", "value": 0.0413}, {"symbol": "M_eff", "value": 0.006557},
          {"symbol": "R", "value": 20.0}, {"symbol": "R_c", "value": 3.72}]
    _CF = "gamma_oc + G_max**2/(2*M_eff*(R + R_c))"

    # ★★★ 真实事故：targets[\gamma] = 2.5978 在 r1/r2/r3 **三代一字未动**，
    #     而它自己的公式算出 2.3454。**STALE-VALUE 对它彻底失明**（old == new ⟹ 直接 continue）。
    eq("★★★ 三代未动的错值（2.5978 vs 公式的 2.345）⟹ SPEC-SELFCONTRADICT",
       _sc({"parameters": _P, "targets": [
           {"symbol": r"G_{\max}", "baseline_value": 0.8466, "numerical_recipe": "(6) 求极值"},
           {"symbol": r"\gamma", "baseline_value": 2.5978, "closed_form": _CF}]}),
       ["SPEC-SELFCONTRADICT"])
    eq("值改对了（2.3454）⟹ 不报",
       _sc({"parameters": _P, "targets": [
           {"symbol": r"G_{\max}", "baseline_value": 0.8466, "numerical_recipe": "(6) 求极值"},
           {"symbol": r"\gamma", "baseline_value": 2.3454, "closed_form": _CF}]}),
       [])
    # ★ 没有闭式、也没有 numerical_recipe ⟹ 这个数**没有任何机械校验** —— 不许沉默地跳过。
    eq("★ 既无 closed_form 也无 numerical_recipe ⟹ TARGET-NO-RECIPE",
       _sc({"parameters": _P, "targets": [{"symbol": r"\gamma", "baseline_value": 2.5978}]}),
       ["TARGET-NO-RECIPE"])
    eq("显式声明「只能数值求解」⟹ 放行（但必须**说出来**）",
       _sc({"parameters": _P, "targets": [
           {"symbol": r"G_{\max}", "baseline_value": 0.8466,
            "numerical_recipe": "(6) 的极值，无闭式"}]}), [])
    eq("闭式写坏了 ⟹ TARGET-CF-BROKEN（不是静默跳过）",
       _sc({"parameters": _P, "targets": [
           {"symbol": r"\gamma", "baseline_value": 2.5978, "closed_form": "gamma_oc + nonexistent"}]}),
       ["TARGET-CF-BROKEN"])

    # ★★★ 容差按存储精度定标（r9 收紧）—— 固定 1% 抓不到「一位数字的笔误」。
    #     真实事故：electrical-damping 的 targets[c_2] 第 4 位 4→5（偏 +0.29%），
    #     1% 门下三代未响；6 位字面量 ⟹ 门槛 1e-5 ⟹ 必须抓到。
    def _one(bl_lit, cf):
        spec = {"targets": [{"symbol": "c_2", "baseline_value": float(bl_lit),
                             "closed_form": cf}]}
        txt = ('{"targets": [{"symbol": "c_2", "baseline_value": ' + bl_lit +
               ', "closed_form": "' + cf + '"}]}')
        return spec, txt
    eq("★★★ c_2 数位笔误（0.0345832 vs 公式 0.0344832，+0.29%，6 位字面量）⟹ 抓到",
       _sc(*_one("0.0345832", "0.0344832")), ["SPEC-SELFCONTRADICT"])
    eq("末位舍入（2.3554174 vs 2.35541744，2e-9 < 1e-7）⟹ 放行",
       _sc(*_one("2.3554174", "2.35541744")), [])
    # ★ 精度即声明：同一个数，写 3 位管 3 位、写 6 位管 6 位。
    eq("字面量 0.0350（3 位 ⟹ 门槛 1e-2）vs 公式 0.0352（0.57%）⟹ 放行",
       _sc(*_one("0.0350", "0.0352")), [])
    eq("字面量 0.035000（6 位 ⟹ 1e-5）vs 同一个公式 0.0352 ⟹ 抓到",
       _sc(*_one("0.035000", "0.0352")), ["SPEC-SELFCONTRADICT"])
    # ★ 盲区探针（wrong-quantity 元探针，r7-③）：门数的必须是**文件原文**的位数。
    #   若门改从 f"{bl:g}" 数（repr 会把 0.010000 吞成 0.01 ⟹ 1 位 ⟹ 门槛 1e-2），
    #   这条就会漏 —— 它钉死「精度声明活在字面量里，不在 float 的 repr 里」。
    eq("★ 探针：0.010000（6 位）vs 0.010002（2e-4）—— repr 门会放行，原文门必须抓",
       _sc(*_one("0.010000", "0.010002")), ["SPEC-SELFCONTRADICT"])
    # ★ 探针：clamp 方向 —— 位数再少，门也**永不比旧 1% 更松**。
    eq("★ 探针：字面量 2（1 位 ⟹ min(10^0,1e-2)=1e-2）vs 公式 2.1（5%）⟹ 照抓",
       _sc(*_one("2", "2.1")), ["SPEC-SELFCONTRADICT"])
    eq("指数形式 3.45832e-2（6 位）与十进制同判 ⟹ 抓到",
       _sc(*_one("3.45832e-2", "0.0344832")), ["SPEC-SELFCONTRADICT"])
    # ★ 已知局限（诚实 scope，不假装门覆盖了它）：没有原文 ⟹ 没有精度声明 ⟹ 退回 1%。
    #   2e-4 的笔误在无 txt 时放行 —— 这不是 bug：调用方不给字面量，门就只能按 1% 管。
    #   main 永远传 spec_raw（load() 保证）；会踩到这条的只有忘传参数的新调用点。
    eq("已知局限：同样的 2e-4 笔误、txt=\"\" ⟹ 退回 1% ⟹ 放行（记录在案）",
       _sc({"targets": [{"symbol": "c_2", "baseline_value": 0.010000,
                         "closed_form": "0.010002"}]}), [])
    # ★ 探针：txt 与 dict 的 targets 数量对不上 ⟹ **不猜对齐**，全部退回 1%。
    eq("★ 探针：原文只有 1 个 target、dict 有 2 个 ⟹ 不猜，按 1% 判（0.29% 放行）",
       _sc({"targets": [{"symbol": "c_2", "baseline_value": 0.0345832,
                         "closed_form": "0.0344832"},
                        {"symbol": "x", "baseline_value": 1.0, "closed_form": "1.0"}]},
           '{"targets": [{"symbol": "c_2", "baseline_value": 0.0345832}]}'), [])
    ERRORS.clear()

    print()
    print("=" * 72)
    print("②d ★★ CLOSED-FORM-ORPHAN：改名必须传播到**代码**，不只是正文")
    print("=" * 72)
    # `\gamma_{oc}` 在 closed_form 里合法的写法只有 gamma_oc / gammaoc —— **gamma0 不是**。
    eq("\\gamma_{oc} → 变体含 gamma_oc",   "gamma_oc" in _ascii_variants(r"\gamma_{oc}"),  True)
    eq("★ \\gamma_{oc} → 变体**不含** gamma0",
       "gamma0" in _ascii_variants(r"\gamma_{oc}"), False)
    eq("\\mu_0 → 变体含 mu0（去下划线的写法合法）", "mu0" in _ascii_variants(r"\mu_0"), True)
    eq("\\ell_c → 变体含 l_c（\\ell 就是 l）",     "l_c" in _ascii_variants(r"\ell_c"), True)

    # ★★★ 反向用例 —— **这道门的第一版就死在这里，而且是被它自己要抓的那个 bug 杀死的。**
    #     `1/(gamma - gamma0) = …` 的左边是一个**表达式**，不是定义。
    #     第一版把 LHS 里所有标识符都塞进「已定义」⟹ **gamma0 把自己定义了 ⟹ 门彻底失明。**
    #     **我差一点就交付了一把新的瞎锁。**
    eq("★★ LHS 是表达式（1/(gamma-gamma0)=…）⟹ **一个名字都不定义**",
       _defs_in("1/(gamma - gamma0) = 2*M_eff*(R + R_c)/G(z0)**2")[0], set())
    eq("LHS 是单标识符 ⟹ 定义它",
       _defs_in("Gp0 = -1.5*mu0*N*m*a**2")[0], {"Gp0"})
    eq("LHS 带函数签名 ⟹ 定义函数名，形参归本地",
       _defs_in("G0(z) = mu0*N*m/(2*l_c)"), ({"G0"}, {"z"}))

    def _cf(spec):
        ERRORS.clear()
        check_closed_forms(spec)
        return [e.split("]")[0].lstrip("[") for e in ERRORS]

    # ★ `\gamma` 和 `\gamma_{oc}` 是**两个**符号 —— 少写一个，门就会（正确地）把它也当孤儿。
    _sym = {"symbols": [{"symbol": r"\gamma"}, {"symbol": r"\gamma_{oc}"}, {"symbol": r"\mu_0"},
                        {"symbol": "M_eff"}, {"symbol": "R"}, {"symbol": "R_c"},
                        {"symbol": "G"}, {"symbol": "z_0"}, {"symbol": r"\beta"}]}
    eq("★★ 孤儿 gamma0（真实 bug，三代存活）⟹ CLOSED-FORM-ORPHAN",
       _cf({**_sym, "equations": [
           {"id": "(16)", "closed_form": "1/(gamma - gamma0) = 2*M_eff*(R + R_c)/G(z0)**2"}]}),
       ["CLOSED-FORM-ORPHAN"])
    eq("改名传播到位（gamma_oc）⟹ 不报",
       _cf({**_sym, "equations": [
           {"id": "(16)", "closed_form": "1/(gamma - gamma_oc) = 2*M_eff*(R + R_c)/G(z0)**2"}]}),
       [])
    eq("跨方程引用（(23) 用 (7) 定义的 Gp0）⟹ 不报",
       _cf({**_sym, "equations": [
           {"id": "(7)",  "closed_form": "Gp0 = -1.5*mu0*M_eff"},
           {"id": "(23)", "closed_form": "beta = Gp0**2/(R + R_c)"}]}),
       [])
    eq("单位不是标识符（`= 2.80 ms`）⟹ 不报",
       _cf({**_sym, "equations": [{"id": "(12)", "closed_form": "tau = M_eff/R = 2.80 ms"}]}), [])
    ERRORS.clear()

    print()
    print("=" * 72)
    print("②e ★★ REVIEW-CITE-GHOST：**作者不许拿自己的记忆替换审稿人的字**")
    print("=" * 72)
    # 真实事故：作者写「r2 审稿的实测 +27.7%」，而 r2 报告里 "27.7" 出现 **0 次**（写的是 17.5%）。
    # 那个数一路进了 CLAUDE.md 的教训表、审稿人的弹药库、和本检查器自己的错误消息。
    _L = ["## 8.5 · 双向表", "",
          "r2 的顶点判据判死正确模型 $+27.7\\%$", "",          # 3: 幽灵
          "r2 的顶点判据判死正确模型 $+17.5\\%$", "",          # 5: 真的（r2 说过）
          "| ±6 mm（**r2 用的**） | **$+16.2\\%$** |",         # 7: 本文算的
          "> ★ 这里的 $+16.2\\%$ 是**本表**的 9 点扫描。", ""]  # 8: 来源在**下一行**
    eq("★ 上下文里点名了「本表」⟹ 放行（窗口必须**双向** —— 表的说明常在表下面）",
       _own_source_near(_L, 7), True)
    eq("★ 孤零零一句「r2 报的是 +27.7%」⟹ 没有来源 ⟹ **抓住**",
       _own_source_near(_L, 3), False)
    # ★ 而放宽的只是「归属」，**没有放宽「存在」**：
    #   一行里同时点名 r1 和 r2 时，无法机械判断哪个数属于哪一版 ——
    #   但「它在**任何**一份被点名的报告里都查无此数」已经足够抓住「凭记忆编造」。
    eq("百分数正则：+17.5% / -3.9% / 16.2% 都抠得出",
       _PCT.findall(r"偏 $+17.5\%$，方向是 $-3.9\%$，本表 16.2%"), ["+17.5", "-3.9", "16.2"])
    ERRORS.clear()

    print()
    print("=" * 72)
    print("③ SILENT-NEGLECT：**「这一项不可忽略」是最负责任的一句话，不许骂它**")
    print("=" * 72)
    _neg = _NEGATED_NEGLECT          # ★ 用同一个对象——自检必须测「真的在跑的那份正则」
    for line,放行, why in [
        ("这一项**不可忽略**",                    True,  "最基本的否定"),
        ("**它不是「可忽略」的 —— 它被吸收进 M_eff**", True,  "★ electrical-damping 踩的"),
        ("涡流不能忽略",                          True,  ""),
        ("这一项 non-negligible",                 True,  ""),
        # ★★ 反向：**绝不能**因为修误报而把真的口头忽略放行
        ("这一项很小，不影响结论，忽略",           False, "★★ 真·口头忽略 —— 必须仍被抓"),
        ("高阶项忽略",                            False, "★★ 真·口头忽略"),
        ("由于对称性，交叉项略去",                 False, "★★ 真·口头忽略"),
    ]:
        eq(f"{'放行' if 放行 else '★抓住'} {line!r}{'  ' + why if why else ''}",
           bool(_neg.search(line)), 放行)

    print()
    print("=" * 72)
    print(r"④ _norm_sym：排版差异 != 符号差异（契约写 A_{cs}，正文写 A_{\rm cs}）")
    print("=" * 72)
    eq(r"A_{cs} == A_{\rm cs}",   _norm_sym(r"A_{cs}"),         _norm_sym(r"A_{\rm cs}"))
    eq(r"\varrho_{air} == \varrho_{\rm air}",
       _norm_sym(r"\varrho_{air}"), _norm_sym(r"\varrho_{\rm air}"))
    eq(r"\mathcal{M} == \mathcal M",
       _norm_sym(r"\mathcal{M}"),    _norm_sym(r"\mathcal M"))
    eq(r"\zeta_{eff} == \zeta_{\rm eff}",
       _norm_sym(r"\zeta_{eff}"),    _norm_sym(r"\zeta_{\rm eff}"))
    # ★★ 反向：**绝不许**把两个不同的符号归一成一个（那才是真的削弱检查）
    eq(r"G' != G       （撇号是语义）",  _norm_sym(r"G'")     == _norm_sym(r"G"),  False)
    eq(r"\Pi_4 != \Pi  （下标是语义）",  _norm_sym(r"\Pi_4")  == _norm_sym(r"\Pi"), False)
    eq(r"M_{eff} != M  （下标是语义）",  _norm_sym(r"M_{eff}") == _norm_sym(r"M"),  False)
    eq(r"\rho != \varrho（字形是语义）", _norm_sym(r"\rho")   == _norm_sym(r"\varrho"), False)

    print()
    print("=" * 72)
    print("⑤ _NUMUNIT：**绝不许**把科学计数法的尾数当成一个数")
    print("=" * 72)
    eq("`5e-5 T` 不是 5 T",        _NUMUNIT.findall("B_E = 5e-5 T"),          [])
    eq("`1.2e-3 mm` 不是 1.2 mm",  _NUMUNIT.findall("d = 1.2e-3 mm"),         [])
    eq("`1.30 T` 正常",            _NUMUNIT.findall("$B_r = 1.30$ T"),        [("1.30", "T")])
    eq("`10.46 mm` 正常",          _NUMUNIT.findall("z_pk = 10.46 mm"),       [("10.46", "mm")])
    eq("LaTeX `\\mathrm{mm}` 正常", _NUMUNIT.findall(r"$4\ \mathrm{mm}$"),     [("4", "mm")])

    print()
    print("=" * 72)
    print("⑥ ★ NUM-DESYNC 必须仍然抓得到 magnetic-brake 那个**真实的**脱钩")
    print("=" * 72)
    #  真实案例：审稿抓到「达到终速的距离用了错误捷径，高估 27%，精确值 0.277 mm」。
    #  作者改了**推导**，但漏了**预测表**和 **model-spec.json** —— 契约里还写着 0.35 mm。
    #  这个 bug 一路活到了 Skill 2 手里。
    #
    #  **这条自检是一道「防削弱」的门**：
    #  我曾为了消掉 electrical-damping 的误报，给这条检查加了一个「同单位的数太多就闭嘴」
    #  的守卫 —— **结果它把这个真 bug 也一起放走了**（被注入式回归当场抓住）。
    #
    #  > **为了消误报而削弱一条检查，是最容易犯、也最贵的错。**
    #  > 从今往后，任何人想动 NUM-DESYNC，**必须先过这一关**。
    _e, _w = ERRORS, WARNINGS
    ERRORS, WARNINGS = [], []
    fake_spec = {
        "parameters": [{"symbol": "a", "value": 0.006, "unit": "m"}],
        "figures": [{"id": "F-3",
                     "expected_shape": "在 0.35 mm 处已达 0.99，之后完全平坦"}],
        "assumptions": [],
    }
    fake_md = ("精确值为 $x = v_t\\tau(\\ln 100 - 0.99) = 0.277$ mm。\n"
               "而 0.35 mm 是那个错误捷径给出的值（高估 27%）。\n")
    check_number_desync(fake_md, fake_spec)
    caught = any("NUM-DESYNC" in w or "NUM-NOT-IN-PROSE" in w for w in WARNINGS)
    ERRORS, WARNINGS = _e, _w
    eq("契约 0.35 mm / 正文 0.277 mm 的脱钩", caught, True)

    print()
    print("=" * 72)
    print("⑦ ★★ PROSE-FORMULA-GHOST（r4）：散文归给「公式/真值」的数必须 = target 的 baseline")
    print("=" * 72)

    def _pf(md, spec):
        ERRORS.clear()
        check_prose_formula_values(md, spec)
        return [e.split("]")[0].lstrip("[") for e in ERRORS]

    _tg = {"targets": [{"symbol": r"\gamma", "baseline_value": 2.3554174},
                       {"symbol": "c_2", "baseline_value": 0.0345832}]}
    # ★★★ 真实事故：幽灵 2.3454 归给「公式」，而真值 2.3554（**只差 0.42%**）。
    eq("★★★ 幽灵 2.3454 归给「公式算出来」（真值 2.3554）⟹ PROSE-FORMULA-GHOST",
       _pf(r"`targets[\gamma]` 而它自己的公式算出来是 **2.3454**（偏 +10.3%）。", _tg),
       ["PROSE-FORMULA-GHOST"])
    eq("改对了 2.3554 ⟹ 不报",
       _pf(r"`targets[\gamma]` 的公式算出来是 **2.3554**。", _tg), [])
    # ★ 关键坑：相对容差 1% 会漏掉它（0.42%）—— 必须在**写出的精度**上比（ULP）。
    eq("★ ULP 抓得到 0.42% 的「4 位幽灵」（而相对容差 1% 会漏）",
       abs(2.3454 - 2.3554174) > 10 ** -4, True)
    eq("★ 四舍五入合法：真值写成 2.36（2 位）⟹ 不报",
       _pf(r"`targets[\gamma]` 的真值 2.36。", _tg), [])
    # ★ 老值 2.5978 归给「三代未动」（版本语境），不是归给「公式」⟹ 不误报。
    eq("★ 同一句里的老值 2.5978（版本语境）+ 真值 2.3554 ⟹ 不误报",
       _pf(r"`targets[γ]` = 2.5978 三代未动（真值 2.3554）", _tg), [])
    # ★ 跨行归属：targets[γ] 在上一行，claim 在下一行。
    eq("★ 跨行归属（targets[γ] 上一行，公式在下一行）⟹ 抓到",
       _pf("`targets[\\gamma]` 三代未动，\n而公式算出来是 2.3454。", _tg),
       ["PROSE-FORMULA-GHOST"])
    # ★★ 位置归属：一行两个 target，「真值 N」归给**最近**的那个 —— 不许硬套给行里所有 target。
    eq("★★ 位置归属：真值 0.0345 属最近的 c_2（不硬套给 γ）⟹ 不误报",
       _pf(r"`targets[\gamma]` 与 `targets[c_2]` 的真值 0.0345。", _tg), [])
    eq("★★ 反向：同一行 c_2 的真值写错 0.099 ⟹ 归给 c_2 抓到（证明归属真在工作）",
       _pf(r"`targets[\gamma]` 与 `targets[c_2]` 的真值 0.099。", _tg),
       ["PROSE-FORMULA-GHOST"])

    # ═══════════ ★★★ r5 审稿 H2 —— 盲区探针（BLINDNESS PROBES）═══════════
    #  上一版的 8 个用例**全部** anchored 到 target、**全部**用那两三个关键词 ——
    #  **没有一个探「它号称要挡、但换个形状 → 该抓却放行」**，r5 审稿一构造就穿了。
    #  ⟹ 把 r5 的每个构造钉成探针：**能修的修（该抓的抓），修不了的明写「已知局限」**（诚实 scope）。
    _tgp = {"targets": [{"symbol": r"\gamma", "baseline_value": 2.3554174}],
            "parameters": [{"symbol": "R_c", "value": 3.71}]}
    # —— 能修的（本轮扩了措辞 + 扩了 parameters 锚）：现在该抓到 ——
    # ★ r6 审稿 H4：r6 加过「约为」抓这个，但它**引入了误报**（`parameters[a] 磁场约为 0.3 T`）——
    #   r7 回退。「约为」这类太泛的措辞归**已知局限**（措辞表是启发式，靠对抗审稿兜底），不硬扩。
    eq("★ 探针（已知局限）：`targets[γ] 约为 2.9999`（太泛的措辞，回退后不抓）⟹ 门不管",
       _pf(r"`targets[γ]` 约为 2.9999", _tgp), [])
    eq("★★ 探针·扩锚：`parameters[R_c] 的真值 9.99`（value=3.71）⟹ 现在抓到",
       _pf(r"`parameters[R_c]` 的真值 9.99", _tgp), ["PROSE-FORMULA-GHOST"])
    # —— ★ 修不了的（记录在案的已知局限，靠对抗审稿 + 人读，不是本门的活）——
    eq("★ 探针（已知局限）：`|G'(0)| 公式算出来 999.99`（非 spec 量、无正确值可比）⟹ 门不管",
       _pf(r"`|G'(0)|` 公式算出来 999.99（非 target/parameter）", _tgp), [])
    eq("★ 探针（已知局限）：`targets[γ] = 9.9999`（裸「=」）⟹ 门不管（契约归 SPEC-SELFCONTRADICT，散文需人读）",
       _pf(r"`targets[γ]` = 9.9999", _tgp), [])
    eq("★ 探针（已知局限）：`9.9999 就是 targets[γ] 的真值`（数字在锚之前）⟹ 门不管",
       _pf(r"9.9999 就是 `targets[γ]` 的真值", _tgp), [])
    ERRORS.clear()

    print()
    print("=" * 72)
    if fails:
        print(f"✗ {len(fails)} 项自检未通过 —— **检查器自己坏了，先修它**\n")
        print("\n".join(fails))
        return 1
    print("✓ 全部通过。")
    print()
    print("  但这只钉死了**已知的**坑。**下一个未知的坑，只有在第二道题上真的跑一遍才会现形。**")
    return 0


# ---------------------------------------------------------------- 主流程

def main() -> int:
    if len(sys.argv) == 2 and sys.argv[1] in ("--selftest", "-t"):
        return selftest()
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    workspace = Path(sys.argv[1])
    if not workspace.is_dir():
        print(f"工作区不存在: {workspace}", file=sys.stderr)
        return 2

    md, problem_md, spec, spec_raw = load(workspace)

    # ★ 每道门单独兜住异常。
    #
    #  **一个崩溃的检查器，比一个漏报的检查器更糟：它什么信息都不给。**
    #  你只看到一行 traceback，然后既不知道**别的**门过没过，也不知道**这道**门本来想说什么。
    #
    #  **血泪教训（electrical-damping 的第一次运行）**：`check_tasks` 假定 `answers_task`
    #  只可能是字符串（因为 magnetic-brake 的 9 张图恰好都是），遇到数组直接
    #  `TypeError: unhashable type: 'list'` —— **整个检查器死掉，另外 30 道门一道都没跑。**
    #
    #  修好那个 bug 是必要的；**但兜住异常是必须的** —— 下一个隐式假设还在某处等着。
    gates = [
        ("check_tasks",            lambda: check_tasks(spec or {})),
        ("check_essence",          lambda: check_essence(spec or {})),
        ("check_model_validation", lambda: check_model_validation(spec or {})),
        ("check_contract",         lambda: check_contract(spec or {})),
        ("check_equations",        lambda: check_equations(md)),
        ("check_ids",              lambda: check_ids(md, problem_md, spec or {})),
        ("check_silent_neglect",   lambda: check_silent_neglect(md)),
        ("check_symbols",          lambda: check_symbols(md, spec or {})),
        ("check_number_desync",    lambda: check_number_desync(md, spec or {})),
        # ★★ 这两道是 CLAUDE.md 教训 4 说「目前没有机械检查能发现」的那两件事
        ("check_stale_values",     lambda: check_stale_values(workspace, md, problem_md, spec or {})),
        ("check_criterion_matrix", lambda: check_criterion_matrix(spec or {})),
        # ★★★ r6 审稿 H1：门读的是内嵌手拷副本 —— 它必须 == 01-criteria/matrix.json
        ("check_matrix_desync",    lambda: check_matrix_desync(spec or {}, workspace)),
        # ★★★ 这三道来自 r3 审稿：STALE-VALUE 只在「值变了」时看得见，
        #     而「忘了改」的定义就是「值没变」——它对自己要抓的主要形态结构性失明。
        ("check_spec_selfcontradict", lambda: check_spec_selfcontradict(spec or {}, spec_raw)),
        ("check_closed_forms",     lambda: check_closed_forms(spec or {})),
        ("check_review_citations", lambda: check_review_citations(workspace, md)),
        # ★★ r4 审稿：散文里归给「公式/真值」的数，没有门代回公式验过（幽灵 2.3454）
        ("check_prose_formula_values", lambda: check_prose_formula_values(md, spec or {})),
        ("check_residue",          lambda: check_residue(md)),
        ("check_sections",         lambda: check_sections(md)),
    ]
    for name, fn in gates:
        try:
            fn()
        except Exception as e:                                       # noqa: BLE001
            import traceback
            err("CHECKER-CRASHED",
                f"**检查器自己崩了**：`{name}` 抛出 {type(e).__name__}: {e}\n"
                f"        这**不是**你的分析有问题 —— **是这道门有 bug**。\n"
                f"        它多半在假定某个字段只可能是某一种类型 / 形状，"
                f"而你的契约合法地用了另一种。\n"
                f"        **修检查器，不要改契约去迁就它。**\n"
                f"{textwrap.indent(traceback.format_exc().strip(), '          ')}")

    print(f"检查工作区: {workspace}\n")

    if ERRORS:
        print(f"✗ {len(ERRORS)} 个 ERROR（必须修）\n")
        for e in ERRORS:
            print(f"  {e}")
        print()

    if WARNINGS:
        print(f"⚠ {len(WARNINGS)} 个 WARNING（看一眼，多数该修）\n")
        for w in WARNINGS:
            print(f"  {w}")
        print()

    if not ERRORS and not WARNINGS:
        print("✓ 机械检查全部通过。")
        print("  注意：这个脚本不做物理判断——量纲代数、适用域、边界条件都不查。")
        print("  接下来必须走 iypt-physics-review。")
    elif not ERRORS:
        print("✓ 无 ERROR。修掉 WARNING 后走 iypt-physics-review。")

    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
