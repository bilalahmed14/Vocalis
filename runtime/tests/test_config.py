"""Loading configs, and schema errors that point at the bad node."""

import json
from pathlib import Path

import pytest

from vocalis import ConfigError, Issue, load_config, parse_config
from vocalis.config import Edge

REPO_ROOT = Path(__file__).resolve().parents[2]


def issues_for(data) -> list[Issue]:
    with pytest.raises(ConfigError) as exc:
        parse_config(data)
    return exc.value.issues


def test_parses_valid_config(config):
    agent = parse_config(config)

    assert agent.name == "Test agent"
    assert [n.id for n in agent.nodes] == ["vad", "stt", "llm", "tts"]
    assert agent.node("llm").system_prompt == "Be brief."
    assert agent.node("stt").params == {"model": "small"}
    assert agent.edges[0] == Edge(source="vad", target="stt")


def test_params_default_to_empty(config):
    del config["nodes"][3]["params"]
    assert parse_config(config).node("tts").params == {}


@pytest.mark.parametrize("path", sorted((REPO_ROOT / "examples").glob("*.json")), ids=str)
def test_examples_match_schema(path):
    load_config(path)


def test_invalid_json_reports_position(tmp_path):
    path = tmp_path / "agent.json"
    path.write_text('{"name": "x",\n  "nodes": [}')

    with pytest.raises(ConfigError) as exc:
        load_config(path)

    assert exc.value.source == str(path)
    assert "not valid JSON" in exc.value.issues[0].message
    assert "line 2" in exc.value.issues[0].message


def test_missing_system_prompt_points_at_llm_node(config):
    del config["nodes"][2]["system_prompt"]

    [issue] = issues_for(config)

    assert issue.node_id == "llm"
    assert issue.node_index == 2
    assert issue.path == "/nodes/2"
    assert str(issue) == 'node "llm": missing required field "system_prompt"'


def test_unknown_node_type_lists_valid_types(config):
    config["nodes"][0]["type"] = "mixer"

    [issue] = issues_for(config)

    assert issue.node_id == "vad"
    assert issue.path == "/nodes/0/type"
    assert issue.message == "type must be one of vad, stt, llm, tts (got 'mixer')"


def test_unknown_field_on_node(config):
    config["nodes"][1]["api_key"] = "sk-..."

    [issue] = issues_for(config)

    assert str(issue) == 'node "stt": unknown field "api_key"'


def test_bad_field_value_names_the_field(config):
    config["nodes"][3]["label"] = 42

    [issue] = issues_for(config)

    assert issue.node_id == "tts"
    assert issue.path == "/nodes/3/label"
    assert issue.message == "label: 42 is not of type 'string'"


def test_node_with_invalid_id_is_pointed_at_by_index(config):
    config["nodes"][1]["id"] = "1bad id"

    [issue] = issues_for(config)

    assert issue.node_index == 1
    assert issue.path == "/nodes/1/id"
    assert str(issue).startswith('node "1bad id": id:')


def test_node_without_id_falls_back_to_index(config):
    del config["nodes"][1]["id"]

    [issue] = issues_for(config)

    assert str(issue) == 'node #1: missing required field "id"'


def test_edge_errors_point_at_edge(config):
    del config["edges"][1]["target"]

    [issue] = issues_for(config)

    assert issue.edge_index == 1
    assert str(issue) == 'edge 1: missing required field "target"'


def test_top_level_errors(config):
    config["schema_version"] = 2
    del config["name"]

    messages = {issue.message for issue in issues_for(config)}

    assert messages == {'missing required field "name"', "schema_version: 1 was expected"}


def test_reports_every_problem_at_once(config):
    del config["nodes"][2]["system_prompt"]
    config["nodes"][0]["type"] = "mixer"
    del config["edges"][0]["source"]

    assert len(issues_for(config)) == 3


def test_config_error_message_lists_issues(config, tmp_path):
    del config["nodes"][2]["system_prompt"]
    path = tmp_path / "agent.json"
    path.write_text(json.dumps(config))

    with pytest.raises(ConfigError) as exc:
        load_config(path)

    assert str(exc.value) == (
        f"{path}: invalid agent config (1 problem)\n"
        '  - node "llm": missing required field "system_prompt"'
    )
