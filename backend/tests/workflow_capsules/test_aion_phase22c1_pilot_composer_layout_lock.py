from pathlib import Path

TEXT = Path("desktop/mac/src/app.js").read_text(encoding="utf-8")


def function_block(name):
    start = TEXT.index(f"function {name}")
    brace = TEXT.index("{", start)
    depth = 0
    in_string = None
    escape = False

    for i in range(brace, len(TEXT)):
        ch = TEXT[i]

        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == in_string:
                in_string = None
            continue

        if ch in ("'", '"', "`"):
            in_string = ch
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return TEXT[start:i + 1]

    raise AssertionError(f"function not closed: {name}")


def test_phase22c1_composer_uses_existing_css_class_contract():
    block = function_block("renderAionPilotSimpleTaskStream")
    assert 'class="aion-pilot-composer-bar"' in block
    assert 'data-aion-pilot-composer' in block
    assert 'class="aion-pilot-composer" data-aion-pilot-composer' not in block


def test_phase22c1_existing_composer_css_still_exists():
    assert ".aion-pilot-composer-bar" in TEXT
    assert ".aion-pilot-composer-bar textarea" in TEXT
    assert ".aion-pilot-composer-bar button" in TEXT
