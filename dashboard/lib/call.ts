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
  tokens_per_sec?: number;
  chars_per_sec?: number;
  realtime_factor?: number;
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
  /** The agent's voice arrived but the browser refused to start it. */
  onAudioBlocked: (blocked: boolean) => void;
  /** Loudness of the agent's voice as it arrives, 0 to 1, ten times a second. */
  onLevel: (level: number) => void;
};

const ICE_SERVERS = [{ urls: "stun:stun.l.google.com:19302" }];
const MIC_TIMEOUT_MS = 10_000;
const CONNECT_TIMEOUT_MS = 20_000;

export class Call {
  private pc: RTCPeerConnection | null = null;
  private mic: MediaStream | null = null;
  private events: EventSource | null = null;
  private audio: HTMLAudioElement | null = null;
  private meter: { ctx: AudioContext; timer: number } | null = null;
  private callId: string | null = null;

  constructor(private handlers: CallHandlers) {}

  async start(config: AgentConfig, slug?: string): Promise<void> {
    this.handlers.onStatus("connecting");
    // Built before the first await, while the click that started the call still
    // counts as a user gesture: browsers refuse to start audio without one.
    this.audio = this.createSpeaker();
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
      this.audio.remove();
      this.audio = null;
      this.handlers.onStatus("failed", "no microphone: allow access for this site and try again");
      return;
    }

    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });
    this.pc = pc;
    for (const track of this.mic.getTracks()) pc.addTrack(track, this.mic);

    pc.ontrack = (event) => {
      if (!this.audio) return;
      this.audio.srcObject = event.streams[0];
      void this.play();
      this.startMeter(event.streams[0]);
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
    this.events = new EventSource(`/api/calls/${encodeURIComponent(callId)}/events`);
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
      await fetch(`/api/calls/${encodeURIComponent(this.callId)}/hangup`, {
        method: "POST",
      }).catch(() => null);
      this.callId = null;
    }

    this.mic?.getTracks().forEach((track) => track.stop());
    this.mic = null;
    this.pc?.close();
    this.pc = null;
    if (this.meter) {
      clearInterval(this.meter.timer);
      void this.meter.ctx.close();
      this.meter = null;
    }
    this.handlers.onLevel(0);
    if (this.audio) {
      this.audio.srcObject = null;
      this.audio.remove();
    }
    this.audio = null;
    this.handlers.onAudioBlocked(false);
    this.handlers.onStatus("ended");
  }

  /** Start playback after the listener clicks, for a browser that blocked autoplay. */
  async allowAudio(): Promise<void> {
    await this.play();
  }

  /** An element in the document, because a detached one is not a playback target. */
  private createSpeaker(): HTMLAudioElement {
    const audio = document.createElement("audio");
    audio.autoplay = true;
    audio.setAttribute("aria-hidden", "true");
    audio.style.cssText = "position:fixed;width:0;height:0;opacity:0;pointer-events:none";
    document.body.append(audio);
    return audio;
  }

  /**
   * Measure the agent's voice as it arrives, so silence can be told apart: a flat
   * meter means nothing reached the browser, a moving one means the browser has the
   * audio and the output device or its volume is what's swallowing it.
   */
  private startMeter(stream: MediaStream): void {
    if (this.meter) return; // `ontrack` can fire again on renegotiation.
    const ctx = new AudioContext();
    void ctx.resume();
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    ctx.createMediaStreamSource(stream).connect(analyser);

    const samples = new Float32Array(analyser.fftSize);
    const timer = window.setInterval(() => {
      analyser.getFloatTimeDomainData(samples);
      let total = 0;
      for (const sample of samples) total += sample * sample;
      this.handlers.onLevel(Math.sqrt(total / samples.length));
    }, 100);

    this.meter = { ctx, timer };
  }

  /**
   * `autoplay` alone is a request, not a guarantee: Safari and a Chrome without
   * autoplay permission reject it, and a rejected promise is the only notice. Left
   * unhandled it looks exactly like a broken agent — transcript, no voice.
   */
  private async play(): Promise<void> {
    if (!this.audio) return;
    try {
      await this.audio.play();
      this.handlers.onAudioBlocked(false);
    } catch {
      this.handlers.onAudioBlocked(true);
    }
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
