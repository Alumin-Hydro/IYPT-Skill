function [t, z, tp, Ap] = simulate_damping(z0, A0, R, T, spec_params)
%SIMULATE_DAMPING  二维系统（A-4 消元后）的 ODE + 包络提取。
%
%   ★ 由 Python 侧生成，**未在 MATLAB 中执行**。用 verify.m 自检后再用。
%   与 Python 侧 model2.simulate2 同构：M_eff·v̇ = −k(z−z₀) − [2M_eff·γ_oc + b(z)]·v，
%   b(z) = G(z)²/(R+R_c)，G 用 Model-0 闭式（要 Model-2 精度请回 Python 侧）。
P = spec_params;
Meff = P('M_eff'); k = P('k'); Rc = P('R_c'); goc = P('\gamma_{oc}');
rhs = @(t, y) [y(2); (-k*(y(1)-z0) ...
    - (2*Meff*goc + G_model0(y(1), P)^2/(R+Rc))*y(2))/Meff];
opt = odeset('RelTol', 1e-10, 'AbsTol', 1e-13);
sol = ode45(rhs, [0 T], [z0 + A0; 0], opt);
t = linspace(0, T, round(T*6000));
zz = deval(sol, t); z = zz(1, :);
[Ap, ipk] = findpeaks(z - z0);
tp = t(ipk); msk = Ap > 0.03e-3;
tp = tp(msk); Ap = Ap(msk);
end
