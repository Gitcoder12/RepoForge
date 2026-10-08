"""
RepoForge OpenRouter Provider

Connects RepoForge to multiple AI models
through OpenRouter API.
"""

import os
from typing import Dict, Any, AsyncGenerator

import requests
from dotenv import load_dotenv

from repoforge.models import DEFAULT_MODEL
from repoforge.providers.base import BaseProvider



class OpenRouterProvider(BaseProvider):
    """
    OpenRouter AI Provider.
    """


    name = "openrouter"


    BASE_URL = (
        "https://openrouter.ai/api/v1/chat/completions"
    )


    def __init__(
        self,
        api_key: str | None = None,
    ):

        load_dotenv()


        self.api_key = (
            api_key
            or os.getenv(
                "OPENROUTER_API_KEY"
            )
        )


        if not self.api_key:

            raise ValueError(
                "OPENROUTER_API_KEY not found."
            )


        self._initialize()



    def _initialize(self):

        """
        Reserved for future clients.
        """

        pass



    @property
    def models(self):

        return [

            "openrouter/auto",

            "openai/gpt-5",

            "openai/gpt-5-mini",

            "anthropic/claude-sonnet-4",

            "anthropic/claude-opus-4",

            "google/gemini-2.5-pro",

            "google/gemini-2.5-flash",

            "deepseek/deepseek-chat",

            "meta-llama/llama-3.3-70b-instruct",

            "qwen/qwen3-235b-a22b",

            "mistralai/mistral-large",

        ]



    def get_capabilities(self):

        return {

            "chat": True,

            "stream": False,

            "vision": True,

            "reasoning": True,

            "tools": False,

        }



    def generate(
        self,
        prompt: str,
        model: str = DEFAULT_MODEL,
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs,
    ) -> str:


        messages = []


        if system_prompt:

            messages.append(
                {
                    "role": "system",
                    "content": system_prompt,
                }
            )


        messages.append(

            {
                "role": "user",
                "content": prompt,
            }

        )


        payload: Dict[str, Any] = {

            "model":
                model,

            "messages":
                messages,

            "temperature":
                temperature,

            "max_tokens":
                max_tokens,

        }


        headers = {

            "Authorization":
                f"Bearer {self.api_key}",

            "Content-Type":
                "application/json",

            "HTTP-Referer":
                "https://github.com/Gitcoder12/RepoForge",

            "X-Title":
                "RepoForge",

        }


        try:

            response = requests.post(

                self.BASE_URL,

                headers=headers,

                json=payload,

                timeout=120,

            )


            response.raise_for_status()


            data = response.json()


            return (

                data["choices"][0]
                ["message"]
                ["content"]
                .strip()

            )


        except requests.exceptions.Timeout:

            raise RuntimeError(
                "OpenRouter timeout."
            )


        except requests.exceptions.ConnectionError:

            raise RuntimeError(
                "OpenRouter connection failed."
            )


        except requests.exceptions.HTTPError:

            raise RuntimeError(

                f"OpenRouter error: {response.text}"

            )


        except Exception as error:

            raise RuntimeError(
                f"OpenRouter failed: {error}"
            )



    async def stream(
        self,
        prompt: str,
        system_prompt: str = "",
        **kwargs,
    ) -> AsyncGenerator[str, None]:

        raise NotImplementedError(
            "Streaming not implemented yet."
        )