# beam_state.py

def filter_beams_by_collapse_status(beams, show_collapsed=True):
    """
    Filters beam traces by collapse status.

    Args:
        beams (list): List of beam events.
        show_collapsed (bool): Whether to include collapsed/dead branches.

    Returns:
        list: Filtered beam events.
    """
    if show_collapsed:
        return beams
    return [b for b in beams if b.get("collapse_state") != "collapsed"]


def group_beams_by_tick(beams):
    """
    Groups beam events by execution tick.

    Args:
        beams (list): List of beam events.

    Returns:
        dict[int, list]: Mapping of tick → list of beams.
    """
    tick_map = {}
    for b in beams:
        tick = b.get("tick") or 0
        tick_map.setdefault(tick, []).append(b)
    return tick_map


def extract_unique_ticks(beams):
    """
    Extracts all unique ticks from the beam list in sorted order.

    Args:
        beams (list): List of beam events.

    Returns:
        list[int]: Sorted list of unique tick values.
    """
    return sorted({b.get("tick", 0) for b in beams})