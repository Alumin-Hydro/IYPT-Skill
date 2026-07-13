#!/usr/bin/env python3
"""deck.json → slides.html（自包含）→ 每页 PNG + PDF + script.md。

## 这个文件的**唯一**设计目标：让数字漂移在结构上不可能发生

`CLAUDE.md`：**「PPT 上引用的每个数字都必须能追回去。」**

弱的做法是「写完之后去核对一遍」。**强的做法是根本不许你手打。**

    ✗  "text": "有限长磁体给出的指数是 3.44"
    ✓  "text": "有限长磁体给出的指数是 {{assertions.AS-8.measured|.2f}}"

第二种写法里，**3.44 这个数字在 deck.json 里根本不存在** —— 它在渲染时从
`results.json` 取出来代入。于是：

  · 仿真重跑、数字变了 -> 幻灯片**自动跟着变**（而不是变成一个谎）
  · 想在 PPT 上写一个 results.json 里没有的数 -> **你做不到**
  · `check_slides.py` 的 `NUM-UNCITED`：正文里出现任何**带小数点 / 百分号 /
    科学计数**的数字而没被 `{{}}` 包住 -> **ERROR**

> **文档里的劝诫会被忽略；机械检查不会。而「根本没有那个入口」比机械检查还硬。**

散文（图注、断言原文）用另一副药 —— 和 `check_sim.py` 的 `quoted_expectation`
是同一副：**逐字抄写 + 机械校验它确实是原文的子串**。见 `quote` 块。

## 为什么图注默认**不填**

`figure: {"figure_id": "F-2"}` —— 不写 caption，渲染时**整段**取 `results.json`
的 `figures[F-2].caption`。**没有转述，就没有走样。**

（`figures[].caption` 写的是「这张图**证明了什么**」，不是「展示了什么」——
Skill 2 已经把最难的那句话写好了。直接用。）

真要缩写，可以写 `"caption": "…"`，但 `check_slides.py` 会校验它是原文的**逐字子串**。
**你只能删字，不能改字。**

## 数学

用 matplotlib 的 mathtext 在**构建时**渲成 SVG（字形转成路径 -> 无字体依赖），
再以 data URI 内嵌。三个好处：

  · **和图是同一个渲染引擎** —— 幻灯片上的 σ 和图上的 σ 长得一模一样
  · 无 CDN、无 JS、单文件自包含（沿用 Skill 2 的交互页的规矩）
  · PDF 导出、PNG 截图里都是矢量

## 为什么**不**把交互页嵌进幻灯片

能做（`<iframe srcdoc>`），但**动画会让 PNG 截图不可复现** —— 每次截到的帧都不一样。
**可复现性是这个 repo 的立身之本，不拿它换花哨。**

幻灯片上放**静止帧**（`figures[].path`，Skill 2 现在保证每张图都有），
并标一行 `▶ live: <路径>`，讲的人想演示就自己打开。
"""
from __future__ import annotations

import base64
import html
import io
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# ---------------------------------------------------------------- 溯源指针

_PTR = re.compile(r"\{\{\s*(.+?)\s*\}\}", re.S)

#: 列表元素的「主键」候选。results.json 里 id 字段的名字不统一，全试一遍。
_KEYS = ("id", "symbol", "assumption_id", "task_id", "field")


class ResolveError(KeyError):
    pass


def parse(inner: str) -> tuple[str, str, str | None]:
    """`{{...}}` 里面那一坨，解析成 (模式, a, b)。

    两种模式：

      **取值**  `{{assertions.AS-8.measured|.2f}}`  ->  ("value", ptr, fmt)
          数字从 results.json **取**出来。deck.json 里根本没有那个数字。

      **行内引文**  `{{10% @ assertions.AS-33.expect}}`  ->  ("quote", literal, src)
          原样渲染 `10%`，但**机械校验它确实是 `AS-33.expect` 原文的子串**。

    ## 为什么必须有第二种

    契约里有一类数字**只以散文形式存在**，没有专门的字段可指：

        阈值      「若 |k-4| > **0.3**，则 P5 降级」  （在 pass_criterion 这句话里）
        判据      「管壁误差必须 > **50%**」          （在 assertion 的 expect 里）
        精度要求  「v_t 要 **10%** 精度」             （在 expected_shape 里）

    只有「取值」一种模式的话，作者面对这些数字只有两条路：**手打**（那就是谎的种子），
    或者**把它们从文案里删掉**（那文案就废了）。

    > **一个逼着人绕过它的机制，最后一定会被绕过。**

    所以给它一条**合法的、但同样堵死了造假**的路：你可以写出那个数，
    但**必须指出它在契约的哪句话里**，而且**必须一字不差**。

    这就是 `check_sim.py` 的 `quoted_expectation` —— 只是做成了行内的。
    **它无法被滥用来编造一个数字**：编的数字不可能是原文的子串。
    """
    if "@" in inner:
        lit, src = inner.rsplit("@", 1)
        return "quote", lit.strip(), src.strip()
    if "|" in inner:
        ptr, fmt = inner.split("|", 1)
        return "value", ptr.strip(), fmt.strip()
    return "value", inner.strip(), None


