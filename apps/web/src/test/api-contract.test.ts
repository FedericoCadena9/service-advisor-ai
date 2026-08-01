import { readFileSync } from "node:fs";

import { expect, test } from "vitest";

import { CIVIC_CITATIONS, CIVIC_VEHICLE_ID } from "./fixtures";

/**
 * vitest runs from apps/web, and `import.meta.url` is not a file URL under its transform,
 * so the rule pack is reached by a path relative to the working directory.
 */
const RULE_PACK = "../api/src/service_advisor_api/knowledge.py";

/** The Honda block declares one configuration per model; the Civic is the first. */
function civicConfiguration(): string {
  const source = readFileSync(RULE_PACK, "utf8");
  const start = source.indexOf('"Honda", "Civic"');
  expect(start).toBeGreaterThan(-1);
  return source.slice(start, source.indexOf("_configuration(", start));
}

/** What if the API renamed the Civic rule instead of keeping the one the fixtures name? */
test("the Civic citation fixture matches the reviewed rule the API serves", () => {
  const civic = civicConfiguration();

  expect(civic).toContain(`version="${CIVIC_CITATIONS.rule_version}"`);
  expect(civic).toContain(`citation_page=${CIVIC_CITATIONS.citation_page}`);
  expect(civic).toContain(
    `citation_section="${CIVIC_CITATIONS.citation_section}"`,
  );
});

/** What if the demo vehicle were renamed instead of staying the one every route uses? */
test("the demo vehicle id is the one the API routes are exercised with", () => {
  const apiTest = readFileSync("../api/tests/test_quote_review_api.py", "utf8");

  expect(apiTest).toContain(`/vehicles/${CIVIC_VEHICLE_ID}/quote-reviews`);
});
