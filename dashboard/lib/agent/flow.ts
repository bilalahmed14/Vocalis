/**
 * Converting between an agent config and the React Flow graph the canvas edits.
 *
 * The config stays the contract: the canvas holds exactly what a config holds, plus
 * node positions, which the config deliberately doesn't carry.
 */
import type { Edge as FlowEdge, Node as FlowNode } from "@xyflow/react";

import type { AgentConfig, Node } from "@/lib/schema/agent.gen";
import type { NodeType } from "@/lib/schema/ports";

export type NodeData = {
  type: NodeType;
  provider: string;
  label?: string;
  system_prompt?: string;
  params: Record<string, unknown>;
};

export type AgentNode = FlowNode<NodeData, "agentNode">;

const COLUMN_WIDTH = 260;
const ROW_HEIGHT = 150;

export function configToFlow(config: AgentConfig): { nodes: AgentNode[]; edges: FlowEdge[] } {
  const order = chainOrder(
    config.nodes.map((node) => node.id),
    config.edges,
  );

  const nodes: AgentNode[] = config.nodes.map((node) => ({
    id: node.id,
    type: "agentNode",
    position: {
      x: order.indexOf(node.id) * COLUMN_WIDTH,
      y: ROW_HEIGHT,
    },
    data: toData(node),
  }));

  const edges: FlowEdge[] = config.edges.map(({ source, target }) => ({
    id: edgeId(source, target),
    source,
    target,
  }));

  return { nodes, edges };
}

export function flowToConfig(
  meta: Pick<AgentConfig, "name" | "description" | "$schema">,
  nodes: AgentNode[],
  edges: FlowEdge[],
): AgentConfig {
  const order = chainOrder(
    nodes.map((node) => node.id),
    edges,
  );
  const sorted = [...nodes].sort((a, b) => order.indexOf(a.id) - order.indexOf(b.id));

  return {
    ...meta,
    schema_version: 1,
    nodes: sorted.map(toNode) as AgentConfig["nodes"],
    edges: [...edges]
      .sort((a, b) => order.indexOf(a.source) - order.indexOf(b.source))
      .map(({ source, target }) => ({ source, target })),
  };
}

export function edgeId(source: string, target: string): string {
  return `${source}->${target}`;
}

function toData(node: Node): NodeData {
  return {
    type: node.type,
    provider: node.provider,
    label: node.label,
    system_prompt: node.type === "llm" ? node.system_prompt : undefined,
    params: (node.params ?? {}) as Record<string, unknown>,
  };
}

function toNode(node: AgentNode): Node {
  const { type, provider, label, system_prompt, params } = node.data;
  return {
    id: node.id,
    type,
    provider,
    ...(label ? { label } : {}),
    ...(type === "llm" ? { system_prompt: system_prompt ?? "" } : {}),
    params,
  } as Node;
}

/**
 * Node ids in pipeline order: walk the cables from the node nothing feeds into.
 * Nodes that aren't on that chain (still being wired up) keep their original order
 * at the end, so an incomplete canvas still exports.
 */
export function chainOrder(ids: string[], edges: { source: string; target: string }[]): string[] {
  const next = new Map(edges.map((edge) => [edge.source, edge.target]));
  const hasIncoming = new Set(edges.map((edge) => edge.target));

  const ordered: string[] = [];
  const seen = new Set<string>();
  for (const id of ids) {
    if (hasIncoming.has(id)) continue;
    for (let at: string | undefined = id; at && !seen.has(at); at = next.get(at)) {
      seen.add(at);
      ordered.push(at);
    }
  }
  return [...ordered, ...ids.filter((id) => !seen.has(id))];
}
