from pipecat.services.anthropic.llm import AnthropicLLMService


def create(params, ctx):
    settings = AnthropicLLMService.Settings(
        model=params["model"],
        system_instruction=ctx.node.system_prompt,
    )
    if "max_tokens" in params:
        settings.max_tokens = params["max_tokens"]
    if "effort" in params:
        # Pipecat merges `extra` into each request; extra_body reaches the API as-is.
        settings.extra = {"extra_body": {"output_config": {"effort": params["effort"]}}}

    return AnthropicLLMService(api_key=ctx.secret("ANTHROPIC_API_KEY"), settings=settings)
