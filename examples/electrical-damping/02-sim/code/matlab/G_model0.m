function [G, gp0] = G_model0(z, spec_params)
%G_MODEL0  换能系数的 Model-0 闭式（契约式 (6)/(7)：点偶极子 + 薄螺线管）。
%
%   ★ 由 Python 侧生成，**未在 MATLAB 中执行**。用 verify.m 自检后再用。
%
%   [G, gp0] = G_MODEL0(z, P)   P 是 containers.Map（symbol → value，见 verify.m）
%   G   : dλ/dz (Wb/m)，严格奇函数，G(0)=0
%   gp0 : |G'(0)| (Wb/m²)，式 (7)
mu0 = spec_params('\mu_0'); N = spec_params('N');
a = spec_params('a'); lc = spec_params('\ell_c'); m = spec_params('m');
G = mu0*N*m*a^2/(2*lc) .* ((a^2+(z+lc/2).^2).^(-1.5) - (a^2+(z-lc/2).^2).^(-1.5));
gp0 = abs(-1.5*mu0*N*m*a^2*(a^2+lc^2/4)^(-2.5));
end
