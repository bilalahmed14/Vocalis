"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  type Edge,
  ReactFlow,
  ReactFlowProvider,
  type Connection,
  useEdgesState,
  useNodesState,
  useReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useRouter } from "next/navigation";
import { useCallback, useMemo, useState } from "react";

import { AgentNode } from "@/components/canvas/agent-node";
import { CallPanel } from "@/components/canvas/call-panel";
import { CallProvider } from "@/components/canvas/call-context";
import { useCall } from "@/components/canvas/use-call";
import { Inspector } from "@/components/canvas/inspector";
import { Palette } from "@/components/canvas/palette";
import { ProvidersProvider, useProviders } from "@/components/canvas/providers-context";
import { type SaveState, Toolbar } from "@/components/canvas/toolbar";
import { SCHEMA_REF, nextNodeId, serializeConfig } from "@/lib/agent/config";
import { type AgentNode as AgentNodeType, type NodeData, configToFlow, edgeId, flowToConfig } from "@/lib/agent/flow";
import { validateAgent } from "@/lib/agent/validate";
import { type AgentVersion, type Provider, api } from "@/lib/api";
import type { AgentConfig } from "@/lib/schema/agent.gen";
import { canConnect } from "@/lib/schema/ports";

const nodeTypes = { agentNode: AgentNode };

type EditorProps = {
  providers: Provider[];
  config: AgentConfig;
  saved?: { slug: string; version: number } | null;
  versions?: AgentVersion[];
};

export function AgentEditor({ providers, ...props }: EditorProps) {
  return (
    <ProvidersProvider value={providers}>
      <ReactFlowProvider>
        <Editor {...props} />
      </ReactFlowProvider>
    </ProvidersProvider>
  );
}

