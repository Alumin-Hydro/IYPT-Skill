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
from pathlib import Path

ERRORS: list[str] = []
WARNINGS: list[str] = []


def err(code: str, msg: str) -> None:
    ERRORS.append(f"[{code}] {msg}")


def warn(code: str, msg: str) -> None:
    WARNINGS.append(f"[{code}] {msg}")


# ---------------------------------------------------------------- 载入

def load(workspace: Path):
    analysis = workspace / "01-analysis.md"
    spec_path = workspace / "handoff" / "model-spec.json"

    if not analysis.is_file():
        print(f"找不到 {analysis}", file=sys.stderr)
        sys.exit(2)
    md = analysis.read_text(encoding="utf-8")

    spec = None
    if spec_path.is_file():
        try:
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            err("SPEC-PARSE", f"model-spec.json 不是合法 JSON: {e}")
    else:
        err("SPEC-MISSING", "handoff/model-spec.json 不存在——Skill 2 没有输入，流水线断了")

    return md, spec


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
    for c in spec.get("risky_assumption_checks", []):
        aid = c.get("assumption_id")
        if aid not in known:
            err("CHECK-ORPHAN", f"risky_assumption_checks 引用了不存在的假设 {aid}")
        if not c.get("pass_criterion"):
            err("CHECK-CRIT", f"{aid} 的验证任务没有 pass_criterion——Skill 2 不知道什么结果算通过")

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


def check_ids(md: str, spec: dict) -> None:
    """S-n / A-n：定义了就要被引用；台账要和 spec 对齐。"""
    defined_s = set(re.findall(r"\|\s*(S-\d+)\s*\|", md))
    defined_a = set(re.findall(r"###\s*(A-\d+)", md))

    if not defined_s:
        err("NO-SPEC-SHEET", "正文里没有设定书条目（S-n）——IYPT 题目是欠定的，"
                             "补全题目设定是 Stage 1 的核心产出，不能跳过")
    if not defined_a:
        err("NO-LEDGER", "正文里没有假设台账条目（A-n）——没有一条简化被记账，"
                         "这在物理上是不可能的：你一定用了假设，只是没说出口")

    # 定义了但正文从未引用（首次定义之外没再出现）
    for sid in sorted(defined_s | defined_a):
        if len(re.findall(rf"\b{re.escape(sid)}\b", md)) < 2:
            warn("ID-UNUSED", f"{sid} 定义之后再也没被引用过——它真的在推导里起作用吗？")

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
    has_number = re.compile(r"\d")
    # 排除掉解释性的段落（表头、模板说明、引用块）
    skip = re.compile(r"^\s*(>|\||#|-{3,})?\s*(硬规则|口头忽略|未纳入的机制|一端可忽略)")

    for i, line in enumerate(md.splitlines(), 1):
        if not kw.search(line):
            continue
        if skip.search(line):
            continue
        if not has_number.search(line):
            warn("SILENT-NEGLECT", f"L{i}: 提到\"忽略\"但这一行没有任何数字 —— "
                                   f"每个忽略都要给出「被略去项/主项」的数值比（审稿模式 P2）：\n"
                                   f"        {line.strip()[:90]}")


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
    for g in sorted(greek):
        if not any(g in s for s in table):
            warn("SYM-UNDECLARED", f"正文用了 \\{g} 但符号表里没有——"
                                    f"注意一符多义：ρ(密度/电阻率)、σ(电导率/表面张力)、μ(磁导率/黏度)")


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


# ---------------------------------------------------------------- 主流程

def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2

    workspace = Path(sys.argv[1])
    if not workspace.is_dir():
        print(f"工作区不存在: {workspace}", file=sys.stderr)
        return 2

    md, spec = load(workspace)

    check_contract(spec or {})
    check_equations(md)
    check_ids(md, spec or {})
    check_silent_neglect(md)
    check_symbols(md, spec or {})
    check_residue(md)
    check_sections(md)

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
