from __future__ import annotations
import math, random
import pytest


class TestCycleUtils:
    def _prices(self, n=100, trend=0.001, vol=0.02, seed=42):
        random.seed(seed); ps = [100.0]
        for _ in range(n-1): ps.append(ps[-1]*(1+trend+random.gauss(0,vol)))
        return ps

    def test_rolling_returns(self):
        from vnpy.temporal_intelligence_ai.utils.cycle_utils import rolling_returns
        rets = rolling_returns(self._prices(50), window=10)
        # implementation returns n - window valid entries (no zero-padding)
        assert len(rets) == 40
        assert all(v != 0.0 for v in rets)

    def test_annualized_volatility(self):
        from vnpy.temporal_intelligence_ai.utils.cycle_utils import annualized_volatility
        assert 0.0 < annualized_volatility(self._prices(100), window=20) < 2.0

    def test_trend_strength(self):
        from vnpy.temporal_intelligence_ai.utils.cycle_utils import trend_strength
        ts = trend_strength(self._prices(60), fast=5, slow=20)
        assert -1.0 <= ts <= 1.0

    def test_max_drawdown(self):
        from vnpy.temporal_intelligence_ai.utils.cycle_utils import max_drawdown
        dd = max_drawdown([100, 110, 90, 95, 80, 100])
        assert -1.0 <= dd < 0.0

    def test_identify_cycle_phase(self):
        from vnpy.temporal_intelligence_ai.utils.cycle_utils import identify_cycle_phase
        from vnpy.temporal_intelligence_ai.constant import CyclePhase
        phase, conf = identify_cycle_phase(
            volatility=0.15, trend=0.25, momentum=0.3, drawdown=0.05, breadth=0.6)
        assert isinstance(phase, CyclePhase)
        assert 0.0 <= conf <= 1.0


class TestDecayUtils:
    def test_exponential_decay(self):
        from vnpy.temporal_intelligence_ai.utils.decay_utils import exponential_decay
        assert exponential_decay(1.0, 0.05, 0) == pytest.approx(1.0)
        assert 0 < exponential_decay(1.0, 0.05, 10) < 1.0

    def test_half_life_roundtrip(self):
        from vnpy.temporal_intelligence_ai.utils.decay_utils import half_life_to_rate, rate_to_half_life
        assert rate_to_half_life(half_life_to_rate(20.0)) == pytest.approx(20.0, rel=1e-6)

    def test_compute_decay_metrics(self):
        from vnpy.temporal_intelligence_ai.utils.decay_utils import compute_decay_metrics
        from vnpy.temporal_intelligence_ai.constant import RegimeType, CyclePhase
        m = compute_decay_metrics(
            10, 0.05, regime=RegimeType.BULL_QUIET, phase=CyclePhase.EXPANSION)
        assert 0 < m.combined_strength <= 1.0
        assert m.half_life > 0

    def test_older_weaker(self):
        from vnpy.temporal_intelligence_ai.utils.decay_utils import compute_decay_metrics
        assert (compute_decay_metrics(50, 0.05).combined_strength
                < compute_decay_metrics(5, 0.05).combined_strength)

    def test_crisis_weaker(self):
        from vnpy.temporal_intelligence_ai.utils.decay_utils import compute_decay_metrics
        from vnpy.temporal_intelligence_ai.constant import RegimeType
        bull   = compute_decay_metrics(10, 0.05, regime=RegimeType.BULL_QUIET)
        crisis = compute_decay_metrics(10, 0.05, regime=RegimeType.CRISIS)
        assert crisis.combined_strength < bull.combined_strength

    def test_build_decay_curve(self):
        from vnpy.temporal_intelligence_ai.utils.decay_utils import build_decay_curve
        from vnpy.temporal_intelligence_ai.constant import DecayMode
        c = build_decay_curve('A1', DecayMode.EXPONENTIAL, 0, 0.05, horizon=20)
        ss = c.strengths()
        assert len(ss) == 21
        assert ss[0] >= ss[-1]


