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
        pool[f"risky_check:{c.get('assumption_id')}"] = \
            (c.get("pass_criterion", "") + " " + c.get("task", ""))
    for t in spec.get("targets", []):
        pool[f"target:{t.get('symbol')}"] = \
            (t.get("analytical_prediction", "") + " " + (t.get("scaling_law") or ""))
    for e in spec.get("equations", []):
        pool[f"equation_limit:{e.get('id')}"] = \
            ((e.get("numerical_notes") or "") + " " + (e.get("suggested_method") or ""))

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

    # Gate 0 的配方也要逐字
    for g in res.get("gates", []):
        if g.get("id") != "gate-0-limit":
            continue
        q = norm(g.get("recipe", ""))
        if not q:
            err("GATE0-NORECIPE", "Gate 0 没有 recipe —— 必须逐字抄写 equations[].numerical_notes "
                                  "里的极限对拍配方。抄不上说明你没读它。")
        elif q not in all_spec_text:
            warn("GATE0-RECIPE-DRIFT",
                 "Gate 0 的 recipe 不是 model-spec 的逐字子串。\n"
                 "        如果你是**有意**改正了一个错误的配方，那应当在 spec_defects[] 里"
                 "登记这个 SPEC-DEFECT，而不是悄悄换掉它。")


# ---------------------------------------------------------------- 覆盖度

def check_coverage(spec: dict, res: dict, workspace: Path) -> None:
    """契约里答应要跑的，一件都不许少。"""

    # --- 图
    spec_figs = {f.get("id"): f for f in spec.get("figures", [])}
    res_figs = {f.get("id"): f for f in res.get("figures", [])}

    for fid in spec_figs:
        if fid not in res_figs:
            err("FIG-MISSING", f"model-spec 要求画 {fid}，但 results.json 里没有它")
    for fid in res_figs:
        if fid not in spec_figs:
            warn("FIG-EXTRA", f"results.json 里的 {fid} 不在 model-spec 的 figures[] 里 —— "
                              f"没有 expected_shape 的图没有验收标准，它只是装饰")

    for fid, f in res_figs.items():
        if not f.get("assertion_ids"):
            err("FIG-NOASSERT", f"{fid} 没有对应的断言 —— **一张没有验收标准的图就是装饰**")
        if not f.get("simulation_stamped"):
            err("FIG-NOSTAMP", f"{fid} 的 simulation_stamped 不是 true")

        p = f.get("path")
        if p:
            fp = workspace / p if not Path(p).is_absolute() else Path(p)
            if not fp.is_file():
                # results.json 里的路径可能相对工作区，也可能相对 repo 根
                alt = Path(p)
                if not alt.is_file():
                    err("FIG-NOFILE", f"{fid} 的产出文件不存在: {p}")

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

def check_gates(res: dict) -> None:
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
