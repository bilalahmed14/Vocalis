/**
 * Phase 2's contract: an agent edited on the canvas exports the same bytes as the
 * hand-written config it was loaded from.
 */
import { readFileSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

import { serializeConfig } from "@/lib/agent/config";
import { chainOrder, configToFlow, flowToConfig } from "@/lib/agent/flow";
import type { AgentConfig } from "@/lib/schema/agent.gen";

const EXAMPLE = path.join(__dirname, "..", "..", "..", "examples", "basic.json");

function loadExample(): { text: string; config: AgentConfig } {
  const text = readFileSync(EXAMPLE, "utf8");
  return { text, config: JSON.parse(text) as AgentConfig };
}

describe("canvas round trip", () => {
  it("exports a hand-written config unchanged", () => {
    const { text, config } = loadExample();
    const { nodes, edges } = configToFlow(config);

    const exported = flowToConfig(
      { $schema: config.$schema, name: config.name, description: config.description },
      nodes,
      edges,
    );

    expect(serializeConfig(exported)).toBe(text);
  });

  it("keeps pipeline order when the canvas holds nodes in another order", () => {
    const { text, config } = loadExample();
    const { nodes, edges } = configToFlow(config);

    const exported = flowToConfig(
      { $schema: config.$schema, name: config.name, description: config.description },
      [...nodes].reverse(),
      [...edges].reverse(),
    );

    expect(serializeConfig(exported)).toBe(text);
  });
});

describe("chainOrder", () => {
  it("follows the cables, not the node list", () => {
    const edges = [
      { source: "stt", target: "llm" },
      { source: "vad", target: "stt" },
      { source: "llm", target: "tts" },
    ];
    expect(chainOrder(["tts", "llm", "stt", "vad"], edges)).toEqual(["vad", "stt", "llm", "tts"]);
  });

  it("keeps nodes that aren't wired up yet", () => {
    const edges = [{ source: "stt", target: "llm" }];
    expect(chainOrder(["stt", "llm", "tts"], edges)).toEqual(["stt", "llm", "tts"]);
  });
});
