"""Run a compiled agent until the user hangs up, printing the conversation."""

from collections.abc import Callable

from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.transports.base_transport import BaseTransport
from pipecat.workers.runner import WorkerRunner

from vocalis import CompiledAgent
from vocalis.tracing import CallTrace, CallTracer
from vocalis_cli.metrics import summary, turn_line, waterfall


async def run_session(
    agent: CompiledAgent,
    transport: BaseTransport,
    echo: Callable[[str], None] = print,
    metrics: bool = False,
) -> CallTrace:
    """Run the agent until the user hangs up, and return what each turn cost."""
    tracer = CallTracer(
        agent,
        on_turn=(lambda turn: echo("\n".join([turn_line(turn), *waterfall(turn)])))
        if metrics
        else None,
    )

    worker = PipelineWorker(
        agent.pipeline(transport),
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
        observers=tracer.observers,
    )

    user = agent.context_aggregator.user()
    assistant = agent.context_aggregator.assistant()

    @user.event_handler("on_user_turn_stopped")
    async def on_user_turn_stopped(aggregator, strategy, message):
        if message.content:
            echo(f"you   > {message.content}")

    @assistant.event_handler("on_assistant_turn_stopped")
    async def on_assistant_turn_stopped(aggregator, message):
        if message.content:
            suffix = "  [interrupted]" if message.interrupted else ""
            echo(f"agent > {message.content}{suffix}")

    await WorkerRunner(handle_sigint=True).run(worker)

    if metrics:
        echo("\n".join(summary(tracer.call)))
    return tracer.call
