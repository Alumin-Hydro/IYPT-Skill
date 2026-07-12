% verify.m — MATLAB 移植版的**自检**。
%
% =============================================================================
%  为什么有这个文件
%
%  Python 是这条流水线唯一的执行引擎 —— results.json 只由它产生。
%  MATLAB 版是**移植**，而且是在一台**没有 MATLAB 的机器上生成的**：
%
%                  ** 它在生成时从未被执行过。 **
%
%  整个 repo 的立身之本是「一切结论必须被数值验证」。未经执行的代码正好是这条规则的
%  反例。所以 results.json 里 matlab_port.verified = **false**，而不是 true。
%  谎报 verified=true 就是伪造。
%
%  这个脚本是那份诚实的补偿：它读**已验证的** results.json，用 MATLAB 重算一遍，
%  逐项打印 PASS/FAIL —— **让你在自己的机器上一分钟内确认移植对不对。**
%
%  用法：
%      cd 02-sim/code/matlab
%      verify
% =============================================================================

clear; clc;
fprintf('\n');
fprintf('=====================================================================\n');
fprintf('  MATLAB 移植版自检  ·  magnetic-brake\n');
fprintf('  对拍基准: ../../results.json  (由 Python 产生并已通过全部验证门)\n');
fprintf('=====================================================================\n\n');

%% ---- 载入契约与已验证的结果 -------------------------------------------------
% 参数**一律从 model-spec.json 载入，不硬编码** —— 硬编码的数字会和契约悄悄漂移。
spec = jsondecode(fileread('../../../handoff/model-spec.json'));
res  = jsondecode(fileread('../../results.json'));

P = containers.Map();
for i = 1:numel(spec.parameters)
    P(spec.parameters(i).symbol) = spec.parameters(i).value;
end

mu0   = P('\mu_0');
g     = P('g');
Rmag  = P('R');
Lmag  = P('L');
aTube = P('a');
wWall = P('w');
sigma = P('\sigma');
mDip  = P('m');
Mmass = P('M');

Ms = mDip / (pi * Rmag^2 * Lmag);      % 磁化强度；安培模型的面电流 K = M_s

fprintf('  基准: R=%.1f mm  L=%.1f mm  a=%.1f mm  w=%.1f mm  sigma=%.3g S/m\n', ...
        Rmag*1e3, Lmag*1e3, aTube*1e3, wWall*1e3, sigma);
fprintf('  M_s = %.4e A/m  ->  mu0*M_s = %.4f T  (spec 的 B_r = %.2f T)\n\n', ...
        Ms, mu0*Ms, P('B_r'));

nPass = 0; nFail = 0;

%% ---- Gate 0：极限对拍 ------------------------------------------------------
% **先跑它。** 纯数学恒等式，与物理对错无关：R 和 L 一起缩小（m 固定）+ 薄壁时，
% (15) 必须回到闭式解 (10)。不过 = 代码错。
%
% 注意配方按 SPEC-DEFECT SD-1 修正过：spec 原文只写了 L->0，那会收敛到 3.55 而非 1
% （只让 L->0 而 R 保持 5mm，得到的是半径 5mm 的**薄圆盘**，不是点偶极子）。
fprintf('  Gate 0 · 极限对拍  (R, L -> 0 同时缩小，m 固定；w -> 0)\n');
wThin = wWall * 1e-4;
b0lim = 45/1024 * mu0^2 * mDip^2 * sigma * wThin / aTube^4;

fprintf('    %8s %14s %12s %12s\n', 'eps', 'b_model2', '比值', '误差');
errs = [];
for eps = [1.0, 0.3, 0.1, 0.03, 0.01]
    Re = Rmag * eps;  Le = Lmag * eps;
    Mse = mDip / (pi * Re^2 * Le);                 % m 固定 -> Ms ~ 1/eps^3
    b2  = damping(Re, Le, Mse, aTube, wThin, sigma, mu0);
    ratio = b2 / b0lim;
    errs(end+1) = abs(ratio - 1);                  %#ok<SAGROW>
    fprintf('    %8.3f %14.6e %12.6f %11.4f%%\n', eps, b2, ratio, abs(ratio-1)*100);
end
[nPass, nFail] = chk('Gate 0 极限对拍  误差 < 0.1%', min(errs) < 1e-3, ...
                     sprintf('%.4f%%', min(errs)*100), nPass, nFail);
fprintf('\n');