class TestDependencyUtils:
    def _ar1(self, n=300, phi=0.7, seed=1):
        random.seed(seed); xs = [0.0]
        for _ in range(n - 1): xs.append(phi * xs[-1] + random.gauss(0, 1))
        return xs

    def test_autocorr_lag1(self):
        from vnpy.temporal_intelligence_ai.utils.dependency_utils import autocorrelation_at_lag
        assert autocorrelation_at_lag(self._ar1(500, phi=0.8), 1) > 0.6

    def test_compute_autocorr(self):
        from vnpy.temporal_intelligence_ai.utils.dependency_utils import compute_autocorr
        r = compute_autocorr('sig1', self._ar1(200), max_lag=20)
        assert r.signal_id == 'sig1'
        assert len(r.lags) == 20
        assert 0 <= r.memory_score <= 1.0

    def test_crosscorr_lead_lag(self):
        from vnpy.temporal_intelligence_ai.utils.dependency_utils import compute_crosscorr
        random.seed(5); n = 300
        a = [random.gauss(0, 1) for _ in range(n)]
        b = [0.0] * 3 + a[:n - 3]
        assert compute_crosscorr('a', a, 'b', b, max_lag=10).lead_lag == -3

    def test_horizons_sum(self):
        from vnpy.temporal_intelligence_ai.utils.dependency_utils import decompose_horizons
        h = decompose_horizons(self._ar1(300))
        assert (h.short_term_weight + h.mid_term_weight + h.long_term_weight) == pytest.approx(1.0, abs=0.02)


class TestTransitionUtils:
    def _rets(self, n=200, mean=0.001, vol=0.02, seed=3):
        random.seed(seed)
        return [random.gauss(mean, vol) for _ in range(n)]

    def _prices(self, rets, p0=100.0):
        ps = [p0]
        for r in rets: ps.append(ps[-1] * (1 + r))
        return ps

    def test_regime_shift_range(self):
        from vnpy.temporal_intelligence_ai.utils.transition_utils import detect_regime_shift
        sig = detect_regime_shift(self._rets(200))
        assert 0.0 <= sig.strength <= 1.0

    def test_volatility_break_range(self):
        from vnpy.temporal_intelligence_ai.utils.transition_utils import detect_volatility_break
        rets = self._rets(60, vol=0.005) + self._rets(20, vol=0.08)
        assert detect_volatility_break(self._prices(rets)).strength >= 0.0

    def test_regime_probs_sum(self):
        from vnpy.temporal_intelligence_ai.utils.transition_utils import estimate_regime_probabilities
        probs = estimate_regime_probabilities(0.20, 0.15, 0.3, 0.2)
        assert sum(probs.probabilities.values()) == pytest.approx(1.0, abs=0.01)

    def test_transition_prob_range(self):
        from vnpy.temporal_intelligence_ai.utils.transition_utils import (
            compute_transition_probability, detect_regime_shift,
            detect_volatility_break, detect_liquidity_regime)
        rets = self._rets(200)
        tp, tc = compute_transition_probability(
            detect_regime_shift(rets),
            detect_volatility_break(self._prices(rets)),
            detect_liquidity_regime([1.0] * 200, rets))
        assert 0.0 <= tp <= 1.0
        assert 0.0 <= tc <= 1.0


class TestTemporalUtils:
    def _records(self, n=20, noise=0.05, seed=9):
        from vnpy.temporal_intelligence_ai.model.validation_model import ValidationRecord
        random.seed(seed); recs = []
        for i in range(n):
            p = random.gauss(0, 0.5)
            recs.append(ValidationRecord(
                record_id=f'r{i}', predicted=p,
                realized=p + random.gauss(0, noise), is_realized=True))
        return recs

    def test_mae_nonneg(self):
        from vnpy.temporal_intelligence_ai.utils.temporal_utils import compute_errors, compute_mae
        assert compute_mae(compute_errors(self._records(50))) >= 0

    def test_rmse_ge_mae(self):
        from vnpy.temporal_intelligence_ai.utils.temporal_utils import (
            compute_errors, compute_mae, compute_rmse)
        res = compute_errors(self._records(50))
        assert compute_rmse(res) >= compute_mae(res)

    def test_direction_acc_range(self):
        from vnpy.temporal_intelligence_ai.utils.temporal_utils import (
            compute_errors, compute_direction_accuracy)
        assert 0.0 <= compute_direction_accuracy(compute_errors(self._records(100))) <= 1.0

    def test_health_score_range(self):
        from vnpy.temporal_intelligence_ai.utils.temporal_utils import compute_temporal_health
        assert 0.0 <= compute_temporal_health(0.6, 0.7, 0.5, 30, 0.02) <= 100.0

    def test_decay_alignment_perfect(self):
        from vnpy.temporal_intelligence_ai.utils.temporal_utils import compute_decay_alignment
        s = [1.0, 0.9, 0.8, 0.5, 0.2, 0.04]
        align, _ = compute_decay_alignment(s, s)
        assert align == pytest.approx(1.0)

    def test_build_metrics(self):
        from vnpy.temporal_intelligence_ai.utils.temporal_utils import build_validation_metrics
        m = build_validation_metrics(self._records(30))
        assert m.n_records == 30 and m.mae >= 0
        assert 0 <= m.temporal_health <= 100


