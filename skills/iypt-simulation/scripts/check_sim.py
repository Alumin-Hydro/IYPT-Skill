#!/usr/bin/env python3
"""IYPT 仿真的机械检查器。

只做**确定性可判**的检查——不做物理判断，也不判断你的数值对不对。
它判断的是：**你有没有真的跑完那些你答应要跑的东西，以及你有没有真的读过契约。**

最重要的一条：`quoted_expectation` 必须是 model-spec 对应字段的**逐字子串**。

  验证类 agent 的通用失效模式是**拿自己重推的正确版本替换掉作者写的字**——
  它会独立把物理推一遍，然后拿数值结果跟"自己心里的预期"比对，而不是跟
  Skill 1 白纸黑字承诺的东西比对。**它验证的是它自己。**

  抄写这个动作本身就是强制去读它。这个脚本机械地验证你真的抄了。

用法:
    python check_sim.py iypt/magnetic-brake

退出码: 0 = 无 error（可能有 warning）；1 = 有 error；2 = 用不了（文件缺失等）
"""

import json
import re
import sys
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


def norm(s: str) -> str:
    """归一化空白，好让「换行重排过的引文」仍然算逐字抄写。

    **只归一化空白**——一个实词都不许变。改了词就是复述，复述就会走样，
    而走样的方向永远对自己有利。
    """
    return re.sub(r"\s+", " ", (s or "")).strip()


# ---------------------------------------------------------------- 载入

def load(workspace: Path):
    res_path = workspace / "02-sim" / "results.json"
    acc_path = workspace / "02-sim" / "acceptance.md"
    cur_path = workspace / "handoff" / "model-spec.json"

    if not cur_path.is_file():
        print(f"找不到 {cur_path} —— Skill 2 没有输入，流水线断了", file=sys.stderr)
        sys.exit(2)
    if not res_path.is_file():
        print(f"找不到 {res_path} —— Skill 2 没有产出契约，下游拿不到东西", file=sys.stderr)
        sys.exit(2)

    try:
        res = json.loads(res_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"results.json 不是合法 JSON: {e}", file=sys.stderr)
        sys.exit(2)

    # ★ 按 results.json 声明的 model_spec_version 去找**它当时跑的那一版** spec。
    #
    #   反向边修订过之后，handoff/model-spec.json 已经是 r2 了，而这份 results.json
    #   记录的是对 r1 的运行 —— 拿 r2 去校验 r1 的引文，会全线报 QUOTE-DRIFT，那是
    #   假警报。归档链在这里从「审稿的物证」变成了**承重结构**。
    #
    #   （反过来说：results 声明 r1 但归档里没有 r1 —— 那是真问题，归档链断了。）
    ver = (res.get("model_spec_version") or "").strip()
    spec_path = cur_path
    if ver and ver not in ("current", "r0"):
        archived = workspace / "handoff" / f"model-spec-{ver}.json"
        if archived.is_file():
            spec_path = archived
        else:
            # 当前版就是它声明的那版（还没被修订过）—— 正常
            pass

    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"{spec_path.name} 不是合法 JSON: {e}", file=sys.stderr)
        sys.exit(2)

    acc = acc_path.read_text(encoding="utf-8") if acc_path.is_file() else None
    if acc is None:
        err("NO-ACCEPTANCE", "02-sim/acceptance.md 不存在 —— 验收断言必须在写求解器之前写下来。"
                            "没有它，「断言」就只是数值结果的复述。")
    return spec, res, acc, spec_path


# ---------------------------------------------------------------- 零号规则：逐字引文

