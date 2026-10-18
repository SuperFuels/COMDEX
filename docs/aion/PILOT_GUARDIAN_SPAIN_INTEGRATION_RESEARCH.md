# Pilot Guardian — Spain / EU Emergency Integration Research

Status: 31 August 2026. This is an engineering boundary record, not legal or
clinical approval.

## Confirmed public position

- 112 is the free European emergency number and connects fixed or mobile callers
  to police, ambulance or fire services throughout the EU.
- Spain's 112 operation is organized through autonomous-community services. The
  national Civil Protection directory points to the corresponding regional 112
  authority.
- EU rules are moving public-safety answering points toward IP voice, real-time
  text and video, and call for common interoperability requirements for emergency
  communication applications. That policy direction is not a public third-party
  dispatch API.
- eCall is a separately regulated and qualified vehicle system. Its ability to
  call 112 and transmit a minimum set of crash/location data does not authorize a
  household assistant to represent itself as eCall.

## Product conclusion

No public, production-ready API was identified that authorizes an ordinary
household application in Almería to dispatch an ambulance or open a 112 incident.
Pilot Guardian must therefore stop at verified trusted-contact delivery and an
explicit authorized-phone call surface. It must display `ambulance_dispatched =
false` until a contractually authorized regional route returns a tested receipt.

Any future 112 integration requires direct engagement with the relevant Andalusian
112 authority, telecom and emergency-communications specialists, legal and
clinical reviewers, accessibility experts, a defined conformity route, end-to-end
PSAP testing, failure drills, and written authority to make dispatch claims.

## Primary references

- European Commission, 112 emergency number and emergency-app interoperability:
  https://digital-strategy.ec.europa.eu/en/policies/112
- European Commission, 2024 implementation report:
  https://digital-strategy.ec.europa.eu/es/library/2024-report-implementation-eu-emergency-number-112
- Your Europe, emergency number guidance:
  https://europa.eu/youreurope/citizens/travel/security-and-emergencies/emergency/indexamp_en.htm
- Spain, Directorate-General for Civil Protection and Emergencies, regional 112
  service directory: https://www.proteccioncivil.es/catalogo/info112/
- European Commission, interoperable EU-wide eCall:
  https://transport.ec.europa.eu/transport-themes/smart-mobility/road/its-directive-and-action-plan/interoperable-eu-wide-ecall_en
