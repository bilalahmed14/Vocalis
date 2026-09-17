/**
 * Manifest for a provider plugin (providers/<type>/<id>/provider.json). The runtime uses it to validate node params and check secrets; the canvas uses it to build the palette and the node inspector form.
 */
export interface ProviderManifest {
  $schema?: string;
  /**
   * Provider id used in agent configs. Must match the plugin's folder name.
   */
  id: string;
  /**
   * Node type this plugin implements. Must match the parent folder name.
   */
  type: "vad" | "stt" | "llm" | "tts";
  /**
   * Display name, e.g. "Deepgram".
   */
  name: string;
  description?: string;
  docs_url?: string;
  /**
   * Environment variables the provider needs, usually API keys. The compiler refuses to build a node while any are missing.
   */
  env?: string[];
  /**
   * An optional dependency the provider needs. The compiler refuses to build the node while the module is missing, and tells the user which extra to install.
   */
  requires?: {
    /**
     * Python module that must be importable, e.g. "faster_whisper".
     */
    module: string;
    /**
     * Extra that installs it: "uv sync --extra <extra>".
     */
    extra: string;
  };
  /**
   * The provider only works when a vad node earlier in the pipeline marks where speech starts and stops (e.g. STT that transcribes whole utterances).
   */
  needs_vad?: boolean;
  /**
   * JSON Schema (draft 2020-12) for the node's params. Top-level property defaults are applied before the adapter runs.
   */
  params: {
    type: "object";
    [k: string]: unknown;
  };
}
