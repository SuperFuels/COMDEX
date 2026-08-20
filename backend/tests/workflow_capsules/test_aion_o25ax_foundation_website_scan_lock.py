from __future__ import annotations

import json
import subprocess
from pathlib import Path


APP = Path(
    "desktop/mac/src/app.js"
).read_text(encoding="utf-8")

CTRL = Path(
    "desktop/mac/src/"
    "aion_business_foundation_voice_controller.js"
).read_text(encoding="utf-8")

INDEX = Path(
    "desktop/mac/src/index.html"
).read_text(encoding="utf-8")

MODULE_PATH = Path(
    "desktop/mac/src/"
    "aion_business_foundation_website_scan.js"
)

MODULE = MODULE_PATH.read_text(
    encoding="utf-8"
)


def test_o25ax_script_load_order():
    controller = INDEX.index(
        "aion_business_foundation_voice_controller.js"
    )

    scanner = INDEX.index(
        "aion_business_foundation_website_scan.js"
    )

    orchestrator = INDEX.index(
        "aion_business_twin_orchestrator.js"
    )

    app = INDEX.index(
        "./app.js"
    )

    assert (
        controller <
        scanner <
        orchestrator <
        app
    )


def test_o25ax_foundation_schema_asks_for_website():
    assert 'field: "website_url"' in CTRL

    assert (
        "Do you have a website?"
        in CTRL
    )

    assert (
        "please provide it starting with www"
        in CTRL
    )

    assert (
        'required: false'
        in CTRL[
            CTRL.index('field: "website_url"'):
            CTRL.index(
                'field: "entry_mode"',
                CTRL.index('field: "website_url"'),
            )
        ]
    )


def test_o25ax_app_automatically_scans_website_answer():
    assert (
        "AION O25AX automatic "
        "Foundation website scan"
        in APP
    )

    assert (
        'answeredFieldBeforeWebsiteScan ===\n'
        '        "website_url"'
        in APP
    )

    assert (
        "AionBusinessFoundationWebsiteScan"
        in APP
    )

    assert (
        ".scanAndMerge("
        in APP
    )

    assert (
        "__aionO25AXLastWebsiteScanReceipt"
        in APP
    )


def test_o25ax_uses_existing_read_only_backend_route():
    assert (
        "/api/local-node/aion/"
        "small-business/website-scan"
        in MODULE
    )

    assert (
        "preview_only: true"
        in MODULE
    )

    assert (
        "live_external_side_effect: false"
        in MODULE
    )

    assert (
        "public_read_only: true"
        in MODULE
    )


def test_o25ax_preserves_founder_answers_and_maps_evidence():
    assert (
        "if (\n"
        "        isMeaningful(\n"
        "          draft[target]\n"
        "        )\n"
        "      )"
        in MODULE
    )

    for field in (
        "business_name",
        "business_model",
        "offer_summary",
        "customer_type",
        "revenue_streams",
        "operating_base",
        "current_tools_and_evidence",
        "current_challenges",
        "near_term_priorities",
    ):
        assert (
            f'target: "{field}"'
            in MODULE
        )

    assert (
        "user_answers_overwritten: false"
        in MODULE
    )

    assert (
        "public_website_scan"
        in MODULE
    )

    assert (
        "website_evidence"
        in MODULE
    )

    assert "brand_design_evidence" in MODULE
    assert "logo_candidates" in MODULE
    assert "colour_candidates" in MODULE
    assert "font_candidates" in MODULE
    assert "detected_evidence_requires_confirmation" in MODULE


def test_o25ax_module_has_no_business_specific_defaults():
    assert "Home Fixed" not in MODULE
    assert "home_fixed" not in MODULE
    assert "Almería" not in MODULE
    assert "Murcia" not in MODULE


def test_o25ax_node_runtime_merges_only_missing_fields():
    script = r'''
const scanner = require(
  "./desktop/mac/src/" +
  "aion_business_foundation_website_scan.js"
);

const packet = {
  foundation_draft: {
    website_url: "www.example.test",
    business_name: "Founder Confirmed Name",
    offer_summary: "",
    customer_type: "",
  },
  business_map: {
    facts: [],
    assumptions: [],
    unanswered_fields: [],
  },
  transcript: [],
  last_turn: {
    mapped_field: "website_url",
    text: "www.example.test",
  },
  next_question: {
    field: "website_url",
    target_field: "website_url",
  },
};

const fetchImpl = async (url, options) => {
  const body = JSON.parse(options.body);

  if (
    url !==
    "http://127.0.0.1:8080" +
    "/api/local-node/aion/" +
    "small-business/website-scan"
  ) {
    throw new Error("Unexpected route: " + url);
  }

  if (
    body.website !==
    "https://www.example.test"
  ) {
    throw new Error(
      "Website was not normalised: " +
      body.website
    );
  }

  return {
    ok: true,
    status: 200,
    async json() {
      return {
        ok: true,
        provider: "openai",
        model: "test-model",
        source_facts: [
          "Public website evidence",
        ],
        evidence: {
          domain: "www.example.test",
        },
        extracted_fields: {
          business_name:
            "Scanner Suggested Name",
          business_type:
            "services",
          products_services:
            "Publicly listed services",
          target_customers:
            "Public website customers",
          revenue_streams:
            "Service fees",
          service_area:
            "Public service area",
          current_tools:
            "Website",
          current_pain_points:
            "No public pain points",
          growth_goals:
            "Public growth statement",
        },
      };
    },
  };
};

scanner.scanAndMerge(
  packet,
  {
    apiBase:
      "http://127.0.0.1:8080",
    fetchImpl,
    buildPacket:
      (state) => ({ ...state }),
  }
).then((result) => {
  const checks = {
    founder_name_preserved:
      result.foundation_draft.business_name ===
      "Founder Confirmed Name",

    website_normalised:
      result.foundation_draft.website_url ===
      "https://www.example.test",

    offer_filled:
      result.foundation_draft.offer_summary ===
      "Publicly listed services",

    customer_filled:
      result.foundation_draft.customer_type ===
      "Public website customers",

    scan_success:
      result.website_scan_receipt.status ===
      "success",

    evidence_attached:
      result.business_map.website_evidence
        .domain ===
      "www.example.test",

    facts_attached:
      result.business_map.facts.length > 0,

    no_overwrite:
      result.website_scan_receipt
        .user_answers_overwritten === false,
  };

  console.log(JSON.stringify(checks));

  if (
    !Object.values(checks).every(Boolean)
  ) {
    process.exit(1);
  }
}).catch((error) => {
  console.error(error);
  process.exit(1);
});
'''

    completed = subprocess.run(
        [
            "node",
            "-e",
            script,
        ],
        cwd=Path.cwd(),
        capture_output=True,
        text=True,
        check=False,
    )

    assert (
        completed.returncode == 0
    ), (
        completed.stdout +
        "\n" +
        completed.stderr
    )

    output = json.loads(
        completed.stdout.strip()
    )

    assert all(output.values())