class TestDecayEngine:
    def _engine(self):
        from vnpy.temporal_intelligence_ai.engine.decay_engine import DecayEngine
        from vnpy.temporal_intelligence_ai.constant import DecayMode
        eng = DecayEngine()
        eng.configure(mode=DecayMode.EXPONENTIAL)
        return eng

    def _rec(self, aid, created_bar=0, hl=20):
        from vnpy.temporal_intelligence_ai.datasource.alpha_loader import AlphaRecord
        from vnpy.temporal_intelligence_ai.utils.decay_utils import half_life_to_rate
        return AlphaRecord(alpha_id=aid, created_bar=created_bar,
                           base_decay_rate=half_life_to_rate(hl))

    def test_register_and_compute(self):
        eng = self._engine()
        eng.register_alpha(self._rec('a1'))
        states = eng.compute(bar=10)
        assert len(states) == 1
        assert 0 < states[0].metrics.combined_strength <= 1.0

    def test_multiple_alphas(self):
        eng = self._engine()
        for i in range(5):
            eng.register_alpha(self._rec(f'a{i}'))
        assert len(eng.compute(bar=5)) == 5

    def test_older_alpha_weaker(self):
        eng = self._engine()
        eng.register_alpha(self._rec('young', created_bar=90))
        eng.register_alpha(self._rec('old', created_bar=0))
        by_id = {s.alpha_id: s for s in eng.compute(bar=100)}
        assert by_id['young'].metrics.combined_strength > by_id['old'].metrics.combined_strength

    def test_expired_flag(self):
        from vnpy.temporal_intelligence_ai.datasource.alpha_loader import AlphaRecord
        from vnpy.temporal_intelligence_ai.utils.decay_utils import half_life_to_rate
        eng = self._engine()
        eng.configure(min_threshold=0.5)
        eng.register_alpha(AlphaRecord(alpha_id='fast', created_bar=0,
                                       base_decay_rate=half_life_to_rate(2)))
        assert eng.compute(bar=20)[0].is_expired

    def test_curves_generated(self):
        eng = self._engine()
        eng.register_alpha(self._rec('c1'))
        eng.compute(bar=5)
        assert 'c1' in eng.get_curves()

    def test_summary_keys(self):
        eng = self._engine()
        eng.register_alpha(self._rec('s1'))
        eng.compute(bar=5)
        summ = eng.get_summary()
        assert all(k in summ for k in ('active_alphas', 'avg_strength', 'expired_count'))

    def test_crisis_context_weaker(self):
        from vnpy.temporal_intelligence_ai.constant import RegimeType, CyclePhase
        eng = self._engine()
        eng.register_alpha(self._rec('x'))
        eng.set_context(regime=RegimeType.BULL_QUIET, phase=CyclePhase.EXPANSION,
                        current_vol=0.15, current_bar=0)
        s_bull = eng.compute(bar=20)[0].metrics.combined_strength
        eng.set_context(regime=RegimeType.CRISIS, phase=CyclePhase.CONTRACTION,
                        current_vol=0.60, current_bar=0)
        s_crisis = eng.compute(bar=20)[0].metrics.combined_strength
        assert s_crisis < s_bull


class TestDependencyEngine:
    def _ar1(self, n=300, phi=0.7, seed=1):
        random.seed(seed); xs = [0.0]
        for _ in range(n - 1):
            xs.append(phi * xs[-1] + random.gauss(0, 1))
        return xs

    def test_analyze_single(self):
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        eng = DependencyEngine()
        eng.register_signal('s1', self._ar1(300))
        state = eng.analyze()
        assert state is not None
        assert 's1' in state.autocorr_results
        assert state.overall_memory > 0

    def test_two_signals(self):
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        eng = DependencyEngine()
        eng.register_signal('a', self._ar1(300, phi=0.8, seed=1))
        eng.register_signal('b', self._ar1(300, phi=0.6, seed=2))
        assert len(eng.analyze().crosscorr_results) == 1

    def test_horizon_sums(self):
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        eng = DependencyEngine()
        eng.register_signal('s', self._ar1(300))
        h = eng.analyze().horizon_decomp
        total = h.short_term_weight + h.mid_term_weight + h.long_term_weight
        assert total == pytest.approx(1.0, abs=0.02)

    def test_high_phi_higher_memory(self):
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        e1, e2 = DependencyEngine(), DependencyEngine()
        e1.register_signal('s', self._ar1(300, phi=0.9))
        e2.register_signal('s', self._ar1(300, phi=0.1))
        assert e1.analyze().overall_memory > e2.analyze().overall_memory

    def test_history_accumulates(self):
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        eng = DependencyEngine()
        eng.register_signal('s', self._ar1(300))
        for _ in range(3):
            eng.analyze()
        assert len(eng.get_history().records) == 3


