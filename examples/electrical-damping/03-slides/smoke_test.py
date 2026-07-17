#!/usr/bin/env python3
"""注入式冒烟测试：往 deck.json 里**故意注入错误**，看 check_slides.py 抓不抓得到。

    python 03-slides/smoke_test.py

## 为什么必须做这个

**你怎么知道你那些门不是摆设？**

一道从来没有抓到过任何东西的检查，和一道**不存在**的检查，行为上完全一样 ——
而你会以为你有它。

> **实测（Skill 2）**：4 个注入里有 **2 个**是靠冒烟测试才发现门漏了的
> ——「结构型 must_not」和「扫描端点收敛检查」两条，都是设计时没想到、
> **被注入的 bug 打出来的**。
>
> **冒烟测试不是走过场，它是这套检查唯一可信的自证。**

## 两个必要条件

1. **每个注入都必须被抓到。** 漏一个 → 那道门是摆设，**重新设计**。
2. **基线（无注入）必须干净。** **会误报的门比没有门更糟** ——
   一个总是响的警报，等于没有警报，而且它会训练人无视所有警报。
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

HERE = Path(__file__).resolve().parent          # 03-slides/
WS = HERE.parent                                # 工作区
REPO = WS.parent.parent                         # repo 根（examples/<slug>/ 往上两层）
CHECK = REPO / "skills" / "iypt-slides" / "scripts" / "check_slides.py"


# ---------------------------------------------------------------- 注入

def i_num_uncited(deck: dict) -> None:
    """① **手打一个数字**（最常见、也最致命的一种腐烂）。

    把一个好端端的指针换成字面值。它今天是对的 —— 而仿真下次重跑，它就是个谎。
    """
    for s in deck["slides"]:
        if s["id"] == "S-09":
            s["takeaway"] = "居中衰减的幂律指数是 -0.51，不是 -0.50"


def i_src_dangling(deck: dict) -> None:
    """② 指针指向一条**不存在**的字段。

    （这正是 results.json 里 `AS-V1` 那个真实 bug 的同类：**非空 ≠ 有效。**）
    本 deck 用 verdict 块承载断言、用 {{}} 指针承载散文数字 —— 破一个真实存在的
    指针（S-01 的 essence 指针）才测得到 SRC-DANGLING；破一个本来就不在的字符串是空注入。
    """
    for s in deck["slides"]:
        if s["id"] == "S-01":
            for b in s.get("body", []):
                if "{{essence.one_sentence}}" in b.get("text", ""):
                    b["text"] = b["text"].replace("essence.one_sentence", "essence.MISSING_FIELD")


def i_falsified_dropped(deck: dict) -> None:
    """③ ★★ **悄悄删掉「模型边界」那一节 —— 只报好消息。**

    这是全篇最重要的一个注入。删掉之后，这份 PPT **在语法上、排版上、
    溯源上全都是合法的** —— 每个数字都能追回 results.json，每张图都有戳。

    **它只是不再提那两条崩掉的假设了。**

    **而它读起来，和一份全部通过的 PPT 一模一样。**

    ★ 本 deck 把崩掉的 A-2 **既**写进 boundary（S-13）**又**写进 summary（S-14 的 status 注）——
    这是冗余的诚实。所以「只删 boundary」并不能把 A-2 藏掉（它还在 summary 里，门正确地不响）。
    要真正测到 FALSIFIED-DROPPED，注入必须把 A-2 从**所有** boundary/summary 里抹掉 ——
    删 boundary 节 + 洗掉 summary 里提到 A-2 的注。抹干净后 A-2 无处可寻，门必须响。
    """
    deck["slides"] = [s for s in deck["slides"] if s.get("section") != "boundary"]
    for s in deck["slides"]:
        if s.get("section") == "summary":
            for b in s.get("body", []):
                if "A-2" in b.get("text", ""):
                    b["text"] = "status = **{{status}}** —— 四条任务全部达成。"


def i_caption_drift(deck: dict) -> None:
    """④ 把图注**改一个词** —— 把一次证伪，改写成一次「基本一致」。"""
    for s in deck["slides"]:
        if s["id"] == "S-09":
            s["figure"]["caption"] = "v_t 与 a 的关系与理论预期基本一致"


def i_overset(deck: dict) -> None:
    """⑤ 往一页里塞一堆字 —— 内容会被 overflow:hidden **静默裁掉**。

    **静默**是关键：浏览器不报错，PNG 上看不出被裁了多少，
    人眼只会觉得"这页有点满"。**只有量包围盒才知道。**

    注意要打在一个**纯文字**页上（`bullets`），不能打在图页上 ——
    图页里的图会自己收缩腾地方，于是内容不会被裁，只会变密（那是 `TOO-DENSE` 的活）。
    **两道门抓的是两件事：TOO-DENSE 是「太挤」，OVERSET 是「有东西你根本看不见了」。**
    """
    for s in deck["slides"]:
        if s.get("layout") == "bullets" and s.get("section") != "appendix":
            s["body"] += [{"kind": "bullet", "text": "填充内容" * 22} for _ in range(6)]
            return


def i_fig_unknown(deck: dict) -> None:
    """⑥ 夹带一张**不在 results.json 里**的图（"好看的示意图"）。

    它没有 SIMULATION 戳，没有断言，没有出处。**它不是论据，是装饰。**
    """
    for s in deck["slides"]:
        if s["id"] == "S-09":
            s["figure"]["figure_id"] = "SCHEMATIC-1"


def i_fake_experiment(deck: dict) -> None:
    """⑦ 把「仿真」写成「**实验测得**」—— 一个词的事。

    在 Physics Fight 上，这是学术不端，不是笔误。
    """
    for s in deck["slides"]:
        if s["id"] == "S-08":
            s["body"].append({"kind": "text", "text": "实验测得的指数与模型完全吻合。"})


def i_disclosure_gone(deck: dict) -> None:
    """⑧ 删掉「这是仿真」的披露块。"""
    for s in deck["slides"]:
        s["body"] = [b for b in s.get("body", []) if b.get("kind") != "disclosure"]


def i_task_dropped(deck: dict) -> None:
    """⑨ 把总结页的打勾表换成一页普通的 bullet —— **任务不再逐条打勾。**"""
    for s in deck["slides"]:
        if s["layout"] == "checklist":
            s["layout"] = "bullets"
            s["body"] = [{"kind": "text", "text": "四条任务全部完成。"}]


CASES = [
    ("① 手打一个数字（3.44 / 4.00）",              i_num_uncited,       "NUM-UNCITED"),
    ("② 指针指向不存在的断言 AS-999",               i_src_dangling,      "SRC-DANGLING"),
    ("③ ★ 悄悄删掉「模型边界」一节（只报好消息）",   i_falsified_dropped, "FALSIFIED-DROPPED"),
    ("④ 把图注从「站不住」改成「基本一致」",         i_caption_drift,     "CAPTION-DRIFT"),
    ("⑤ 往一页里塞 300 字（内容被静默裁掉）",        i_overset,           "OVERSET"),
    ("⑥ 夹带一张不在 results.json 里的图",          i_fig_unknown,       "FIG-UNKNOWN"),
    ("⑦ 把「仿真」写成「实验测得」",                 i_fake_experiment,   "FAKE-EXPERIMENT"),
    ("⑧ 删掉「这是仿真」的披露块",                   i_disclosure_gone,   "DISCLOSURE-MISSING"),
    ("⑨ 总结页不再逐条打勾",                         i_task_dropped,      "NO-CHECKLIST"),
]


# ---------------------------------------------------------------- 跑

def run_check(ws: Path) -> str:
    r = subprocess.run([sys.executable, str(CHECK), str(ws)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return (r.stdout or "") + (r.stderr or "")


def rebuild_html(ws: Path, deck: dict) -> bool:
    """只重渲 `slides.html`（不出 PNG/PDF —— 那太慢，而审计只需要 HTML）。

    **必须重渲**：`OVERSET` / `TOO-DENSE` 这几道门是在**真实布局**上量的。
    不重渲，注入的 300 字根本进不了 HTML，那道门就永远"通过" ——
    **一道测不到自己目标的检查，比没有这道检查更糟，因为你会以为你有它。**
    """
    sys.path.insert(0, str(ws / "03-slides"))
    import deckkit as dk
    R = json.loads((ws / "02-sim" / "results.json").read_text(encoding="utf-8"))
    css = (ws / "03-slides" / "deck.css").read_text(encoding="utf-8")
    try:
        html = dk.render(deck, R, ws, css)
    except Exception:
        # 渲染直接崩了（如指针解析不到）。**保留基线 HTML**，让检查器自己去抓 ——
        # 我们要验的是「检查器抓不抓得到」，不是「程序会不会崩」。
        return False
    (ws / "03-slides" / "slides.html").write_text(html, encoding="utf-8")
    return True


def main() -> int:
    orig = json.loads((HERE / "deck.json").read_text(encoding="utf-8"))

    tmp = Path(tempfile.mkdtemp(prefix="iypt-slides-smoke-"))
    ws = tmp / WS.name
    shutil.copytree(WS, ws, ignore=shutil.ignore_patterns("__pycache__", "*.pdf"))
    deck_p = ws / "03-slides" / "deck.json"

    print("=" * 82)
    print("基线（无注入）—— **会误报的门比没有门更糟**")
    print("=" * 82)
    base = run_check(ws)
    base_ok = "机械检查全部通过" in base
    print(f"  {'✓ 不误报' if base_ok else '✗ 基线就报错了！'}")
    if not base_ok:
        print("\n".join(l for l in base.splitlines() if l.strip().startswith("["))[:1200])

    print()
    print("=" * 82)
    print("注入")
    print("=" * 82)
    results = []
    for name, fn, code in CASES:
        d = copy.deepcopy(orig)
        fn(d)
        deck_p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        built = rebuild_html(ws, d)          # ★ 必须重渲，否则渲染后的门测的是旧 HTML
        out = run_check(ws)
        caught = f"[{code}]" in out
        results.append((name, code, caught))
        note = "" if built else "   （渲染器直接拒绝了它 —— 但我们要的是**检查器**抓到）"
        print(f"  {'✓ 抓到' if caught else '✗ 漏了'}  {name}{note}")
        print(f"          期望的门：{code}")
        if caught:
            for line in out.splitlines():
                if f"[{code}]" in line:
                    print(f"          {line.strip()[:104]}")
                    break
        else:
            print("          !! **这道门是摆设，必须重新设计。**")
            hits = sorted({l.split("]")[0].strip("[ ") for l in out.splitlines()
                           if l.strip().startswith("[")})
            print(f"          实际报的是：{hits or '什么都没报'}")

    deck_p.write_text(json.dumps(orig, ensure_ascii=False, indent=2), encoding="utf-8")
    shutil.rmtree(tmp, ignore_errors=True)

    print()
    print("=" * 82)
    print("小结")
    print("=" * 82)
    print(f"  {'注入':<40} {'抓到了？':<10} 抓它的门")
    print("  " + "-" * 76)
    for name, code, ok in results:
        print(f"  {name:<40} {'✓ 是' if ok else '✗ 否':<10} {code}")
    print()

    all_ok = base_ok and all(ok for _, _, ok in results)
    if all_ok:
        print("  ✓ 九个注入全被抓到，且基线不误报。**这些门不是摆设。**")
        print()
        print("  但它们**仍然查不了**：哪个框压住了哪条曲线、takeaway 是不是一句人话、")
        print("  一页是不是塞了三个论点。**那些只能靠 Read 每一页 PNG，用眼睛看。**")
    else:
        print("  ✗ **有门是摆设。重新设计它，不要绕过它。**")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
