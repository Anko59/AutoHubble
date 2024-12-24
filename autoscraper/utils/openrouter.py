"""OpenRouter API client utilities."""

import json
import os
import random
import re
import time
from typing import TypeVar

import chompjs
import tiktoken
from loguru import logger
from openai import APIError, APITimeoutError, OpenAI, RateLimitError
from pydantic import BaseModel
from pydantic_core import ValidationError

from ..config import MODELS, OPENROUTER_BASE_URL, OPENROUTER_HEADERS, MODEL_CHOICES, Model

T = TypeVar("T", bound=BaseModel)


class OpenRouterClient:
    """Client for making OpenRouter API calls with retries."""

    def __init__(self) -> None:
        """Initialize the OpenRouter client."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")

        self.client = OpenAI(
            api_key=api_key,
            base_url=OPENROUTER_BASE_URL,
            default_headers=OPENROUTER_HEADERS,
        )
        self.encoding = tiktoken.get_encoding("cl100k_base")

    def get_completion(
        self,
        model_role: str,
        system_prompt: str,
        user_content: dict,
        response_model: type[T],
    ) -> T:
        """Get a completion from OpenRouter with retries.

        Args:
            model_role: Role of the model to use
            system_prompt: System prompt for the model
            user_content: Content to send to the model
            response_model: Pydantic model for response parsing

        Returns:
            Parsed response in the specified model type
        """
        # Convert content to string and count tokens
        content_str = json.dumps(user_content)

        for model_name in MODEL_CHOICES[model_role]:
            model_config = MODELS[model_name]
            max_tokens = model_config.context_length

            total_tokens = len(self.encoding.encode(system_prompt + content_str))

            # Truncate content if needed
            if total_tokens > max_tokens:
                content_str = self._truncate_content(content_str, system_prompt, max_tokens)

            response = self._try_model(model_config, system_prompt, content_str, response_model)
            if response:
                return response

        raise Exception(f"All models failed for {model_role}")

    def _truncate_content(self, content_str: str, system_prompt: str, max_tokens: int) -> str:
        # Reserve 20% for system prompt and response
        available_tokens = int(max_tokens * 0.8)
        system_tokens = len(self.encoding.encode(system_prompt))
        content_tokens = len(self.encoding.encode(content_str))

        if content_tokens > available_tokens:
            # Calculate the number of characters to keep
            keep_ratio = available_tokens / content_tokens
            keep_chars = int(len(content_str) * keep_ratio)

            # Keep 10% at the beginning and end
            keep_end = int(keep_chars * 0.1)
            beginning = content_str[:keep_end]
            end = content_str[-keep_end:]

            # Middle section to be truncated
            middle = content_str[keep_end:-keep_end]

            # Split the middle into chunks (paragraphs or large sentences)
            chunks = re.split(r"(\n{2,}|\. )", middle)

            # Randomly select chunks to keep
            total_chars = sum(len(chunk) for chunk in chunks)
            keep_middle_chars = keep_chars - 2 * keep_end

            selected_chunks = []
            current_chars = 0

            while current_chars < keep_middle_chars and chunks:
                chunk = chunks.pop(random.randint(0, len(chunks) - 1))
                if current_chars + len(chunk) <= keep_middle_chars:
                    selected_chunks.append(chunk)
                    current_chars += len(chunk)

            # Combine the parts
            truncated_middle = "".join(selected_chunks)
            content_str = beginning + truncated_middle + end

            logger.warning(f"Content truncated to fit context window ({content_tokens} -> {available_tokens} tokens)")

        return content_str

    def _try_model(self, model: Model, system_prompt: str, content_str: str, response_model: type[T]) -> T | None:
        retries = 0
        while retries < model.retries:
            logger.debug(f"Sending request to {model.name} (attempt {retries + 1})")
            try:
                if model.structured_output:
                    return self._handle_structured_output(model, system_prompt, content_str, response_model)
                else:
                    return self._handle_unstructured_output(model, system_prompt, content_str, response_model)
            except (APIError, APITimeoutError, RateLimitError, TypeError, ValidationError) as e:
                retries += 1
                if retries < model.retries:
                    logger.warning(f"API error: {str(e)}, retrying in {2 ** retries} seconds...")
                    time.sleep(2**retries)  # Exponential backoff
                else:
                    logger.error(f"Failed after {model.retries} attempts with {model.name}")
                    return None

        return None

    def _get_extra_body(self, model: Model) -> dict:
        if model.providers:
            return {"provider": {"order": [provider.value for provider in model.providers]}}
        return {}

    def _handle_structured_output(self, model: Model, system_prompt: str, content_str: str, response_model: type[T]) -> T:
        extra_body = self._get_extra_body(model)
        if model.pydantic_output:
            completion = self.client.beta.chat.completions.parse(
                model=model.name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_str},
                ],
                response_format=response_model,
                **({"extra_body": extra_body} if extra_body else {}),
            )
            return completion.choices[0].message.parsed
        else:
            completion = self.client.chat.completions.create(
                model=model.name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content_str},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "strict": True,
                        "schema": response_model.model_json_schema(),
                    },
                },
                **({"extra_body": extra_body} if extra_body else {}),
            )
            parsed_content = chompjs.parse_js_object(completion.choices[0].message.content)
            return response_model(**parsed_content)

    def _handle_unstructured_output(self, model: Model, system_prompt: str, content_str: str, response_model: type[T]) -> T:
        extra_body = self._get_extra_body(model)
        completion = self.client.chat.completions.create(
            model=model.name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content_str},
            ],
            **({"extra_body": extra_body} if extra_body else {}),
        )
        unstructured_response = completion.choices[0].message.content
        return self.structure_response(unstructured_response, response_model)

    def structure_response(self, unstructured_response: str, response_model: type[T]) -> T:
        """Structure the unstructured response using the structurer model."""
        structurer_model = MODELS[MODEL_CHOICES["structurer"]]
        system_prompt = f"Structure the following response according to this schema: {response_model.model_json_schema()}"

        extra_body = self._get_extra_body(structurer_model)
        completion = self.client.beta.chat.completions.parse(
            model=structurer_model.name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": unstructured_response},
            ],
            response_format=response_model,
            **({"extra_body": extra_body} if extra_body else {}),
        )

        return completion.choices[0].message.parsed
