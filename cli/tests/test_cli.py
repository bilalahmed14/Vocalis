"""The `vocalis` command. No test here opens an audio device or calls a provider."""

import json
from pathlib import Path

import pytest

from vocalis_cli.main import main

REPO_ROOT = Path(__file__).resolve().parents[2]
BASIC = str(REPO_ROOT / "examples" / "basic.json")
SECRETS = [
    "DEEPGRAM_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GROQ_API_KEY",
    "ELEVENLABS_API_KEY",
    "CARTESIA_API_KEY",
]


@pytest.fixture(autouse=True)
def no_real_secrets(monkeypatch, tmp_path):
    """Never pick up the developer's .env or shell keys, so `run` can't reach real APIs."""
    for name in SECRETS:
        monkeypatch.delenv(name, raising=False)
    empty = tmp_path / "empty.env"
    empty.write_text("")
    return str(empty)


def test_validate_ok_warns_about_missing_secrets(no_real_secrets, capsys):
    assert main(["validate", BASIC, "--env-file", no_real_secrets]) == 0

    out = capsys.readouterr().out
    assert f"{BASIC}: ok" in out
    assert 'node "stt" needs DEEPGRAM_API_KEY' in out


def test_validate_reads_secrets_from_env_file(tmp_path, capsys):
    env_file = tmp_path / "keys.env"
    env_file.write_text("\n".join(f"{name}=x" for name in SECRETS))

    assert main(["validate", BASIC, "--env-file", str(env_file)]) == 0
    assert "warning" not in capsys.readouterr().out


def test_validate_reports_bad_nodes(tmp_path, no_real_secrets, capsys):
    config = json.loads(Path(BASIC).read_text())
    config["nodes"][3]["provider"] = "elevenlab"
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(config))

    assert main(["validate", str(path), "--env-file", no_real_secrets]) == 1

    err = capsys.readouterr().err
    assert 'node "tts": unknown tts provider "elevenlab"' in err
    assert "available: cartesia, deepgram, elevenlabs, kokoro" in err


def test_run_refuses_without_secrets(no_real_secrets, capsys):
    assert main(["run", BASIC, "--env-file", no_real_secrets]) == 1

    err = capsys.readouterr().err
    assert "Deepgram needs the DEEPGRAM_API_KEY environment variable" in err
    assert "Cartesia needs the CARTESIA_API_KEY environment variable" in err


def test_missing_config_file(no_real_secrets, capsys):
    assert main(["validate", "nope.json", "--env-file", no_real_secrets]) == 1
    assert "file not found: nope.json" in capsys.readouterr().err


def test_missing_env_file(capsys):
    assert main(["validate", BASIC, "--env-file", "missing.env"]) == 1
    assert "env file not found" in capsys.readouterr().err


def test_providers_lists_everything_installed(no_real_secrets, capsys):
    assert main(["providers", "--env-file", no_real_secrets]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert [line.split()[:2] for line in lines] == [
        ["vad", "silero"],
        ["stt", "deepgram"],
        ["stt", "moonshine"],
        ["stt", "whisper"],
        ["llm", "anthropic"],
        ["llm", "groq"],
        ["llm", "ollama"],
        ["llm", "openai"],
        ["tts", "cartesia"],
        ["tts", "deepgram"],
        ["tts", "elevenlabs"],
        ["tts", "kokoro"],
    ]
    assert lines[0].endswith("ready")
    assert lines[1].endswith("needs DEEPGRAM_API_KEY")


def test_providers_flags_uninstalled_extras(no_real_secrets, capsys, monkeypatch):
    import vocalis.providers

    monkeypatch.setattr(vocalis.providers.importlib.util, "find_spec", lambda name: None)

    main(["providers", "--env-file", no_real_secrets])

    whisper = next(line for line in capsys.readouterr().out.splitlines() if "whisper" in line)
    assert whisper.endswith("uv sync --extra whisper")