%% ---- Gate 3：解析对拍（地面真值） -------------------------------------------
b0  = 45/1024 * mu0^2 * mDip^2 * sigma * wWall / aTube^4;
vt0 = Mmass * g / b0;
[nPass, nFail] = chk('Model-0 的 b   == spec baseline', ...
                     relerr(b0, target(spec, 'b')) < 1e-3, ...
                     sprintf('%.4f  (spec %.4f)', b0, target(spec, 'b')), nPass, nFail);
[nPass, nFail] = chk('Model-0 的 v_t == spec baseline', ...
                     relerr(vt0, target(spec, 'v_t')) < 5e-3, ...
                     sprintf('%.5f  (spec %.4f)', vt0, target(spec, 'v_t')), nPass, nFail);

%% ---- 对拍 Python 的 Model-2 结果 --------------------------------------------
b2  = damping(Rmag, Lmag, Ms, aTube, wWall, sigma, mu0);
vt2 = Mmass * g / b2;

pyB  = resTarget(res, 'b');
pyVt = resTarget(res, 'v_t');

[nPass, nFail] = chk('Model-2 的 b   == Python 的 b', relerr(b2, pyB) < 1e-6, ...
                     sprintf('%.6f  (python %.6f)', b2, pyB), nPass, nFail);
[nPass, nFail] = chk('Model-2 的 v_t == Python 的 v_t', relerr(vt2, pyVt) < 1e-6, ...
                     sprintf('%.6f  (python %.6f)', vt2, pyVt), nPass, nFail);

%% ---- F-2 的关键指数 k -------------------------------------------------------
% v_t ~ a^k。Model-0 必须精确给 4；Model-2 预期显著小于 4（A-1 崩溃）。
aScan = logspace(log10(5.5e-3), log10(12.0e-3), 9);
vt2s = zeros(size(aScan));
for i = 1:numel(aScan)
    vt2s(i) = Mmass * g / damping(Rmag, Lmag, Ms, aScan(i), wWall, sigma, mu0);
end
pf = polyfit(log(aScan), log(vt2s), 1);
k2 = pf(1);
kPy = 3.4392;
[nPass, nFail] = chk('F-2 的指数 k (Model-2)', abs(k2 - kPy) < 0.01, ...
                     sprintf('k = %.4f  (python %.4f)', k2, kPy), nPass, nFail);
[nPass, nFail] = chk('A-1 触发条件 |k-4| > 0.3  (P5 必须降级)', abs(k2-4) > 0.3, ...
                     sprintf('|k-4| = %.4f', abs(k2-4)), nPass, nFail);

%% ---- A-2：径向积分 vs 薄壁近似 ----------------------------------------------
bThin = damping(Rmag, Lmag, Ms, aTube, wWall, sigma, mu0, true);
devA2 = abs(b2 - bThin) / bThin;
[nPass, nFail] = chk('A-2 基准点偏差 == Python 的 23.42%', abs(devA2 - 0.2342) < 5e-4, ...
                     sprintf('%.2f%%  (python 23.42%%)', devA2*100), nPass, nFail);
fprintf('        ^ 注意：这条**没有**跨过 spec 的 15%% 门槛 —— A-2 在基准点就站不住。\n');
fprintf('          这是 results.json 里 status = MODEL-CHALLENGED 的原因。\n');

%% ---- 总结 ------------------------------------------------------------------
fprintf('\n=====================================================================\n');
if nFail == 0
    fprintf('  ✓ 移植版自检全部通过 (%d/%d)。\n', nPass, nPass);
    fprintf('    MATLAB 与 Python 在这台机器上给出一致的结果。\n');
else
    fprintf('  ✗ %d 项通过，%d 项**失败**。移植有问题，别用它出结果。\n', nPass, nFail);
end
fprintf('=====================================================================\n\n');

%% ---- 小工具 ----------------------------------------------------------------
function [p, f] = chk(name, ok, detail, p, f)
    if ok
        fprintf('  [PASS]  %-40s  %s\n', name, detail);
        p = p + 1;
    else
        fprintf('  [FAIL]  %-40s  %s\n', name, detail);
        f = f + 1;
    end
end

function e = relerr(a, b)
    e = abs(a - b) / abs(b);
end

function v = target(spec, sym)
    v = NaN;
    for i = 1:numel(spec.targets)
        if strcmp(spec.targets(i).symbol, sym)
            v = spec.targets(i).baseline_value; return
        end
    end
end

function v = resTarget(res, sym)
    v = NaN;
    for i = 1:numel(res.targets)
        if strcmp(res.targets(i).symbol, sym)
            v = res.targets(i).value_numeric; return
        end
    end
end
