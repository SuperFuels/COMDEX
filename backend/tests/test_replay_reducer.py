from backend.replay.reducer import ReplayReducer


def test_reducer():
    base = {"a": 1, "b": {"x": 1}, "c": [1]}
    frames = [
        {"a": 2},
        {"b": {"y": 9}},
        {"c": [2, 3]},
    ]

    out = ReplayReducer.apply_state(base, frames)
    expected = {"a": 2, "b": {"x": 1, "y": 9}, "c": [1, 2, 3]}
    assert out == expected, f"Expected {expected}, got {out}"


if __name__ == "__main__":
    test_reducer()
    print("✅ ReplayReducer test passed.")