function Editor({
  config,
  saved: initialSaved = null,
  versions: initialVersions = [],
}: Omit<EditorProps, "providers">) {
  const providers = useProviders();
  const initial = useMemo(() => configToFlow(config), [config]);

  const [nodes, setNodes, onNodesChange] = useNodesState<AgentNodeType>(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initial.edges);
  const [meta, setMeta] = useState({ name: config.name, description: config.description });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [saved, setSaved] = useState(initialSaved);
  const [versions, setVersions] = useState(initialVersions);
  const [state, setState] = useState<SaveState>({ kind: "idle" });
  const call = useCall();
  const { screenToFlowPosition } = useReactFlow();
  const router = useRouter();

  const agent = useMemo(
    () => flowToConfig({ $schema: SCHEMA_REF, ...meta }, nodes, edges),
    [meta, nodes, edges],
  );
  const issues = useMemo(() => validateAgent(agent, providers), [agent, providers]);

  const addNode = useCallback(
    (type: NodeData["type"], providerId: string, position?: { x: number; y: number }) => {
      const provider = providers.find((p) => p.type === type && p.id === providerId);
      const params = provider?.params as
        | { required?: string[]; properties?: Record<string, { examples?: unknown[] }> }
        | undefined;
      const prefilled = Object.fromEntries(
        (params?.required ?? [])
          .map((name) => [name, params?.properties?.[name]?.examples?.[0]])
          .filter(([, value]) => value !== undefined),
      );

      setNodes((current) => {
        const id = nextNodeId(type, current.map((node) => node.id));
        const node: AgentNodeType = {
          id,
          type: "agentNode",
          position: position ?? { x: 80 + current.length * 40, y: 80 + current.length * 40 },
          data: {
            type,
            provider: providerId,
            params: prefilled,
            ...(type === "llm"
              ? { system_prompt: "You are a friendly voice assistant. Keep replies short and conversational." }
              : {}),
          },
        };
        setSelectedId(id);
        return [...current, node];
      });
    },
    [providers, setNodes],
  );

  const isValidConnection = useCallback(
    (connection: Connection | Edge) => {
      const source = nodes.find((node) => node.id === connection.source);
      const target = nodes.find((node) => node.id === connection.target);
      if (!source || !target || source.id === target.id) return false;
      return canConnect(source.data.type, target.data.type);
    },
    [nodes],
  );

  const onConnect = useCallback(
    (connection: Connection) => {
      if (!isValidConnection(connection)) return;
      setEdges((current) => [
        // One cable per port: a new one replaces whatever was plugged in.
        ...current.filter(
          (edge) => edge.source !== connection.source && edge.target !== connection.target,
        ),
        { id: edgeId(connection.source, connection.target), source: connection.source, target: connection.target },
      ]);
    },
    [isValidConnection, setEdges],
  );

  const updateNode = useCallback(
    (id: string, data: Partial<NodeData>) => {
      setNodes((current) =>
        current.map((node) => (node.id === id ? { ...node, data: { ...node.data, ...data } } : node)),
      );
    },
    [setNodes],
  );

  const renameNode = useCallback(
    (id: string, next: string) => {
      if (!next || nodes.some((node) => node.id === next)) return;
      setNodes((current) => current.map((node) => (node.id === id ? { ...node, id: next } : node)));
      setEdges((current) =>
        current.map((edge) => {
          const source = edge.source === id ? next : edge.source;
          const target = edge.target === id ? next : edge.target;
          return { ...edge, id: edgeId(source, target), source, target };
        }),
      );
      setSelectedId(next);
    },
    [nodes, setEdges, setNodes],
  );

  const deleteNode = useCallback(
    (id: string) => {
      setNodes((current) => current.filter((node) => node.id !== id));
      setEdges((current) => current.filter((edge) => edge.source !== id && edge.target !== id));
      setSelectedId(null);
    },
    [setEdges, setNodes],
  );

  const load = useCallback(
    (next: AgentConfig) => {
      const flow = configToFlow(next);
      setMeta({ name: next.name, description: next.description });
      setNodes(flow.nodes);
      setEdges(flow.edges);
      setSelectedId(null);
    },
    [setEdges, setNodes],
  );

  const save = useCallback(async () => {
    setState({ kind: "saving" });
    try {
      const result = saved ? await api.save(saved.slug, agent) : await api.create(agent);
      setSaved({ slug: result.slug, version: result.version });
      setVersions(await api.versions(result.slug));
      setState({ kind: "saved", message: `saved v${result.version}` });
      if (!saved) router.replace(`/agents/${result.slug}`);
    } catch (error) {
      setState({ kind: "error", message: error instanceof Error ? error.message : "save failed" });
    }
  }, [agent, saved, router]);

  const openVersion = useCallback(
    async (version: number) => {
      if (!saved) return;
      const old = await api.versionConfig(saved.slug, version);
      load(old.config);
      setSaved({ slug: old.slug, version });
      setState(
        version === versions[0]?.version
          ? { kind: "idle" }
          : { kind: "idle", message: `viewing v${version}` },
      );
    },
    [load, saved, versions],
  );

  const restore = useCallback(
    async (version: number) => {
      if (!saved) return;
      const restored = await api.restore(saved.slug, version);
      load(restored.config);
      setSaved({ slug: restored.slug, version: restored.version });
      setVersions(await api.versions(restored.slug));
      setState({ kind: "saved", message: `restored v${version} as v${restored.version}` });
    },
    [load, saved],
  );

  const exportJson = useCallback(() => {
    const blob = new Blob([serializeConfig(agent)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${agent.name.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.json`;
    link.click();
    URL.revokeObjectURL(url);
  }, [agent]);

  const importJson = useCallback(
    async (file: File) => {
      load(JSON.parse(await file.text()) as AgentConfig);
      setState({ kind: "idle", message: `imported ${file.name}` });
    },
    [load],
  );

  const selected = nodes.find((node) => node.id === selectedId) ?? null;
  const nodeIssues = (id: string) =>
    issues.filter((issue) => issue.nodeId === id).map((issue) => issue.message);

  return (
    <CallProvider value={call}>
    <div className="flex min-h-0 flex-1 flex-col">
      <Toolbar
        name={meta.name}
        onNameChange={(name) => setMeta((current) => ({ ...current, name }))}
        issueCount={issues.length}
        saved={saved}
        versions={versions}
        state={state}
        onSave={save}
        onImport={(file) => void importJson(file)}
        onExport={exportJson}
        onOpenVersion={(version) => void openVersion(version)}
        onRestore={(version) => void restore(version)}
        call={{
          status: call.status,
          onStart: () => call.start(agent, saved?.slug),
          onStop: call.stop,
        }}
      />

      <div className="flex min-h-0 flex-1">
        <Palette onAdd={(type, providerId) => addNode(type, providerId)} />

        <div
          className="relative min-w-0 flex-1"
          onDragOver={(event) => {
            event.preventDefault();
            event.dataTransfer.dropEffect = "move";
          }}
          onDrop={(event) => {
            event.preventDefault();
            const payload = event.dataTransfer.getData("application/vocalis");
            if (!payload) return;
            const [type, providerId] = payload.split(":");
            addNode(type as NodeData["type"], providerId, screenToFlowPosition({ x: event.clientX, y: event.clientY }));
          }}
        >
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            isValidConnection={isValidConnection}
            onNodeClick={(_, node) => setSelectedId(node.id)}
            onPaneClick={() => setSelectedId(null)}
            fitView
            fitViewOptions={{ padding: 0.3, maxZoom: 1 }}
            defaultEdgeOptions={{ animated: true }}
            proOptions={{ hideAttribution: false }}
            className="bg-background"
          >
            <Background variant={BackgroundVariant.Dots} gap={18} size={1} className="opacity-60" />
            <Controls showInteractive={false} className="!shadow-lg" />
          </ReactFlow>

          {nodes.length === 0 ? (
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
              <div className="rounded-xl border border-dashed border-border bg-card/80 px-6 py-5 text-center backdrop-blur">
                <p className="text-sm font-medium">Start with a microphone stage</p>
                <p className="mt-1 max-w-xs text-xs text-muted-foreground">
                  Add voice activity, speech to text, a language model and a voice, then patch
                  them left to right.
                </p>
              </div>
            </div>
          ) : null}
        </div>

        <Inspector
          node={selected}
          issues={selected ? nodeIssues(selected.id) : []}
          onChange={(data) => selected && updateNode(selected.id, data)}
          onRename={(id) => selected && renameNode(selected.id, id)}
          onDelete={() => selected && deleteNode(selected.id)}
        />
      </div>

      <CallPanel />

      {issues.length > 0 ? (
        <footer className="max-h-32 shrink-0 overflow-y-auto border-t border-border bg-surface/80 px-4 py-2.5">
          <ul className="space-y-1">
            {issues.map((issue, index) => (
              <li
                key={`${issue.nodeId ?? "config"}-${index}`}
                className="flex items-baseline gap-2 text-xs"
              >
                <span className="shrink-0 rounded bg-destructive/10 px-1.5 py-0.5 font-mono text-[10px] text-destructive">
                  {issue.nodeId ?? "config"}
                </span>
                <span className="text-muted-foreground">{issue.message}</span>
              </li>
            ))}
          </ul>
        </footer>
      ) : null}
    </div>
    </CallProvider>
  );
}
