function M = mutual(R, r, d, mu0)
% MUTUAL  共轴圆环互感 M(R, r, d)。
%
%   M = mu0 * sqrt(R r) * [ (2/k - k) K(k) - (2/k) E(k) ],
%   k^2 = 4 R r / ((R+r)^2 + d^2)
%
% 只用第一、二类完全椭圆积分。
%
% ** 坑 **：MATLAB 的 ellipke(m) 吃的是**参数 m = k^2**，不是模数 k。
%          （scipy 的 ellipk(m) 约定相同，所以移植时无需转换。）
%          文献里的公式几乎都用模数 k 写 —— 传错不会报错，只会默默给你一个错的数。
%
% ** 另一个坑 **：k^2 -> 1 时 K(k) 对数发散。k^2 = 1 发生在 R = r 且 d = 0，
%          即磁体半径逼近管内半径。基准参数下 k^2_max = 4*5*6/11^2 = 0.9917，
%          K ~ 3.7 —— 大但有限。把 a 扫到接近 R 时这里会炸。
%
% 本文件由 iypt-simulation 从已验证的 Python 实现移植；生成时未在 MATLAB 中执行。
% 跑 verify.m 自验。

    k2 = 4 .* R .* r ./ ((R + r).^2 + d.^2);
    k  = sqrt(k2);
    [K, E] = ellipke(k2);
    M = mu0 .* sqrt(R .* r) .* ((2 ./ k - k) .* K - (2 ./ k) .* E);
end
