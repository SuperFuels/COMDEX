from pathlib import Path

from backend.modules.aion_cognition.native_english_games import FAMILIES, NativeEnglishGames
from backend.modules.aion_cognition.native_lexical_intelligence import NativeLexicalIntelligence


def _games(tmp_path: Path) -> NativeEnglishGames:
    lexical = NativeLexicalIntelligence(
        tmp_path / "native.sqlite3",
        authority_provider=lambda: {"allow_learn": True, "source": "test"},
    )
    lexical.ingest_records((
        {"lemma": "calculate", "definition": "perform a mathematical computation"},
        {"lemma": "inspect", "definition": "look at something carefully"},
        {"lemma": "repair", "definition": "restore something damaged"},
        {"lemma": "carry", "definition": "support and move something"},
        {"lemma": "open", "definition": "move so access is possible"},
        {"lemma": "verify", "definition": "check that something is true"},
    ), source="test", require_authority=False)
    return NativeEnglishGames(repo_root=tmp_path, lexical=lexical)


def test_all_game_families_hide_the_answer(tmp_path: Path):
    games = _games(tmp_path)

    created = [games.new_game(family=family, difficulty=3) for family in FAMILIES]

    assert {row["family"] for row in created} == set(FAMILIES)
    assert all(row["answer_withheld"] is True for row in created)
    assert all("answer" not in row and "answer_key" not in row for row in created)


def test_wrong_aion_answer_creates_verified_remediation_and_retry_learning(tmp_path: Path, monkeypatch):
    games = _games(tmp_path)
    game = games.new_game(family="sentence_unscramble", difficulty=5)
    native_solver = games._aion_answer
    monkeypatch.setattr(games, "_aion_answer", lambda game: "wrong answer")
    first = games.submit(game_id=game["game_id"], player="aion")

    assert first["correct"] is False
    assert first["correction"]["verified"] is True
    assert first["learning"]["related_retry_scheduled"] is True
    assert first["integrity"]["answer_withheld_from_student"] is True
    assert first["integrity"]["model_used"] is False

    monkeypatch.setattr(games, "_aion_answer", native_solver)
    retry = games.submit(game_id=game["game_id"], player="aion")
    assert retry["correct"] is True
    assert retry["answer"] == retry["correct_answer"]


def test_user_correction_must_match_independent_key(tmp_path: Path):
    games = _games(tmp_path)
    game = games.new_game(family="missing_word", difficulty=2)
    graded = games.submit(game_id=game["game_id"], player="human", answer="invent")

    rejected = games.propose_correction(
        game_id=game["game_id"], answer="invent", reason="I think this is right",
    )
    accepted = games.propose_correction(
        game_id=game["game_id"], answer=graded["correct_answer"],
        reason="The modal requires the base verb.",
    )

    assert rejected["status"] == "rejected_unverified"
    assert accepted["status"] == "accepted"
    assert accepted["verified"] is True


def test_game_metrics_separate_corrections_from_vocabulary_mastery(tmp_path: Path):
    games = _games(tmp_path)
    game = games.new_game(family="grammar_repair", difficulty=4)
    result = games.submit(game_id=game["game_id"], player="human", answer="wrong")
    games.propose_correction(
        game_id=game["game_id"], answer=result["correct_answer"],
        reason="Independent key confirms the repair.",
    )

    metrics = games.metrics()
    assert result["learning"]["counts_as_vocabulary_mastery"] is False
    assert metrics["games_created"] == 1
    assert metrics["attempts"] == 1
    assert metrics["verified_corrections"] == 1
    assert metrics["model_used"] is False
