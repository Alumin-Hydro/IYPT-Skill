#!/usr/bin/env python3
"""Skill 3 的机械检查。

    python skills/iypt-slides/scripts/check_slides.py iypt/<problem-slug>

**ERROR 必须清零。**

## 这个脚本在防什么

一份 PPT 有三种腐烂方式，而**三种都不会让任何东西报错**：

1. **数字悄悄漂了。** 仿真重跑，指数从 3.44 变成 3.51 —— PPT 上还写着 3.44。
   没人会发现，因为**没有任何东西把它们绑在一起**。
2. **只报好消息。** 六条断言过了四条，PPT 上讲那四条。
   **剩下两条不是「没讲」，是「被消失」了。** 而 IYPT 的 Opponent 专门找这个。
3. **仿真被讲成了实验。** 一个词的事：「实测」→「实验测得」。
   在 Physics Fight 上，这是学术不端，不是笔误。

**这三样都不是「粗心」—— 它们是一个必须交差的 agent 的最优策略。**
所以对策不能是提醒，只能是**结构上做不到**：

  · 数字**不许手打**（写指针，渲染时从 results.json 代入）→ 漂移不可能发生
  · 被证伪的东西**必须出现在 deck 里** → 选择性汇报会 ERROR
  · 「这是仿真」这句话**由 deckkit 写死** → 作者改不了措辞

> **文档里的劝诫会被忽略；机械检查不会。而「根本没有那个入口」比机械检查还硬。**
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

_TPL = Path(__file__).resolve().parent.parent / "templates"
sys.path.insert(0, str(_TPL))
import deckkit as dk                                            # noqa: E402

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(code: str, msg: str) -> None:
    ERRORS.append(f"[{code}] {msg}")


def warn(code: str, msg: str) -> None:
    WARNINGS.append(f"[{code}] {msg}")


#: 比对引文用：折叠空白、抹掉 markdown 强调、统一负号与破折号。
#  **内容必须一字不差；排版不算内容。**
norm = dk.norm_q


# ---------------------------------------------------------------- 载入

def load(ws: Path):
    deck_p = ws / "03-slides" / "deck.json"
    res_p = ws / "02-sim" / "results.json"
    if not deck_p.is_file():
        err("NO-DECK", f"{deck_p} 不存在 —— Skill 3 的产出契约就是它。")
        return None, None
    if not res_p.is_file():
        err("NO-RESULTS", f"{res_p} 不存在 —— **PPT 不能凭空长出来**，"
                          f"它的每个数字都必须来自 Skill 2 的 results.json。")
        return None, None
    return (json.loads(deck_p.read_text(encoding="utf-8")),
            json.loads(res_p.read_text(encoding="utf-8")))


# ---------------------------------------------------------------- 文本抽取

#: 会被**显示在幻灯片上**、且由作者**手打**的字段。
#  quote / figure.caption / verdict 不在里面 —— 它们逐字来自 results.json，
#  由 QUOTE-DRIFT / CAPTION-DRIFT 守着，那是比「引用数字」更强的约束。
def authored_texts(s: dict):
    sid = s["id"]
    if s.get("takeaway"):
        yield f"{sid}.takeaway", s["takeaway"]
    if s.get("notes"):
        yield f"{sid}.notes", s["notes"]
    for i, b in enumerate(s.get("body", [])):
        k = b.get("kind", "bullet")
        w = f"{sid}.body[{i}]:{k}"
        if k in ("bullet", "text", "lead", "note"):
            yield w, b["text"]
        elif k == "kv":
            yield w + ".k", b["k"]
            yield w + ".v", b["v"]
        elif k == "table":
            for h in b["head"]:
                yield w + ".head", h
            for r in b["rows"]:
                for c in r:
                    yield w + ".cell", str(c)
        elif k == "eq" and b.get("label"):
            yield w + ".label", b["label"]


def all_strings(deck: dict) -> str:
    """deck.json 的**全文**（含 quote / caption / verdict id）—— 查「有没有提到」用。"""
    return json.dumps(deck, ensure_ascii=False)


# ---------------------------------------------------------------- A · 溯源

#: **必须被引用的数字**：带小数点 / 百分号 / 科学计数。
#
#  为什么是这三类而不是「所有数字」：
#    · `1024/45`、`Model-0`、`A-1`、`12 分钟`、`5 组` —— 整数，是**定义或计数**，不是测量
#    · `3.44`、`82.7%`、`1.35e-14`、`0.60` —— **一律是测出来的**，一律必须能追回去
#
#  这条线好在它**简单到无法争辩**：带小数点的数字，你不可能是「随口一说」。
_NUM = re.compile(r"""
    \d+\.\d+                       |   # 3.44
    \d+(?:\.\d+)?\s*%              |   # 82.7%  /  40 %
    \d+(?:\.\d+)?\s*[eE][-+]?\d+       # 1.35e-14
