"""Run a compiled agent until the user hangs up, printing the conversation."""

from collections.abc import Callable

from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.transports.base_transport import BaseTransport
from pipecat.workers.runner import WorkerRunner

from vocalis import CompiledAgent


async def run_session(
    agent: CompiledAgent,
    transport: BaseTransport,
    echo: Callable[[str], None] = print,
) -> None:
    worker = PipelineWorker(
        agent.pipeline(transport),
        params=PipelineParams(enable_metrics=True, enable_usage_metrics=True),
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
