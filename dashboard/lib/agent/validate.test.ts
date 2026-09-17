/**
 * Canvas validation, checked against the real provider manifests in /providers.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { beforeAll, describe, expect, it } from "vitest";

import { validateAgent } from "@/lib/agent/validate";
import { loadProviders, type Provider } from "@/lib/providers";
import type { AgentConfig } from "@/lib/schema/agent.gen";

const EXAMPLE = path.join(__dirname, "..", "..", "..", "examples", "basic.json");

let providers: Provider[];

beforeAll(async () => {
  providers = await loadProviders();
});

function example(): AgentConfig {
  return JSON.parse(readFileSync(EXAMPLE, "utf8")) as AgentConfig;
}

function messages(config: AgentConfig): string[] {
  return validateAgent(config, providers).map((issue) =>
    issue.nodeId ? `node "${issue.nodeId}": ${issue.message}` : `config: ${issue.message}`,
  );
}

describe("validateAgent", () => {
  it("accepts the shipped example", () => {
    expect(messages(example())).toEqual([]);
  });

  it("flags a node nothing is patched into, without calling it the last node", () => {
    const config = example();
    config.edges = [
      { source: "vad", target: "stt" },
      { source: "stt", target: "tts" },
    ];

    expect(messages(config)).toEqual(['node "llm": isn\'t patched into the pipeline']);
  });

  it("flags a chain that doesn't start and end with audio", () => {
    const config = example();
    config.nodes = config.nodes.filter((node) => node.type !== "vad") as AgentConfig["nodes"];
    config.edges = [
      { source: "llm", target: "tts" },
      { source: "tts", target: "stt" },
    ];

    expect(messages(config)).toEqual([
      'node "llm": is first in the pipeline, so it receives mic audio, but it takes text input',
      'node "stt": is last in the pipeline, so its output is played back, but it outputs text',
    ]);
  });

  it("reports an unknown provider with the installed ones", () => {
    const config = example();
    config.nodes[3].provider = "elevenlab";

    expect(messages(config)).toEqual([
      'node "tts": unknown tts provider "elevenlab" (available: cartesia, elevenlabs)',
    ]);
  });

  it("validates params against the provider's own schema", () => {
    const config = example();
    config.nodes[1].params = { smart_format: "yes", api_key: "sk-..." };

    expect(messages(config)).toEqual([
      'node "stt": params: unknown field "api_key"',
      'node "stt": params.smart_format: must be boolean',
    ]);
  });

  it("requires a system prompt on llm nodes", () => {
    const config = example();
    const llm = config.nodes[2];
    if (llm.type === "llm") llm.system_prompt = "";

    expect(messages(config)).toEqual([
      'node "llm": system_prompt must NOT have fewer than 1 characters',
    ]);
  });

  it("wants one node of each stage", () => {
    const config = example();
    config.nodes = config.nodes.filter((node) => node.type !== "tts") as AgentConfig["nodes"];
    config.edges = config.edges.filter((edge) => edge.target !== "tts");

    expect(messages(config)).toContain("config: the pipeline needs a tts node");
  });
});
