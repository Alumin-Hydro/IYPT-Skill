#!/usr/bin/env python3
r"""★★ 判据 × 模型 的双向表（Stage 8.5）——把 Skill 2 会用的验收判据，
在**正确模型**和**学生真会写的错模型**上都跑一遍。只跑正确模型 = 换了一把新的失明的锁。

正确模型：随机相位碰撞振子。棒尖 z_tip=A sin(ωt)，球飞行(自由落体)+碰撞 (5)。
相位在碰撞间以 φ→φ+ω·2u/g 演化（ω·2u/g~3600 ⟹ 敏感依赖 ⟹ 有效随机）——
这是**确定性混沌**如何表现为随机相位统计稳态（§5）。稳态给 h̄=(1+e)/(1-e)(Aω)²/4g。

输出 matrix.json（供 model-spec.json 内嵌 + check_analysis 校验）。
"""
from __future__ import annotations
import hashlib, json, math, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

g = 9.81
HERE = Path(__file__).resolve().parent

# ─────────────────────────────────────────── 正确模型：随机相位弹跳
def hbar_sim(A, w, e, n=60000, burn=20000):
    """稳态平均弹高，确定性混沌相位演化（无 random，可复现）。"""
    u = A * w                       # 初始launch速率
    phi = 0.123
    acc, cnt = 0.0, 0
    for i in range(n):
        T = 2.0 * u / g             # 飞行时间（棒尖位移 μm ≪ 飞行 mm，忽略）
        phi = (phi + w * T) % (2 * math.pi)
        wtip = A * w * math.cos(phi)
        v_out = (1 + e) * wtip + e * u
        u = abs(v_out)
        if i >= burn:
            acc += u * u / (2 * g); cnt += 1
    return acc / cnt

def hbar_theory(A, w, e):
    return (1 + e) / (1 - e) * (A * w) ** 2 / (4 * g)

def hbar_dist_cv(A, w, e, n=60000, burn=20000):
    """稳态弹高分布的变异系数（随机相位 ⟹ 宽；确定性锁相 ⟹ ~0）。"""
    u = A * w; phi = 0.123; hs = []
    for i in range(n):
        T = 2.0 * u / g; phi = (phi + w * T) % (2 * math.pi)
        u = abs((1 + e) * A * w * math.cos(phi) + e * u)
        if i >= burn: hs.append(u * u / (2 * g))
    mean = sum(hs) / len(hs)
    var = sum((h - mean) ** 2 for h in hs) / len(hs)
    return var ** 0.5 / mean

# ─────────────────────────────────────────── 共振（BC）
def f1(c, L, bc):
    return c / (4 * L) if bc == "fixed-free" else c / (2 * L)   # 固定-自由 vs 自由-自由

# 基准参数
c, L, e0 = 5590.169943749474, 0.100, 0.6
f_res = f1(c, L, "fixed-free")
w0 = 2 * math.pi * f_res
A0 = 2.0e-6                        # μm 级棒尖振幅（可见弹跳，Γ≫π）

# ─────────────────────────────────────────── 四条判据（Skill 2 会用的验收）
# 每条判据是一个函数 model -> 标量；正确模型给一个值，判据检查它落在带内。
# model 用一组可被错模型篡改的钩子表示。
def measure(model):
    """跑一个 model（dict of overrides），返回四个可判量。"""
    A, w, e = A0, w0, e0
    hb = model.get("hbar_fn", hbar_sim)(A, w, e)
    peak = model.get("f1", f_res)                       # 共振峰位
    cv = model.get("cv_fn", hbar_dist_cv)(A, w, e)      # 弹高分布 CV
    # e→1 发散比：h̄(e=0.9)/h̄(e=0.6) —— 正确 (1+e)/(1-e) 结构给 ~4.75×
    hb_hi = model.get("hbar_fn", hbar_sim)(A, w, 0.9)
    diverge = hb_hi / hb
    return dict(hbar=hb, peak=peak, cv=cv, diverge=diverge)

correct = measure({})
hb_th = hbar_theory(A0, w0, e0)
diverge_th = (hbar_theory(A0, w0, 0.9) / hbar_theory(A0, w0, e0))

