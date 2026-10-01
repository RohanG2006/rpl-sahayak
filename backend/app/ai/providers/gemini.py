"""Google Gemini provider. Only this module imports the Gemini SDK (pip install -r requirements-ai.txt)."""
from app.ai.providers.base import ImageInput, ProviderError


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str, timeout: float):
        if not api_key:
            raise ProviderError("GEMINI_API_KEY is not set")
        try:
            from google import genai  # noqa: PLC0415
        except ImportError as e:  # pragma: no cover
            raise ProviderError("google-genai package not installed") from e
        self._genai = genai
        self._client = genai.Client(api_key=api_key, http_options={"timeout": int(timeout * 1000)})
        self.model = model

    def complete_json(self, system: str, user: str, json_schema: dict, images: list[ImageInput] | None = None) -> str:
        types = self._genai.types
        parts = [types.Part.from_text(text=user)]
        for img in images or []:
            parts.append(types.Part.from_bytes(data=img.data, mime_type=img.mime))
        try:
            resp = self._client.models.generate_content(
                model=self.model,
                contents=[types.Content(role="user", parts=parts)],
                config=types.GenerateContentConfig(
                    system_instruction=system, response_mime_type="application/json", temperature=0.1
                ),
            )
        except Exception as e:  # network / auth / quota
            raise ProviderError(f"Gemini call failed: {type(e).__name__}") from e
        return resp.text or ""
