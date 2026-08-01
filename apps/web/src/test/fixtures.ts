/**
 * The values the API actually emits for the demo Civic.
 *
 * TypeScript checks the shape of a mock and never its values, so a fixture that repeats an
 * API literal keeps compiling long after the API stopped emitting it. Every test spells
 * these once, from here, and `api-contract.test.ts` pins them to the API's own rule pack.
 */
export const CIVIC_VEHICLE_ID = "honda-civic-2019-lx";

export const CIVIC_CITATIONS = {
  rule_version: "honda-civic-2019-lx-us-v1",
  citation_page: 1,
  citation_section: "Maintenance Minder Service Codes",
} as const;
