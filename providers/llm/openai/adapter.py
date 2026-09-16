from pipecat.services.openai.llm import OpenAILLMService

OPTIONAL = ("temperature", "max_tokens")


def create(params, ctx):
    return OpenAILLMService(
        api_key=ctx.secret("OPENAI_API_KEY"),
        base_url=params.get("base_url"),
        settings=OpenAILLMService.Settings(
            model=params["model"],
            system_instruction=ctx.node.system_prompt,
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