criteria = [
 {"id":"C1-peak","statement":"共振峰位 = c/4L（固定-自由）","tolerance":0.10,
  "tolerance_source":"【结构】峰位是本征值，固定-自由 c/4L=13975Hz vs 自由-自由 c/2L=27951Hz，**差 2× 离散**。门槛 10% ≪ 100% 间隔 ⟹ 远离两者。不用弹高幅度（连续可漂移）。",
  "measure":"peak","target":f_res,"kind":"relerr"},
 {"id":"C2-slope","statement":"h̄ = (1+e)/(1-e)(Aω)²/4g（绝对值/斜率）","tolerance":0.15,
  "tolerance_source":"实验侧：独立测 A（干涉 ~10%）+ e（落球 ~5%）⟹ 预言侧不确定度 ~15%。这是**绝对值**判据（唯一能抓『形状全对、系数偏了』的错模型）。",
  "measure":"hbar","target":hb_th,"kind":"relerr"},
 {"id":"C3-diverge","statement":"h̄ 随 e→1 发散（(1+e)/(1-e) 结构）","tolerance":0.20,
  "tolerance_source":"【结构】比值 h̄(0.9)/h̄(0.6)：正确 (1+e)/(1-e) 给 (1.9/0.1)/(1.6/0.4)=4.75；无耗散结构（如 e² 或常数）给 ≠4.75。门槛 20% 分辨 4.75 vs 其它。",
  "measure":"diverge","target":diverge_th,"kind":"relerr"},
 {"id":"C4-broad","statement":"弹高分布是宽的（随机相位），非单值锁相","tolerance":0.15,
  "tolerance_source":"【结构】随机相位稳态 CV~O(0.5-1)；确定性单值锁相 CV→0。门槛：CV<0.15 判为『锁相/退化』。",
  "measure":"cv","target":None,"kind":"broad"},
]

def judge(crit, vals):
    m = vals[crit["measure"]]
    if crit["kind"] == "relerr":
        return abs(m / crit["target"] - 1) <= crit["tolerance"]     # True = pass(在带内)
    if crit["kind"] == "broad":
        return m >= crit["tolerance"]                                # True = 够宽=pass
    raise ValueError

# ─────────────────────────────────────────── 错模型（学生真会写的）
def hbar_locked(A, w, e):        # WM4：单值锁相，抛到峰值棒尖速度高度，忽略能量泵入
    return (A * w) ** 2 / (2 * g)
def cv_locked(A, w, e): return 0.0
def hbar_offset(A, w, e):        # WM5：形状全对、系数偏 2×（漏随机相位 1/2，用峰值而非 rms）
    return (1 + e) / (1 - e) * (A * w) ** 2 / (2 * g)
def diverge_const(A, w, e):      # helper for WM3
    return None

wrong_models = [
 {"id":"WM1-free-free","statement":"棒两端都自由，f_n=nc/2L",
  "why_a_student_writes_it":"忘了底端贴管底支承，默认『一根棒』两端自由——最常见的 BC 疏忽。峰位翻倍。",
  "override":{"f1": f1(c, L, "free-free")}},
 {"id":"WM2-no-resonance","statement":"棒尖幅度与频率无关（无 Q 共振），A 直接正比驱动",
  "why_a_student_writes_it":"忽略声共振，以为线圈磁场幅度直接给棒尖位移——漏掉『为什么要靠近本征频率』。共振曲线无峰。",
  "override":{"f1": None}},   # 无峰：peak 取 None（远离 f_res）
 {"id":"WM3-elastic","statement":"理想弹性 e=1，无碰撞耗散",
  "why_a_student_writes_it":"把球当理想弹性体，忽略恢复系数<1——则无稳态、弹高发散，且发散结构错。",
  "override":{"elastic": True}},
 {"id":"WM4-locked","statement":"球被抛到峰值棒尖速度对应高度 h=(Aω)²/2g，单值",
  "why_a_student_writes_it":"直觉：球被棒尖以最大速度 Aω 抛起，一次到位——忽略多次随机碰撞的能量泵入与统计稳态。给单值、无 (1+e)/(1-e)。",
  "override":{"hbar_fn": hbar_locked, "cv_fn": cv_locked}},
 {"id":"WM5-offset","statement":"h̄=(1+e)/(1-e)(Aω)²/2g（系数偏 2×）",
  "why_a_student_writes_it":"★ 最难抓：随机相位能量平衡里用了峰值棒尖速度 Aω 而非 rms=Aω/√2，漏了 ⟨w²⟩=½(Aω)² 的 1/2。**标度律一字不差（h̄∝(Aω)²、随 (1+e)/(1-e)），只有绝对值偏 2×。**",
  "override":{"hbar_fn": hbar_offset}},
]