def resolve(ptr: str, results: dict):
    """把 `assertions.AS-8.measured` 这样的指针解析成 results.json 里的值。

    遇到 list 就按主键找（id / symbol / assumption_id / task_id）。
    解析不到 -> ResolveError。**check_slides.py 的 SRC-DANGLING 就是它。**
    """
    cur = results
    for part in ptr.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                raise ResolveError(f"{ptr}  （`{part}` 不在 {sorted(cur)[:8]}… 里）")
            cur = cur[part]
        elif isinstance(cur, list):
            hit = None
            for el in cur:
                if isinstance(el, dict) and any(el.get(k) == part for k in _KEYS):
                    hit = el
                    break
            if hit is None:
                have = [next((e[k] for k in _KEYS if k in e), "?")
                        for e in cur if isinstance(e, dict)]
                raise ResolveError(f"{ptr}  （列表里没有 `{part}`；有的是 {have[:10]}）")
            cur = hit
        else:
            raise ResolveError(f"{ptr}  （`{part}` 之前已经到底了，拿到的是 {type(cur).__name__}）")
    return cur


_SCALE = re.compile(r"^([0-9.eE+-]+)\*(.*)$")


def _fmt(val, spec: str | None) -> str:
    """格式串 = Python 的 format spec，外加两条**缩放**语法。

    为什么需要缩放：`results.json` 里的一切都是 **SI**（a = 0.006 m，
    relative_deviation = 0.827333）。而 PPT 上要写的是 **6 mm** 和 **+82.7%**。

    如果不给缩放，作者就只有一条路：**手打 6 和 82.7** —— 那正是我们要堵死的那条路。
    **一个逼着人手打数字的溯源机制，等于没有溯源机制。**

        {{parameters.a.value|1e3*.0f}}            -> 6          （m -> mm）
        {{targets.v_t.value_numeric|100*.2f}}     -> 5.01       （m/s -> cm/s）
        {{targets.v_t.relative_deviation|%+.1f}}  -> +82.7%     （分数 -> 百分数）
    """
    if spec is None or spec == "":
        return str(val)
    # `%+.1f`：乘 100、按 `+.1f` 格式化、补一个 %
    if spec.startswith("%"):
        return format(float(val) * 100.0, spec[1:]) + "%"
    # `1e3*.0f`：先乘 1e3，再按 `.0f` 格式化
    m = _SCALE.match(spec)
    if m:
        return format(float(val) * float(m.group(1)), m.group(2))
    return format(val, spec)


def norm_q(s: str) -> str:
    """比对引文用：折叠空白、抹掉 markdown 强调、统一负号与破折号。

    **内容必须一字不差；排版不算内容。**
    （契约里写的是 `|k-4| > 0.3`，幻灯片上想写 `|k−4| > 0.3`（真正的减号）——
    那不是走样。而把 `0.3` 写成 `0.5` 才是。）
    """
    s = re.sub(r"\*\*|__|[`*]", "", str(s))
    s = s.translate(str.maketrans("−–—～≈", "-----"))
    return re.sub(r"\s+", "", s)


