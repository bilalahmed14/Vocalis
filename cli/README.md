# vocalis-cli

Run Vocalis agents from the terminal: no dashboard, no browser.

```bash
vocalis run examples/basic.json        # talk to the agent through your mic
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

Audio goes through [sounddevice](https://python-sounddevice.readthedocs.io), whose
macOS and Windows wheels include PortAudio. On Linux, install the PortAudio library
first (`apt install libportaudio2`).