def measure_wrong(wm):
    ov = wm["override"]
    A, w, e = A0, w0, e0
    if ov.get("elastic"):
        # e=1：稳态不存在，弹高无界（用大 e 近似发散）；发散比也失去 (1+e)/(1-e) 意义
        hb = hbar_sim(A, w, 0.995)         # 巨大
        peak = f_res; cv = hbar_dist_cv(A, w, 0.995)
        diverge = hbar_sim(A, w, 0.999) / hb   # 仍在涨，但结构量偏离 4.75
        return dict(hbar=hb, peak=peak, cv=cv, diverge=diverge)
    hbfn = ov.get("hbar_fn", hbar_sim); cvfn = ov.get("cv_fn", hbar_dist_cv)
    hb = hbfn(A, w, e); peak = ov.get("f1", f_res); cv = cvfn(A, w, e)
    hb_hi = hbfn(A, w, 0.9); diverge = hb_hi / hb if hb else float("inf")
    return dict(hbar=hb, peak=peak, cv=cv, diverge=diverge)

# ─────────────────────────────────────────── 跑双向表
rows = []
correct_pass = {}
for crit in criteria:
    ok = judge(crit, correct)
    correct_pass[crit["id"]] = ok
catches = {crit["id"]: [] for crit in criteria}
model_caught = {wm["id"]: False for wm in wrong_models}
for wm in wrong_models:
    vals = measure_wrong(wm)
    for crit in criteria:
        # WM2 no-peak: peak=None ⟹ 判 fail
        if crit["measure"] == "peak" and vals["peak"] is None:
            caught = True
        else:
            caught = not judge(crit, vals)
        if caught:
            catches[crit["id"]].append(wm["id"]); model_caught[wm["id"]] = True

# ─────────────────────────────────────────── robustness_scan（正确模型在自己承认的系统误差上不误杀）
# 承认的系统误差：e 的测量不确定度 ±5%（A-4）。扫 e，确认 C1(峰位) 与 C3(发散结构) 不误杀。
budget_e = 0.05
scan_upper = 0.20                    # 扫到 4× budget（≥3×，CRIT-ROBUSTNESS-COARSE）
scan = []
for de in [-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20]:
    ee = e0 * (1 + de)
    hb = hbar_sim(A0, w0, ee)
    passC2 = abs(hb / hb_th - 1) <= 0.15
    scan.append({"delta_e": round(de, 4), "hbar": hb, "C2_pass": passC2})
# delta_max：C2 开始误杀正确模型的最小 |de| —— **二分**定界（bracket 相对宽 <5%，非网格）
def falsekilled(de):
    return abs(hbar_sim(A0, w0, e0 * (1 + de)) / hb_th - 1) > 0.15
lo, hi, delta_max = 0.0, None, None
step = 0.005
d = step
while d <= scan_upper + 1e-9:
    if falsekilled(d):
        hi = d; lo = d - step; break
    d += step
bracket_lo, bracket_hi = None, None
if hi is not None:                       # 二分收紧 [lo,hi] 到相对宽 <5%
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        if falsekilled(mid): hi = mid
        else: lo = mid
        if (hi - lo) / hi < 0.02: break
    delta_max = hi                       # first_fail
    bracket_lo, bracket_hi = lo, hi       # last_pass ≤ delta_max ≤ first_fail

# ─────────────────────────────────────────── min_detectable（判据集的分辨率 ε*）
# ε*_offset：C2 能检测的最小 h̄ 系数偏差（扫 WM5 的因子 2→接近 4）
eps_offset = None
for fac in [x / 100 for x in range(400, 200, -2)]:   # 4.00 → 2.02
    hb_wm = (1 + e0) / (1 - e0) * (A0 * w0) ** 2 / (fac * g)
    if abs(hb_wm / hb_th - 1) > 0.15:                 # 被 C2 抓到
        eps_offset = abs(4.0 / fac - 1); break
# ε*_BC：C1 能检测的最小峰位偏移（连续从 c/4L 移开）
eps_bc = 0.10   # = C1 tolerance（峰位偏 >10% 即抓）

