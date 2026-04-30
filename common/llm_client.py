from abc import ABC, abstractmethod

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from common.config import Settings


class BaseLLMClient(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        raise NotImplementedError


class OpenAIClient(BaseLLMClient):
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = httpx.AsyncClient(timeout=settings.llm_timeout_seconds)

    @retry(
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(3),
        retry=retry_if_exception_type((httpx.HTTPError, RuntimeError)),
        reraise=True,
    )
    async def generate(self, prompt: str) -> str:
        # Повторяем запросы при временных ошибках API (rate limit / transient 5xx).
        if not self.settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        payload = {
            "model": self.settings.llm_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.settings.llm_temperature,
            "max_tokens": self.settings.llm_max_tokens,
            "top_p": self.settings.llm_top_p,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        response = await self.client.post(self.settings.llm_base_url, json=payload, headers=headers)
        if response.status_code in {429, 500, 502, 503, 504}:
            raise RuntimeError(f"Retryable LLM status: {response.status_code}")
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()


class LocalLLMClient(BaseLLMClient):
    def __init__(self, settings: Settings):
        from transformers import pipeline

        self.settings = settings
        model_id = settings.llm_model_path or settings.llm_model
        self.pipe = pipeline("text-generation", model=model_id)

    async def generate(self, prompt: str) -> str:
        # Для локальной модели возвращаем только сгенерированное продолжение.
        out = self.pipe(
            prompt,
            max_new_tokens=self.settings.llm_max_tokens,
            temperature=self.settings.llm_temperature,
            top_p=self.settings.llm_top_p,
            do_sample=True,
        )
        return out[0]["generated_text"][len(prompt):].strip()
