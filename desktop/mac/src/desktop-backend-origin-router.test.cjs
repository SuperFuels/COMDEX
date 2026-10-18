const assert = require("node:assert/strict");
const test = require("node:test");

const {
  normalizeLoopbackBase,
  rewriteLegacyLoopbackUrl,
} = require("./desktop-backend-origin-router");

test("normalizes only bounded loopback desktop origins", () => {
  assert.equal(normalizeLoopbackBase("http://127.0.0.1:8180/"), "http://127.0.0.1:8180");
  assert.equal(normalizeLoopbackBase("http://localhost:8180"), "http://localhost:8180");
  assert.equal(normalizeLoopbackBase("https://example.com"), "");
  assert.equal(normalizeLoopbackBase("http://0.0.0.0:8180"), "");
  assert.equal(normalizeLoopbackBase("http://127.0.0.1:99999"), "");
});

test("rewrites legacy renderer calls while preserving path, query and hash", () => {
  assert.equal(
    rewriteLegacyLoopbackUrl(
      "http://127.0.0.1:8080/api/aion/test?q=1#result",
      "http://127.0.0.1:8180",
    ),
    "http://127.0.0.1:8180/api/aion/test?q=1#result",
  );
  assert.equal(
    rewriteLegacyLoopbackUrl(
      "http://localhost:8080/health",
      "http://127.0.0.1:8180",
    ),
    "http://127.0.0.1:8180/health",
  );
});

test("does not reroute providers, arbitrary ports or relative URLs", () => {
  for (const value of [
    "https://api.stripe.com/v1/test",
    "http://127.0.0.1:8765/health",
    "/api/aion/test",
  ]) {
    assert.equal(rewriteLegacyLoopbackUrl(value, "http://127.0.0.1:8180"), value);
  }
});
