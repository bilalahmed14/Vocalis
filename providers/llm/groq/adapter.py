from pipecat.services.groq.llm import GroqLLMService

OPTIONAL = ("temperature", "max_tokens")


def create(params, ctx):
    return GroqLLMService(
        api_key=ctx.secret("GROQ_API_KEY"),
        settings=GroqLLMService.Settings(
            model=params["model"],
            system_instruction=ctx.node.system_prompt,
            **{key: params[key] for key in OPTIONAL if key in params},
        ),
    )
