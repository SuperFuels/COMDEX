# Dependency assurance register — 18 October 2026

## Release position

This register records local evidence and proposed remediation work. It is not an external security review and does not approve any exception. General release remains fail closed until the open items are migrated or a named security authority accepts a time-bounded exception.

## Reproducible evidence

| Surface | Evidence | Result |
|---|---|---|
| Python environment | `.venv/bin/python -m pip check` | No broken requirements |
| Python installed-package inventory | `backend-python-pip-inspect-2026-10-18.json` | 191 installed distributions; SHA-256 `397a533ac6cf058db43fa996b54b687e9f041c0bc37328bd5c75ecbaaa3919fe` |
| macOS Electron production dependencies | `npm audit --omit=dev` | 0 known vulnerabilities |
| Frontend production dependencies, before remediation | `npm audit --omit=dev` | 49 total: 2 critical, 29 high, 5 moderate, 13 low |
| Frontend production dependencies, after controlled migrations | `npm audit --omit=dev` | 0 known vulnerabilities |
| Frontend build | `npm run build` | Optimized production build passed |
| Smart-contract toolchain | Hardhat compile, test, simulated deployment and `npm audit` | 2 Solidity contracts compile; simulated GLU and escrow deployment passed; 0 known vulnerabilities |
| Frontend CycloneDX 1.5 SBOM | `frontend-cyclonedx-2026-10-18.json` | 1,077 components; SHA-256 `7c5ff88423e89aba81fbf277b73709372f75b46c8529af87a38df03e9f6cda09` |
| Smart-contract CycloneDX 1.5 SBOM | `smart-contracts-cyclonedx-2026-10-18.json` | 66 components; SHA-256 `1963b1d14f7e6f652d4012ee1f2922194cf09e50bb09245b8d0ede4121bd2ba1` |
| macOS Electron CycloneDX 1.5 SBOM | `desktop-mac-cyclonedx-2026-10-18.json` | 269 components; SHA-256 `fb9da7d3e3aef21ec845a3e32a4d26da5db61d526d3a3eb46ee350755621614f` |

The SBOM digests are evidence for this working tree only. Release builds must regenerate and sign SBOMs from the reviewed release commit.

## Remediation completed

- Removed unused `@react-pdf-viewer/core` and `@react-pdf-viewer/default-layout` dependencies, eliminating their unpatched PDF.js chain.
- Upgraded `jspdf` to 4.2.1, eliminating both critical findings.
- Migrated the styling pipeline from Tailwind CSS 3 to 4.3.3, enabled the forms and typography plugins explicitly, rebuilt all 67 routes and visually checked the pricing and AION Business surfaces.
- Migrated the application wallet/signing boundary from Ethers 5 to 6.17.0, including BrowserProvider, async signer, bigint and transaction-receipt handling. Removed unused `@web3-react`, `web3` and OpenAI client packages rather than carrying dormant runtime surface.
- Upgraded the compatible 3D set to Three.js 0.159.0 and Drei 9.122.0, removing the vulnerable UUID chain. The optimized build and dependency-tree validation pass.
- Migrated the isolated contract toolchain from Hardhat 2/Ethers 5 to Hardhat 3.20.0/Ethers 6.17.0 and OpenZeppelin 5.4.0. Compilation, an empty test harness and an actual simulated GLU/escrow deployment pass; its full audit reports zero findings.
- Constrained `source-map-js` to patched 1.2.2.
- Installed the correct YAML 2 dependency for PostCSS while retaining the nested YAML 1 dependency required by the older configuration loader. This makes the dependency graph valid for SBOM generation.
- Upgraded KaTeX to 0.19.0 and constrained `rehype-katex` to the same patched runtime. The configured Tessaris macros render successfully and the complete optimized build passes.
- Constrained the Tailwind typography plugin's build-time selector parser to patched 7.1.6. Its nested-selector compatibility check and the full Tailwind/Next.js production build pass.

## Closed migration decisions

| ID | Resolution | Evidence |
|---|---|---|
| DEP-001 | Tailwind CSS 4.3.3 migration completed | Optimized build of 67 routes passed; pricing and AION Business surfaces visually checked |
| DEP-002 | Application and isolated contract toolchain migrated to Ethers 6.17.0 | Frontend build passed; Hardhat compile and simulated deployment passed |
| DEP-003 | Three.js/Drei stack migrated to Three.js 0.159.0 and Drei 9.122.0 | Dependency tree valid and optimized build passed |
| DEP-004 | KaTeX migrated to 0.19.0, including the `rehype-katex` runtime boundary | Configured macro render check and optimized 67-route build passed |
| DEP-005 | Typography selector parser constrained to patched 7.1.6 | Nested typography selector parse check and optimized Tailwind/Next.js build passed |

## Open migration decisions

None in the current production dependency audit. New findings, lock-file changes or upstream advisories reopen this gate automatically.

## Exception requirements

Any exception must state the exact package/range, reachable product surface, exploit preconditions, compensating controls, owner, approval date, expiry date and planned migration. Exceptions must never be inferred from a passing build. Critical findings are not eligible for release exceptions under this programme.

## External work still required

- Independent software-supply-chain review of the release build and all SBOMs.
- Signed provenance tying source revision, lock files, builder identity, artifacts and SBOM digests together.
- Malware and artifact scanning on immutable platform packages.
- Review of install scripts before allowlisting any native dependency lifecycle script.
- Dependency-update and revocation runbooks, including an emergency rebuild path.
