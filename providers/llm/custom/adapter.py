from pipecat.services.openai.llm import OpenAILLMService

OPTIONAL = ("temperature", "max_tokens")


def create(params, ctx):
    return OpenAILLMService(
        api_key=ctx.env.get(params.get("api_key_env", ""), "not-needed"),
        base_url=params["base_url"],
        settings=OpenAILLMService.Settings(
            model=params["model"],
            system_instruction=ctx.node.system_prompt,
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