def check_quotes(spec: dict, res: dict) -> None:
    """★ 每条 quoted_expectation 必须是 model-spec 对应字段的逐字子串。"""

    # 把 model-spec 里所有「可被引用」的字段收成一个池子
    pool: dict[str, str] = {}
    for f in spec.get("figures", []):
        pool[f"figure:{f.get('id')}"] = f.get("expected_shape", "")
    for c in spec.get("risky_assumption_checks", []):
        # degenerate_signature 也是可引用的字段 —— 结构型 must_not 断言正是从它抄来的
        pool[f"risky_check:{c.get('assumption_id')}"] = " ".join(
            (c.get("pass_criterion") or "", c.get("task") or "",
             c.get("degenerate_signature") or ""))
    for t in spec.get("targets", []):
        pool[f"target:{t.get('symbol')}"] = \
            (t.get("analytical_prediction", "") + " " + (t.get("scaling_law") or ""))
    for e in spec.get("equations", []):
        pool[f"equation_limit:{e.get('id')}"] = \
            ((e.get("numerical_notes") or "") + " " + (e.get("suggested_method") or ""))
    # ★ 中间量验证（V-*）与假设（A-*）也是可引用的字段。
    #   magnetic-brake 恰好把 V 图写进了契约 figures[]，所以没暴露这个洞；
    #   electrical-damping 的契约里 V-1..V-3 只活在 model_validation_checks[] ——
    #   没有这两类池子，从 V 检查抄来的引文只能落 QUOTE-NOSRC（真引文被判成假的）。
    #   assumptions[].impact_if_false 则是 must_not「陷阱值」的常见出处（如 c₂ 的
    #   0.0345 → 0.0360）。
    for v in spec.get("model_validation_checks", []):
        pool[f"validation:{v.get('id')}"] = " ".join(
            (v.get("intermediate_quantity") or "",
             v.get("why_it_can_fail_silently") or "",
             " ".join(v.get("independent_checks") or []),
             v.get("experimental_check") or ""))
    for a in spec.get("assumptions", []):
        pool[f"assumption:{a.get('id')}"] = " ".join(
            (a.get("statement") or "", a.get("criterion") or "",
             a.get("criterion_check") or "", a.get("breaks_when") or "",
             a.get("impact_if_false") or ""))

    normed = {k: norm(v) for k, v in pool.items()}
    all_spec_text = norm(json.dumps(spec, ensure_ascii=False))

    for a in res.get("assertions", []):
        aid = a.get("id", "?")
        q = norm(a.get("quoted_expectation", ""))
        kind = a.get("source_kind", "")
        src = a.get("source", "")
        key = f"{kind}:{src}"

        # 收敛门是 Skill 2 **自己的**纪律，不来自 model-spec —— 没有原文可抄。
        # （契约里的东西才要求逐字抄：figure / target / risky_check / equation_limit。）
        if kind == "convergence":
            continue

        if not q:
            err("QUOTE-EMPTY", f"{aid} 的 quoted_expectation 是空的 —— "
                              f"逐字抄写被验对象的原文是硬要求，抄写这个动作本身就是强制你去读它")
            continue

        target_text = normed.get(key)
        if target_text is None:
            # 来源指错了地方；退一步，看它是否至少出现在 spec 的某处
            if q in all_spec_text:
                warn("QUOTE-SRC", f"{aid} 的引文能在 model-spec 里找到，但 source_kind:source "
                                  f"= `{key}` 对不上任何字段 —— 来源标错了")
            else:
                err("QUOTE-NOSRC", f"{aid} 的 source `{key}` 在 model-spec 里不存在，"
                                   f"且引文也匹配不上任何字段")
            continue

        if q not in target_text:
            if norm(q[:20]) and norm(q[:20]) in target_text:
                err("QUOTE-DRIFT",
                    f"{aid} 的 quoted_expectation **不是逐字抄写**（开头能对上，后面走样了）。\n"
                    f"        你写的：{q[:110]}\n"
                    f"        原文是：{target_text[:110]}\n"
                    f"        —— 复述一次就走样，而走样的方向永远对自己有利。逐字抄。")
            else:
                err("QUOTE-DRIFT",
                    f"{aid} 的 quoted_expectation **不是 `{key}` 字段的子串** —— "
                    f"这是复述，不是抄写。\n"
                    f"        你写的：{q[:110]}\n"
                    f"        原文是：{target_text[:110]}")

    # RISKY 检查的 pass_criterion 同样要逐字
    for c in res.get("risky_checks", []):
        aid = c.get("assumption_id", "?")
        q = norm(c.get("quoted_pass_criterion", ""))
        src = normed.get(f"risky_check:{aid}", "")
        if not q:
            err("QUOTE-EMPTY", f"risky_check {aid} 没有 quoted_pass_criterion（逐字抄）")
        elif q not in src:
            err("QUOTE-DRIFT", f"risky_check {aid} 的 quoted_pass_criterion 不是逐字抄写：\n"
                               f"        你写的：{q[:110]}\n"
                               f"        原文是：{src[:110]}")

    # Gate 0 的配方也要逐字。
    # ★ 对「解析后的字段池」查，不能对 json.dumps 的原文查 —— dumps 会把真换行转义成
    #   反斜杠+n 两个字符，norm() 折叠不了它 ⟹ **任何多行 recipe 必然误报 DRIFT**
    #   （electrical-damping 实测：recipe 是程序化切片、字面逐字，照样报）。
    #   断言引文没这个病，因为 check_quotes 用的本来就是解析后的 pool。
    for g in res.get("gates", []):
        if g.get("id") != "gate-0-limit":
            continue
        q = norm(g.get("recipe", ""))
        if not q:
            err("GATE0-NORECIPE", "Gate 0 没有 recipe —— 必须逐字抄写 equations[].numerical_notes "
                                  "里的极限对拍配方。抄不上说明你没读它。")
        elif not any(q in v for v in normed.values()) and q not in all_spec_text:
            warn("GATE0-RECIPE-DRIFT",
                 "Gate 0 的 recipe 不是 model-spec 的逐字子串。\n"
                 "        如果你是**有意**改正了一个错误的配方，那应当在 spec_defects[] 里"
                 "登记这个 SPEC-DEFECT，而不是悄悄换掉它。")


