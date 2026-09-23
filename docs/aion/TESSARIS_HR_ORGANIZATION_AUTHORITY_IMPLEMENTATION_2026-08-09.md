# Tessaris HR Pilot: Organisation and Authority Foundation

**Implemented:** 9 August 2026  
**Status:** Operational local v1  
**Purpose:** Establish who acts for a business, what they may see, what they may do, and who must approve it.

## Product decision

Tessaris does not attempt to become a payroll, leave, recruitment or performance-management platform in this phase. The HR Pilot now owns the small canonical layer required by every other department:

- people and their business relationship;
- reporting lines;
- departments and teams;
- application roles separated from job titles;
- capability and data scope;
- expense approval limits;
- assigned company cards and accountable assets;
- viewer-specific Boardroom and Finance projections; and
- immutable organisation-authority audit events.

The model supports a founder with no documentation. The empty-state workflow offers **Add me as owner**, **New employee**, and **New self-employed person** without requiring an HR integration or pre-existing organisation chart.

## Canonical model

The `organization_authority` business container contains:

| Collection | Purpose |
|---|---|
| `people` | Identity, employment relationship, position, status, manager, departments, roles, location, cost centre and projects. |
| `departments` | Hierarchical teams/functions and accountable leads. |
| `roles` | Tessaris capabilities, data scope and approval limits. |
| `authority_policies` | Additional business-specific authority rules. |
| `assets` | Company cards, vehicles, tools, devices and financial accounts assigned to responsible people. |
| `external_sources` | Future Google, Microsoft or HRIS source references. |
| `governance` | Deny-by-default, least-privilege and sensitive-data exclusions. |

Sensitive payroll, medical and performance data are deliberately excluded.

## Included role templates

1. Owner / Director
2. Finance Controller
3. Department Manager
4. Employee
5. Self-employed / Contractor
6. External Accountant

Roles grant capabilities; job titles do not. People may hold multiple roles.

## Access decisions

Every authority decision can consider:

```text
authenticated person
  + assigned role capabilities
  + business or department scope
  + subject person, when applicable
  + transaction amount
  = allowed or denied with reason
```

The current API can answer individual capability checks and generate a bounded viewer projection. An employee receives only their own expense class by default. A department manager receives assigned-department scope and a bounded approval limit. An owner/director receives the complete Boardroom and detailed Finance projection.

## Boardroom and Finance projection

Saving the organisation model projects a non-sensitive summary into:

- `business_structure.json` for human agents and teams;
- `department_intelligence.json` for HR status and Boardroom summary; and
- `boardroom_snapshot.json` for the current organisation-authority revision and viewer policy.

The Finance security policy now declares `organization_authority.v1` as its authority source and requires a viewer projection. This is the contract the future Finance Inbox will use for receipt ownership, card responsibility, expense visibility and approval.

## API surface

```text
GET  /api/aion/business/organisation/templates
GET  /api/aion/business/organisation/{workspace_id}
PUT  /api/aion/business/organisation/{workspace_id}
POST /api/aion/business/organisation/{workspace_id}/access-decision
GET  /api/aion/business/organisation/{workspace_id}/viewer-projection/{person_id}
```

Writes use optimistic revision checks so stale editors cannot silently overwrite newer organisation data. Reporting-line cycles are rejected.

## HR Pilot user experience

The working HR Pilot contains five views:

1. **People** — add, edit and deactivate owners, employees, self-employed people, contractors, freelancers and external advisers.
2. **Organisation chart** — reporting lines plus optional standard departments.
3. **Roles & permissions** — plain-English role capabilities and approval limits.
4. **Cards & assets** — responsibility, last four card digits and spending limits; full card data is never stored.
5. **Access check** — explain whether a selected person may perform a selected action.

The UI is a lightweight white workspace aligned with Products & Services and the refreshed Finance design.

## Key implementation files

- `backend/modules/aion_business/contracts/business_containers.py`
- `backend/modules/aion_business/runtime/business_container_repository.py`
- `backend/modules/aion_business/runtime/organization_authority_service.py`
- `backend/modules/aion_business/api/organization_authority_api.py`
- `backend/modules/aion_business/runtime/finance_security_policy.py`
- `backend/modules/aion_business/runtime/department_pilot_profiles.py`
- `backend/desktop_app.py`
- `backend/main.py`
- `desktop/mac/src/aion_hr_people_workspace.js`
- `desktop/mac/src/index.html`
- `backend/tests/test_organization_authority_service.py`
- `backend/tests/test_organization_authority_api.py`

## Verification

- Python compilation passed.
- JavaScript syntax validation passed.
- 24 focused HR, API and Department Pilot tests passed.
- 90 combined Finance, operating-model, HR and Department Pilot tests passed.
- Browser QA passed for blank-state rendering, owner setup, self-employed defaults, role display, standard departments, persistence and authority decisions.
- Packaged desktop health endpoint returned `status=ok`.
- Installed backend exposed all organisation endpoints.
- Packaged renderer remained at low CPU after installation.

## Installation and recovery

The updated application is installed at:

```text
/Applications/Tessaris.app
```

The previous recoverable build is retained at:

```text
/Applications/Tessaris.app.backup-20260809-before-hr-authority
```

## Honest boundary

The authority model and viewer-projection contract are operational. Tessaris remains a single-user local desktop application today, so real multi-user enforcement still requires authenticated person identity. Google Workspace, Microsoft 365 and HRIS connectors are not yet implemented. They should populate this canonical model rather than replace it.

## Finance Inbox integration completed

The Finance Inbox vertical slice now uses this model to:

1. identify the receipt submitter;
2. identify their card and department/project;
3. extract and match the receipt;
4. evaluate their submission and approval authority;
5. route exceptions to the correct manager or Finance role;
6. create an exact provider-neutral accounting instruction after approval; and
7. refresh Finance and Boardroom projections.

Desktop document upload is operational. Phone capture, the mobile share sheet and the Finance Agent mailbox remain future intake adapters to the same canonical Inbox contract. Automated image/PDF extraction and provider-specific accounting writes also remain separately governed future work.
