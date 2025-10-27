"""
LLM message tracking utilities for AeroOps services.
Provides centralized tracking of all LLM interactions across services.
"""

import json
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime


class LLMTracker:
    """Centralized LLM message tracking system."""
    
    @staticmethod
    def track_llm_call(
        service_name: str,
        prompt: str,
        response: str,
        model: str = "gpt-4o-mini",
        tokens_used: Optional[int] = None,
        duration_ms: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Track an LLM call and return the message data.
        
        Args:
            service_name: Name of the service making the call
            prompt: The prompt sent to the LLM
            response: The response received from the LLM
            model: The model used (default: gpt-4o-mini)
            tokens_used: Number of tokens used (if available)
            duration_ms: Duration of the call in milliseconds (if available)
            metadata: Additional metadata about the call
            
        Returns:
            Dictionary containing the tracked message data
        """
        message = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat(),
            "service": service_name,
            "prompt": prompt,
            "response": response,
            "model": model,
            "tokens_used": tokens_used,
            "duration_ms": duration_ms,
            "metadata": metadata or {}
        }
        
        return message
    
    @staticmethod
    def create_llm_wrapper(service_name: str, original_function):
        """
        Create a wrapper function that tracks LLM calls.
        
        Args:
            service_name: Name of the service
            original_function: The original LLM function to wrap
            
        Returns:
            Wrapped function that tracks calls
        """
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Call the original function
                result = original_function(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract prompt and response from the result
                # This assumes the function returns a dict with 'prompt' and 'response' keys
                if isinstance(result, dict):
                    prompt = result.get('prompt', '')
                    response = result.get('response', '')
                    model = result.get('model', 'gpt-4o-mini')
                    tokens_used = result.get('tokens_used')
                    metadata = result.get('metadata', {})
                    
                    # Track the message
                    message = LLMTracker.track_llm_call(
                        service_name=service_name,
                        prompt=prompt,
                        response=response,
                        model=model,
                        tokens_used=tokens_used,
                        duration_ms=duration_ms,
                        metadata=metadata
                    )
                    
                    # Add the message to the result
                    result['llm_message'] = message
                
                return result
                
            except Exception as e:
                # Track failed calls too
                duration_ms = (time.time() - start_time) * 1000
                
                error_message = LLMTracker.track_llm_call(
                    service_name=service_name,
                    prompt=str(args[0]) if args else '',
                    response=f"Error: {str(e)}",
                    model=kwargs.get('model', 'gpt-4o-mini'),
                    duration_ms=duration_ms,
                    metadata={'error': True, 'error_type': type(e).__name__}
                )
                
                # Re-raise the exception
                raise e
        
        return wrapper


def track_openai_call(service_name: str, model: str):
    """
    Decorator to track OpenAI API calls.
    
    Usage:
        @track_openai_call("agent-svc", "gpt-4o-mini")
        def my_llm_function(prompt: str) -> str:
            # Your LLM logic here
            return response
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Call the original function
                result = func(*args, **kwargs)
                
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Extract prompt from args (assuming first arg is the prompt)
                prompt = str(args[0]) if args else ''
                
                # Extract response from result
                if isinstance(result, str):
                    response = result
                elif isinstance(result, dict):
                    response = result.get('content', str(result))
                else:
                    response = str(result)
                
                # Track the message
                message = LLMTracker.track_llm_call(
                    service_name=service_name,
                    prompt=prompt,
                    response=response,
                    model=model,
                    duration_ms=duration_ms
                )
                
                # Store the message (you might want to send this to a central store)
                # For now, we'll just return it in the result
                if isinstance(result, dict):
                    result['llm_message'] = message
                else:
                    # If result is not a dict, wrap it
                    return {
                        'content': result,
                        'llm_message': message
                    }
                
                return result
                
            except Exception as e:
                # Track failed calls
                duration_ms = (time.time() - start_time) * 1000
                
                error_message = LLMTracker.track_llm_call(
                    service_name=service_name,
                    prompt=str(args[0]) if args else '',
                    response=f"Error: {str(e)}",
                    model=model,
                    duration_ms=duration_ms,
                    metadata={'error': True, 'error_type': type(e).__name__}
                )
                
                raise e
        
        return wrapper
    return decorator


def send_message_to_frontend(message: Dict[str, Any]):
    """
    Send a message to the frontend via a custom event.
    This would typically be called from the backend service.
    """
    # In a real implementation, you might use WebSockets or Server-Sent Events
    # For now, this is a placeholder for the concept
    print(f"LLM Message: {json.dumps(message, indent=2)}")
