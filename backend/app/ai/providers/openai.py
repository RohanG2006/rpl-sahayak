"""OpenAI provider. Only this module imports the OpenAI SDK (pip install -r requirements-ai.txt)."""
import base64

from app.ai.providers.base import ImageInput, ProviderError


class OpenAIProvider:
    name = "openai"

    def __init__(self, api_key: str, model: str, timeout: float):
        if not api_key:
            raise ProviderError("OPENAI_API_KEY is not set")
        try:
            from openai import OpenAI  # noqa: PLC0415
        except ImportError as e:  # pragma: no cover
            raise ProviderError("openai package not installed") from e
        self._client = OpenAI(api_key=api_key, timeout=timeout)
        self.model = model

    def complete_json(self, system: str, user: str, json_schema: dict, images: list[ImageInput] | None = None) -> str:
        content: list[dict] = [{"type": "text", "text": user}]
        for img in images or []:
            b64 = base64.b64encode(img.data).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:{img.mime};base64,{b64}"}})
        try:
            resp = self._client.chat.completions.create(
                model=self.model,
                temperature=0.1,
                response_format={"type": "json_object"},
                messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
            )
        except Exception as e:
            raise ProviderError(f"OpenAI call failed: {type(e).__name__}") from e
        return resp.choices[0].message.content or ""
