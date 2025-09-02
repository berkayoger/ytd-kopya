from backend.draks.advanced import advanced_decision_logic


def test_direction_mismatch_returns_false():
    out = {"decision": "LONG", "score": 0.2}
    ok, scale = advanced_decision_logic(
        draks_out=out, side="SELL", base_scale=0.5, live_mode=False
    )
    assert ok is False and scale == 0.0


def test_regime_scaling_and_caps():
    out = {"decision": "LONG", "score": 0.5, "regime_probs": {"bull": 1.0}}
    ok, scale = advanced_decision_logic(
        draks_out=out, side="BUY", base_scale=0.5, live_mode=False
    )
    assert ok is True and scale == 0.6


def test_live_mode_cap():
    out = {"decision": "LONG", "score": 1.0, "regime_probs": {"bull": 1.0}}
    ok, scale = advanced_decision_logic(
        draks_out=out, side="BUY", base_scale=1.0, live_mode=True
    )
    assert ok is True and scale == 0.75
