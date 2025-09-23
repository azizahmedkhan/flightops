"""
Centralized LLM client for FlightOps services.
Provides a single interface for all OpenAI chat completions with built-in logging and tracking.
"""

import json
import os
import time
from typing import Any, Dict, List, Optional, Union

import requests
from loguru import logger
from openai import OpenAI
try:
    from .llm_tracker import LLMTracker
except ImportError:  # pragma: no cover - fallback for path-based imports
    from llm_tracker import LLMTracker


class LLMClient:
    """Centralized LLM client with built-in logging and tracking."""
    
    def __init__(self, service_name: str, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM client.
        
        Args:
            service_name: Name of the service using this client
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Default model to use for completions
        """
        self.service_name = service_name
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.gateway_url = os.getenv("GATEWAY_URL", "http://gateway-api:8080")
        
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass api_key parameter.")
        
        self.client = OpenAI(api_key=self.api_key)

    def _extract_prompt(self, messages: List[Dict[str, str]]) -> str:
        """Return the first user message content for tracking."""
        for message in messages:
            if message.get("role") == "user":
                return message.get("content", "")
        return ""

    @staticmethod
    def _extract_tokens(response: Any) -> Optional[int]:
        """Safely pull total token usage from an OpenAI response."""
        usage = getattr(response, "usage", None)
        return getattr(usage, "total_tokens", None) if usage else None

    @staticmethod
    def _merge_metadata(base: Optional[Dict[str, Any]], **extra: Any) -> Dict[str, Any]:
        """Combine tracked metadata while preserving caller-provided fields."""
        merged: Dict[str, Any] = {
            **{key: value for key, value in extra.items() if key is not None}
        }
        if base:
            merged.update(base)
        return merged

    def _track_and_send(
        self,
        *,
        prompt: str,
        response_text: str,
        model: str,
        duration_ms: float,
        metadata: Optional[Dict[str, Any]] = None,
        tokens_used: Optional[int] = None
    ) -> Dict[str, Any]:
        llm_message = LLMTracker.track_llm_call(
            service_name=self.service_name,
            prompt=prompt,
            response=response_text,
            model=model,
            tokens_used=tokens_used,
            duration_ms=duration_ms,
            metadata=metadata
        )
        self._send_message_to_gateway(llm_message)
        return llm_message
    
    def _send_message_to_gateway(self, message: Dict[str, Any]) -> None:
        """
        Send a tracked LLM message to the gateway API for centralized storage.
        
        Args:
            message: The tracked LLM message to send
        """
        try:
            response = requests.post(
                f"{self.gateway_url}/llm/track",
                json=message,
                timeout=5
            )
            if response.status_code != 200:
                logger.warning(
                    "LLM tracking post returned status {status}",
                    status=response.status_code
                )
        except Exception as exc:  # pragma: no cover - defensive path
            # Don't fail the main operation if tracking fails
            logger.warning("Failed to send LLM message to gateway: {error}", error=exc)
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        function_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        
        start_time = time.time()
        model = model or self.model
        prompt = self._extract_prompt(messages)
        prompt_preview = (prompt[:120] + "...") if len(prompt) > 120 else prompt

        logger.info(
            "chat_completion begin service={} model={} temperature={} max_tokens={} prompt='{}'",
            self.service_name,
            model,
            temperature,
            max_tokens,
            prompt_preview
        )

        logger.debug("LLM request payload", messages=messages, model=model)

        try:
            # Make the API call
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Extract response content
            content = response.choices[0].message.content
            logger.debug("LLM response received", content=content)

            duration_ms = (time.time() - start_time) * 1000

            tracking_metadata = self._merge_metadata(
                metadata,
                function=function_name,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens
            )

            tokens_used = self._extract_tokens(response)

            llm_message = self._track_and_send(
                prompt=prompt,
                response_text=content or "",
                model=model,
                duration_ms=duration_ms,
                metadata=tracking_metadata,
                tokens_used=tokens_used
            )

            logger.info(
                "chat_completion success service={} model={} tokens_used={} duration_ms={:.2f}",
                self.service_name,
                model,
                tokens_used,
                duration_ms
            )

            return {
                "content": content,
                "response": response,
                "llm_message": llm_message,
                "tokens_used": tokens_used,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            error_metadata = self._merge_metadata(
                metadata,
                function=function_name,
                error=True,
                error_type=type(e).__name__,
                error_message=str(e)
            )

            self._track_and_send(
                prompt=prompt,
                response_text=f"Error: {e}",
                model=model,
                duration_ms=duration_ms,
                metadata=error_metadata
            )
            logger.exception(
                "chat_completion error service={} model={} duration_ms={:.2f}",
                self.service_name,
                model,
                duration_ms
            )
            
            # Re-raise the exception
            raise e
    
    def simple_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        function_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        include_tracking: bool = False,
        **kwargs
    ) -> Union[str, Dict[str, Any]]:
        
        messages = [{"role": "user", "content": prompt}]

        result = self.chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            function_name=function_name,
            metadata=metadata,
            **kwargs
        )

        if include_tracking:
            return {
                "content": result["content"],
                "llm_message": result["llm_message"],
                "tokens_used": result["tokens_used"],
                "duration_ms": result["duration_ms"]
            }
        return result["content"]
    
    def json_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        function_name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        fallback_value: Any = None,
        **kwargs
    ) -> Any:
        
        result = self.simple_completion(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            function_name=function_name,
            metadata=metadata,
            include_tracking=True,
            **kwargs
        )
        
        # Extract content from the result
        if isinstance(result, dict):
            content = result.get("content", "")
        else:
            content = str(result)
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            if fallback_value is not None:
                return fallback_value
            raise ValueError(f"Failed to parse JSON response: {content}")
    
    async def call_function(
        self,
        messages: List[Dict[str, str]],
        function_schema: Dict[str, Any],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call a function using OpenAI's function calling feature.
        
        Args:
            messages: List of message dictionaries
            function_schema: Function schema for OpenAI function calling
            model: Model to use (defaults to self.model)
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            metadata: Additional metadata for tracking
            **kwargs: Additional arguments for chat completion
            
        Returns:
            Dictionary containing the function call response
        """
        try:
            start_time = time.time()
            model = model or self.model
            prompt = self._extract_prompt(messages)
            prompt_preview = (prompt[:120] + "...") if len(prompt) > 120 else prompt

            logger.info(
                "call_function begin service={} model={} function={} prompt='{}'",
                self.service_name,
                model,
                function_schema["name"],
                prompt_preview
            )

            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                functions=[function_schema],
                function_call={"name": function_schema["name"]},
                **kwargs
            )

            message = response.choices[0].message
            content = message.content or ""
            function_call = message.function_call

            duration_ms = (time.time() - start_time) * 1000
            tokens_used = self._extract_tokens(response)

            call_metadata = self._merge_metadata(
                metadata,
                function=function_schema["name"],
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                function_call={
                    "name": function_call.name,
                    "arguments": function_call.arguments
                } if function_call else None
            )

            llm_message = self._track_and_send(
                prompt=prompt,
                response_text=content,
                model=model,
                duration_ms=duration_ms,
                metadata=call_metadata,
                tokens_used=tokens_used
            )

            logger.info(
                "call_function success service={} model={} function={} tokens_used={} duration_ms={:.2f}",
                self.service_name,
                model,
                function_schema["name"],
                tokens_used,
                duration_ms
            )

            return {
                "function_call": function_call,
                "content": content,
                "llm_message": llm_message,
                "tokens_used": tokens_used,
                "duration_ms": duration_ms
            }
                
        except Exception as e:
            logger.exception(
                "call_function error service={} model={} function={}",
                self.service_name,
                model,
                function_schema["name"]
            )
            raise


# Convenience function to create a client for a service
def create_llm_client(service_name: str, model: str = "gpt-4o-mini") -> LLMClient:
    return LLMClient(service_name=service_name, model=model)
