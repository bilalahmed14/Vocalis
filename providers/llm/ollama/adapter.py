from pipecat.services.ollama.llm import OLLamaLLMService

OPTIONAL = ("temperature", "max_tokens")


def create(params, ctx):
    return OLLamaLLMService(
        base_url=params["base_url"],
        settings=OLLamaLLMService.Settings(
            model=params["model"],
            system_instruction=ctx.node.system_prompt,
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
