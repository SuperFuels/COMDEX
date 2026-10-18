from backend.modules.hexcore.wall_clock_scheduler import wait_for_wall_clock


def test_wall_clock_wait_uses_bounded_chunks():
    now = [100.0]
    calls = []

    def clock():
        return now[0]

    def sleeper(seconds):
        calls.append(seconds)
        now[0] += seconds

    wait_for_wall_clock(65, max_chunk_seconds=30, clock=clock, sleeper=sleeper)
    assert calls == [30, 30, 5]


def test_wall_clock_wait_finishes_promptly_after_simulated_system_sleep():
    now = [100.0]
    calls = []

    def clock():
        return now[0]

    def sleeper(seconds):
        calls.append(seconds)
        now[0] += 8 * 60 * 60

    wait_for_wall_clock(2 * 60 * 60, max_chunk_seconds=30, clock=clock, sleeper=sleeper)
    assert calls == [30]
