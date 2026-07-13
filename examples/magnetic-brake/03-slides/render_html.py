#!/usr/bin/env python3
"""HTML → 每页 PNG + PDF + **渲染后的机械审计**。headless Chrome / Edge 的封装。

## 为什么这个文件存在

`iypt-design-review` 的**铁律 0**：

> **你会脑补出一张比实际渲染出来的更好看的图。必须真的打开 PNG 用眼睛看。**
> **读代码猜排版 = 没审。**

而幻灯片和交互页面**都是 HTML**。**没有 PNG，它们就根本无法被审查。**

> 实测：`02-sim/interactive/*.html` 从来没有被设计审查过 —— **不是因为没人想审，
> 是因为在此之前根本渲染不出来。** 第一次渲出来看，立刻发现两个峰值标注叠印成一团。

## 为什么不用 python-pptx / Marp / LibreOffice

本机都没有，而且更要命的是：**python-pptx 直出的 .pptx 渲染不成 PNG**（没有 LibreOffice），
于是 Skill 3 ⇄ Skill 4 的设计审查回路**在那里就断了**。

Edge 和 Chrome 是 Windows 上**必然存在**的东西，而且 headless 模式同时给出：

  · 每页 PNG   —— Skill 4 打开来**看**
  · PDF        —— 直接上 Physics Fight 的赛场
  · **可执行的 JS** —— 于是「文字有没有溢出」可以**在浏览器里量**，而不是靠人眼

最后这一条是白捡的：**生成式幻灯片的头号 bug 是文字溢出/被裁**，而它恰恰是人最容易
看漏、机器最容易量准的东西。`audit()` 把它变成一道机械门。

## 用法

    # 库
    from render_html import shoot, to_pdf, audit
    shoot("slides.html", "png/S-01.png", query="only=S-01")
    to_pdf("slides.html", "deck.pdf")
    report = audit("slides.html")          # 溢出 / 字号 / 密度

    # CLI（Skill 4 用这个去渲交互页）
    python render_html.py 02-sim/interactive/F-5-eddy-currents.html --png /tmp/f5.png
    python render_html.py 03-slides/slides.html --audit
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import pathname2url

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

# ---------------------------------------------------------------- 找浏览器

#: 按优先级找。Edge 在 Windows 上是**保底**的 —— 它不可能不在。
_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


class BrowserNotFound(RuntimeError):
    pass


def find_browser() -> str:
    env = os.environ.get("IYPT_BROWSER")
    if env and Path(env).is_file():
        return env
    for c in _CANDIDATES:
        if Path(c).is_file():
            return c
    for name in ("chrome", "chromium", "msedge", "google-chrome"):
        p = shutil.which(name)
        if p:
            return p
    raise BrowserNotFound(
        "找不到 Chrome / Edge。\n"
        "  幻灯片渲染不出 PNG，**Skill 4 就没法「打开 PNG 用眼睛看」** —— 设计审查回路断掉。\n"
        "  设 IYPT_BROWSER=<浏览器可执行文件的路径> 指定一个。"
    )


def _url(path: Path, query: str = "") -> str:
    u = "file:" + pathname2url(str(path.resolve()))
    return f"{u}?{query}" if query else u


def _run(args: list[str], timeout: int = 90) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout)


def _base_flags(profile: Path) -> list[str]:
    return [
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        "--hide-scrollbars",              # 滚动条会出现在截图里
        "--force-device-scale-factor=1",
        "--allow-file-access-from-files",
        "--disable-extensions",
        f"--user-data-dir={profile}",
    ]


# ---------------------------------------------------------------- 截图 / PDF

#: 16:9，1600x900。投影和 PPT 的原生比例。
W, H = 1600, 900


def shoot(html: str | Path, png: str | Path, *, query: str = "",
          width: int = W, height: int = H, wait_ms: int = 1200) -> Path:
    """把 HTML 渲染成一张 PNG。

    query: URL 查询串。deckkit 生成的 slides.html 认 `only=<slide-id>` ——
           **只显示那一页**，于是截出来的正好是一页幻灯片，不用裁剪。
    wait_ms: 给页面上的 JS（图表、动画）留出跑完的时间（--virtual-time-budget）。
    """
    html, png = Path(html), Path(png)
    png.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="iypt-shot-") as tmp:
        r = _run([find_browser(), *_base_flags(Path(tmp)),
                  f"--window-size={width},{height}",
                  f"--screenshot={png.resolve()}",
                  f"--virtual-time-budget={wait_ms}",
                  _url(html, query)])
    if not png.is_file():
        raise RuntimeError(f"渲染失败：{html}\n{r.stdout}\n{r.stderr}")
    return png


def to_pdf(html: str | Path, pdf: str | Path, *, wait_ms: int = 1500) -> Path:
    """整份 HTML → PDF。**赛场上放的就是它。**

    页面尺寸由 CSS 的 `@page { size: ... }` 决定 —— deck.css 已经设成 16:9。
    """
    html, pdf = Path(html), Path(pdf)
    pdf.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="iypt-pdf-") as tmp:
        r = _run([find_browser(), *_base_flags(Path(tmp)),
                  f"--print-to-pdf={pdf.resolve()}",
                  "--no-pdf-header-footer",
                  f"--virtual-time-budget={wait_ms}",
                  _url(html, "print=1")])
    if not pdf.is_file():
        raise RuntimeError(f"导出 PDF 失败：{html}\n{r.stdout}\n{r.stderr}")
    return pdf


# ---------------------------------------------------------------- 渲染后审计

#: 在**真实布局**上跑的审计脚本。
#
#  这是整个文件里最值钱的东西：**文字溢出是生成式幻灯片的头号 bug**，
#  而它在源码里完全看不出来 —— 你要等到渲染，甚至要等到有人眯着眼看幻灯片才发现。
#  浏览器知道每个元素的真实包围盒。**问它。**
_AUDIT_JS = r"""
(function () {
  const EPS = 1.5;                       // 亚像素舍入的容差
  const out = { slides: [], fonts: {} };

  try {
    out.fonts.cjk_ok = document.fonts.check('16px "Microsoft YaHei"')
                    || document.fonts.check('16px "Noto Sans SC"')
                    || document.fonts.check('16px SimHei');
  } catch (e) { out.fonts.cjk_ok = null; }

  // 页面「框架」—— 页脚、SIMULATION 角标、图注里的小字。
  //
  // **字号和密度只在「内容」上量，不能把框架算进去。**
  // 否则每一页的「最小字号」永远是页脚的 15px，这道门就成了摆设 —— 它会对每一页
  // 都报同一个假警报，于是所有人学会无视它。**一个总是响的警报等于没有警报。**
  const CHROME = 'footer, .simbadge, .src, .live, .figid, .eqlab';

  const slides = document.querySelectorAll('.slide');
  slides.forEach(function (s) {
    const sb = s.getBoundingClientRect();
    const rec = {
      id: s.id || null,
      w: Math.round(sb.width), h: Math.round(sb.height),
      // 内容比容器高/宽 -> 被裁掉了。**这是最直接的溢出证据。**
      clipped_y: s.scrollHeight - s.clientHeight > EPS,
      clipped_x: s.scrollWidth - s.clientWidth > EPS,
      overflow: [],                      // 跑出幻灯片边界的元素
      overset: [],                       // 自身内容被自己裁掉的元素
      min_font_px: null,
      figs: [],                          // 每张图被缩了多少倍（图上的字够不够大）
      words: 0, bullets: 0, figures: 0,
    };

    let minFont = Infinity;
    const all = s.querySelectorAll('*');
    all.forEach(function (el) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) return;      // 隐藏的不算
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.display === 'none') return;

      // ---- 跑出幻灯片边界了吗（框架也要查 —— 页脚一样会跑出去）
      const dl = sb.left - r.left, dt = sb.top - r.top;
      const dr = r.right - sb.right, db = r.bottom - sb.bottom;
      const worst = Math.max(dl, dt, dr, db);
      if (worst > EPS) {
        rec.overflow.push({
          tag: el.tagName.toLowerCase(),
          cls: (el.className && el.className.baseVal !== undefined)
                 ? el.className.baseVal : String(el.className || ''),
          px: Math.round(worst),
          side: (worst === dl ? 'left' : worst === dt ? 'top'
                 : worst === dr ? 'right' : 'bottom'),
          text: (el.textContent || '').trim().slice(0, 60),
        });
      }

      // ---- 自己的内容被自己裁掉了吗（文字塞不下、被 overflow:hidden 切掉）
      if (el.scrollHeight - el.clientHeight > EPS && cs.overflowY !== 'visible'
          && cs.overflowY !== 'auto' && cs.overflowY !== 'scroll') {
        rec.overset.push({
          tag: el.tagName.toLowerCase(),
          cls: String(el.className || ''),
          px: Math.round(el.scrollHeight - el.clientHeight),
          text: (el.textContent || '').trim().slice(0, 60),
        });
      }

      // ---- 字号：投影到会议厅大屏，后排要读。**只量内容，不量框架。**
      if (el.children.length === 0 && (el.textContent || '').trim()
          && !el.closest(CHROME)) {
        const fs = parseFloat(cs.fontSize);
        if (fs > 0) minFont = Math.min(minFont, fs);
      }
    });

    rec.min_font_px = isFinite(minFont) ? Math.round(minFont * 10) / 10 : null;

    // ---- ★ 图被缩了多少倍。
    //
    //  幻灯片上的字够大，**不代表图上的字够大**。
    //  一张 13 英寸宽的双面板图塞进半栏（~717px），缩放到 0.27x ——
    //  它自己的 13pt 轴标签在屏幕上只剩 ~10px。**后排什么都看不见。**
    //  而 slide 层面的 min_font_px 完全看不到这件事：图对它来说只是一个 <img>。
    s.querySelectorAll('figure.fig img').forEach(function (im) {
      const nw = im.naturalWidth || 0, rw = im.getBoundingClientRect().width;
      if (nw > 0) {
        rec.figs.push({ natural_w: nw, rendered_w: Math.round(rw),
                        scale: Math.round(rw / nw * 1000) / 1000 });
      }
    });

    // ---- 密度：同样**只数内容**。页脚的 "3 / 12" 不是这一页的信息量。
    const content = s.cloneNode(true);
    content.querySelectorAll(CHROME).forEach(function (e) { e.remove(); });
    const txt = (content.textContent || '').trim();
    // 中英混排：中文按**字**数，英文按**词**数
    const cjk = (txt.match(/[一-鿿]/g) || []).length;
    const lat = (txt.replace(/[一-鿿]/g, ' ').match(/[A-Za-z][\w'-]*/g) || []).length;
    rec.words = cjk + lat;
    rec.bullets = s.querySelectorAll('li').length;
    rec.figures = s.querySelectorAll('figure.fig').length;
    out.slides.push(rec);
  });

  const el = document.createElement('div');
  el.id = '__iypt_audit__';
  el.style.display = 'none';
  el.textContent = JSON.stringify(out);
  document.body.appendChild(el);
})();
"""


def audit(html: str | Path, *, wait_ms: int = 1500) -> dict:
    """在**真实渲染出来的布局**上量：溢出、裁切、最小字号、密度。

    做法：把审计脚本注入一份**临时副本**（原文件不动），用 `--dump-dom` 跑，
    再从 DOM 里把 JSON 捞出来。零额外依赖。

    返回 `{"slides": [...], "fonts": {...}}`。整个页面不含 `.slide` 时 `slides` 为空
    （比如交互页面）—— 那种情况下 `audit` 没什么可说的，用 `shoot` 去看图。
    """
    html = Path(html)
    src = html.read_text(encoding="utf-8")
    inject = f"<script>{_AUDIT_JS}</script>"
    patched = (src.replace("</body>", inject + "\n</body>", 1)
               if "</body>" in src else src + inject)

    with tempfile.TemporaryDirectory(prefix="iypt-audit-") as tmp:
        tmpd = Path(tmp)
        # 副本必须和原文件**同目录** —— 否则相对路径的图片/CSS 全断掉
        shadow = html.with_name(html.stem + ".__audit__.html")
        try:
            shadow.write_text(patched, encoding="utf-8")
            r = _run([find_browser(), *_base_flags(tmpd),
                      f"--window-size={W},{H}",
                      "--dump-dom",
                      f"--virtual-time-budget={wait_ms}",
                      _url(shadow)])
        finally:
            shadow.unlink(missing_ok=True)

    m = re.search(r'<div id="__iypt_audit__"[^>]*>(.*?)</div>', r.stdout or "", re.S)
    if not m:
        raise RuntimeError(f"审计脚本没跑起来：{html}\n{(r.stderr or '')[:500]}")
    raw = m.group(1)
    # --dump-dom 会把 JSON 里的 & < > 转义掉
    for a, b in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')):
        raw = raw.replace(a, b)
    return json.loads(raw)


# ---------------------------------------------------------------- CLI

def main() -> int:
    ap = argparse.ArgumentParser(description="HTML → PNG / PDF / 渲染后审计")
    ap.add_argument("html")
    ap.add_argument("--png", help="截一张 PNG 到这里")
    ap.add_argument("--pdf", help="导出 PDF 到这里")
    ap.add_argument("--audit", action="store_true", help="量溢出 / 字号 / 密度")
    ap.add_argument("--only", default="", help="只渲这一页（slide id）")
    ap.add_argument("--size", default=f"{W}x{H}")
    a = ap.parse_args()

    w, h = (int(x) for x in a.size.lower().split("x"))
    if not (a.png or a.pdf or a.audit):
        a.png = str(Path(a.html).with_suffix(".png"))

    if a.png:
        p = shoot(a.html, a.png, query=(f"only={a.only}" if a.only else ""),
                  width=w, height=h)
        print(f"  PNG -> {p}")
        print(f"  ★ 现在用 Read 打开它，**用眼睛看**。读代码猜排版 = 没审。")
    if a.pdf:
        print(f"  PDF -> {to_pdf(a.html, a.pdf)}")
    if a.audit:
        rep = audit(a.html)
        if not rep["slides"]:
            print("  （页面里没有 .slide 元素 —— 没什么可量的。用 --png 去看图。）")
        for s in rep["slides"]:
            bad = s["overflow"] or s["overset"] or s["clipped_x"] or s["clipped_y"]
            print(f"  {'✗' if bad else '✓'} {s['id'] or '?':<8} "
                  f"{s['w']}x{s['h']}  字 {s['words']:>3}  bullet {s['bullets']:>2}  "
                  f"最小字号 {s['min_font_px']}px")
            for o in s["overflow"]:
                print(f"        溢出 {o['px']}px ({o['side']}): <{o['tag']} class=\"{o['cls']}\"> "
                      f"{o['text'][:40]}")
            for o in s["overset"]:
                print(f"        内容被裁 {o['px']}px: <{o['tag']} class=\"{o['cls']}\"> "
                      f"{o['text'][:40]}")
        print(f"  CJK 字体: {rep['fonts'].get('cjk_ok')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
