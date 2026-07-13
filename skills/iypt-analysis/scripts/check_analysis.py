#!/usr/bin/env python3
"""IYPT 分析的机械检查器。

只做**确定性可判**的检查——不做物理判断。物理判断是 iypt-physics-review 的活。
先跑这个把机械错修掉，再去叫审稿人，别浪费审稿轮次。

用法:
    python check_analysis.py iypt/magnetic-brake

退出码: 0 = 无 error（可能有 warning）；1 = 有 error；2 = 用不了（文件缺失等）
"""

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

    spec = None
    if spec_path.is_file():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            err("SPEC-PARSE", f"model-spec.json 不是合法 JSON: {e}")
    else:
        err("SPEC-MISSING", "handoff/model-spec.json 不存在——Skill 2 没有输入，流水线断了")

    return md, problem_md, spec


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

def check_equations(md: str) -> None:
    """公式编号连续、无重复。"""
    tags = re.findall(r"\\tag\{\(?(\d+)\)?\}", md)
    if not tags:
        warn("EQ-NONE", "正文里没有找到 \\tag{n} 编号公式——推导应当给公式编号，审稿人要靠它定位")
        return
    nums = [int(t) for t in tags]

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


def check_ids(md: str, problem_md: str, spec: dict) -> None:
    """S-n / A-n：定义了就要被引用；台账要和 spec 对齐。"""
    defined_s = set(re.findall(rf"\|\s*{_EMPH}(S-\d+){_EMPH}\s*\|", problem_md))
    defined_a = set(re.findall(rf"###\s*{_EMPH}(A-\d+){_EMPH}", md))

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
        if len(re.findall(rf"\b{re.escape(aid)}\b", both)) < 2:
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
    negated = re.compile(r"(?:不[可能得容]?|无法|不能|绝不|决不|cannot|can't|must not|"
                         r"non-negligible|not\s+negligible)\s*(?:被)?\s*"
                         r"(?:忽略|略去|neglect|ignor)", re.I)

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


def check_symbols(md: str, spec: dict) -> None:
    """符号表双向闭合。"""
    if not spec or not spec.get("symbols"):
        err("NO-SYMBOLS", "model-spec.json 没有符号表")
        return

    table = {s.get("symbol", "").strip() for s in spec["symbols"]}
    body = md

    # 表里有，正文没用
    for sym in sorted(table):
        if not sym:
            continue
        if sym not in body:
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
    ]:
        eq(f"设定书 {raw!r}",
           set(re.findall(rf"\|\s*{_EMPH}(S-\d+){_EMPH}\s*\|", raw)), want)
    for raw, want in [
        ("### A-1 · 点偶极子",      {"A-1"}),
        ("### **A-2** · 线性阻尼",  {"A-2"}),
    ]:
        eq(f"台账 {raw!r}",
           set(re.findall(rf"###\s*{_EMPH}(A-\d+){_EMPH}", raw)), want)

    print()
    print("=" * 72)
    print("③ _NUMUNIT：**绝不许**把科学计数法的尾数当成一个数")
    print("=" * 72)
    eq("`5e-5 T` 不是 5 T",        _NUMUNIT.findall("B_E = 5e-5 T"),          [])
    eq("`1.2e-3 mm` 不是 1.2 mm",  _NUMUNIT.findall("d = 1.2e-3 mm"),         [])
    eq("`1.30 T` 正常",            _NUMUNIT.findall("$B_r = 1.30$ T"),        [("1.30", "T")])
    eq("`10.46 mm` 正常",          _NUMUNIT.findall("z_pk = 10.46 mm"),       [("10.46", "mm")])
    eq("LaTeX `\\mathrm{mm}` 正常", _NUMUNIT.findall(r"$4\ \mathrm{mm}$"),     [("4", "mm")])

    print()
    print("=" * 72)
    print("④ ★ NUM-DESYNC 必须仍然抓得到 magnetic-brake 那个**真实的**脱钩")
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
    global ERRORS, WARNINGS
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

    md, problem_md, spec = load(workspace)

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