# ---------------------------------------------------------------- 覆盖度

def check_tasks_and_validation(spec: dict, res: dict) -> None:
    """★ 任务要逐条打勾；中间量验证要全跑。"""

    # ---- 每条 task 都必须被答（或诚实标 answered=false）
    spec_t = {t.get("id"): t for t in spec.get("tasks", [])}
    res_t = {t.get("task_id"): t for t in res.get("tasks_answered", [])}

    if spec_t and not res_t:
        err("NO-TASKS-ANSWERED",
            f"model-spec 里有 {len(spec_t)} 条 task，但 results.json 里没有 tasks_answered[]。\n"
            f"        **每条任务都必须被答掉，并逐条打勾** —— 真实的 IYPT 报告最后一页就是这张表。\n"
            f"        答不上来就诚实标 answered=false，说清卡在哪。**藏起来才是灾难。**")

    for tid, t in spec_t.items():
        if tid not in res_t:
            err("TASK-NOTANSWERED",
                f"task {tid}（{(t.get('statement') or '')[:40]}）在 results.json 的 "
                f"tasks_answered[] 里**没有出现** —— 挖出来的任务，一条都不许漏答。")
            continue
        a = res_t[tid]
        if not a.get("by_figures"):
            err("TASK-NOFIG", f"{tid} 没写 by_figures —— 是哪几张图/target 回答了它？")
        if not a.get("answer"):
            err("TASK-NOANSWER",
                f"{tid} 没写 answer —— **要一句话的答案，不是「见图 F-2」。**")

    # ---- 每条 model_validation_check 都必须跑
    spec_v = {v.get("id"): v for v in spec.get("model_validation_checks", [])}
    res_v = {v.get("id"): v for v in res.get("validation_checks", [])}

    for vid, v in spec_v.items():
        if vid not in res_v:
            err("VALIDATION-SKIPPED",
                f"{vid}（{v.get('intermediate_quantity','?')}）的**中间量验证没跑**。\n"
                f"        **「最终结果对了」不代表「模型对了」—— 两个错误可以互相抵消。**\n"
                f"        真题的做法是拿高斯计去测 B 场（链条中间的量），不是拿末速度反证模型。")
            continue
        r = res_v[vid]
        paths = r.get("paths") or []
        if len(paths) < 2:
            err("VALIDATION-ONEPATH",
                f"{vid} 只有 {len(paths)} 条验证路径 —— **至少要两条互不依赖的**。"
                f"只有一条路 = 没有交叉验证。")
        if r.get("passed") is False and res.get("status") != "FAIL-CODE":
            err("VALIDATION-FAILED-BUT-SHIPPED",
                f"{vid} 的中间量验证**没过**，但 status 是 `{res.get('status')}`。\n"
                f"        中间量算错了 = 实现问题 = **FAIL-CODE**，不许交付下游。")


