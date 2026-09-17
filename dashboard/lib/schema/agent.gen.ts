export type Node = VadNode | SttNode | LlmNode | TtsNode;
/**
 * Unique id of a node within the agent. Edges and error messages refer to nodes by this id.
 */
export type NodeId = string;
/**
 * Id of a provider plugin in /providers, e.g. "deepgram". Must support the node's type.
 */
export type ProviderId = string;
/**
 * Optional display name for the node on the canvas.
 */
export type Label = string;

/**
 * A Vocalis voice agent: provider nodes patched together by edges. Graph rules that JSON Schema cannot express (unique node ids, edges that reference real nodes, audio/text port compatibility, using each node type's x-ports) are enforced by the runtime compiler.
 */
export interface AgentConfig {
  /**
   * Optional path or URL of this schema, so editors can validate hand-written configs.
   */
  $schema?: string;
  /**
   * Version of this config format. Bumped only on breaking changes.
   */
  schema_version: 1;
  name: string;
  description?: string;
  /**
   * @minItems 1
   */
  nodes: [Node, ...Node[]];
  edges: Edge[];
}
/**
 * Voice activity detection. Audio in, audio out; marks where the user starts and stops speaking.
 */
export interface VadNode {
  id: NodeId;
  type: "vad";
  provider: ProviderId;
  label?: Label;
  params?: ProviderParams;
}
/**
 * Provider-specific settings, validated against the provider plugin's own schema. Never put API keys here; they are read from the environment.
 */
export interface ProviderParams {
  [k: string]: unknown;
}
/**
 * Speech to text. Audio in, text out.
 */
export interface SttNode {
  id: NodeId;
  type: "stt";
  provider: ProviderId;
  label?: Label;
  params?: ProviderParams;
}
/**
 * Language model. Text in, text out.
 */
export interface LlmNode {
  id: NodeId;
  type: "llm";
  provider: ProviderId;
  label?: Label;
  /**
   * Instructions for the agent. Lives on the node, not in provider params, so it survives swapping the LLM provider.
   */
  system_prompt: string;
  params?: ProviderParams;
}
/**
 * Text to speech. Text in, audio out.
 */
export interface TtsNode {
  id: NodeId;
  type: "tts";
  provider: ProviderId;
  label?: Label;
  params?: ProviderParams;
}
/**
 * A cable from one node's output to another node's input.
 */
export interface Edge {
  source: NodeId;
  target: NodeId;
}
