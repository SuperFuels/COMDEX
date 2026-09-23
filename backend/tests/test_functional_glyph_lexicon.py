from pathlib import Path

from backend.modules.hexcore.functional_glyph_lexicon import FunctionalGlyphLexicon


def test_functional_lexicon_links_language_procedure_failure_and_verifier(tmp_path: Path):
    evidence_path = tmp_path / "evidence.json"
    evidence_path.write_text('{"passed":true}', encoding="utf-8")
    store = tmp_path / "lexicon.json.gz"
    lex = FunctionalGlyphLexicon(repo_root=tmp_path, store_path=store)
    evidence = lex.add_evidence("evidence.json", authority="executable_test")
    procedure = lex.add_node(
        kind="procedure", key="ordered_work", summary="order dependency work safely",
        aliases=["topological planner"], evidence=[evidence],
        facets={
            "purpose": "order work", "inputs": ["tasks"], "preconditions": ["known dependencies"],
            "steps": ["find ready", "emit ready"], "invariants": ["dependency first"],
            "failure_signals": ["cycle"], "verification": ["ordering property"],
            "transfer": ["build systems"],
        },
    )
    failure = lex.add_node(kind="failure", key="cycle", summary="no ready tasks remain",
                           facets={"repair": "reject"}, evidence=[evidence])
    verifier = lex.add_node(kind="verifier", key="ordering_property", summary="dependency position check",
                            facets={"authority": "executable"}, evidence=[evidence])
    lex.relate(procedure, "fails_as", failure)
    lex.relate(procedure, "verified_by", verifier)
    validation = lex.validate()
    assert validation["complete_procedures"] == 1
    assert validation["node_provenance_resolves"]
    lex.save()

    loaded = FunctionalGlyphLexicon.load(repo_root=tmp_path, store_path=store)
    assert loaded.query("topological dependency planner")[0]["key"] == "ordered_work"
    capsule = loaded.reconstruct("ordered_work")
    assert capsule["passed"]
    assert {row["kind"] for row in capsule["associations"]} == {"failure", "verifier"}


def test_functional_lexicon_abstains_without_a_reconstructable_procedure(tmp_path: Path):
    lex = FunctionalGlyphLexicon(repo_root=tmp_path, store_path=tmp_path / "x.gz")
    assert lex.query("completely unknown language") == []
    assert lex.reconstruct("not_known")["status"] == "ABSTAIN_UNKNOWN_PROCEDURE"