def check_coverage(spec: dict, res: dict, workspace: Path) -> None:
    """契约里答应要跑的，一件都不许少。"""

    # --- 图
    spec_figs = {f.get("id"): f for f in spec.get("figures", [])}
    res_figs = {f.get("id"): f for f in res.get("figures", [])}
    # ★ model_validation_checks[].figure 点名的 V-* 也是契约要求的图 ——
    #   magnetic-brake 的契约把 V 图直接写进了 figures[]，所以这个洞两道题才暴露：
    #   electrical-damping 的 V-1..V-3 只活在 validation checks 里，曾被误报「装饰」。
    val_figs = {v.get("figure") for v in spec.get("model_validation_checks", [])
                if v.get("figure")}

    for fid in spec_figs:
        if fid not in res_figs:
            err("FIG-MISSING", f"model-spec 要求画 {fid}，但 results.json 里没有它")
    for fid in res_figs:
        if fid not in spec_figs and fid not in val_figs:
            warn("FIG-EXTRA", f"results.json 里的 {fid} 不在 model-spec 的 figures[] 里 —— "
                              f"没有 expected_shape 的图没有验收标准，它只是装饰")

    # ★ 断言 id 的全集 —— 下面要用它查悬空引用
    all_as_ids = {a.get("id") for a in res.get("assertions", [])}
    seen_paths: dict[str, str] = {}

    for fid, f in res_figs.items():
        if not f.get("assertion_ids"):
            err("FIG-NOASSERT", f"{fid} 没有对应的断言 —— **一张没有验收标准的图就是装饰**")
        if not f.get("simulation_stamped"):
            err("FIG-NOSTAMP", f"{fid} 的 simulation_stamped 不是 true")

        # ---- ★ assertion_ids 里的 id 必须**真的存在**于 assertions[]
        #
        #  FIG-NOASSERT 只查了「非空」。而一个**编出来的** id（"AS-V1"）是非空的 ——
        #  它从 FIG-NOASSERT 底下大摇大摆走了过去，图看上去有验收标准，其实一条都没有。
        #
        #  **实测（magnetic-brake）**：V-1…V-4 的 assertion_ids 全是 `AS-V{n}`，
        #  四个 id 在 assertions[] 里一个都不存在。连带掩盖了一个更糟的事实：
        #  **V-4 一条真断言都没有** —— 而 FIG-NOASSERT 本来就是为了抓这个而写的。
        #
        #  **非空 ≠ 有效。凡是 id 之间的引用，都必须解析一遍。**
        dangling = [i for i in (f.get("assertion_ids") or []) if i not in all_as_ids]
        if dangling:
            err("FIG-ASSERT-DANGLING",
                f"{fid} 的 assertion_ids 里有**不存在**的断言 id：{', '.join(dangling)}\n"
                f"        assertions[] 里根本没有它们。**一张挂着假 id 的图 = 一张没有验收标准的图**，"
                f"只是伪装成有。\n"
                f"        （典型踩法：图的 id 是 V-4，就顺手写 `assertion_ids=[\"AS-V4\"]` —— "
                f"而真正的断言叫 AS-31。）")

        # ---- ★ 两张图不许指向同一个文件
        #
        #  **实测（magnetic-brake）**：F-5 是 kind: animation，没有静态 PNG，
        #  于是 run_all.py 拿 F-1 的 PNG 顶了上去。后果：Skill 3 照 `path` 取图，
        #  会把**幂律图**配上**涡流的 caption** 摆进 PPT —— 而没有任何检查会发现，
        #  因为 F-1.png 确实存在（FIG-NOFILE 过）。
        p = f.get("path")
        if p:
            if p in seen_paths:
                err("FIG-PATH-DUP",
                    f"{fid} 和 {seen_paths[p]} 指向**同一个文件**：{p}\n"
                    f"        两张图共用一个 PNG = 其中至少一张是**冒名顶替**的。"
                    f"下游（Skill 3）会照 `path` 取图，把它配上另一张图的 caption 摆进 PPT。")
            seen_paths[p] = fid

            fp = workspace / p if not Path(p).is_absolute() else Path(p)
            if not fp.is_file():
                # results.json 里的路径可能相对工作区，也可能相对 repo 根
                alt = Path(p)
                if not alt.is_file():
                    err("FIG-NOFILE", f"{fid} 的产出文件不存在: {p}")
        else:
            # ---- ★ 每张图都必须有一张静态 PNG —— **包括动画**。
            #
            #  **PPT 和 PDF 印不出动画。** Physics Fight 上你面对的是投影和评委手里的讲义。
            #  交互页面是**加分项**，不是**替代品**：
            #    · Skill 3 必须能往幻灯片上放一张静止帧
            #    · Skill 4 的铁律 0 要求「真的打开 PNG 用眼睛看」—— 没有 PNG 就没法审
            #    · SIMULATION 戳是在 SVG 里 grep 的（见 check_stamps）；没有 SVG 就没有戳
            err("FIG-NOSTILL",
                f"{fid} 没有 `path`（静态 PNG）。**动画也必须出一张静止帧。**\n"
                f"        PPT 和 PDF **印不出动画**，Skill 4 也没法「打开 PNG 用眼睛看」。\n"
                f"        `path_interactive` 是**加分项**，不是**替代品** —— 两个都要有。")

    # --- 目标量
    spec_t = {t.get("symbol") for t in spec.get("targets", [])}
    res_t = {t.get("symbol") for t in res.get("targets", [])}
    for s in spec_t - res_t:
        err("TARGET-MISSING", f"model-spec 的 target `{s}` 在 results.json 里没有数值结果")

    for t in res.get("targets", []):
        if t.get("value_numeric") is None:
            err("TARGET-NOVAL", f"target `{t.get('symbol')}` 没有 value_numeric")
        if t.get("value_analytical") is not None and t.get("relative_deviation") is None:
            warn("TARGET-NODEV", f"target `{t.get('symbol')}` 有解析预测但没算相对偏差 —— "
                                 f"偏差是 RISKY 假设崩溃的量度，必须记录")

    # --- RISKY 验证任务：一条都不许跳
    spec_rc = {c.get("assumption_id") for c in spec.get("risky_assumption_checks", [])}
    res_rc = {c.get("assumption_id") for c in res.get("risky_checks", [])}
    for a in spec_rc - res_rc:
        err("RISKY-SKIPPED", f"RISKY 假设 {a} 的验证任务**没跑** —— 契约硬约束。"
                             f"RISKY 假设的存在意义就是它必须被数值验证。")

    for c in res.get("risky_checks", []):
        aid = c.get("assumption_id", "?")
        if c.get("holds") is None:
            err("RISKY-NOVERDICT", f"{aid} 没有 holds 判定")
        if c.get("prescribed_action") and c.get("prescribed_action_taken") is None:
            err("PRESCRIBED-UNTAKEN",
                f"{aid} 的 pass_criterion 里预先注册了应对动作，但没记录它执行了没有。\n"
                f"        **预注册的动作写了却不执行，比没写更糟。**")
        if c.get("prescribed_action") and c.get("prescribed_action_taken") is False:
            err("PRESCRIBED-REFUSED",
                f"{aid} 的预注册动作被触发了却**没有执行**：{c.get('prescribed_action', '')[:80]}")

    # ---- ★ 每条带 degenerate_signature 的 RISKY，必须有一条对应的 must_not 断言
    #
    #  degenerate_signature 是 Skill 1 交给你的**结构性陷阱** —— 它是唯一能识破
    #  "代码偷懒偷偷退化回玩具模型"的手段。收到了不用，等于白给。
    must_nots = {a.get("source") for a in res.get("assertions", [])
                 if a.get("assert_kind") == "must_not"}
    for c in spec.get("risky_assumption_checks", []):
        aid = c.get("assumption_id")
        if c.get("degenerate_signature") and aid not in must_nots:
            err("DEGEN-UNUSED",
                f"{aid} 的契约里给了 degenerate_signature（结构性退化特征），"
                f"但 results.json 里**没有对应的 must_not 断言**（source = {aid}）。\n"
                f"        契约原文：{norm(c['degenerate_signature'])[:110]}\n"
                f"        **这是唯一能识破「代码偷偷退化回玩具模型」的手段。收到了不用，等于白给。**\n"
                f"        血泪教训：只查「拟合出来的斜率是不是陷阱值」，会被「只少一个修正」的 bug\n"
                f"        以一个落在陷阱值和真值**之间**的数溜走（实测 3.79，陷阱 4.00，真值 3.44）。")


