%VERIFY  自检脚本：读已验证的 results.json，重算，逐项打印 PASS/FAIL。
%
%   ★★ 本文件由 Python 侧生成，**生成时未在 MATLAB 中执行**（该机器没有 MATLAB）。
%      在有 MATLAB 的机器上：
%          cd examples/electrical-damping/02-sim/code/matlab
%          verify
%      全部 PASS 之前，results.json 里的 matlab_port.verified 必须保持 false。
%
%   验什么（三层，与 Python 侧的门同构）：
%     1. Model-0 闭式 targets（G_max/z_pk/γ/ζ/t*/A_c/c₂）vs results.targets 的
%        value_analytical（<0.5%）—— 纯代数，抓移植的参数/单位错。
%     2. Gate-0b 教科书对拍：G≡const、γ_oc=0 的 ODE vs 解析衰减解（<1e-8）——
%        抓 ode45 的用法错。
%     3. Gate-0c 能量法对拍：b=βz² 的包络 vs (23) 闭式（<0.2%）—— 抓动力学移植错。
clear; clc;
here = fileparts(mfilename('fullpath'));
spec = jsondecode(fileread(fullfile(here, '..', '..', '..', 'handoff', 'model-spec.json')));
res  = jsondecode(fileread(fullfile(here, '..', '..', 'results.json')));

P = containers.Map();
for i = 1:numel(spec.parameters)
    P(spec.parameters(i).symbol) = spec.parameters(i).value;
end
mu0 = P('\mu_0');  N = P('N');  a = P('a');  lc = P('\ell_c');  m = P('m');
Meff = P('M_eff'); k = P('k'); Rc = P('R_c'); R = P('R'); goc = P('\gamma_{oc}');
om0 = sqrt(k / Meff);
npass = 0; nfail = 0;

% ── 1. Model-0 闭式 targets ────────────────────────────────────────────
G0  = @(z) mu0*N*m*a^2/(2*lc) .* ((a^2+(z+lc/2).^2).^(-1.5) - (a^2+(z-lc/2).^2).^(-1.5));
gp0 = abs(-1.5*mu0*N*m*a^2*(a^2+lc^2/4)^(-2.5));
zpk = fminbnd(@(z) -abs(G0(z)), 1e-6, 0.03, optimset('TolX', 1e-12));
gmax = abs(G0(zpk));
beta_sc = gp0^2 / Rc;
vals = containers.Map();
vals('G_{\max}')    = gmax;
vals('z_{\rm pk}')  = zpk;
vals('\gamma')      = goc + gmax^2/(2*Meff*(R+Rc));
vals('\zeta')       = gmax^2/(2*sqrt(Meff*k)*(R+Rc));
vals('t^*')         = 4*Meff/(beta_sc*P('A_0')^2);
vals('A_c')         = sqrt(8*Meff*goc/beta_sc);
vals('c_2')         = gp0^2/(2*Meff*(R+Rc))*1e-6;
fprintf('== 1. Model-0 targets vs results.value_analytical ==\n');
for i = 1:numel(res.targets)
    t = res.targets(i);
    v = vals(t.symbol);
    dev = abs(v/t.value_analytical - 1);
    ok = dev < 5e-3;
    npass = npass + ok; nfail = nfail + ~ok;
    fprintf('  %-12s %-4s  matlab=%.6g  python=%.6g  dev=%.2e\n', ...
            t.symbol, tern(ok), v, t.value_analytical, dev);
end

% ── 2. Gate-0b：教科书对拍（只测积分器用法）──────────────────────────
b0 = gmax^2/(R+Rc); gam = b0/(2*Meff); omd = sqrt(om0^2-gam^2); A0 = 3e-3;
T = 10*2*pi/omd;
opt = odeset('RelTol', 1e-12, 'AbsTol', 1e-15);
rhs = @(t, y) [y(2); (-k*y(1) - b0*y(2))/Meff];
sol = ode45(rhs, [0 T], [A0; -gam*A0], opt);
tt = linspace(0, T, 20000);
u = deval(sol, tt); u = u(1, :);
err0b = max(abs(u - A0*exp(-gam*tt).*cos(omd*tt)))/A0;
ok = err0b < 1e-8;
npass = npass + ok; nfail = nfail + ~ok;
fprintf('== 2. Gate-0b textbook: err=%.2e  %s ==\n', err0b, tern(ok));

% ── 3. Gate-0c：b=βz² 的包络 vs (23) 闭式 ─────────────────────────────
rhs23 = @(t, y) [y(2); (-k*y(1) - (2*Meff*goc + beta_sc*y(1)^2)*y(2))/Meff];
T = 12; sol = ode45(rhs23, [0 T], [A0; 0], opt);
tt = linspace(0, T, 72000);
u = deval(sol, tt); u = u(1, :);
[pk, ipk] = findpeaks(u);
tp = tt(ipk); msk = pk > 0.03e-3; tp = tp(msk); pk = pk(msk);
tstar = 4*Meff/(beta_sc*A0^2); q = 1/(2*goc*tstar);
A23 = A0 ./ sqrt((1+q)*exp(2*goc*tp) - q);
err0c = max(abs(pk - A23)./A23);
ok = err0c < 2e-3;
npass = npass + ok; nfail = nfail + ~ok;
fprintf('== 3. Gate-0c energy-method: err=%.2e  %s ==\n', err0c, tern(ok));

fprintf('\n%d PASS / %d FAIL\n', npass, nfail);
if nfail == 0
    fprintf(['全部通过 ⟹ 可以把 results.json 的 matlab_port.verified 改为 true\n' ...
             '（并在提交信息里注明是在哪台 MATLAB 上跑通的）。\n']);
else
    fprintf('有 FAIL —— matlab_port.verified 保持 false，先查移植。\n');
end

function s = tern(ok)
    if ok, s = 'PASS'; else, s = 'FAIL'; end
end
