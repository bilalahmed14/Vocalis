"""Graph shape: port types, a single chain, and node order."""

import pytest

from vocalis import parse_config
from vocalis.graph import order_chain


def chain_ids(config) -> list[str]:
    chain, issues = order_chain(parse_config(config))
    assert issues == []
    return [node.id for node in chain]


def messages(config) -> list[str]:
    chain, issues = order_chain(parse_config(config))
    assert chain == []
    return [str(issue) for issue in issues]


def set_edges(config, *pairs):
    config["edges"] = [{"source": s, "target": t} for s, t in pairs]


def test_orders_chain_from_edges_not_node_order(config):
    config["nodes"].reverse()
    config["edges"].reverse()

    assert chain_ids(config) == ["vad", "stt", "llm", "tts"]


def test_vad_is_optional(config):
    config["nodes"] = [n for n in config["nodes"] if n["type"] != "vad"]
    set_edges(config, ("stt", "llm"), ("llm", "tts"))

    assert chain_ids(config) == ["stt", "llm", "tts"]


def test_port_type_mismatch(config):
    set_edges(config, ("vad", "llm"), ("stt", "tts"), ("llm", "stt"))

    assert 'node "llm": "vad" outputs audio but "llm" takes text input' in messages(config)


def test_cable_to_unknown_node(config):
    config["edges"][2]["target"] = "speaker"

    assert messages(config) == ['edge 2: cable to unknown node "speaker"']


def test_node_patched_into_itself(config):
    config["edges"].append({"source": "llm", "target": "llm"})

    assert messages(config) == ['node "llm": can\'t be patched into itself']


def test_duplicate_node_id(config):
    config["nodes"][3]["id"] = "llm"

    assert 'node "llm": duplicate node id "llm"' in messages(config)


@pytest.mark.parametrize("missing", ["stt", "llm", "tts"])
def test_required_node_types(config, missing):
    config["nodes"] = [n for n in config["nodes"] if n["type"] != missing]
    config["edges"] = []

    assert f"config: the pipeline needs a {missing} node" in messages(config)


def test_only_one_node_per_type(config):
    config["nodes"].append({**config["nodes"][2], "id": "llm2"})
    set_edges(config, ("vad", "stt"), ("stt", "llm"), ("llm", "llm2"), ("llm2", "tts"))

    assert messages(config) == [
        'node "llm": only one llm node is supported in a pipeline',
        'node "llm2": only one llm node is supported in a pipeline',
    ]


def test_fan_out_is_rejected(config):
    config["edges"].append({"source": "vad", "target": "tts"})

    result = messages(config)
    assert 'node "vad": has more than one outgoing cable' in result
    assert 'node "tts": has more than one incoming cable' in result


def test_disconnected_nodes(config):
    config["edges"] = [{"source": "llm", "target": "tts"}]

    assert messages(config) == [
        'node "vad": not connected to the rest of the pipeline '
        '(chains start at "vad", "stt", "llm")',
        'node "stt": not connected to the rest of the pipeline '
        '(chains start at "vad", "stt", "llm")',
        'node "llm": not connected to the rest of the pipeline '
        '(chains start at "vad", "stt", "llm")',
    ]


def test_loop_with_no_first_node(config):
    config["nodes"] = [n for n in config["nodes"] if n["type"] != "vad"]
    set_edges(config, ("stt", "llm"), ("llm", "tts"), ("tts", "stt"))

    assert messages(config) == ["config: the cables form a loop; the pipeline needs a first node"]


def test_chain_must_start_and_end_with_audio(config):
    set_edges(config, ("llm", "tts"), ("tts", "vad"), ("vad", "stt"))

    assert messages(config) == [
        'node "llm": is first in the pipeline, so it receives mic audio, but it takes text input',
        'node "stt": is last in the pipeline, so its output is played back, but it outputs text',
    ]


def test_vad_after_stt(config):
    set_edges(config, ("stt", "llm"), ("llm", "tts"), ("tts", "vad"))

    assert messages(config) == ['node "vad": vad must come before stt']
