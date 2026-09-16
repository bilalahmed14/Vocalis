"""Graph checks the JSON Schema can't express, and ordering nodes into a chain.

v1 pipelines are a single chain from mic to speaker: `[vad ->] stt -> llm -> tts`.
Cables must connect matching port types (audio to audio, text to text).
"""

from collections import Counter

from vocalis.config import AgentConfig, Node
from vocalis.issues import Issue
from vocalis.schema import node_ports

REQUIRED_ONCE = ("stt", "llm", "tts")
OPTIONAL_ONCE = ("vad",)


def order_chain(config: AgentConfig) -> tuple[list[Node], list[Issue]]:
    """Return the nodes in pipeline order, or the issues that prevent it.

    The chain is only returned when there are no issues.
    """
    ports = node_ports()
    issues: list[Issue] = []

    nodes: dict[str, Node] = {}
    for i, node in enumerate(config.nodes):
        if node.id in nodes:
            issues.append(Issue(f'duplicate node id "{node.id}"', node_id=node.id, node_index=i))
        else:
            nodes[node.id] = node

    next_node: dict[str, str] = {}
    prev_node: dict[str, str] = {}
    for i, edge in enumerate(config.edges):
        unknown = [end for end in (edge.source, edge.target) if end not in nodes]
        if unknown:
            for end in unknown:
                issues.append(Issue(f'cable to unknown node "{end}"', edge_index=i))
            continue
        if edge.source == edge.target:
            issues.append(Issue("can't be patched into itself", node_id=edge.source, edge_index=i))
            continue

        source, target = nodes[edge.source], nodes[edge.target]
        out_type, in_type = ports[source.type].output, ports[target.type].input
        if out_type != in_type:
            issues.append(
                Issue(
                    f'"{source.id}" outputs {out_type} but "{target.id}" takes {in_type} input',
                    node_id=target.id,
                    edge_index=i,
                )
            )
        if source.id in next_node:
            issues.append(
                Issue("has more than one outgoing cable", node_id=source.id, edge_index=i)
            )
        if target.id in prev_node:
            issues.append(
                Issue("has more than one incoming cable", node_id=target.id, edge_index=i)
            )
        next_node.setdefault(source.id, target.id)
        prev_node.setdefault(target.id, source.id)

    issues += _count_issues(list(nodes.values()))
    if issues:
        return [], issues

    heads = [node for node in nodes.values() if node.id not in prev_node]
    if not heads:
        return [], [Issue("the cables form a loop; the pipeline needs a first node")]
    if len(heads) > 1:
        starts = ", ".join(f'"{node.id}"' for node in heads)
        return [], [
            Issue(
                f"not connected to the rest of the pipeline (chains start at {starts})",
                node_id=node.id,
            )
            for node in heads
        ]

    # Every node has at most one incoming cable and the head has none, so walking
    # forward from the head can't revisit a node.
    chain = [heads[0]]
    while chain[-1].id in next_node:
        chain.append(nodes[next_node[chain[-1].id]])
    if len(chain) != len(nodes):
        in_chain = {node.id for node in chain}
        return [], [
            Issue("is part of a loop that isn't connected to the pipeline", node_id=node_id)
            for node_id in nodes
            if node_id not in in_chain
        ]

    issues = _endpoint_issues(chain)
    return ([] if issues else chain), issues


def _count_issues(nodes: list[Node]) -> list[Issue]:
    counts = Counter(node.type for node in nodes)
    issues = []
    for node_type in REQUIRED_ONCE:
        if counts[node_type] == 0:
            issues.append(Issue(f"the pipeline needs a {node_type} node"))
    for node_type in (*REQUIRED_ONCE, *OPTIONAL_ONCE):
        if counts[node_type] > 1:
            issues += [
                Issue(f"only one {node_type} node is supported in a pipeline", node_id=node.id)
                for node in nodes
                if node.type == node_type
            ]
    return issues


def _endpoint_issues(chain: list[Node]) -> list[Issue]:
    ports = node_ports()
    issues = []
    first, last = chain[0], chain[-1]
    if ports[first.type].input != "audio":
        issues.append(
            Issue(
                f"is first in the pipeline, so it receives mic audio, but it takes "
                f"{ports[first.type].input} input",
                node_id=first.id,
            )
        )
    if ports[last.type].output != "audio":
        issues.append(
            Issue(
                f"is last in the pipeline, so its output is played back, but it outputs "
                f"{ports[last.type].output}",
                node_id=last.id,
            )
        )

    positions = {node.type: i for i, node in enumerate(chain)}
    if "vad" in positions and positions["vad"] > positions["stt"]:
        vad = chain[positions["vad"]]
        issues.append(Issue("vad must come before stt", node_id=vad.id))
    return issues
