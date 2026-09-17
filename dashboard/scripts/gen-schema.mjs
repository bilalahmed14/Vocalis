/**
 * Regenerate everything the dashboard derives from /schema.
 *
 * The JSON Schemas at the repo root are the single source of truth: this copies them
 * in (so they can be bundled for the browser) and generates TypeScript types from
 * them. Run `pnpm gen:schema` after changing a schema; CI checks the output is clean.
 */
import { execFileSync } from "node:child_process";
import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const schemaDir = join(here, "..", "..", "schema");
const outDir = join(here, "..", "lib", "schema");

mkdirSync(outDir, { recursive: true });

for (const [source, copy, types] of [
  ["agent.v1.schema.json", "agent.schema.json", "agent.gen.ts"],
  ["provider.v1.schema.json", "provider.schema.json", "provider.gen.ts"],
]) {
  copyFileSync(join(schemaDir, source), join(outDir, copy));
  execFileSync(
    "json2ts",
    ["-i", join(schemaDir, source), "-o", join(outDir, types), "--bannerComment", ""],
    { stdio: "inherit", preferLocal: true, shell: false, env: { ...process.env, PATH: `${join(here, "..", "node_modules", ".bin")}:${process.env.PATH}` } },
  );
}

console.log("schema: copied 2 files, generated 2 type files");
