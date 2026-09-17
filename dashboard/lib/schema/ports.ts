/**
 * Node types and port types, read from the agent schema rather than repeated here.
 *
 * The schema annotates each node definition with `x-ports`, so the canvas and the
 * Python compiler agree on which cables are legal.
 */
import agentSchema from "./agent.schema.json";
import type { Node } from "./agent.gen";

export type NodeType = Node["type"];
export type PortType = "audio" | "text";
export type Ports = { input: PortType; output: PortType };

type Definition = {
  properties: { type: { const: NodeType } };
  "x-ports": Ports;
};

const defs = agentSchema.$defs as unknown as Record<string, Definition> & {
  Node: { oneOf: { $ref: string }[] };
};

const definitions = defs.Node.oneOf.map(({ $ref }) => defs[$ref.split("/").pop()!]);

/** Node types in pipeline order: vad, stt, llm, tts. */
export const NODE_TYPES: NodeType[] = definitions.map((def) => def.properties.type.const);

export const PORTS: Record<NodeType, Ports> = Object.fromEntries(
  definitions.map((def) => [def.properties.type.const, def["x-ports"]]),
) as Record<NodeType, Ports>;

/** An output can only feed an input of the same type: audio to audio, text to text. */
export function canConnect(source: NodeType, target: NodeType): boolean {
  return PORTS[source].output === PORTS[target].input;
}
