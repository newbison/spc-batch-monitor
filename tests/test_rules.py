import numpy as np
from spc_engine.rules import check_rules


def test_rule1_point_beyond_limits():
    # Point beyond UCL
    xbar = np.array([6.5, 6.7, 6.6, 8.0, 6.8])  # index 3 is beyond UCL 7.5
    violations = check_rules(xbar, ucl=7.5, lcl=5.5, cl=6.5)
    rule1s = [v for v in violations if v["rule"] == 1]
    assert any(v["batch_index"] == 3 for v in rule1s)


def test_rule4_eight_above_cl():
    # 10 points all above centerline
    xbar = np.array([6.6] * 10)
    violations = check_rules(xbar, ucl=9.0, lcl=4.0, cl=6.5)
    rule4s = [v for v in violations if v["rule"] == 4]
    assert len(rule4s) >= 1  # at least one "8 above CL" flag


def test_trending_6_up():
    xbar = np.array([6.0, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6])
    violations = check_rules(xbar, ucl=10.0, lcl=2.0, cl=6.0)
    trend = [v for v in violations if v["rule"] == 5]
    assert len(trend) >= 1


def test_no_violations_in_control():
    xbar = np.array([6.4, 6.6, 6.5, 6.3, 6.7, 6.5, 6.4, 6.6, 6.3, 6.5])
    violations = check_rules(xbar, ucl=7.5, lcl=5.5, cl=6.5)
    assert len(violations) == 0
