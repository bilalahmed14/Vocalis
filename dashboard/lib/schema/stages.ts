/** How each pipeline stage is presented: colour, label and what it does. */
import type { NodeType } from "@/lib/schema/ports";

export const STAGE: Record<NodeType, { label: string; short: string; blurb: string; color: string }> = {
  vad: {
    label: "Voice activity",
    short: "VAD",
    blurb: "Hears when the caller starts and stops speaking",
    color: "var(--stage-vad)",
  },
  stt: {
    label: "Speech to text",
    short: "STT",
    blurb: "Turns the caller's audio into text",
    color: "var(--stage-stt)",
  },
  llm: {
    label: "Language model",
    short: "LLM",
    blurb: "Decides what the agent says next",
    color: "var(--stage-llm)",
  },
  tts: {
    label: "Text to speech",
    short: "TTS",
    blurb: "Speaks the reply back",
    color: "var(--stage-tts)",
  },
};
