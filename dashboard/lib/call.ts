/**
 * Placing a browser call to an agent.
 *
 * The browser offers, the runtime answers, and the agent's voice comes back on the
 * same connection. Transcript and per-turn latency arrive separately as server-sent
 * events, so the canvas can show a call while it's still going.
 */
import type { AgentConfig } from "@/lib/schema/agent.gen";

export type CallStatus = "idle" | "connecting" | "live" | "ended" | "failed";

export type TranscriptLine = {
  role: "user" | "agent";
  text: string;
  interrupted?: boolean;
  at: string;
};

export type TurnStage = {
  key: string;
  label: string;
  owner: string;
  node_id: string | null;
  ms: number;
};

export type TurnEvent = {
  turn: number;
  total_ms: number;
  interrupted: boolean;
  by_node: Record<string, number>;
  stages: TurnStage[];
};

export type CallHandlers = {
  onStatus: (status: CallStatus, detail?: string) => void;
  onTranscript: (line: TranscriptLine) => void;
  onTurn: (turn: TurnEvent) => void;
};

const ICE_SERVERS = [{ urls: "stun:stun.l.google.com:19302" }];
const MIC_TIMEOUT_MS = 10_000;
const CONNECT_TIMEOUT_MS = 20_000;

export class Call {
  private pc: RTCPeerConnection | null = null;
  private mic: MediaStream | null = null;
  private events: EventSource | null = null;
  private audio: HTMLAudioElement | null = null;
  private callId: string | null = null;

  constructor(private handlers: CallHandlers) {}

  async start(config: AgentConfig, slug?: string): Promise<void> {
    this.handlers.onStatus("connecting");
    try {
      // Some browsers never settle this promise when the permission prompt can't be
      // shown, so a hung microphone reports as a failure rather than "connecting…".
      this.mic = await withTimeout(
        navigator.mediaDevices.getUserMedia({
          // The agent hears itself without these; browsers do the cancellation for us.
          audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
        }),
        MIC_TIMEOUT_MS,
      );
    } catch {
      this.handlers.onStatus("failed", "no microphone: allow access for this site and try again");
      return;
    }

    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    this.pc = pc;
    for (const track of this.mic.getTracks()) pc.addTrack(track, this.mic);

    this.audio = new Audio();
    this.audio.autoplay = true;
    pc.ontrack = (event) => {
      if (this.audio) this.audio.srcObject = event.streams[0];
    };
    pc.onconnectionstatechange = () => {
      if (pc.connectionState === "failed") this.handlers.onStatus("failed", "connection failed");
      if (pc.connectionState === "closed") this.handlers.onStatus("ended");
    };

    await pc.setLocalDescription(await pc.createOffer());
    await iceGathered(pc);

    const response = await fetch("/api/calls", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        sdp: pc.localDescription?.sdp,
        type: pc.localDescription?.type,
        ...(slug ? { slug } : { config }),
      }),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const issues = body?.detail?.issues as { message: string }[] | undefined;
      this.handlers.onStatus(
        "failed",
        issues?.map((issue) => issue.message).join("; ") ??
          (typeof body?.detail === "string" ? body.detail : "the runtime refused the call"),
      );
      await this.stop();
      return;
    }

    const answer = (await response.json()) as { sdp: string; type: string; call_id: string };
    await pc.setRemoteDescription({ sdp: answer.sdp, type: answer.type as RTCSdpType });
    this.callId = answer.call_id;
    this.listen(answer.call_id);

    // If the peer connection never comes up (a firewall, no route to the runtime),
    // say so instead of waiting forever.
    setTimeout(() => {
      if (this.pc && this.pc.connectionState !== "connected") {
        this.handlers.onStatus("failed", "the call didn't connect");
        void this.stop();
      }
    }, CONNECT_TIMEOUT_MS);
  }

  private listen(callId: string): void {
    this.events = new EventSource(`/api/calls/${callId}/events`);
    this.events.onmessage = (message) => {
      const event = JSON.parse(message.data);
      if (event.type === "state") this.handlers.onStatus(event.state === "live" ? "live" : "ended");
      else if (event.type === "transcript") this.handlers.onTranscript(event as TranscriptLine);
      else if (event.type === "turn") this.handlers.onTurn(event as TurnEvent);
      else if (event.type === "error") this.handlers.onStatus("failed", event.message);
    };
    this.events.onerror = () => this.events?.close();
  }

  async stop(): Promise<void> {
    this.events?.close();
    this.events = null;

    if (this.callId) {
      await fetch(`/api/calls/${this.callId}/hangup`, { method: "POST" }).catch(() => null);
      this.callId = null;
    }

    this.mic?.getTracks().forEach((track) => track.stop());
    this.mic = null;
    this.pc?.close();
    this.pc = null;
    if (this.audio) this.audio.srcObject = null;
    this.audio = null;
    this.handlers.onStatus("ended");
  }
}

/** Wait for ICE candidates, which the runtime expects folded into the offer. */
function iceGathered(pc: RTCPeerConnection, timeoutMs = 2000): Promise<void> {
  if (pc.iceGatheringState === "complete") return Promise.resolve();
  return new Promise((resolve) => {
    const done = () => {
      pc.removeEventListener("icegatheringstatechange", check);
      clearTimeout(timer);
      resolve();
    };
    const check = () => pc.iceGatheringState === "complete" && done();
    const timer = setTimeout(done, timeoutMs);
    pc.addEventListener("icegatheringstatechange", check);
  });
}

function withTimeout<T>(promise: Promise<T>, ms: number): Promise<T> {
  return Promise.race([
    promise,
    new Promise<T>((_, reject) => setTimeout(() => reject(new Error("timed out")), ms)),
  ]);
}
