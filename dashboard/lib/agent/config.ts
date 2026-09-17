/**
 * Reading and writing agent configs.
 *
 * `serializeConfig` is the canvas's export format: field order follows the schema and
 * the file is 2-space JSON, so a canvas export and a hand-written config are the same
 * bytes for the same agent.
 */
import type { AgentConfig, Edge, Node } from "@/lib/schema/agent.gen";

export const SCHEMA_REF = "../schema/agent.v1.schema.json";

export function serializeConfig(config: AgentConfig): string {
  const ordered: AgentConfig = {
    ...(config.$schema ? { $schema: config.$schema } : {}),
    schema_version: 1,
    name: config.name,
    ...(config.description ? { description: config.description } : {}),
    nodes: config.nodes.map(orderNode) as AgentConfig["nodes"],
    edges: config.edges.map(({ source, target }) => ({ source, target })),
  };
  return JSON.stringify(ordered, null, 2) + "\n";
}

function orderNode(node: Node): Node {
  return {
    id: node.id,
    type: node.type,
    provider: node.provider,
    ...(node.label ? { label: node.label } : {}),
    ...(node.type === "llm" ? { system_prompt: node.system_prompt } : {}),
    params: node.params ?? {},
  } as Node;
}

export function emptyConfig(name = "Untitled agent"): AgentConfig {
  return { $schema: SCHEMA_REF, schema_version: 1, name, nodes: [] as unknown as AgentConfig["nodes"], edges: [] };
}

/** A node id that doesn't clash with the ones already on the canvas. */
export function nextNodeId(type: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  if (!used.has(type)) return type;
  for (let i = 2; ; i++) {
    const candidate = `${type}${i}`;
    if (!used.has(candidate)) return candidate;
  }
}

export type { AgentConfig, Edge, Node };
