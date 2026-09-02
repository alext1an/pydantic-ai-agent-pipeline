from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models import Model
from myagent.core.config import Settings

def build_model(settings:Settings) -> Model:
    provider = OpenAIProvider(
        base_url=settings.BASE_URL,
        api_key=settings.API_KEY.get_secret_value(),
    )
    return OpenAIChatModel(settings.DEFAULT_LLM_MODEL, provider=provider)