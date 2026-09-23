# Open Public API Acquisition

Promoted procedure:
`procedure_open_public_api_acquisition_80b9a41d73c6`.

AION read current official documentation for GitHub repositories, the PyPI JSON
API and Open-Meteo forecasts. It recovered the documented route from each
source, constructed a read-only GET adapter, inferred a bounded typed schema
from the first live response and transferred the adapter to an unseen target.

| Measure | Result |
|---|---:|
| Official documentation sources | 3 |
| Independent public API authorities | 3 |
| Documented routes discovered | 3/3 |
| Typed adapters retained | 3 |
| Development and transfer calls | 6 |
| Successful calls | 6/6 |
| Source-disjoint transfers | 3/3 |
| Malformed-parameter rejection | Passed |
| Information-action reduction | 50% |
| Credentials used | No |
| Non-GET requests | 0 |
| Unsafe or paid actions | 0 |

The first challenger was rejected because an empty Open-Meteo request returned
a permissive response rather than proving parameter validation. The revised
counterexample supplied an invalid coordinate type; the remote authority
rejected it, demonstrating that the adapter's typed contract was falsifiable.

This is bounded, read-only acquisition across three preselected public
authorities. Documentation URLs, objectives, candidate authorities and the
safety policy remain engineered. It is not unrestricted browsing, credential
use, deployment, purchasing, independent certification or AGI.
