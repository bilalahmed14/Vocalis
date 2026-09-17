/**
 * Canvas-side validation: enough to show problems while editing.
 *
 * The runtime compiler stays the authority (it also checks secrets and builds the
 * pipeline); these checks use the same schemas and phrasing so nothing contradicts it.
 */
import { Ajv, type ErrorObject, type ValidateFunction } from "ajv";

import agentSchema from "@/lib/schema/agent.schema.json";
import type { AgentConfig, Node } from "@/lib/schema/agent.gen";
import type { ProviderManifest } from "@/lib/schema/provider.gen";
import { NODE_TYPES, PORTS } from "@/lib/schema/ports";
import { chainOrder } from "@/lib/agent/flow";

export type Issue = { message: string; nodeId?: string };

const ajv = new Ajv({ allErrors: true, strict: false });
const nodeValidators = new Map<string, ValidateFunction>();
const paramValidators = new Map<string, ValidateFunction>();

const defs = agentSchema.$defs as unknown as Record<string, { properties: { type: { const: string } } }> & {
  Node: { oneOf: { $ref: string }[] };
};

function nodeValidator(type: string): ValidateFunction {
  let validate = nodeValidators.get(type);
  if (!validate) {
    const name = defs.Node.oneOf
      .map(({ $ref }) => $ref.split("/").pop()!)
      .find((candidate) => defs[candidate].properties.type.const === type)!;
    validate = ajv.compile({ $defs: agentSchema.$defs, $ref: `#/$defs/${name}` });
    nodeValidators.set(type, validate);
  }
  return validate;
}

function paramValidator(provider: ProviderManifest): ValidateFunction {
  const key = `${provider.type}/${provider.id}`;
  let validate = paramValidators.get(key);
  if (!validate) {
    validate = ajv.compile(provider.params);
    paramValidators.set(key, validate);
  }
  return validate;
}

export function validateAgent(config: AgentConfig, providers: ProviderManifest[]): Issue[] {
  const issues: Issue[] = [];
  for (const node of config.nodes) {
    issues.push(...nodeIssues(node, providers));
  }
  return [...issues, ...graphIssues(config)];
}

function nodeIssues(node: Node, providers: ProviderManifest[]): Issue[] {
  const issues: Issue[] = [];

  const validate = nodeValidator(node.type);
  // Ajv validators are type guards; keep the result a plain boolean so `node` isn't narrowed.
  const structureOk: boolean = validate(node);
  if (!structureOk) {
    issues.push(
      ...(validate.errors ?? []).map((error) => {
        const field = error.instancePath.split("/").filter(Boolean).join(".");
        return { message: field ? `${field} ${describe(error)}` : describe(error), nodeId: node.id };
      }),
    );
  }

  const provider = providers.find((p) => p.type === node.type && p.id === node.provider);
  if (!provider) {
    const available = providers.filter((p) => p.type === node.type).map((p) => p.id);
    issues.push({
      message: `unknown ${node.type} provider "${node.provider}" (available: ${available.join(", ") || "none installed"})`,
      nodeId: node.id,
    });
    return issues;
  }

  const params = paramValidator(provider);
  const paramsOk: boolean = params(node.params ?? {});
  if (!paramsOk) {
    issues.push(
      ...(params.errors ?? []).map((error) => ({
        message: `params${error.instancePath.replace(/\//g, ".")}: ${describe(error)}`,
        nodeId: node.id,
      })),
    );
  }
  return issues;
}

function graphIssues(config: AgentConfig): Issue[] {
  const issues: Issue[] = [];
  const counts = new Map<string, number>();
  for (const node of config.nodes) counts.set(node.type, (counts.get(node.type) ?? 0) + 1);

  for (const type of NODE_TYPES) {
    if (type === "vad") continue;
    const count = counts.get(type) ?? 0;
    if (count === 0) issues.push({ message: `the pipeline needs a ${type} node` });
  }
  for (const type of NODE_TYPES) {
    if ((counts.get(type) ?? 0) > 1) {
      for (const node of config.nodes.filter((n) => n.type === type)) {
        issues.push({ message: `only one ${type} node is supported in a pipeline`, nodeId: node.id });
      }
    }
  }

  const hasIncoming = new Set(config.edges.map((edge) => edge.target));
  const hasOutgoing = new Set(config.edges.map((edge) => edge.source));
  const heads = config.nodes.filter((node) => !hasIncoming.has(node.id));
  const loose = config.nodes.filter(
    (node) => !hasIncoming.has(node.id) && !hasOutgoing.has(node.id),
  );

  for (const node of loose) {
    if (config.nodes.length > 1) {
      issues.push({ message: "isn't patched into the pipeline", nodeId: node.id });
    }
  }

  // The ends only mean anything once everything is on one chain.
  if (heads.length === 1 && loose.length === 0) {
    const order = chainOrder(config.nodes.map((n) => n.id), config.edges);
    const byId = new Map(config.nodes.map((node) => [node.id, node]));
    const first = byId.get(order[0]);
    const last = byId.get(order[order.length - 1]);
    if (first && PORTS[first.type].input !== "audio") {
      issues.push({
        message: `is first in the pipeline, so it receives mic audio, but it takes ${PORTS[first.type].input} input`,
        nodeId: first.id,
      });
    }
    if (last && PORTS[last.type].output !== "audio") {
      issues.push({
        message: `is last in the pipeline, so its output is played back, but it outputs ${PORTS[last.type].output}`,
        nodeId: last.id,
      });
    }
  }

  return issues;
}

/** The problem itself; callers say which field it belongs to. */
function describe(error: ErrorObject): string {
  if (error.keyword === "required") {
    return `missing required field "${(error.params as { missingProperty: string }).missingProperty}"`;
  }
  if (error.keyword === "additionalProperties") {
    return `unknown field "${(error.params as { additionalProperty: string }).additionalProperty}"`;
  }
  return error.message ?? "is invalid";
}