class TestTransitionEngine:
    def _rets(self, n=200, mean=0.001, vol=0.02, seed=3):
        import random as rr; rr.seed(seed)
        return [rr.gauss(mean, vol) for _ in range(n)]
    def _prices(self, rets, p0=100.0):
        ps = [p0]
        for r in rets: ps.append(ps[-1] * (1 + r))
        return ps
    def _engine(self):
        from vnpy.temporal_intelligence_ai.engine.transition_engine import TransitionEngine
        eng = TransitionEngine()
        eng.configure(regime_fast=10, regime_slow=40, regime_thresh=1.5,
                      vol_short=10, vol_long=40, vol_ratio=1.5,
                      liq_short=10, liq_long=40, liq_thresh=1.3)
        return eng
    def test_detect_returns_state(self):
        eng = self._engine(); rets = self._rets(200)
        eng.update_series(prices=self._prices(rets), returns=rets)
        assert eng.detect() is not None
    def test_prob_range(self):
        eng = self._engine(); rets = self._rets(200)
        eng.update_series(prices=self._prices(rets), returns=rets)
        s = eng.detect()
        assert 0.0 <= s.transition_prob <= 1.0
        assert 0.0 <= s.transition_confidence <= 1.0
    def test_regime_probs_sum(self):
        eng = self._engine(); rets = self._rets(200)
        eng.update_series(prices=self._prices(rets), returns=rets)
        total = sum(eng.detect().regime_probs.probabilities.values())
        assert total == pytest.approx(1.0, abs=0.02)
    def test_context_preserved(self):
        from vnpy.temporal_intelligence_ai.constant import RegimeType, CyclePhase
        eng = self._engine()
        eng.set_context(regime=RegimeType.BEAR_VOLATILE, phase=CyclePhase.CONTRACTION,
                        current_vol=0.40, current_trend=-0.15)
        rets = self._rets(200)
        eng.update_series(prices=self._prices(rets), returns=rets)
        assert eng.detect().current_regime == RegimeType.BEAR_VOLATILE
    def test_summary_keys(self):
        eng = self._engine(); rets = self._rets(200)
        eng.update_series(prices=self._prices(rets), returns=rets)
        eng.detect()
        summ = eng.get_summary()
        assert all(k in summ for k in
                   ('transition_prob','transition_confidence','is_transitioning','current_regime'))


class TestValidationEngine:
    def _engine(self):
        from vnpy.temporal_intelligence_ai.engine.validation_engine import ValidationEngine
        return ValidationEngine()
    def _rec(self, rid, pred, real=None, realized=False, horizon=5):
        from vnpy.temporal_intelligence_ai.model.validation_model import ValidationRecord
        return ValidationRecord(record_id=rid, predicted=pred,
                                realized=real, is_realized=realized, horizon_bars=horizon)
    def test_empty_validate(self):
        assert self._engine().validate().metrics.n_records == 0
    def test_unrealized_excluded(self):
        eng = self._engine()
        eng.submit_prediction(self._rec('r1', pred=0.5))
        assert eng.validate().metrics.n_realized == 0
    def test_realized_included(self):
        import random as rr; rr.seed(42)
        eng = self._engine()
        for i in range(20):
            p = rr.gauss(0, 1)
            eng.submit_prediction(self._rec(f'r{i}', p, real=p+rr.gauss(0,0.1), realized=True))
        assert eng.validate().metrics.n_realized == 20
    def test_realize_method(self):
        eng = self._engine()
        eng.submit_prediction(self._rec('x1', pred=0.3))
        eng.realize('x1', 0.28)
        assert eng.validate().metrics.n_realized == 1
    def test_perfect_predictions(self):
        eng = self._engine()
        for i in range(30):
            v = float(i) * 0.01
            eng.submit_prediction(self._rec(f'p{i}', v, real=v, realized=True))
        m = eng.validate().metrics
        assert m.direction_acc == pytest.approx(1.0, abs=0.01)
        assert m.bias == pytest.approx(0.0, abs=1e-6)
    def test_good_better_than_bad(self):
        import random as rr; rr.seed(7)
        eg, eb = self._engine(), self._engine()
        for i in range(40):
            p = rr.gauss(0, 1)
            eg.submit_prediction(self._rec(f'g{i}', p, real=p+rr.gauss(0,0.02), realized=True))
            eb.submit_prediction(self._rec(f'b{i}', p, real=-p+rr.gauss(0,0.5), realized=True))
        assert eg.validate().metrics.temporal_health > eb.validate().metrics.temporal_health
    def test_history_length(self):
        eng = self._engine()
        for _ in range(5): eng.validate()
        assert len(eng.get_history().snapshots) == 5


