"use client";

import {
  Background,
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
import { useCallback, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { AgentNode } from "@/components/canvas/agent-node";
import { Inspector } from "@/components/canvas/inspector";
import { Palette } from "@/components/canvas/palette";
import { ProvidersProvider, useProviders } from "@/components/canvas/providers-context";
import { SCHEMA_REF, nextNodeId, serializeConfig } from "@/lib/agent/config";
import { type AgentNode as AgentNodeType, type NodeData, configToFlow, edgeId, flowToConfig } from "@/lib/agent/flow";
import { validateAgent } from "@/lib/agent/validate";
import type { Provider } from "@/lib/providers";
import type { AgentConfig } from "@/lib/schema/agent.gen";
import { canConnect } from "@/lib/schema/ports";

const nodeTypes = { agentNode: AgentNode };

export function AgentEditor({ providers, config }: { providers: Provider[]; config: AgentConfig }) {
  return (
    <ProvidersProvider value={providers}>
      <ReactFlowProvider>
        <Editor config={config} />
      </ReactFlowProvider>
    </ProvidersProvider>
  );
}

function Editor({ config }: { config: AgentConfig }) {
  const providers = useProviders();
  const initial = useMemo(() => configToFlow(config), [config]);

  const [nodes, setNodes, onNodesChange] = useNodesState<AgentNodeType>(initial.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initial.edges);
  const [meta, setMeta] = useState({ name: config.name, description: config.description });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const { screenToFlowPosition } = useReactFlow();
  const fileInput = useRef<HTMLInputElement>(null);

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
      const imported = JSON.parse(await file.text()) as AgentConfig;
      const flow = configToFlow(imported);
      setMeta({ name: imported.name, description: imported.description });
      setNodes(flow.nodes);
      setEdges(flow.edges);
      setSelectedId(null);
    },
    [setEdges, setNodes],
  );

  const selected = nodes.find((node) => node.id === selectedId) ?? null;
  const nodeIssues = (id: string) =>
    issues.filter((issue) => issue.nodeId === id).map((issue) => issue.message);

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center gap-3 border-b px-4 py-2">
        <span className="font-semibold">Vocalis</span>
        <Input
          aria-label="Agent name"
          className="h-8 w-64"
          value={meta.name}
          onChange={(event) => setMeta((current) => ({ ...current, name: event.target.value }))}
        />
        <span
          className={
            issues.length
              ? "rounded bg-destructive/10 px-2 py-1 text-xs text-destructive"
              : "rounded bg-emerald-500/10 px-2 py-1 text-xs text-emerald-600"
          }
        >
          {issues.length ? `${issues.length} problem${issues.length > 1 ? "s" : ""}` : "valid"}
        </span>
        <div className="ml-auto flex gap-2">
          <input
            ref={fileInput}
            type="file"
            accept="application/json"
            className="hidden"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) void importJson(file);
              event.target.value = "";
            }}
          />
          <Button variant="outline" size="sm" onClick={() => fileInput.current?.click()}>
            Import
          </Button>
          <Button size="sm" onClick={exportJson}>
            Export JSON
          </Button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <Palette onAdd={(type, providerId) => addNode(type, providerId)} />

        <div
          className="min-w-0 flex-1"
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
            fitViewOptions={{ padding: 0.25 }}
            proOptions={{ hideAttribution: false }}
          >
            <Background />
            <Controls />
          </ReactFlow>
        </div>

        <Inspector
          node={selected}
          issues={selected ? nodeIssues(selected.id) : []}
          onChange={(data) => selected && updateNode(selected.id, data)}
          onRename={(id) => selected && renameNode(selected.id, id)}
          onDelete={() => selected && deleteNode(selected.id)}
        />
      </div>

      {issues.length > 0 ? (
        <footer className="max-h-28 overflow-y-auto border-t bg-muted/30 px-4 py-2 text-xs">
          <ul className="space-y-0.5">
            {issues.map((issue, index) => (
              <li key={`${issue.nodeId ?? "config"}-${index}`}>
                <span className="font-medium">{issue.nodeId ? `node "${issue.nodeId}"` : "config"}:</span>{" "}
                {issue.message}
              </li>
            ))}
          </ul>
        </footer>
      ) : null}
    </div>
  );
}