def subst(text: str, results: dict, *, where: str = "") -> str:
    """把 `{{...}}` 换掉。取值模式从 results.json 取；引文模式原样渲染但**校验**。

    **这就是「数字不许手打」的实现。** deck.json 里根本没有那个数字 ——
    要么它在 results.json 里（取值），要么它是契约原文的逐字子串（引文）。
    **没有第三条路。**
    """
    def one(m: re.Match) -> str:
        mode, a, b = parse(m.group(1))

        if mode == "quote":
            lit, src = a, b
            try:
                real = resolve(src, results)
            except ResolveError as e:
                raise ResolveError(f"{where}：行内引文的出处解析不到 —— {e}") from None
            if norm_q(lit) not in norm_q(real):
                raise ValueError(
                    f"{where}：行内引文 `{lit}` **不是** `{src}` 原文的逐字子串。\n"
                    f"  原文：{str(real)[:120]}\n"
                    f"  **一转述就走样，而走样的方向永远是对自己有利的。**")
            return lit

        ptr, spec = a, b
        try:
            val = resolve(ptr, results)
        except ResolveError as e:
            raise ResolveError(f"{where}：{e}") from None
        try:
            return _fmt(val, spec)
        except (TypeError, ValueError) as e:
            raise ValueError(
                f"{where}：`{ptr}` 的值是 {val!r}（{type(val).__name__}），"
                f"套不上格式 `{spec}` —— {e}") from None

    return _PTR.sub(one, text)


def refs(text: str) -> list[tuple[str, str, str | None]]:
    """文本里所有的 `{{...}}`，解析好（给 check_slides.py 用）。"""
    return [parse(m.group(1)) for m in _PTR.finditer(text)]


def strip_pointers(text: str) -> str:
    """把 `{{...}}` 整段挖掉 —— 剩下的就是**作者手打**的部分。

    `check_slides.py` 的 `NUM-UNCITED` 在这上面找带小数点/百分号/科学计数的数字。
    """
    return _PTR.sub(" ", text)


# ---------------------------------------------------------------- 数学 → SVG

_EQ_CACHE: dict[str, tuple[str, float, float]] = {}

#: 公式的字号（pt）。**在这里定死，而不是靠 CSS 缩放。**
#  投影到会议厅大屏：正文 26px，展示公式该比正文大一圈 —— 32pt ≈ 43 CSS px。
EQ_FONT_PT = 32.0

#: pt → CSS px 的**真实**换算（CSS 定义 1pt = 4/3 px）。不是魔法数字。
PT_TO_PX = 4.0 / 3.0

_SVG_SIZE = re.compile(r'width="([\d.]+)pt"\s+height="([\d.]+)pt"')


def eq_svg(tex: str, *, color: str = "#0b0b0b") -> tuple[str, float, float]:
    """LaTeX → (data URI, 宽 px, 高 px)。字形转成路径，**无字体依赖**。

    ★ **返回内禀尺寸，而不是让 CSS 定一个固定高度。**

    为什么这很要紧：如果 CSS 写死 `height: 62px`，那么一个带 `\\frac` 的公式（本身就高）
    会被压到和一个单行公式一样高 —— **于是它里面的字比旁边那个公式小一圈**。
    实测：(12) 和 (10) 摆在一起，(10) 的字明显小，像是缩略图。

    正确做法：所有公式**在同一个字号下渲染**（matplotlib 的 12pt @ 200dpi），
    然后按**同一个倍数**放大。高的公式就该占更多高度 —— 那才是排版的本意。
    """
    if tex in _EQ_CACHE:
        return _EQ_CACHE[tex]
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import mathtext
    from matplotlib.font_manager import FontProperties
    buf = io.BytesIO()
    body = tex.strip()
    if not (body.startswith("$") and body.endswith("$")):
        body = f"${body}$"
    try:
        mathtext.math_to_image(body, buf, dpi=200, format="svg", color=color,
                               prop=FontProperties(size=EQ_FONT_PT))
    except Exception as e:                                   # mathtext 语法错
        raise ValueError(
            f"公式渲染失败：{tex}\n  {type(e).__name__}: {e}\n"
            f"  mathtext 只支持 LaTeX 的一个子集 —— 常见的坑：\\text{{}}、\\begin{{}}、"
            f"中文。用 \\mathrm{{}} 代替 \\text{{}}；中文写在 text 块里，不要写进公式。"
        ) from None
    raw = buf.getvalue()
    m = _SVG_SIZE.search(raw.decode("utf-8", "replace")[:600])
    w, h = (float(m.group(1)), float(m.group(2))) if m else (400.0, 60.0)
    b64 = base64.b64encode(raw).decode("ascii")
    out = (f"data:image/svg+xml;base64,{b64}", w * PT_TO_PX, h * PT_TO_PX)
    _EQ_CACHE[tex] = out
    return out


