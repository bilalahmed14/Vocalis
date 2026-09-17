/**
 * Reading the provider plugins in /providers.
 *
 * Each plugin's manifest drives the palette and the node inspector form, so adding a
 * provider needs no dashboard change. Server-side only: it reads the filesystem.
 */
import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

import type { ProviderManifest } from "@/lib/schema/provider.gen";
import type { NodeType } from "@/lib/schema/ports";

export type Provider = ProviderManifest & { type: NodeType; icon: string | null };

function providersDir(): string {
  return process.env.VOCALIS_PROVIDERS_DIR ?? path.join(process.cwd(), "..", "providers");
}

export async function loadProviders(): Promise<Provider[]> {
  const root = providersDir();
  const providers: Provider[] = [];

  for (const type of await subdirectories(root)) {
    for (const id of await subdirectories(path.join(root, type))) {
      const folder = path.join(root, type, id);
      const manifest = JSON.parse(
        await readFile(path.join(folder, "provider.json"), "utf8"),
      ) as ProviderManifest;
      providers.push({
        ...manifest,
        type: manifest.type as NodeType,
        icon: await readFile(path.join(folder, "icon.svg"), "utf8").catch(() => null),
      });
    }
  }

  return providers.sort((a, b) => a.id.localeCompare(b.id));
}

async function subdirectories(at: string): Promise<string[]> {
  const entries = await readdir(at, { withFileTypes: true }).catch(() => []);
  return entries.filter((entry) => entry.isDirectory()).map((entry) => entry.name);
}