# ---------------------------------------------------------------- 断言的完整性

def check_assertions(res: dict) -> None:
    """不许有「未评估」的断言。"""
    seen = set()
    for a in res.get("assertions", []):
        aid = a.get("id", "?")
        if aid in seen:
            err("AS-DUP", f"断言 id 重复: {aid}")
        seen.add(aid)

        if a.get("measured") is None or a.get("measured") == "":
            err("AS-UNEVALUATED", f"{aid} 没有 measured —— **不许有未评估的断言，跳过一条 = 契约违约**")
        if not a.get("verdict"):
            err("AS-NOVERDICT", f"{aid} 没有 verdict")
        if a.get("verdict") in ("FAIL-CODE", "FAIL-MODEL", "PRESCRIBED") and not a.get("verdict_note"):
            err("AS-NONOTE", f"{aid} 判 {a['verdict']} 但没写 verdict_note")
        if not a.get("expect"):
            err("AS-NOEXPECT", f"{aid} 没有 expect —— 断言必须是机械可判的")

        # 歧义判读
        if a.get("source_kind") == "figure" and not a.get("interpretation"):
            warn("AS-NOINTERP",
                 f"{aid} 没有写 interpretation —— expected_shape 是自然语言，"
                 f"若原文有歧义，**必须记录你选了哪个读法**。不记录，agent 会挑对自己有利的读法。")


# ---------------------------------------------------------------- 验证门

