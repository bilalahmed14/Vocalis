"""The JSON Schemas are the contract; these tests keep the Python side in sync."""

import dataclasses

from jsonschema import Draft202012Validator

from vocalis import AgentConfig, Edge, Node
from vocalis.schema import (
    Ports,
    agent_schema,
    dotted,
    node_ports,
    node_types,
    pointer,
    provider_schema,
)


def test_schemas_are_valid_json_schema():
    Draft202012Validator.check_schema(agent_schema())
    Draft202012Validator.check_schema(provider_schema())


def test_node_types_and_ports_come_from_schema():
    assert node_types() == ["vad", "stt", "llm", "tts"]
    assert node_ports() == {
        "vad": Ports("audio", "audio"),
        "stt": Ports("audio", "text"),
        "llm": Ports("text", "text"),
        "tts": Ports("text", "audio"),
    }


def test_provider_manifest_types_match_node_types():
    assert provider_schema()["properties"]["type"]["enum"] == node_types()


def _fields(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def test_config_dataclasses_match_schema_properties():
    schema = agent_schema()
    defs = schema["$defs"]

    assert _fields(AgentConfig) == set(schema["properties"]) - {"$schema"}
    assert _fields(Edge) == set(defs["Edge"]["properties"])

    node_properties = set()
    for ref in defs["Node"]["oneOf"]:
        node_properties |= set(defs[ref["$ref"].rsplit("/", 1)[1]]["properties"])
    assert _fields(Node) == node_properties


def test_dotted_and_pointer_paths():
    assert dotted(["params", "voices", 0, "id"]) == "params.voices[0].id"
    assert pointer(["nodes", 2, "a/b~c"]) == "/nodes/2/a~1b~0c"
