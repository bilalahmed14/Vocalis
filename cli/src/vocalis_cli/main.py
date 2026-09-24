"""`vocalis`: run, validate and inspect agents from the terminal, without the dashboard."""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from loguru import logger


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    _configure_logging(args.verbose)

    env_file = Path(args.env_file) if args.env_file else Path(".env")
    if args.env_file and not env_file.is_file():
        return _fail(f"env file not found: {env_file}")
    load_dotenv(env_file, override=False)

    # Imported here so logging is configured before Pipecat loads.
    from vocalis import ConfigError, ProviderError

    try:
        return args.handler(args)
    except (ConfigError, ProviderError) as e:
        return _fail(str(e))
    except FileNotFoundError as e:
        return _fail(f"file not found: {e.filename}")


def _run(args: argparse.Namespace) -> int:
    from vocalis import compile_agent, load_config
    from vocalis_cli.audio import LocalAudioParams, LocalAudioTransport
    from vocalis_cli.session import run_session

    config = load_config(args.agent)
    agent = compile_agent(config)
    transport = LocalAudioTransport(
        LocalAudioParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            input_device=_device(args.input_device),
            output_device=_device(args.output_device),
        )
    )

    chain = " -> ".join(f"{c.node.type}:{c.node.provider}" for c in agent.nodes)
    print(f"{config.name}  ({chain})")
    print("Listening. Speak into your mic; press Ctrl+C to hang up. Headphones stop echo.\n")
    asyncio.run(run_session(agent, transport, metrics=args.metrics))
    return 0


def _validate(args: argparse.Namespace) -> int:
    from vocalis import ProviderRegistry, load_config, validate

    config = load_config(args.agent)
    registry = ProviderRegistry.from_directory()
    issues = validate(config, registry)
    if issues:
        return _fail(
            f"{args.agent}: invalid agent config\n" + "\n".join(f"  - {i}" for i in issues)
        )

    print(f"{args.agent}: ok")
    for node in config.nodes:
        spec = registry.get(node.type, node.provider)
        for name in spec.missing_env(os.environ):
            print(f'  warning: node "{node.id}" needs {name} to run (set it in .env)')
        if hint := spec.install_hint():
            print(f'  warning: node "{node.id}" needs {spec.name} installed; run: {hint}')
    return 0


def _providers(args: argparse.Namespace) -> int:
    from vocalis import ProviderRegistry

    specs = sorted(ProviderRegistry.from_directory(), key=lambda s: (_TYPE_ORDER[s.type], s.id))
    for spec in specs:
        missing = spec.missing_env(os.environ)
        status = ("needs " + ", ".join(missing)) if missing else (spec.install_hint() or "ready")
        print(f"{spec.type:<4} {spec.id:<12} {spec.name:<18} {status}")
    return 0


def _devices(args: argparse.Namespace) -> int:
    import sounddevice as sd

    print(sd.query_devices())
    return 0


_TYPE_ORDER = {"vad": 0, "stt": 1, "llm": 2, "tts": 3}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vocalis", description=__doc__)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--env-file", help="read secrets from this file (default: ./.env)")
    common.add_argument("-v", "--verbose", action="store_true", help="show Pipecat debug logs")

    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", parents=[common], help="talk to an agent through your mic")
    run.add_argument("agent", help="path to an agent config JSON")
    run.add_argument("--input-device", help="mic device index or name (see `vocalis devices`)")
    run.add_argument("--output-device", help="speaker device index or name")
    run.add_argument(
        "--metrics",
        action="store_true",
        help="show where each turn's latency went, and a summary on hangup",
    )
    run.set_defaults(handler=_run)

    check = commands.add_parser(
        "validate", parents=[common], help="check a config without running it"
    )
    check.add_argument("agent", help="path to an agent config JSON")
    check.set_defaults(handler=_validate)

    listing = commands.add_parser("providers", parents=[common], help="list installed providers")
    listing.set_defaults(handler=_providers)

    devices = commands.add_parser("devices", parents=[common], help="list audio devices")
    devices.set_defaults(handler=_devices)

    return parser


def _configure_logging(verbose: bool) -> None:
    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if verbose else "WARNING")


def _device(value: str | None) -> int | str | None:
    return int(value) if value is not None and value.isdigit() else value


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