def check_gates(res: dict) -> None:                                    # noqa: C901
    gates = {g.get("id"): g for g in res.get("gates", [])}

    if "gate-0-limit" not in gates:
        err("GATE0-MISSING",
            "**没有 Gate 0（极限对拍）的记录。**\n"
            "        它是纯数学恒等式，把「代码对不对」和「物理对不对」解耦。\n"
            "        没有它，后面每一个不符都是糊涂账 —— 你不知道该改代码还是改模型，于是你会改图。")
    else:
        g0 = gates["gate-0-limit"]
        if not g0.get("ran"):
            err("GATE0-NOTRUN", "Gate 0 没跑。**它必须最先跑，跑不过一律不许往下走。**")
        elif not g0.get("passed") and res.get("status") not in ("FAIL-CODE", "SPEC-DEFECT"):
            err("GATE0-FAILED-BUT-SHIPPED",
                f"Gate 0 没过，但 status 是 `{res.get('status')}`。\n"
                f"        Gate 0 不过 = 代码错。status 只能是 FAIL-CODE（改代码）"
                f"或 SPEC-DEFECT（配方本身错了）。")

    if "gate-1-convergence" not in gates:
        err("GATE1-MISSING",
            "没有收敛门的记录 —— 结果必须与网格/容差/截断无关。\n"
            "        不做这个，你那个「斜率 -1.02」可能纯粹是网格太粗，然后你会以为发现了物理。")
    else:
        # ★ 收敛门必须在**扫描端点**上也做，不能只在基准点做。
        #   （和 Skill 1 的「机制预算必须做扫描端点检查」是同一个道理。）
        g1 = gates["gate-1-convergence"]
        rows = (g1.get("numbers") or {}).get("rows") or []
        ev = g1.get("evidence", "")
        if len(rows) < 3 and not re.search(r"端点|endpoint|扫描的两端|sweep", ev):
            err("GATE1-BASELINE-ONLY",
                f"收敛门只有 {len(rows)} 个检查点 —— **看起来只在基准点做了**。\n"
                f"        **必须在扫描端点上也做。** 基准点收敛，不代表扫描的另一端也收敛。\n"
                f"        血泪教训：把广义积分的截断长度写成**绝对值**而非自然尺度的倍数，\n"
                f"        基准点上一切正常（Gate 0 也过，误差 0.017%），但扫描上端每个点都偏小一点，\n"
                f"        **拟合出的斜率是 3.4509，真值 3.4392 —— 差 0.012，肉眼完全看不出来。**\n"
                f"        （这和 Skill 1 的「机制预算必须做扫描端点检查」是同一个道理。）")

    for g in res.get("gates", []):
        if g.get("ran") and not g.get("evidence"):
            err("GATE-NOEVIDENCE", f"门 `{g.get('id')}` 没有 evidence —— "
                                   f"要具体数字，不是「通过了」")


# ---------------------------------------------------------------- SIMULATION 戳

def check_stamps(res: dict, workspace: Path) -> None:
    """★ SVG 是纯文本 XML —— 直接在里面 grep。这个检查伪造不了，除非你真的盖了戳。"""
    for f in res.get("figures", []):
        fid = f.get("id", "?")
        svg = f.get("path_svg")

        if not svg:
            err("STAMP-NOSVG",
                f"{fid} 没有 path_svg。\n"
                f"        SVG 是 SIMULATION 戳唯一可机械校验的载体（PNG 里的文字读不出来）。\n"
                f"        figkit.Figure 会自动同时存 PNG 和 SVG —— 没有 SVG 说明你绕过了 figkit。")
            continue

        p = workspace / svg if not Path(svg).is_absolute() else Path(svg)
        if not p.is_file():
            p = Path(svg)
        if not p.is_file():
            err("STAMP-NOFILE", f"{fid} 的 SVG 不存在: {svg}")
            continue

        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError as e:
            err("STAMP-UNREADABLE", f"{fid} 的 SVG 读不了: {e}")
            continue

        # matplotlib 会把文字拆成 <use> 引用的字形，也可能直接存 <text>。
        # 两种都查：字面串，或逐字母的 glyph 序列。
        if "SIMULATION" not in text and not re.search(
                r"S.{0,400}?I.{0,400}?M.{0,400}?U.{0,400}?L.{0,400}?A.{0,400}?T.{0,400}?I.{0,400}?O.{0,400}?N",
                text, re.S):
            err("STAMP-MISSING",
                f"{fid} 的 SVG 里找不到 SIMULATION 戳。\n"
                f"        **仿真结果绝不伪装成实验数据**（docs/pipeline.md §7）。\n"
                f"        真实 IYPT 里实验占很大权重——一张没标注的仿真图进了 PPT，\n"
                f"        在 Physics Fight 上会被当作伪造实验数据。这是学术不端，不是排版疏忽。")


