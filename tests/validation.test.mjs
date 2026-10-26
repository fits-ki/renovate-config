import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

const validator = process.env.RENOVATE_VALIDATOR;
assert.ok(validator, "Run inside the pinned Renovate npm exec environment");
const check = fileURLToPath(new URL("../scripts/validate-preset.mjs", import.meta.url));
const baseline = JSON.parse(
  readFileSync(new URL("../default.json", import.meta.url), "utf8"),
);

function validate(config) {
  const directory = mkdtempSync(join(tmpdir(), "renovate-preset-test-"));
  const file = join(directory, "default.json");
  try {
    writeFileSync(file, typeof config === "string" ? config : JSON.stringify(config));
    const result = spawnSync(process.execPath, [check, validator, file], {
      encoding: "utf8",
      timeout: 60_000,
    });
    assert.ifError(result.error);
    assert.equal(result.signal, null, result.stderr);
    return result;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

test("the real baseline and its recursive built-in presets are valid", () => {
  const result = validate(baseline);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  assert.match(result.stdout, /Resolved repository preset is valid/);
});

test("global-only options cannot hide in the repository preset", () => {
  const result = validate({ ...baseline, allowedCommands: ["echo"] });
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stdout + result.stderr, /global option/);
});

test("an additional missing preset fails even with all original extends retained", () => {
  const missing = "config:reviewProbeDefinitelyMissingPreset";
  const result = validate({
    ...baseline,
    extends: [...baseline.extends, missing],
  });
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stdout + result.stderr, /reviewProbeDefinitelyMissingPreset/);
});

test("a valid inherited preset must not re-enable automerge", () => {
  const result = validate({
    ...baseline,
    extends: [...baseline.extends, ":automergeMinor"],
  });
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, /automerge must remain false after preset resolution/);
});

test("invalid JSON fails closed", () => {
  const result = validate("{invalid");
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, /Preset validation failed/);
});

test("a non-object preset fails closed", () => {
  const result = validate("[]");
  assert.equal(result.status, 1, result.stdout + result.stderr);
  assert.match(result.stderr, /preset must be a JSON object/);
});
