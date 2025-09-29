import re
from backend.modules.dna_chain import dna_switch

def test_utc_now_returns_iso_z():
    ts = dna_switch._utc_now()

    # Must be a string ending in Z
    assert isinstance(ts, str)
    assert ts.endswith("Z")

    # Should match ISO datetime pattern
    pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.match(pattern, ts), f"Not ISO datetime: {ts}"

    # Ensure no timezone offsets like +00:00 or -05:00
    assert not ts.endswith("+00:00")
    assert not re.search(r"[+-]\d{2}:\d{2}$", ts)