""", re.X)


def check_provenance(deck: dict, R: dict) -> None:
    for s in deck["slides"]:
        sid = s["id"]

        # ---- NUM-UNCITED：数字不许手打
        for where, text in authored_texts(s):
            bare = dk.strip_pointers(text)              # 把 {{...}} 整段挖掉
            for m in _NUM.finditer(bare):
                err("NUM-UNCITED",
                    f"{where}：`{m.group(0)}` 是**手打**的数字。\n"
                    f"        原文：{text[:90]}\n"
                    f"        **PPT 上的每个数字都必须能追回 results.json。** 写成指针：\n"
                    f"            {{{{assertions.AS-8.measured|.2f}}}}   "
                    f"{{{{targets.v_t.relative_deviation|%+.1f}}}}\n"
                    f"        渲染时由 deckkit 代入 —— 于是仿真一重跑，"
                    f"幻灯片跟着变，**而不是变成一个谎**。")

        # ---- SRC-DANGLING / INLINE-QUOTE-DRIFT：每个 {{...}} 都要立得住
        for where, text in list(authored_texts(s)) + _quote_and_caption(s):
            for mode, a, b in dk.refs(text):
                try:
                    val = dk.resolve(b if mode == "quote" else a, R)
                except dk.ResolveError as e:
                    err("SRC-DANGLING",
                        f"{where}：`{{{{{a if mode=='value' else b}}}}}` 在 results.json 里"
                        f"**解析不到**。\n        {e}")
                    continue

                if mode == "quote":
                    # 行内引文：数字可以写出来，但**必须是契约原文的逐字子串**。
                    # 这条路无法被滥用来编造一个数字 —— 编的数字不可能是原文的子串。
                    if norm(a) not in norm(val):
                        err("INLINE-QUOTE-DRIFT",
                            f"{where}：行内引文 `{a}` **不是** `{b}` 原文的逐字子串。\n"
                            f"        原文：{str(val)[:110]}\n"
                            f"        **你可以写出契约里的那个数，但必须一字不差 ——"
                            f"一转述就走样，而走样的方向永远是对自己有利的。**")
                elif b:
                    try:
                        dk._fmt(val, b)
                    except (TypeError, ValueError):
                        err("FMT-BAD",
                            f"{where}：`{a}` 的值是 {val!r}（{type(val).__name__}），"
                            f"套不上格式 `{b}`")

        # ---- QUOTE-DRIFT：引文必须是原文的**逐字子串**
        for i, b in enumerate(s.get("body", [])):
            if b.get("kind") != "quote":
                continue
            w = f"{sid}.body[{i}]:quote"
            try:
                src = dk.resolve(b["src"], R)
            except dk.ResolveError as e:
                err("SRC-DANGLING", f"{w}：引文出处 `{b['src']}` 解析不到。{e}")
                continue
            if norm(b["text"]) not in norm(src):
                err("QUOTE-DRIFT",
                    f"{w}：引文**不是逐字抄写**。\n"
                    f"        你写的：{b['text'][:80]}\n"
                    f"        原文  ：{str(src)[:80]}\n"
                    f"        **一转述就走样，而走样的方向永远是对自己有利的。** 逐字抄。")

        # ---- CAPTION-DRIFT：图注只能删字，不能改字
        f = s.get("figure")
        if f and f.get("caption"):
            try:
                real = dk.resolve(f"figures.{f['figure_id']}.caption", R)
            except dk.ResolveError:
                continue                                # FIG-UNKNOWN 会报
            if norm(f["caption"]) not in norm(real):
                err("CAPTION-DRIFT",
                    f"{sid}.figure：图注**不是原文的逐字子串**。\n"
                    f"        你写的：{f['caption'][:80]}\n"
                    f"        原文  ：{str(real)[:80]}\n"
                    f"        `figures[].caption` 写的是「这张图**证明了什么**」——"
                    f"Skill 2 已经把最难的那句话写好了。\n"
                    f"        **不填 caption 是最安全的**（整段自动取原文）。"
                    f"真要缩短，**只能删字，不能改字**。")


def _quote_and_caption(s: dict) -> list[tuple[str, str]]:
    out = []
    for i, b in enumerate(s.get("body", [])):
        if b.get("kind") == "quote":
            out.append((f"{s['id']}.body[{i}]:quote", b["text"]))
    if s.get("figure", {}).get("caption"):
        out.append((f"{s['id']}.figure.caption", s["figure"]["caption"]))
    return out


# ---------------------------------------------------------------- B · 诚实

#: 声称**做过物理实验**的措辞。
#
#  注意「实测」**不在**里面 —— 这个 repo 用它表示「数值上测到的」（results.json
#  里到处都是）。只拦那些**无歧义地宣称做过实验**的说法。
#  「实验方案」「待执行的实验」也不拦 —— 那是诚实的（附录里就该写它）。
_FAKE_EXP = [
    "实验测得", "实验数据", "实验结果", "实验值", "实测数据", "实验观测",
    "我们测量", "我们测得", "测量结果表明", "实验表明", "实验证实", "实验验证了",
    "experimental data", "we measured", "our measurement", "measured value",
    "experiment shows", "experimentally",
]


def check_honesty(deck: dict, R: dict) -> None:
    slides = deck["slides"]
    corpus = all_strings(deck)
    status = R.get("status", "?")

    # ---- FIG-UNKNOWN：**禁止夹带非仿真产出的图**
    known = {f["id"] for f in R.get("figures", [])}
    used = set()
    for s in slides:
        f = s.get("figure")
        if not f:
            continue
        fid = f["figure_id"]
        used.add(fid)
        if fid not in known:
            err("FIG-UNKNOWN",
                f"{s['id']}：图 `{fid}` 不在 results.json 的 figures[] 里。\n"
                f"        有的是：{sorted(known)}\n"
                f"        **PPT 上的每一张图都必须是 Skill 2 验证过的产出。**\n"
                f"        随手找一张好看的示意图放上去 —— 它没有 SIMULATION 戳，"
                f"没有断言，没有出处。**那不是论据，是装饰。**")
    for fid in sorted(known - used):
        warn("FIG-ORPHAN",
             f"图 {fid} 一次都没上 PPT —— 它是 Skill 2 验证过的一条论据。"
             f"真的不需要吗？（附录也算。）")

    # ---- DISCLOSURE-MISSING：「这是仿真」必须说出口
    has_disc = any(b.get("kind") == "disclosure"
                   for s in slides for b in s.get("body", []))
    if not has_disc:
        err("DISCLOSURE-MISSING",
            "整份 PPT 里没有一个 `disclosure` 块。\n"
            "        **必须有一页明确声明「以下全部结果来自数值仿真，不是实验数据」**"
            "（pipeline.md §7 的底线）。\n"
            "        真实 IYPT 的评分里实验占很大权重。**一份不加区分地展示仿真结果的 PPT，"
            "在 Physics Fight 上就是在冒充实验。**\n"
            "        在数值探究那一节的第一页加 `{\"kind\": \"disclosure\"}`。\n"
            "        （它不接受任何参数 —— **文字是写死的，你改不了措辞**。"
            "凡是可以被措辞软化的底线，迟早会被措辞软化。）")

    # ---- FAKE-EXPERIMENT：仿真不许说成实验
    for s in slides:
        for where, text in authored_texts(s):
            low = text.lower()
            for bad in _FAKE_EXP:
                if bad.lower() in low:
                    err("FAKE-EXPERIMENT",
                        f"{where}：出现「{bad}」—— **但这条流水线没有做过任何实验。**\n"
                        f"        原文：{text[:90]}\n"
                        f"        这不是措辞问题，是把仿真伪装成实验数据（pipeline.md §7）。\n"
                        f"        **仿真验证「方程解对了」，实验验证「方程写对了」。**\n"
                        f"        想说数值上测到的 -> 用「实测」「数值给出」；"
                        f"想说该做的实验 -> 用「实验方案（待执行）」。")

    # ---- STATUS-HIDDEN：status 不是 PASS，就必须有「模型边界」一节
    if status != "PASS":
        if not any(s.get("section") == "boundary" for s in slides):
            err("STATUS-HIDDEN",
                f"results.json 的 status 是 `{status}`，但 PPT 里**没有 `boundary`"
                f"（模型边界）那一节**。\n"
                f"        status_reason：{str(R.get('status_reason',''))[:150]}\n"
                f"        `{status}` 意味着某条结论已被数值**证伪**或**降级**。"
                f"不许当作没发生。\n"
                f"        **而且这不是要藏的东西 —— 这是加分项**："
                f"一个标出了 RISKY 假设、并且用数值把它打崩了的报告，"
                f"说明模型边界被**正确定位**了。\n"
                f"        藏起来的 RISKY 才是被 Opponent 一击致命的那个。")

    # ---- FALSIFIED-DROPPED：**选择性汇报** —— 这个脚本存在的头号理由
    #
    #  一份只讲通过了的断言的 PPT，读起来和一份全部通过的 PPT **一模一样**。
    #  **这就是它危险的原因。**
    #
    #  ★★ 第一版这道门是**摆设** —— 被冒烟测试当场打穿。
    #
    #     第一版查的是「这条断言的 id 或它的来源（A-1）有没有在 deck 里出现过」。
    #     然后冒烟测试**删掉了整个「模型边界」节** —— 而它照样通过了。
    #
    #     为什么：**A-1 是一条假设的名字。** 它在理论页的假设台账里本来就会出现。
    #     于是一份对那两条崩掉的假设**只字未提**的 PPT，照样处处提到 A-1。
    #
    #     > **名字出现 ≠ 结论被汇报。**
    #
    #  所以现在要求：**被证伪 / 被降级的断言，必须以 `verdict` 块的形式出现。**
    #
    #  为什么是 `verdict` 块而不是「随便讲一句」：verdict 块的 expect / measured /
    #  verdict **全部从 results.json 长出来，一个字都不经你的手**。
    #  **你无法在展示它的同时，把它说成一次成功。**
    #  ——这正是它比任何措辞要求都硬的地方。
    verdict_blocks = {b["assertion_id"] for s in slides for b in s.get("body", [])
                      if b.get("kind") == "verdict"}
    vb_slide = {b["assertion_id"]: s for s in slides for b in s.get("body", [])
                if b.get("kind") == "verdict"}
    main_ids = {s["id"] for s in slides if s.get("section") != "appendix"}

    for a in R.get("assertions", []):
        v = a.get("verdict")
        if v not in ("FAIL-MODEL", "PRESCRIBED"):
            continue
        aid = a["id"]
        if aid not in verdict_blocks:
            err("FALSIFIED-DROPPED",
                f"断言 `{aid}`（来源 {a.get('source')}）判 **{v}** —— "
                f"被数值证伪 / 触发了预注册降级，\n"
                f"        **而整份 PPT 里没有一个 `verdict` 块展示它。**\n"
                f"        实测：{str(a.get('measured'))[:70]}\n"
                f"\n"
                f"        这就是**选择性汇报**：六条断言过了四条，你讲了那四条 ——\n"
                f"        剩下两条不是「没讲」，是**被消失**了。"
                f"**而 Opponent 专门找这个，一找一个准。**\n"
                f"\n"
                f"        **注意：在别处提一句「A-1」不算汇报。** A-1 是一条假设的名字，\n"
                f"        它在理论页的假设台账里本来就会出现。**名字出现 ≠ 结论被汇报。**\n"
                f"\n"
                f"        修法（一行）：在 `boundary` 那一节放\n"
                f"            {{\"kind\": \"verdict\", \"assertion_id\": \"{aid}\"}}\n"
                f"        期望、实测、判定**全部从 results.json 长出来** ——"
                f"一个字都不用你打，\n"
                f"        因此**一个字都不会走样**。")
        elif vb_slide[aid]["id"] not in main_ids:
            warn("FALSIFIED-BURIED",
                 f"断言 `{aid}` 判 {v}，但它的 verdict 块**只在附录里**"
                 f"（{vb_slide[aid]['id']}）。\n"
                 f"        主线里避而不谈 —— 这在 Opponent 眼里和藏起来没有区别。")

    # ---- RISKY 假设崩了，必须在**模型边界 / 总结**里出现（不能只在理论页被提名）
    for c in R.get("risky_checks", []):
        if c.get("holds") is not False:
            continue
        aid = c["assumption_id"]
        where = [s["id"] for s in slides
                 if s.get("section") in ("boundary", "summary")
                 and aid in json.dumps(s, ensure_ascii=False)]
        if not where:
            err("FALSIFIED-DROPPED",
                f"RISKY 假设 `{aid}` **不成立**（holds = false），"
                f"但 `boundary` / `summary` 两节里一个字都没提它。\n"
                f"        结果：{str(c.get('result'))[:80]}\n"
                f"        **标出来的 RISKY + 一个验过它的数值实验 = 满分答案；"
                f"藏起来的 RISKY = 被一击致命。**\n"
                f"        （在理论页的假设台账里提到它的名字**不算** —— 那里本来就该有它。）")

    # ---- 任务：一条都不许掉
    tasks = [t["task_id"] for t in R.get("tasks_answered", [])]
    if not any(s.get("layout") == "checklist" for s in slides):
        err("NO-CHECKLIST",
            "PPT 里没有 `layout: \"checklist\"` 的总结页。\n"
            "        **13 份真实 IYPT 报告，最后一页就是「题目任务逐条打勾」这张表。**\n"
            "        它直接从 results.json 的 tasks_answered[] 长出来 —— 一个字都不用你打。")
    covered = {t for s in slides if s.get("section") != "appendix"
               for t in (s.get("answers_task") or [])}
    for tid in tasks:
        if tid not in covered:
            err("TASK-UNCOVERED",
                f"任务 `{tid}` **没有任何一页主线幻灯片挂在它上面**"
                f"（slides[].answers_task）。\n"
                f"        题面：{str(next((t.get('quoted_statement','') for t in R['tasks_answered'] if t['task_id']==tid), ''))[:80]}\n"
                f"        在总结页打个勾，不等于在报告里回答了它。**评委听的是主线。**")
    for tid in sorted(covered - set(tasks)):
        warn("TASK-UNKNOWN",
             f"slides[].answers_task 里的 `{tid}` 不在 results.json 的 tasks_answered[] 里。")


# ---------------------------------------------------------------- C · 结构与时间

_SECTIONS = {"problem", "picture", "theory", "numerics", "boundary", "summary", "appendix"}
_LAYOUTS = {"title", "section", "bullets", "figure-full", "figure-left",
            "figure-right", "equation", "table", "checklist"}


def check_structure(deck: dict, R: dict) -> None:
    if deck.get("problem_slug") != R.get("problem_slug"):
        err("SLUG-MISMATCH",
            f"deck.json 的 problem_slug（{deck.get('problem_slug')}）和 "
            f"results.json 的（{R.get('problem_slug')}）对不上 —— **你在给另一道题做 PPT。**")

    seen = set()
    for s in deck["slides"]:
        sid = s.get("id", "?")
        if sid in seen:
            err("ID-DUP", f"幻灯片 id 重复：{sid}")
        seen.add(sid)
        if not re.fullmatch(r"S-\d{2}", sid):
            err("ID-FORMAT", f"幻灯片 id `{sid}` 不合规 —— 必须是 S-01 这样"
                             f"（截图文件名和 ?only= 都用它）")
        if s.get("section") not in _SECTIONS:
            err("BAD-SECTION", f"{sid}：section `{s.get('section')}` 不认识。"
                               f"有的是：{sorted(_SECTIONS)}")
        if s.get("layout") not in _LAYOUTS:
            err("BAD-LAYOUT", f"{sid}：layout `{s.get('layout')}` 不认识。"
                              f"有的是：{sorted(_LAYOUTS)}")

        # ---- NO-TAKEAWAY：**每页必须有一句话**
        if not (s.get("takeaway") or "").strip():
            err("NO-TAKEAWAY",
                f"{sid} 没有 takeaway。\n"
                f"        **takeaway 是「这一页要说的那一句话」，而且必须是一个「判断」，"
                f"不是一个「名词」**：\n"
                f"          ✓ 「v_t ∝ a⁴ 站不住：指数是 3.44 不是 4.00」\n"
                f"          ✗ 「终速的标度律」\n"
                f"        **说不出这一句 = 这一页不知道自己为什么存在。**")

        if s.get("layout") == "checklist" and s.get("section") != "summary":
            warn("CHECKLIST-SECTION", f"{sid} 是打勾表，但 section 不是 summary")

    # ---- 时间预算
    budget = deck.get("duration_budget_s", 720)
    main = [s for s in deck["slides"]
            if s.get("section") != "appendix" and s.get("layout") != "section"]
    for s in main:
        if s.get("duration_s") is None:
            err("SLIDE-NODUR",
                f"{s['id']} 是主线页但没写 duration_s —— **时间预算不是可选项。**")
    used = sum(s.get("duration_s") or 0 for s in main)
    if used > budget:
        err("TIME-OVER",
            f"主线 {len(main)} 页要讲 **{used} s**，预算只有 **{budget} s**"
            f"（超 {used - budget} s）。\n"
            f"        IYPT 的 Reporter 是 **12 分钟**。**讲不完 = 结论页永远讲不到。**\n"
            f"        砍页，或者把内容挪进 `appendix`（附录不计时 —— "
            f"它是给 Opponent 追问时翻的）。")
    elif used < budget * 0.6:
        warn("TIME-THIN",
             f"主线只用了 {used} s / {budget} s —— 空了 {budget-used} s。"
             f"是不是有该讲的东西没讲？")


# ---------------------------------------------------------------- D · 渲染后

#: 密度上限。真实 IYPT 的幻灯片是**稀**的 —— **观众在听你讲，不是在读你的 PPT。**
#
#  但上限得**按 layout 分** —— 因为「读」和「扫」是两件事：
#
#    · 散文（bullets / figure-*）是**线性读**的。观众一旦开始读，就停止听你讲。
#      一页 190 字 ≈ 40 秒的阅读量，而你只打算讲 55 秒 —— **你在和自己的幻灯片抢观众。**
#    · 表格 / 打勾表是**扫**的。观众只看你指的那一行。真实 IYPT 报告的总结页
#      就是一张密密麻麻的任务打勾表 —— 而它是全场最有效的一页。
#
#  **给它们同一个上限，等于逼着人把表格拆成三页，或者把散文写成表格。两个都更糟。**
CAPS = {
    "table":     (320, 240),
    "checklist": (320, 240),
    None:        (190, 130),        # 其余（散文）
}
MAX_BULLETS_ERR, MAX_BULLETS_WARN = 8, 6
MIN_FONT_PX = 18            # 投影到会议厅大屏，后排要读

#: 图上最小的字，在原生 PNG 里有多少像素。
#  `iypt.mplstyle`：`font.size: 13`（pt），`savefig.dpi: 200` -> 13 × 200/72 ≈ 36 px。
#  图被缩到 s 倍，这个字就只剩 36·s px。
FIG_FONT_PX_AT_200DPI = 13.0 * 200.0 / 72.0

#: 两档。为什么不是一档 —— 见 check_render 里的长注释。
FIG_FONT_WARN = 18.0        # 低于它：图上的刻度读不到了。**确认结论不依赖它。**
FIG_FONT_ERR = 12.0         # 低于它：连轴标题和直标都没了。**这张图废了。**


def check_render(ws: Path, deck: dict) -> None:
    layouts = {s["id"]: s.get("layout") for s in deck["slides"]}
    html = ws / "03-slides" / "slides.html"
    if not html.is_file():
        err("NO-BUILD",
            f"{html} 不存在 —— **先跑 `python 03-slides/build.py`。**\n"
            f"        没渲染过的幻灯片，**溢出、裁切、字号**全都查不了 —— "
            f"而那正是生成式幻灯片最常见的病。")
        return

    try:
        import render_html as rh
        rep = rh.audit(html)
    except Exception as e:                                        # noqa: BLE001
        warn("AUDIT-FAILED", f"渲染后审计跑不起来（{type(e).__name__}: {e}）—— "
                             f"溢出/字号/密度这几道门这次没查。")
        return

    for s in rep["slides"]:
        sid = s["id"] or "?"

        if s["clipped_y"] or s["clipped_x"]:
            err("OVERSET",
                f"{sid}：**内容塞不下，被裁掉了**"
                f"（{'纵向' if s['clipped_y'] else ''}{'横向' if s['clipped_x'] else ''}）。\n"
                f"        字 {s['words']}，bullet {s['bullets']}。**砍内容，或拆成两页。**")

        for o in s["overflow"]:
            err("OVERFLOW",
                f"{sid}：<{o['tag']} class=\"{o['cls']}\"> **跑出幻灯片边界 "
                f"{o['px']}px（{o['side']}）**。\n"
                f"        内容：{o['text'][:60]}")

        for o in s["overset"]:
            err("OVERSET",
                f"{sid}：<{o['tag']} class=\"{o['cls']}\"> 的内容**被自己裁掉了 "
                f"{o['px']}px**。\n        内容：{o['text'][:60]}")

        lay = layouts.get(sid)
        hi, lo = CAPS.get(lay if lay in CAPS else None)
        if s["words"] > hi:
            err("TOO-DENSE",
                f"{sid}（{lay}）：**{s['words']} 字**（上限 {hi}）。\n"
                f"        **观众在听你讲，不是在读你的 PPT。** 一页一个 takeaway。\n"
                f"        砍掉的话不是丢了 —— 放进 `notes`（讲稿）里，"
                f"由**你**说出来，而不是让幻灯片替你说。")
        elif s["words"] > lo:
            warn("DENSE", f"{sid}（{lay}）：{s['words']} 字，偏密（软上限 {lo}）")

        if s["bullets"] > MAX_BULLETS_ERR:
            err("TOO-MANY-BULLETS",
                f"{sid}：{s['bullets']} 个 bullet（上限 {MAX_BULLETS_ERR}）。"
                f"**该拆页了。**")
        elif s["bullets"] > MAX_BULLETS_WARN:
            warn("BULLETS", f"{sid}：{s['bullets']} 个 bullet，偏多")

        mf = s["min_font_px"]
        if mf is not None and mf < MIN_FONT_PX:
            err("FONT-SMALL",
                f"{sid}：最小字号 **{mf}px**（下限 {MIN_FONT_PX}px）。\n"
                f"        Physics Fight 是**投影到会议厅大屏** —— 后排读不到的字，"
                f"等于没写。")

        # ---- ★ 图上的字够不够大 —— **这和幻灯片上的字是两回事**
        #
        #  `min_font_px` 完全看不到这件事：**图对它来说只是一个 <img>。**
        #  于是这一页在每一道门下都是干净的，实际上却有半页是废的。
        #
        #  分两档，因为「半栏图」本身是**合法**的设计：
        #
        #    · 半栏图里，**图负责「形状」，右栏的 verdict 块负责「数字」**。
        #      观众看曲线怎么走，数字由讲的人说出来、由 21px 的 verdict 块复述。
        #      轴刻度读不到 —— **只要这一页的结论不依赖它**，就不是错。
        #      → **WARN**：逼你确认一次，而不是逼你改。
        #
        #    · 但缩到某个程度，**连轴标题、图例、直标的斜率都没了** —— 那张图就只剩
        #      一团彩色的线，什么都证明不了。
        #      → **ERROR**。
        #
        #  实测（S-10 / S-08）：V-1 和 F-1 都是 **13 英寸宽的双面板图**，
        #  塞进半栏缩到 0.27x，13pt 的字只剩 10px。**双面板图塞不进半栏。**
        for f in s.get("figs", []):
            eff = FIG_FONT_PX_AT_200DPI * f["scale"]
            base = (f"{sid}：图被缩到 **{f['scale']:.2f}×**"
                    f"（原生 {f['natural_w']}px → 渲染 {f['rendered_w']}px）——"
                    f"图上 13pt 的字只剩 **{eff:.0f}px**。")
            if eff < FIG_FONT_ERR:
                err("FIG-TOO-SMALL",
                    base + f"（硬下限 {FIG_FONT_ERR}px）\n"
                    f"        **这个尺寸下，轴标题、图例、直标的斜率全都没了** ——"
                    f"这张图只剩一团彩色的线，什么都证明不了。\n"
                    f"        **双面板图塞不进半栏。** 换 `figure-full`，"
                    f"或者让 Skill 2 把它拆成两张。")
            elif eff < FIG_FONT_WARN:
                warn("FIG-SMALL",
                     base + f"（软下限 {FIG_FONT_WARN}px）\n"
                     f"        半栏图里，**图负责「形状」，右栏的 verdict 块负责「数字」**"
                     f" —— 这是合法的设计。\n"
                     f"        但请确认一次：**这一页的结论，不依赖读者读出图上的刻度。**"
                     f"依赖的话，换 `figure-full`。")

    if rep["fonts"].get("cjk_ok") is False:
        warn("CJK-FONT", "浏览器报告**找不到中文字体** —— 幻灯片上的中文可能是豆腐块。"
                         "渲出 PNG 用眼睛确认一下。")


# ---------------------------------------------------------------- main

def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    ws = Path(sys.argv[1]).resolve()

    print(f"检查工作区: {ws.name}")
    deck, R = load(ws)
    if deck is None:
        _report()
        return 1

    n_main = len([s for s in deck["slides"] if s.get("section") != "appendix"])
    print(f"对拍的契约: 02-sim/results.json   (status = {R.get('status')})")
    print(f"deck: {len(deck['slides'])} 页（主线 {n_main}，"
          f"附录 {len(deck['slides']) - n_main}）"
          f"   预算 {deck.get('duration_budget_s', 720)} s")
    print()

    check_structure(deck, R)
    check_provenance(deck, R)
    check_honesty(deck, R)
    check_render(ws, deck)

    return _report()


def _report() -> int:
    if ERRORS:
        print(f"✗ {len(ERRORS)} 个 ERROR —— **必须清零**\n")
        for e in ERRORS:
            print(f"  {e}\n")
    if WARNINGS:
        print(f"⚠ {len(WARNINGS)} 个 WARNING（看一眼，多数该修）\n")
        for w in WARNINGS:
            print(f"  {w}\n")
    if not ERRORS:
        print("✓ 机械检查全部通过。")
        print("  但这**不代表 PPT 是好的** —— 它只代表：")
        print("    · 每个数字都能追回 results.json")
        print("    · 被证伪的东西没有被藏起来")
        print("    · 仿真没有被讲成实验")
        print("    · 没有溢出、没有被裁、后排读得到")
        print()
        print("  ★ 接下来必须做的事，这个脚本做不了：")
        print("    **Read 03-slides/png/S-*.png，逐页用眼睛看。**")
        print("    然后走 iypt-design-review（D1–D16 + S1–S10）。")
        print("    **没看过的页，不许判 PASS。**")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