class TestModels:
    def test_cycle_state_to_dict(self):
        from vnpy.temporal_intelligence_ai.model.cycle_model import CycleMetrics, CycleState
        from vnpy.temporal_intelligence_ai.constant import CyclePhase, RegimeType
        m = CycleMetrics(volatility=0.20, trend_strength=0.10, momentum=0.05, drawdown=0.08, breadth=0.6)
        d = CycleState(phase=CyclePhase.EXPANSION, regime=RegimeType.BULL_QUIET, confidence=0.75, metrics=m).to_dict()
        assert d['phase'] == 'expansion'
        assert d['confidence'] == pytest.approx(0.75)
    def test_decay_state_to_dict(self):
        from vnpy.temporal_intelligence_ai.model.decay_model import DecayMetrics, DecayState
        from vnpy.temporal_intelligence_ai.constant import DecayMode
        m = DecayMetrics(combined_strength=0.65, half_life=20.0, decay_rate=0.05, age_bars=10)
        d = DecayState(alpha_id='A1', mode=DecayMode.EXPONENTIAL, metrics=m).to_dict()
        assert d['alpha_id'] == 'A1'
        assert d['combined_strength'] == pytest.approx(0.65, abs=1e-4)
    def test_dependency_matrix_symmetric(self):
        from vnpy.temporal_intelligence_ai.model.dependency_model import DependencyMatrix
        dm = DependencyMatrix(signal_ids=['a', 'b', 'c'])
        dm.set('a', 'b', 0.72)
        assert dm.get('a', 'b') == dm.get('b', 'a') == pytest.approx(0.72)
        assert dm.get('a', 'c') == 0.0
    def test_regime_probability_dominant(self):
        from vnpy.temporal_intelligence_ai.model.transition_model import RegimeProbability
        from vnpy.temporal_intelligence_ai.constant import RegimeType
        rp = RegimeProbability(probabilities={
            RegimeType.BULL_QUIET.value: 0.55,
            RegimeType.SIDEWAYS.value: 0.30,
            RegimeType.BEAR_QUIET.value: 0.15})
        assert rp.dominant() == RegimeType.BULL_QUIET.value
        assert rp.confidence() == pytest.approx(0.55)
    def test_validation_history_max_size(self):
        from vnpy.temporal_intelligence_ai.model.validation_model import ValidationHistory, ValidationState
        h = ValidationHistory(max_size=5)
        for _ in range(10): h.append_snapshot(ValidationState())
        assert len(h.snapshots) == 5
    def test_decay_curve_strengths(self):
        from vnpy.temporal_intelligence_ai.model.decay_model import DecayCurve, DecayCurvePoint
        from vnpy.temporal_intelligence_ai.constant import DecayMode
        pts = [DecayCurvePoint(bar=i, strength=1.0 - i * 0.05) for i in range(10)]
        c = DecayCurve(alpha_id='X', mode=DecayMode.EXPONENTIAL, points=pts)
        ss = c.strengths()
        assert len(ss) == 10 and ss[0] > ss[-1]


