import { spawnSync } from "node:child_process";
import { readFileSync, realpathSync } from "node:fs";
import { dirname, join } from "node:path";
import { pathToFileURL } from "node:url";

function requireManualMerges(config) {
  if (config === null || typeof config !== "object") return;
  for (const [key, value] of Object.entries(config)) {
    if ((key === "automerge" || key === "platformAutomerge") && value !== false) {
      throw new Error(`${key} must remain false after preset resolution`);
    }
    requireManualMerges(value);
  }
}

try {
  const [executable, file] = process.argv.slice(2);
  if (!executable || !file || process.argv.length !== 4) {
    throw new Error("Usage: node scripts/validate-preset.mjs <validator-executable> <config-file>");
  }
  const validator = realpathSync(executable);
  const raw = JSON.parse(readFileSync(file, "utf8"));
  if (raw === null || Array.isArray(raw) || typeof raw !== "object") {
    throw new Error("The preset must be a JSON object");
  }

  const result = spawnSync(
    process.execPath,
    [validator, "--strict", "--no-global", file],
    { stdio: "inherit", timeout: 60_000 },
  );
  if (result.error) throw result.error;
  if (result.status !== 0) {
    throw new Error("Strict repository configuration validation failed");
  }

  // Use the resolver from the same pinned npm package, not another installation.
  const load = (file) => import(pathToFileURL(join(dirname(validator), file)).href);
  const [{ init }, { resolveConfigPresets }, { massageConfig }, { validateConfig }] =
    await Promise.all([
      load("logger/index.js"),
      load("config/presets/index.js"),
      load("config/massage.js"),
      load("config/validation.js"),
    ]);
  await init();
  const { config } = await resolveConfigPresets(massageConfig(raw));
  const { errors, warnings } = await validateConfig("repo", config);
  if (errors.length || warnings.length) {
    throw new Error(
      [...errors, ...warnings].map(({ message }) => message).join("\n"),
    );
  }
  requireManualMerges(config);
  console.log("Resolved repository preset is valid; automerge remains disabled");
} catch (error) {
  console.error(`Preset validation failed: ${error.validationError ?? error.message}`);
  process.exitCode = 1;
}