# ---------------------------------------------------------------- 图 → data URI

_IMG_CACHE: dict[str, str] = {}


def img_uri(path: Path) -> str:
    p = str(path)
    if p in _IMG_CACHE:
        return _IMG_CACHE[p]
    if not path.is_file():
        raise FileNotFoundError(f"图不存在：{path}")
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    mime = "image/svg+xml" if path.suffix == ".svg" else "image/png"
    out = f"data:{mime};base64,{b64}"
    _IMG_CACHE[p] = out
    return out


# ---------------------------------------------------------------- 行内标记

_MD = [
    (re.compile(r"\*\*(.+?)\*\*"), r"<b>\1</b>"),
    (re.compile(r"`(.+?)`"), r"<code>\1</code>"),
    (re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])"), r"<i>\1</i>"),
]


def inline(text: str) -> str:
    """极小的行内标记：**粗**、`码`、*斜*。转义在前，标记在后。"""
    s = html.escape(text)
    for pat, rep in _MD:
        s = pat.sub(rep, s)
    return s


# ---------------------------------------------------------------- 块渲染

def _block(b: dict, R: dict, ws: Path, where: str) -> str:
    k = b.get("kind", "bullet")

    if k in ("bullet", "text", "note", "lead"):
        t = inline(subst(b["text"], R, where=where))
        if k == "bullet":
            return f"<li>{t}</li>"
        return f'<p class="{k}">{t}</p>'

    if k == "quote":
        # 逐字引文。**check_slides.py 校验 text 是 src 所指原文的子串。**
        t = inline(subst(b["text"], R, where=where))
        src = b.get("src", "")
        return (f'<blockquote>{t}'
                f'<span class="src">{html.escape(src)}</span></blockquote>')

    if k == "eq":
        uri, w, h = eq_svg(b["tex"])
        cap = b.get("label", "")
        lab = f'<span class="eqlab">{inline(cap)}</span>' if cap else ""
        # 尺寸由 SVG 的内禀大小定 —— 所有公式**同一个字号**（见 eq_svg 的注释）
        return (f'<div class="eqrow"><img class="eq" src="{uri}" alt="equation" '
                f'style="width:{w:.0f}px;height:{h:.0f}px">{lab}</div>')

    if k == "kv":
        return (f'<div class="kv"><span class="k">{inline(subst(b["k"], R, where=where))}</span>'
                f'<span class="v">{inline(subst(b["v"], R, where=where))}</span></div>')

    if k == "table":
        head = "".join(f"<th>{inline(subst(h, R, where=where))}</th>" for h in b["head"])
        rows = "".join(
            "<tr>" + "".join(f"<td>{inline(subst(str(c), R, where=where))}</td>" for c in r) + "</tr>"
            for r in b["rows"])
        return f"<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>"

    if k == "disclosure":
        # ★ 仿真披露。**文字是写死的，作者改不了。**
        #
        #   和 figkit 的 SIMULATION 戳同一个道理：**凡是可以被措辞软化的底线，
        #   迟早会被措辞软化。** 一个被逼到墙角又必须交差的 agent，会把
        #   「以下全部来自仿真，不是实验」写成「我们的模型与预期高度一致」——
        #   一个字都没撒谎，而听众会以为他做了实验。
        #
        #   所以这个块**不接受任何参数**。你只能决定它出现在哪一页，不能决定它说什么。
        #   （pipeline.md §7 的底线。check_slides.py 的 DISCLOSURE-MISSING 查它在不在。）
        return (
            '<div class="disclosure">'
            '<b>以下全部结果来自数值仿真，不是实验数据。</b>'
            '实验方案见附录 —— <b>尚未执行</b>。'
            '<span class="why">仿真验证「方程解对了」，实验验证「方程写对了」。'
            '<b>只有实验能证伪模型。</b></span>'
            '</div>')

    if k == "verdict":
        # 一条断言的「期望 vs 实测 vs 判定」—— 直接从 results.json 长出来
        aid = b["assertion_id"]
        a = resolve(f"assertions.{aid}", R)
        v = a.get("verdict", "?")
        cls = {"PASS": "pass", "PRESCRIBED": "warn"}.get(v, "fail")
        return (f'<div class="verdict {cls}"><span class="aid">{html.escape(aid)}</span>'
                f'<span class="exp">{inline(str(a.get("expect", "")))}</span>'
                f'<span class="meas">{inline(str(a.get("measured", "")))}</span>'
                f'<span class="tag">{html.escape(v)}</span></div>')

    raise ValueError(f"{where}：不认识的 block kind `{k}`")