class TestEndToEnd:
    def test_decay_to_validation(self):
        import random as rr; rr.seed(42)
        import math as mm
        from vnpy.temporal_intelligence_ai.engine.decay_engine import DecayEngine
        from vnpy.temporal_intelligence_ai.engine.validation_engine import ValidationEngine
        from vnpy.temporal_intelligence_ai.datasource.alpha_loader import AlphaRecord
        from vnpy.temporal_intelligence_ai.model.validation_model import ValidationRecord
        from vnpy.temporal_intelligence_ai.utils.decay_utils import half_life_to_rate
        decay_eng = DecayEngine(); val_eng = ValidationEngine()
        for i in range(10):
            decay_eng.register_alpha(AlphaRecord(alpha_id=f'a{i}', created_bar=0,
                base_decay_rate=half_life_to_rate(rr.randint(10, 40))))
        pred_s = []
        for bar in range(1, 51):
            st = decay_eng.compute(bar)
            if st: pred_s.append(st[0].metrics.combined_strength)
        for i, s in enumerate(pred_s):
            val_eng.submit_prediction(ValidationRecord(record_id=f'v{i}', predicted=s,
                realized=max(0.0, s + rr.gauss(0, 0.02)), is_realized=True))
        state = val_eng.validate()
        assert state.metrics.temporal_health > 0
        assert state.metrics.n_realized == len(pred_s)
    def test_dependency_then_transition(self):
        import random as rr; rr.seed(10)
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        from vnpy.temporal_intelligence_ai.engine.transition_engine import TransitionEngine
        n = 250; v = 0.0; series = []
        for _ in range(n):
            v = 0.8 * v + rr.gauss(0, 1); series.append(v)
        rets = [rr.gauss(0.001, 0.02) for _ in range(n)]
        prices = [100.0]
        for r in rets: prices.append(prices[-1] * (1 + r))
        dep_eng = DependencyEngine()
        dep_eng.register_signal('s', series)
        assert dep_eng.analyze() is not None
        tran_eng = TransitionEngine()
        tran_eng.configure(regime_fast=10, regime_slow=40,
                           vol_short=10, vol_long=40, liq_short=10, liq_long=40)
        tran_eng.update_series(prices=prices, returns=rets)
        tran_state = tran_eng.detect()
        assert tran_state is not None
        assert 0 <= tran_state.transition_prob <= 1.0
    def test_full_pipeline(self):
        import random as rr; rr.seed(99)
        import math as mm
        from vnpy.temporal_intelligence_ai.engine.decay_engine import DecayEngine
        from vnpy.temporal_intelligence_ai.engine.dependency_engine import DependencyEngine
        from vnpy.temporal_intelligence_ai.engine.transition_engine import TransitionEngine
        from vnpy.temporal_intelligence_ai.engine.validation_engine import ValidationEngine
        from vnpy.temporal_intelligence_ai.datasource.alpha_loader import AlphaRecord
        from vnpy.temporal_intelligence_ai.model.validation_model import ValidationRecord
        from vnpy.temporal_intelligence_ai.utils.decay_utils import half_life_to_rate
        from vnpy.temporal_intelligence_ai.constant import RegimeType, CyclePhase, DecayMode
        n = 300
        rets = [rr.gauss(0.0005, 0.018) for _ in range(n)]
        prices = [100.0]
        for r in rets: prices.append(prices[-1] * (1 + r))
        sig = [sum(rets[max(0, i-5):i+1]) for i in range(n)]
        decay_eng = DecayEngine()
        decay_eng.configure(mode=DecayMode.REGIME_DEPENDENT)
        decay_eng.set_context(regime=RegimeType.BULL_QUIET, phase=CyclePhase.EXPANSION,
                              current_vol=0.18, current_bar=0)
        for i in range(5):
            decay_eng.register_alpha(AlphaRecord(alpha_id=f'a{i}', created_bar=0,
                base_decay_rate=half_life_to_rate(20 + i * 5)))
        decay_states = decay_eng.compute(bar=50)
        assert len(decay_states) == 5
        dep_eng = DependencyEngine()
        dep_eng.register_signal('rets', rets)
        dep_eng.register_signal('cum', sig)
        assert dep_eng.analyze() is not None
        tran_eng = TransitionEngine()
        tran_eng.configure(regime_fast=10, regime_slow=40,
                           vol_short=10, vol_long=40, liq_short=10, liq_long=40)
        tran_eng.update_series(prices=prices, returns=rets)
        assert tran_eng.detect() is not None
        val_eng = ValidationEngine()
        for i, ds in enumerate(decay_states):
            s = ds.metrics.combined_strength
            val_eng.submit_prediction(ValidationRecord(record_id=f'v{i}', predicted=s,
                realized=s + rr.gauss(0, 0.02), is_realized=True))
        pred_s = [mm.exp(-0.05 * t) for t in range(60)]
        real_s = [mm.exp(-0.055 * t) for t in range(60)]
        val_eng.set_decay_series(pred_s, real_s)
        val_state = val_eng.validate()
        assert 0 <= val_state.metrics.temporal_health <= 100
        assert val_state.metrics.n_realized == 5