# ---------------------------------------------------------------- status 自洽

def check_status(res: dict) -> None:
    st = res.get("status")
    verdicts = [a.get("verdict") for a in res.get("assertions", [])]

    if st != "PASS" and not res.get("status_reason"):
        err("STATUS-NOREASON", f"status 是 `{st}` 但没写 status_reason")

    if "FAIL-CODE" in verdicts and st != "FAIL-CODE":
        err("STATUS-INCONSISTENT",
            f"有断言判 FAIL-CODE，但 status 是 `{st}`。\n"
            f"        **FAIL-CODE 不许交付下游。** 回去改代码。")

    if "FAIL-MODEL" in verdicts and st not in ("MODEL-CHALLENGED", "GAP"):
        err("STATUS-INCONSISTENT",
            f"有断言判 FAIL-MODEL，但 status 是 `{st}` —— 应当是 MODEL-CHALLENGED（走反向边）。\n"
            f"        把「我的模型错了」悄悄改叙述成别的，正是这个 repo 要防的事。")

    if "PRESCRIBED" in verdicts and st == "PASS":
        warn("STATUS-PRESCRIBED",
             "有断言判 PRESCRIBED（命中了 Skill 1 预先注册的分支），但 status 是 PASS。\n"
             "        预注册的应对动作要执行，status 应为 PRESCRIBED-REVISION。")

    if st == "FAIL-CODE":
        err("STATUS-FAILCODE",
            "status = FAIL-CODE —— **不许交付下游**。Gate 0 / must_not / 收敛门 有一个没过。")

    # SPEC-DEFECT 的逃生舱防线
    for d in res.get("spec_defects", []):
        if not d.get("proof_without_simulation"):
            err("SPECDEFECT-NOPROOF",
                f"spec_defect `{d.get('field')}` 没有 proof_without_simulation。\n"
                f"        **如果你必须引用仿真数字才能说明「契约写错了」，那它就不是 SPEC-DEFECT——\n"
                f"        它是模型被数据打脸了。** 这条线不画死，SPEC-DEFECT 就是一个逃生舱：\n"
                f"        任何不想面对「我的模型错了」的 agent 都能从这里溜走。")


# ---------------------------------------------------------------- MATLAB 移植的诚实性

def check_matlab(res: dict, workspace: Path) -> None:
    mp = res.get("matlab_port")
    if not mp or not mp.get("generated"):
        return

    if mp.get("verified") is not False:
        err("MATLAB-LIED",
            "matlab_port.verified 不是 false。\n"
            "        本机没有 MATLAB/Octave，移植版**在生成时未被执行过**。\n"
            "        谎报 verified=true 违反这个 repo 的立身之本：一切结论必须被数值验证。\n"
            "        **未经执行的代码不是「验证过的代码」。**")

    scr = mp.get("self_check_script")
    if not scr:
        err("MATLAB-NOSELFCHECK",
            "生成了 MATLAB 移植但没有 self_check_script。\n"
            "        移植版必须附自检脚本（读已验证的 results.json、重算、逐项打印 PASS/FAIL），\n"
            "        让用户在自己的机器上一键自验。")
    else:
        p = workspace / scr if not Path(scr).is_absolute() else Path(scr)
        if not p.is_file() and not Path(scr).is_file():
            err("MATLAB-NOFILE", f"self_check_script 不存在: {scr}")


# ---------------------------------------------------------------- 可复现

