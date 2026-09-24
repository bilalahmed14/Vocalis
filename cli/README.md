# vocalis-cli

Run Vocalis agents from the terminal: no dashboard, no browser.

```bash
vocalis run examples/basic.json        # talk to the agent through your mic
vocalis run examples/local.json --metrics   # ...and show where each turn's time went
vocalis validate examples/basic.json   # check a config without running it
vocalis providers                      # installed providers and missing keys
vocalis devices                        # audio devices, for --input-device / --output-device
```

`run` reads API keys from `./.env` (or `--env-file`), prints the conversation as it
happens, and hangs up on Ctrl+C:

```
Basic assistant  (vad:silero -> stt:deepgram -> llm:openai -> tts:cartesia)
Listening. Speak into your mic; press Ctrl+C to hang up. Headphones stop echo.

you   > What's the tallest mountain in Africa?
agent > Kilimanjaro, at about 5,895 meters.
```

Use headphones: the local transport has no echo cancellation, so on speakers the
agent can hear itself and interrupt its own reply.

## Measuring latency

`--metrics` prints a waterfall per turn and a summary when you hang up:

```
  turn 2: 843 ms to first audio
       120 ms  ████████                      vad silence [config:stop_secs]
        96 ms  ██████                        stt ttfb [stt]
       284 ms  ███████████████████           llm ttfb [llm]
       343 ms  ████████████████████████      tts ttfb [tts]

4 turns   p50 861 ms   p95 1204 ms   worst 1204 ms

  slowest stages (median across turns):
       343 ms  tts ttfb [tts]
       284 ms  llm ttfb [llm]
```

Every stage is named, and they add up to the total, so time that no service is
measuring — the silence the VAD waits out, a grace window for a late transcript —
shows up next to the services rather than hiding between them. Stages that belong to
a node are labelled with that node's id, so a slow stage points at the box to change.

Medians are across turns on purpose: one cold model load shouldn't decide where you
spend your effort.

Audio goes through [sounddevice](https://python-sounddevice.readthedocs.io), whose
macOS and Windows wheels include PortAudio. On Linux, install the PortAudio library
first (`apt install libportaudio2`).
