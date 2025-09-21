"""
Centralized LLM client for FlightOps services.
Provides a single interface for all OpenAI chat completions with built-in logging and tracking.
"""

import json
import time
import os
import requests
from typing import Dict, Any, Optional, List, Union
from openai import OpenAI
from .llm_tracker import LLMTracker


class LLMClient:
    """Centralized LLM client with built-in logging and tracking."""
    
    def __init__(self, service_name: str, api_key: Optional[str] = None, model: str = "gpt-4"):
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
                print(f"Warning: Failed to send LLM message to gateway: {response.status_code}")
        except Exception as e:
            # Don't fail the main operation if tracking fails
            print(f"Warning: Failed to send LLM message to gateway: {e}")
    
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
        
        # Extract prompt for logging (first user message)
        prompt = ""
        for message in messages:
            if message.get("role") == "user":
                prompt = message.get("content", "")
                break

        print(f"DEBUG: LLM message in client: {messages}")

        
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
            print(f"DEBUG: LLM response: {content}")

            duration_ms = (time.time() - start_time) * 1000
            
            # Prepare tracking metadata
            tracking_metadata = {
                "function": function_name,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                **(metadata or {})
            }
            
            # Track the LLM call
            llm_message = LLMTracker.track_llm_call(
                service_name=self.service_name,
                prompt=prompt,
                response=content,
                model=model,
                tokens_used=response.usage.total_tokens if response.usage else None,
                duration_ms=duration_ms,
                metadata=tracking_metadata
            )
            
            # Send the tracked message to the gateway API
            self._send_message_to_gateway(llm_message)
            
            return {
                "content": content,
                "response": response,
                "llm_message": llm_message,
                "tokens_used": response.usage.total_tokens if response.usage else None,
                "duration_ms": duration_ms
            }
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            # Track the error
            error_metadata = {
                "function": function_name,
                "error": True,
                "error_type": type(e).__name__,
                "error_message": str(e),
                **(metadata or {})
            }
            
            error_message = LLMTracker.track_llm_call(
                service_name=self.service_name,
                prompt=prompt,
                response=f"Error: {str(e)}",
                model=model,
                duration_ms=duration_ms,
                metadata=error_metadata
            )
            
            # Send the error message to the gateway API
            self._send_message_to_gateway(error_message)
            
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
        else:
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


# Convenience function to create a client for a service
def create_llm_client(service_name: str, model: str = "gpt-4") -> LLMClient:
    return LLMClient(service_name=service_name, model=model)
