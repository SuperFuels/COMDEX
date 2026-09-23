'use strict';

/*
 * AION O25AU — Business Twin Orchestrator
 * ---------------------------------------
 *
 * Purpose:
 * - Own progression from Business Foundation into department discovery.
 * - Preserve the Business Twin progression manifest.
 * - Coordinate Finance-first activation without owning desktop rendering.
 * - Keep department lifecycle orchestration outside app.js.
 *
 * This module does not:
 * - render the desktop interface;
 * - ask Business Foundation questions;
 * - contain Finance discovery logic;
 * - enable live automation;
 * - perform external actions.
 */

(function installAionBusinessTwinOrchestrator(root, factory) {
  const api = factory(root);

  if (root && typeof root === "object") {
    root.AionBusinessTwinOrchestrator = api;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(
  typeof window !== "undefined" ? window : globalThis,
  function createAionBusinessTwinOrchestrator(root) {
    const VERSION =
      "aion.o25au.business_twin_orchestrator.v0.1";

    const MANIFEST_STORAGE_KEY =
      "aion.businessTwin.progressionManifest.v1";

    const DEPARTMENT_SEQUENCE = Object.freeze([
      "finance",
      "operations",
      "sales",
      "marketing",
      "support",
      "boardroom",
    ]);

    function clean(value) {
      return String(value || "").trim();
    }

    function clone(value) {
      if (!value || typeof value !== "object") {
        return value;
      }

      try {
        return JSON.parse(JSON.stringify(value));
      } catch {
        return value;
      }
    }

    function recogniseFoundationHandoff(packet = {}) {
      const nextQuestion =
        packet?.next_question &&
        typeof packet.next_question === "object"
          ? packet.next_question
          : {};

      return (
        clean(packet?.status) ===
          "foundation_ready_for_finance_handoff" ||
        clean(nextQuestion.reason) ===
          "finance_handoff_ready" ||
        clean(nextQuestion.action) ===
          "route_finance_live_agent"
      );
    }

    function createDepartmentState(
      department,
      status = "locked"
    ) {
      return {
        department,
        pilot:
          department === "boardroom"
            ? "ai_boardroom"
            : `${department}_pilot`,
        status,
        started_at: null,
        completed_at: null,
        evidence_refs: [],
        artifact_refs: [],
        handoff_receipt: null,
      };
    }

    function createProgressionManifest(packet = {}) {
      const now = new Date().toISOString();

      const departments = {};

      DEPARTMENT_SEQUENCE.forEach((department) => {
        departments[department] = createDepartmentState(
          department,
          department === "finance"
            ? "ready_to_activate"
            : "locked"
        );
      });

      return {
        version: VERSION,
        manifest_version:
          "aion.business_twin.progression_manifest.v0.1",
        status: "foundation_complete",
        created_at: now,
        updated_at: now,

        foundation: {
          status: clean(packet?.status) || null,
          completed: true,
          completed_at: now,
          packet_version:
            clean(
              packet?.schema_version ||
              packet?.version
            ) || null,
          readiness_score:
            Number(
              packet?.readiness?.readiness_score || 0
            ),
          foundation_draft:
            clone(packet?.foundation_draft || {}),
          transcript_count:
            Number(packet?.transcript_count || 0),
        },

        progression: {
          strategy: "finance_first",
          sequence: [...DEPARTMENT_SEQUENCE],
          current_department: "finance",
          current_pilot: "finance_pilot",
          next_department: "finance",
          completed_departments: [],
          unlocked_departments: ["finance"],
        },

        departments,

        governance: {
          preview_only: true,
          human_review_required: true,
          live_automation_enabled: false,
          external_actions_allowed: false,
          autonomous_department_transition: false,
        },

        provenance: {
          source:
            "business_foundation_voice_discovery",
          source_packet_status:
            clean(packet?.status) || null,
          source_reason:
            clean(packet?.next_question?.reason) ||
            null,
          source_action:
            clean(packet?.next_question?.action) ||
            null,
        },
      };
    }

    function persistProgressionManifest(manifest) {
      const safeManifest = clone(manifest);

      if (root && typeof root === "object") {
        root.__aionBusinessTwinProgressionManifest =
          safeManifest;
      }

      try {
        root?.localStorage?.setItem(
          MANIFEST_STORAGE_KEY,
          JSON.stringify(safeManifest)
        );
      } catch {}

      return safeManifest;
    }

    function getProgressionManifest() {
      if (
        root?.__aionBusinessTwinProgressionManifest &&
        typeof root
          .__aionBusinessTwinProgressionManifest ===
          "object"
      ) {
        return clone(
          root.__aionBusinessTwinProgressionManifest
        );
      }

      try {
        const raw =
          root?.localStorage?.getItem(
            MANIFEST_STORAGE_KEY
          );

        if (raw) {
          return JSON.parse(raw);
        }
      } catch {}

      return null;
    }

    function prepareFinanceHandoff(packet = {}) {
      if (!recogniseFoundationHandoff(packet)) {
        return {
          ok: false,
          reason:
            "packet_not_ready_for_finance_handoff",
          manifest: null,
        };
      }

      const manifest =
        createProgressionManifest(packet);

      manifest.status =
        "finance_handoff_prepared";

      manifest.departments.finance.status =
        "handoff_prepared";

      manifest.departments.finance.handoff_receipt = {
        version:
          "aion.business_twin.finance_handoff_receipt.v0.1",
        prepared_at: new Date().toISOString(),
        source: "business_foundation",
        target_tab: "live_agents",
        target_department: "finance",
        target_pilot: "finance_pilot",
        preview_only: true,
      };

      manifest.updated_at =
        new Date().toISOString();

      persistProgressionManifest(manifest);

      if (root && typeof root === "object") {
        root.__aionBusinessFoundationCompletedPacket =
          packet;

        root.__aionBusinessFoundationFinanceHandoff = {
          completed_at: new Date().toISOString(),
          target_tab: "live_agents",
          target_department: "finance",
          target_pilot: "finance_pilot",
          packet_status: packet?.status || null,
          manifest_version:
            manifest.manifest_version,
          preview_only: true,
          live_automation_enabled: false,
        };
      }

      try {
        root?.localStorage?.setItem(
          "aion.businessTwin.financeFirstRouted.v1",
          "false"
        );
      } catch {}

      return {
        ok: true,
        reason: "finance_handoff_prepared",
        manifest,
      };
    }

    function activateFinancePilot(
      packet = {},
      adapters = {}
    ) {
      const prepared =
        prepareFinanceHandoff(packet);

      if (!prepared.ok) {
        return false;
      }

      const adapter =
        typeof adapters.activateFinancePilot ===
        "function"
          ? adapters.activateFinancePilot
          : null;

      if (!adapter) {
        prepared.manifest.status =
          "finance_route_adapter_missing";

        prepared.manifest.updated_at =
          new Date().toISOString();

        persistProgressionManifest(
          prepared.manifest
        );

        return false;
      }

      let routed = false;

      try {
        routed =
          adapter({
            packet,
            manifest: clone(prepared.manifest),
            target_tab: "live_agents",
            target_department: "finance",
            target_pilot: "finance_pilot",
          }) !== false;
      } catch (error) {
        prepared.manifest.status =
          "finance_route_failed";

        prepared.manifest.route_error =
          String(
            error && error.message
              ? error.message
              : error
          );

        prepared.manifest.updated_at =
          new Date().toISOString();

        persistProgressionManifest(
          prepared.manifest
        );

        return false;
      }

      prepared.manifest.status = routed
        ? "finance_pilot_active"
        : "finance_route_failed";

      prepared.manifest.departments.finance.status =
        routed ? "active" : "route_failed";

      prepared.manifest.departments.finance.started_at =
        routed
          ? new Date().toISOString()
          : null;

      prepared.manifest.updated_at =
        new Date().toISOString();

      persistProgressionManifest(
        prepared.manifest
      );

      return routed;
    }

    function handleFoundationPacket(
      packet = {},
      adapters = {}
    ) {
      if (!recogniseFoundationHandoff(packet)) {
        return false;
      }

      return activateFinancePilot(
        packet,
        adapters
      );
    }

    function getCurrentDepartment() {
      return (
        getProgressionManifest()
          ?.progression
          ?.current_department || null
      );
    }

    function getDepartmentSequence() {
      return [...DEPARTMENT_SEQUENCE];
    }

    function completeFinancePilot(receipt = {}) {
      const manifest = getProgressionManifest();
      if (!manifest) return { ok: false, reason: "progression_manifest_missing" };
      const now = new Date().toISOString();
      manifest.status = "finance_complete_operations_unlocked";
      manifest.departments.finance.status = "complete";
      manifest.departments.finance.completed_at = now;
      manifest.departments.finance.completion_receipt = clone(receipt);
      manifest.departments.operations.status = "ready_to_activate";
      manifest.progression.completed_departments = Array.from(new Set([...(manifest.progression.completed_departments || []), "finance"]));
      manifest.progression.unlocked_departments = Array.from(new Set([...(manifest.progression.unlocked_departments || []), "operations"]));
      manifest.progression.current_department = "finance";
      manifest.progression.current_pilot = "finance_pilot";
      manifest.progression.next_department = "operations";
      manifest.updated_at = now;
      persistProgressionManifest(manifest);
      root?.dispatchEvent?.(new CustomEvent("aion:business-twin-progression-changed", { detail: clone(manifest) }));
      return { ok: true, manifest };
    }

    const api = Object.freeze({
      VERSION,
      MANIFEST_STORAGE_KEY,
      DEPARTMENT_SEQUENCE,
      recogniseFoundationHandoff,
      createProgressionManifest,
      getProgressionManifest,
      persistProgressionManifest,
      prepareFinanceHandoff,
      activateFinancePilot,
      handleFoundationPacket,
      getCurrentDepartment,
      getDepartmentSequence,
      completeFinancePilot,
    });

    if (root && typeof root === "object") {
      root.__debugAionBusinessTwinOrchestrator =
        function debugAionBusinessTwinOrchestrator() {
          return {
            installed: true,
            version: VERSION,
            current_department:
              getCurrentDepartment(),
            department_sequence:
              getDepartmentSequence(),
            manifest:
              getProgressionManifest(),
          };
        };
    }

    return api;
  }
);
