function b = damping(R, L, Ms, a, w, sigma, mu0, thinWall)
% DAMPING  方程 (15)：有限长磁体 + 有限壁厚的阻尼系数。
%
%   b = F/v = sigma * int_a^{a+w} dr/(2 pi r) int_{-inf}^{inf} (dPhi/dz)^2 dz
%
% thinWall = true 时用薄壁近似 w/(2 pi a) 替代径向积分 —— **只用来隔离 A-2 这一条
% 假设本身的效应**（两边都用有限长磁体的场）。
%
% 数值上的三条规矩（见 references/numerical-recipes.md）：
%   1) 被积函数是**偶函数**（dPhi/dz 是奇的）-> 用 2 * int_0^inf。
%   2) 截断长度用**自然尺度的倍数**（200*a），不是绝对值 —— 参数扫描时 a 会变，
%      绝对截断长度会在扫描的一端悄悄失效。
%   3) 截断必须**翻倍再算一遍**才算证明够长（Gate 1 收敛门）。
%      截短了结果**系统性偏小**，而且偏得平滑 —— 曲线看起来完全正常，只是每个点都
%      错了一点，于是你的**斜率**是错的。
%
% 本文件由 iypt-simulation 从已验证的 Python 实现移植；生成时未在 MATLAB 中执行。

    if nargin < 8, thinWall = false; end

    zmax = 200 * a;
    reltol = 1e-10;

    % 内层：2 * int_0^{200a} (dPhi/dz)^2 dz   （偶函数）
    zint = @(rr) 2 * integral(@(z) dphi_dz(R, L, Ms, rr, z, mu0).^2, ...
                              0, zmax, 'RelTol', reltol, 'AbsTol', 0);

    if thinWall
        b = sigma * w / (2*pi*a) * zint(a);
        return
    end

    % 外层：int_a^{a+w} zint(r) / (2 pi r) dr
    outer = @(r) arrayfun(zint, r) ./ (2*pi*r);
    b = sigma * integral(outer, a, a + w, 'RelTol', reltol, 'AbsTol', 0, ...
                         'ArrayValued', false);
end
