import { readdirSync, readFileSync } from "node:fs";

import { expect, test } from "vitest";

import { requestFailed } from "./failure";

/**
 * The E2E found a 409 mid-journey rendered as nothing at all: the client threw a bare Error,
 * so the panel could not tell "the server refused this" from "the network is gone".
 */
test("a refusal carries the status the caller has to act on", () => {
  const failure = requestFailed("Quote review unavailable", { response: { status: 409 } });

  expect(failure.message).toBe("Quote review unavailable");
  expect((failure as { status?: number }).status).toBe(409);
});

test("a network error carries no status, which is how an outage is recognised", () => {
  expect((requestFailed("unreachable", {}) as { status?: number }).status).toBeUndefined();
});

test("every API client fails through the shared contract", () => {
  const directory = "src/api/";
  const clients = readdirSync(directory).filter(
    (file) =>
      file.endsWith(".ts") &&
      !file.endsWith(".test.ts") &&
      !["failure.ts", "advisor-context.ts"].includes(file),
  );
  const offenders = clients.filter((file) => {
    const source = readFileSync(`${directory}${file}`, "utf8");
    return source.includes("throw new Error(");
  });

  expect(clients.length).toBeGreaterThan(8);
  expect(offenders).toEqual([]);
});