matrix = {
 "generated_by": "01-criteria/criterion_matrix.py",
 "purpose": "判据 × 模型 双向表。正确模型全 PASS（←CRIT-FALSEKILL）· 每个错模型被抓（↑CRIT-MODEL-UNCAUGHT）· 每条判据抓到东西（→CRIT-BLIND）。含 robustness（不误杀）与 min_detectable（ε*，判据集的分辨率）。",
 "correct_model": {
   "detail": "随机相位碰撞振子；h̄_sim=%.4e vs 理论 (1+e)/(1-e)(Aω)²/4g=%.4e（偏 %.2f%%）；峰位 c/4L=%.1fHz；CV=%.3f；e→1 发散比=%.3f（理论 %.3f）" % (
     correct["hbar"], hb_th, (correct["hbar"]/hb_th-1)*100, f_res, correct["cv"], correct["diverge"], diverge_th),
   "passes_all": all(correct_pass.values()),
 },
 "robustness_scan": {
   "parameter": "e（恢复系数）测量不确定度",
   "why": "A-4 承认 e 有 ±5% 测量不确定度；正确模型在这条系统误差上不能被 C2 误杀。",
   "scan_upper_bound": scan_upper,
   "systematic_error_budget": budget_e,
   "delta_max": bracket_hi,
   "delta_max_bracket": [bracket_lo, bracket_hi] if bracket_hi is not None else None,
   "margin": (bracket_hi / budget_e) if bracket_hi else None,
   "scan": scan,
   "verdict": "PASS" if (delta_max is None or delta_max >= budget_e) else "FALSEKILL-RISK",
 },
 "min_detectable": {
   "why": "ε* 是判据集的分辨率——可汇报的物理结论，而非『某个错模型被抓到』。",
   "offset_C2": {"eps_star": eps_offset, "criterion": "C2-slope",
                 "meaning": "C2 能分辨的最小 h̄ 绝对系数相对偏差（扫 WM5 的 2×→4× 因子）"},
   "bc_C1": {"eps_star": eps_bc, "criterion": "C1-peak",
             "meaning": "C1 能分辨的最小共振峰位相对偏移"},
 },
 "wrong_models": [{"id":wm["id"],"statement":wm["statement"],"why_a_student_writes_it":wm["why_a_student_writes_it"]} for wm in wrong_models],
 "criteria": [
   {"id":c["id"],"statement":c["statement"],"tolerance":c["tolerance"],"tolerance_source":c["tolerance_source"],
    "passes_correct":correct_pass[c["id"]],
    "correct_model_detail":"correct measure=%s target=%s" % (
        {"hbar":round(correct["hbar"],6),"peak":round(correct["peak"],2),"cv":round(correct["cv"],4),"diverge":round(correct["diverge"],4)}[c["measure"]],
        (round(c["target"],4) if c["target"] is not None else "broad")),
    "catches":catches[c["id"]]}
   for c in criteria],
 "verdict": "PASS" if (all(correct_pass.values()) and all(model_caught.values()) and all(catches[c["id"]] for c in criteria)) else "FAIL",
}

# 自 sha256（脚本自身）——check_analysis 用 read_text().replace(CRLF,LF).encode 复算比对，
# 这里必须用**同一口径**（否则 Windows 的 \r\n 会让戳对不上）。
# ★ matrix.json **不写 `script` 键** —— check_analysis 把内嵌副本剥掉 `script` 再和 matrix.json 比，
#   故 `script` 只存在于契约内嵌那份（嵌入时补上），matrix.json 里不能有。
_src = (HERE / "criterion_matrix.py").read_text(encoding="utf-8").replace("\r\n", "\n")
matrix["source_sha256"] = hashlib.sha256(_src.encode("utf-8")).hexdigest()

(HERE / "matrix.json").write_text(json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8")
print("=== 双向表 ===")
print("正确模型全 PASS :", matrix["correct_model"]["passes_all"], correct_pass)
print("每个错模型被抓 :", model_caught)
print("每条判据抓到   :", {k: v for k, v in catches.items()})
print("robustness      : delta_max=%s budget=%s margin=%s" % (delta_max, budget_e, matrix["robustness_scan"]["margin"]))
print("min_detectable  : eps_offset(C2)=%s eps_bc(C1)=%s" % (eps_offset, eps_bc))
print("VERDICT         :", matrix["verdict"])
raise SystemExit(0 if matrix["verdict"] == "PASS" else 1)
