"""write_pe_health_scorer.py — append HealthScorer + HealthEngine"""
import pathlib, ast

P = pathlib.Path(
    r"c:\Users\11229\Documents\GitHub\vnpy\vnpy\platform_engineering\engine\health_engine.py"
)

SCORER = '''

class HealthScorer:
    DIM_WEIGHT = {"perf": 0.40, "risk": 0.25, "alpha": 0.20, "exec": 0.15}

    def compute(self, snap: HealthMetricSnapshot):
        warns: List[str] = []
        # perf
        pp = []
        if snap.sharpe is not None:
            pp.append((_sm(snap.sharpe, _T.SHARPE_GOOD, _T.SHARPE_WARN, _T.SHARPE_BAD), 0.50))
            if snap.sharpe < _T.SHARPE_WARN: warns.append(f"Sharpe \\u504f\\u4f4e ({snap.sharpe:.2f})")
        if snap.max_drawdown is not None:
            pp.append((_sm(snap.max_drawdown, _T.DRAWDOWN_GOOD, _T.DRAWDOWN_WARN, _T.DRAWDOWN_BAD, hi=False), 0.30))
            if snap.max_drawdown > _T.DRAWDOWN_WARN: warns.append(f"\\u6700\\u5927\\u56de\\u64a4 ({snap.max_drawdown*100:.1f}%)")
        if snap.win_rate is not None:
            pp.append((_sm(snap.win_rate, _T.WIN_RATE_GOOD, _T.WIN_RATE_WARN, 0.30), 0.20))
            if snap.win_rate < _T.WIN_RATE_WARN: warns.append(f"\\u80dc\\u7387\\u504f\\u4f4e ({snap.win_rate*100:.1f}%)")
        perf = _wt(pp)
        # risk
        rp = []
        if snap.risk_exposure is not None:
            rp.append((_sm(snap.risk_exposure, _T.RISK_EXP_GOOD, _T.RISK_EXP_WARN, _T.RISK_EXP_BAD, hi=False), 1.0))
            if snap.risk_exposure > _T.RISK_EXP_WARN: warns.append(f"\\u98ce\\u9669\\u655e\\u53e3 ({snap.risk_exposure*100:.1f}%)")
        risk = _wt(rp)
        # alpha
        ap = []
        if snap.ic_mean is not None:
            ap.append((_sm(snap.ic_mean, _T.IC_GOOD, _T.IC_WARN, 0.0), 0.60))
            if snap.ic_mean < _T.IC_WARN: warns.append(f"IC \\u5747\\u503c\\u504f\\u4f4e ({snap.ic_mean:.3f})")
        if snap.alpha_decay is not None:
            ap.append((_sm(snap.alpha_decay, _T.ALPHA_DECAY_OK, _T.ALPHA_DECAY_WARN, _T.ALPHA_DECAY_BAD, hi=False), 0.40))
            if snap.alpha_decay > _T.ALPHA_DECAY_WARN: warns.append(f"Alpha \\u8870\\u51cf ({snap.alpha_decay*100:.1f}%)")
        alpha = _wt(ap)
        # exec
        ep = []
        if snap.order_delay_ms is not None:
            ep.append((_sm(snap.order_delay_ms, _T.DELAY_GOOD, _T.DELAY_WARN, _T.DELAY_BAD, hi=False), 0.40))
            if snap.order_delay_ms > _T.DELAY_WARN: warns.append(f"\\u8ba2\\u5355\\u5ef6\\u8fdf ({snap.order_delay_ms:.0f}ms)")
        if snap.fill_rate is not None:
            ep.append((_sm(snap.fill_rate, _T.FILL_GOOD, _T.FILL_WARN, 0.70), 0.40))
            if snap.fill_rate < _T.FILL_WARN: warns.append(f"\\u6210\\u4ea4\\u7387\\u504f\\u4f4e ({snap.fill_rate*100:.1f}%)")
        if snap.slippage_bps is not None:
            ep.append((_sm(snap.slippage_bps, _T.SLIP_GOOD, _T.SLIP_WARN, _T.SLIP_BAD, hi=False), 0.20))
            if snap.slippage_bps > _T.SLIP_WARN: warns.append(f"\\u6ed1\\u70b9\\u504f\\u9ad8 ({snap.slippage_bps:.1f}bps)")
        exc = _wt(ep)
        # total
        tp = [(s, w) for s, w in [
            (perf,  self.DIM_WEIGHT["perf"]),
            (risk,  self.DIM_WEIGHT["risk"]),
            (alpha, self.DIM_WEIGHT["alpha"]),
            (exc,   self.DIM_WEIGHT["exec"]),
        ] if s is not None]
        total = _wt(tp)
        return total, perf, risk, alpha, exc, warns
'''

ast.parse(SCORER)
with open(P, "a", encoding="utf-8") as f:
    f.write(SCORER)
print("Scorer OK")
