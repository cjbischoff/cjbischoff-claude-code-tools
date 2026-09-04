from sec_overlay import cost
from sec_overlay.models import CampaignState


def test_record_and_aggregate_timings():
    st = CampaignState(pass_number=1, active_sha=None)
    cost.record_timing(st, "prefilter", 1.5)
    cost.record_timing(st, "prefilter", 0.5)
    cost.record_timing(st, "report", 2.0)
    agg = cost.aggregate_timings_by_phase(st)
    assert agg == {"prefilter": 2.0, "report": 2.0}