def check_passthrough(spec: dict, res: dict) -> None:
    """★ `results.json` 必须**自足** —— Skill 3 不该去读 `model-spec.json`。

    这和「Skill 2 只读契约、不读散文」是同一条原则的下一环：

    > **如果 `results.json` 里的信息不够 Skill 3 做出 PPT，那是 `results.json` 的缺陷。**

    **实测（magnetic-brake，做 PPT 时才发现）**：第一页「问题设定」要写
    `a = 6 mm`、`σ = 5.96e7 S/m`、`a/L = 0.60` —— 而 `results.json` 里**根本没有参数**。
    于是 Skill 3 只有两条路：跑去读 `model-spec.json`（那「PPT 上每个数字都必须能追回
    `results.json`」这条铁律当场破功），或者**手打**那几个数（那就是谎的种子）。

    **两条都不行。所以透传。**
    """
    need = {
        "parameters": "PPT 的「问题设定」页要写 a = 6 mm、σ = 5.96e7 S/m —— "
                      "**这些数字也必须能被追溯**，不能靠 Skill 3 手打",
        "essence": "★ `essence.one_sentence` 是**定性分析页的核心** —— "
                   "「说不出物理本质 = 不知道该画什么图」，对 PPT 同样成立",
        "assumptions": "假设台账（含 RISKY 分级）= **理论模型页 + 模型边界页**的骨架。"
                       "藏起来的 RISKY 会被 Opponent 一击致命",
    }
    for field, why in need.items():
        if not res.get(field):
            err("PASSTHROUGH-MISSING",
                f"results.json 里没有 `{field}` —— 必须从 model-spec.json **原样透传**过来。\n"
                f"        为什么：{why}\n"
                f"        **`results.json` 是 Skill 3 的唯一输入。它不自足，"
                f"下游就只能去别处找补，或者手打。两条都是谎的种子。**")
            continue

        # 透传就得是**原样**的 —— 不许在路上悄悄改
        if field == "parameters":
            a = {p.get("symbol") for p in spec.get("parameters", [])}
            b = {p.get("symbol") for p in res["parameters"]}
            if a != b:
                err("PASSTHROUGH-DRIFT",
                    f"results.json 的 parameters 和 model-spec 对不上：\n"
                    f"        少了 {sorted(a - b) or '—'}；多了 {sorted(b - a) or '—'}\n"
                    f"        **透传就是原样搬过来。改了，就是给下游埋一个查不出来的错。**")
        elif field == "assumptions":
            a = {x.get("id") for x in spec.get("assumptions", [])}
            b = {x.get("id") for x in res["assumptions"]}
            if a != b:
                err("PASSTHROUGH-DRIFT",
                    f"results.json 的 assumptions 和 model-spec 对不上："
                    f"少了 {sorted(a - b) or '—'}；多了 {sorted(b - a) or '—'}")
        elif field == "essence":
            if norm(spec.get("essence", {}).get("one_sentence", "")) \
                    != norm(res["essence"].get("one_sentence", "")):
                err("PASSTHROUGH-DRIFT",
                    f"essence.one_sentence 和 model-spec **对不上**：\n"
                    f"        契约：{spec.get('essence', {}).get('one_sentence', '')[:70]}\n"
                    f"        实际：{res['essence'].get('one_sentence', '')[:70]}\n"
                    f"        **这句话是 Skill 1 的结论，不是你的。逐字搬。**")


def check_reproduce(res: dict) -> None:
    rp = res.get("reproduce") or {}
    if not rp.get("command"):
        err("NO-REPRO", "没有 reproduce.command —— **一条命令重现全部数字和图，做不到 = 结果不可信**")


def check_acceptance_sync(res: dict, acc: str | None) -> None:
    """results.json 里的每条断言，acceptance.md 里都要有。"""
    if acc is None:
        return
    for a in res.get("assertions", []):
        aid = a.get("id", "")
        if aid and aid not in acc:
            warn("ACC-DESYNC", f"断言 {aid} 在 results.json 里有，但 acceptance.md 里找不到 —— "
                               f"**断言必须先写进 acceptance.md，再去算**。反过来就是数值结果的复述。")


# ---------------------------------------------------------------- 主流程

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    workspace = Path(sys.argv[1])
    if not workspace.is_dir():
        print(f"工作区不存在: {workspace}", file=sys.stderr)
        return 2

    spec, res, acc, spec_path = load(workspace)

    check_quotes(spec, res)
    check_passthrough(spec, res)
    check_tasks_and_validation(spec, res)
    check_coverage(spec, res, workspace)
    check_assertions(res)
    check_gates(res)
    check_stamps(res, workspace)
    check_status(res)
    check_matlab(res, workspace)
    check_reproduce(res)
    check_acceptance_sync(res, acc)

    print(f"检查工作区: {workspace}")
    print(f"对拍的契约: handoff/{spec_path.name}"
          f"   (results.json 声明 model_spec_version = {res.get('model_spec_version') or '未声明'})")
    print(f"status: {res.get('status')}   "
          f"断言 {len(res.get('assertions', []))} 条   "
          f"图 {len(res.get('figures', []))} 张   "
          f"RISKY 检查 {len(res.get('risky_checks', []))} 条\n")

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
        print("  注意：这个脚本**不判断你的数值对不对**——它只判断你有没有真的跑完")
        print("  你答应要跑的东西，以及你有没有真的读过契约。")
        print("  物理正确性归 iypt-physics-review 管；美观度归 iypt-design-review 管。")
    elif not ERRORS:
        print("✓ 无 ERROR。")

    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