def _blocks(bs: list[dict], R: dict, ws: Path, where: str) -> str:
    """连续的 bullet 自动包进 <ul>。"""
    out, buf = [], []
    for b in bs:
        if b.get("kind", "bullet") == "bullet":
            buf.append(_block(b, R, ws, where))
        else:
            if buf:
                out.append("<ul>" + "".join(buf) + "</ul>")
                buf = []
            out.append(_block(b, R, ws, where))
    if buf:
        out.append("<ul>" + "".join(buf) + "</ul>")
    return "".join(out)


# ---------------------------------------------------------------- 图

def _figure(f: dict, R: dict, ws: Path, where: str) -> str:
    fid = f["figure_id"]
    meta = resolve(f"figures.{fid}", R)          # 不存在 -> SRC-DANGLING

    png = ws / meta["path"]
    uri = img_uri(png)

    # **默认整段用 results.json 的 caption** —— 没有转述，就没有走样。
    cap = f.get("caption") or meta.get("caption", "")
    cap_html = inline(subst(cap, R, where=where))

    live = ""
    if meta.get("path_interactive"):
        live = (f'<div class="live">▶ live: '
                f'<code>{html.escape(meta["path_interactive"])}</code></div>')

    # SIMULATION 角标。**每一张图都有。这是底线，不是风格。**（pipeline.md §7）
    #
    #   ★ 它在**图注里**，不是浮在图上。
    #
    #   浮在图上试过两版，两版都撞了：
    #     · 锚在整栏容器上 -> 图按比例收缩后，角标飘到图的右**外**侧，落在一片白底上
    #       （看起来像给这一页盖的戳，不是给这张图盖的戳）
    #     · 锚在图上       -> **正好压住图自己的标题**（D1：标注压住内容）
    #
    #   而图的 PNG 里**本来就有 figkit 烤进去的 SIMULATION 戳**（那个是给「图被单独
    #   截出去」准备的）。幻灯片这一层的角标只需要保证「读者看这一页时看得见它」——
    #   **图注是读者一定会看的地方，而且那里永远不会压住任何东西。**
    return (f'<figure class="fig">'
            f'<div class="figwrap"><span class="figbox">'
            f'<img src="{uri}" alt="{html.escape(fid)}"></span></div>'
            f'<figcaption><span class="simbadge">SIMULATION</span>'
            f'<span class="figid">{html.escape(fid)}</span>{cap_html}</figcaption>'
            f'{live}</figure>')


# ---------------------------------------------------------------- 任务打勾表

def _checklist(R: dict) -> str:
    """★ 真实 IYPT 报告的最后一页，就是这张表。直接从 tasks_answered[] 长出来。"""
    rows = []
    for t in R.get("tasks_answered", []):
        ok = t.get("answered") is True
        mark = "✓" if ok else "✗"
        figs = "、".join(t.get("by_figures", []))
        rows.append(
            f'<div class="task {"done" if ok else "open"}">'
            f'<span class="mark">{mark}</span>'
            f'<span class="tid">{html.escape(t["task_id"])}</span>'
            f'<span class="stm">{inline(t.get("quoted_statement", ""))}</span>'
            f'<span class="by">{html.escape(figs)}</span></div>')
    return f'<div class="checklist">{"".join(rows)}</div>'


# ---------------------------------------------------------------- 幻灯片

SECTIONS = {
    "problem":  "问题",
    "picture":  "定性图像",
    "theory":   "理论模型",
    "numerics": "数值探究",
    "boundary": "模型边界",
    "summary":  "总结",
    "appendix": "附录",
}


