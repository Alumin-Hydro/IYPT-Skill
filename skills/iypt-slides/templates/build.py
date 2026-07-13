#!/usr/bin/env python3
"""一键：deck.json → slides.html（自包含）→ png/S-xx.png + deck.pdf + script.md。

    python 03-slides/build.py

**做不到「一条命令重现整份 PPT」= PPT 和数据已经脱钩了。**
（这和 Skill 2 的 `run_all.py` 是同一条规矩：仿真一重跑，PPT 上的数字必须跟着变，
而不是变成一个谎。）

产物：
    03-slides/slides.html      自包含单文件（图、公式全部内嵌；无 CDN）
    03-slides/png/S-xx.png     ★ 每页一张 —— **Skill 4 打开来用眼睛看**
    03-slides/deck.pdf         赛场上放的就是它
    03-slides/script.md        讲稿（notes 里的 {{}} 一样被代入）
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, OSError):
        pass

HERE = Path(__file__).resolve().parent          # 03-slides/
WS = HERE.parent                                # 工作区
sys.path.insert(0, str(HERE))

import deckkit as dk                            # noqa: E402
import render_html as rh                        # noqa: E402


def main() -> int:
    t0 = time.time()
    deck = json.loads((HERE / "deck.json").read_text(encoding="utf-8"))
    R = json.loads((WS / "02-sim" / "results.json").read_text(encoding="utf-8"))
    css = (HERE / "deck.css").read_text(encoding="utf-8")

    print("=" * 78)
    print(f"deck: {deck['title']}")
    print(f"  {len(deck['slides'])} 页   ·   results.json status = {R.get('status')}")
    print("=" * 78)

    # ---- HTML
    html = dk.render(deck, R, WS, css)
    out_html = HERE / "slides.html"
    out_html.write_text(html, encoding="utf-8")
    print(f"  slides.html   {out_html.stat().st_size/1024:.0f} KB（自包含：图与公式全内嵌）")

    # ---- 每页 PNG。**这是 Skill 4 唯一能看见幻灯片的方式。**
    png_dir = HERE / "png"
    for old in png_dir.glob("S-*.png"):
        old.unlink()
    for s in deck["slides"]:
        rh.shoot(out_html, png_dir / f"{s['id']}.png", query=f"only={s['id']}")
    print(f"  png/          {len(deck['slides'])} 张   ← ★ Read 打开它们，**用眼睛看**")

    # ---- PDF
    rh.to_pdf(out_html, HERE / "deck.pdf")
    print(f"  deck.pdf      {(HERE / 'deck.pdf').stat().st_size/1024:.0f} KB")

    # ---- 讲稿
    (HERE / "script.md").write_text(dk.script_md(deck, R), encoding="utf-8")
    print("  script.md")

    # ---- 渲染后审计：溢出 / 字号 / 密度。**在浏览器里量，不靠人眼。**
    rep = rh.audit(out_html)
    bad = 0
    for s in rep["slides"]:
        problems = []
        if s["clipped_y"] or s["clipped_x"]:
            problems.append("内容被裁")
        if s["overflow"]:
            problems.append(f"{len(s['overflow'])} 个元素跑出边界")
        if s["overset"]:
            problems.append(f"{len(s['overset'])} 处文字塞不下")
        if problems:
            bad += 1
            print(f"    ✗ {s['id']}: {'；'.join(problems)}")
            for o in (s["overflow"] + s["overset"])[:3]:
                print(f"        {o['px']}px  <{o['tag']} class=\"{o['cls']}\">  {o['text'][:44]}")

    print()
    print("=" * 78)
    if bad:
        print(f"✗ {bad} 页有溢出/裁切 —— **去 check_slides.py 看详情，然后改 deck.json**")
    else:
        print("✓ 无溢出、无裁切（在真实渲染出来的布局上量的）")
    print(f"总耗时 {time.time()-t0:.1f} s")
    print()
    print("接下来：")
    print("  python <skill>/scripts/check_slides.py <工作区>     # 12 道机械门")
    print("  Read 03-slides/png/S-*.png                        # ★ 铁律 0：逐页用眼睛看")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