def _slide(s: dict, R: dict, ws: Path, n: int, total: int) -> str:
    sid = s["id"]
    where = f"slides[{sid}]"
    lay = s.get("layout", "bullets")
    sec = s.get("section", "")

    head = ""
    if lay != "title":
        take = inline(subst(s.get("takeaway", ""), R, where=where))
        eyebrow = SECTIONS.get(sec, sec)
        head = (f'<header><span class="eyebrow">{html.escape(eyebrow)}</span>'
                f'<h2>{take}</h2></header>')

    body = _blocks(s.get("body", []), R, ws, where) if s.get("body") else ""
    fig = _figure(s["figure"], R, ws, where) if s.get("figure") else ""
    chk = _checklist(R) if lay == "checklist" else ""

    if lay == "title":
        t = inline(subst(s.get("takeaway", ""), R, where=where))
        inner = f'<div class="titlebox"><h1>{t}</h1>{body}</div>'
    elif lay == "section":
        t = inline(subst(s.get("takeaway", ""), R, where=where))
        inner = f'<div class="sectionbox"><h1>{t}</h1>{body}</div>'
    elif lay == "figure-full":
        inner = f'{head}<div class="body full">{fig}{body}</div>'
    elif lay in ("figure-left", "figure-right"):
        cols = (fig, f'<div class="txt">{body}</div>')
        if lay == "figure-right":
            cols = cols[::-1]
        inner = f'{head}<div class="body split">{cols[0]}{cols[1]}</div>'
    elif lay == "checklist":
        inner = f'{head}<div class="body">{chk}{body}</div>'
    else:
        inner = f'{head}<div class="body">{body}</div>'

    dur = s.get("duration_s")
    foot = (f'<footer><span class="sec">{html.escape(SECTIONS.get(sec, sec))}</span>'
            f'<span class="pg">{n} / {total}</span></footer>')

    return (f'<section class="slide lay-{lay} sec-{sec}" id="{html.escape(sid)}" '
            f'data-duration="{dur if dur is not None else ""}">'
            f'{inner}{foot}</section>')


# ---------------------------------------------------------------- 全页

def render(deck: dict, R: dict, ws: Path, css: str) -> str:
    slides = deck["slides"]
    total = len(slides)
    body = "\n".join(_slide(s, R, ws, i + 1, total) for i, s in enumerate(slides))

    # `?only=<id>` -> 只显示那一页。**于是截图截出来的正好是一页，不用裁剪。**
    # `?print=1`   -> 打印模式（PDF 导出走这个）。
    js = """
    (function () {
      var q = new URLSearchParams(location.search);
      var only = q.get('only');
      if (only) {
        document.body.classList.add('solo');
        document.querySelectorAll('.slide').forEach(function (s) {
          if (s.id !== only) s.remove();
        });
      }
      if (q.get('print')) document.body.classList.add('printing');
    })();
    """
    title = html.escape(deck.get("title", deck.get("problem_slug", "IYPT")))
    return (
        "<!doctype html>\n"
        '<html lang="zh"><head><meta charset="utf-8">\n'
        f"<title>{title}</title>\n"
        f"<style>\n{css}\n</style>\n"
        "</head><body>\n"
        f"{body}\n"
        f"<script>{js}</script>\n"
        "</body></html>\n"
    )


def script_md(deck: dict, R: dict) -> str:
    """讲稿。`notes` 里的 `{{}}` 一样会被代入 —— **讲的人念出来的数字也必须能追回去。**"""
    out = [f"# 讲稿 · {deck.get('title', deck.get('problem_slug', ''))}", ""]
    budget = deck.get("duration_budget_s", 720)
    main = [s for s in deck["slides"] if s.get("section") != "appendix"]
    used = sum(s.get("duration_s") or 0 for s in main)
    out += [f"**时间预算**：{used} s / {budget} s（主线 {len(main)} 页；"
            f"附录 {len(deck['slides']) - len(main)} 页不计）", ""]
    for i, s in enumerate(deck["slides"], 1):
        sid, dur = s["id"], s.get("duration_s")
        take = subst(s.get("takeaway", ""), R, where=f"slides[{sid}]")
        out += [f"## {i}. {sid} · {take}",
                f"*{SECTIONS.get(s.get('section',''), '')}* · {dur} s" if dur else "", ""]
        if s.get("notes"):
            out += [subst(s["notes"], R, where=f"slides[{sid}].notes"), ""]
    return "\n".join(out)
