"""
API endpoints for prompt management.
Can be included in any service to provide prompt management capabilities.
"""

from fastapi import APIRouter
from typing import Dict, Any
from prompt_manager import PromptManager

# Create router for prompt management endpoints
prompt_router = APIRouter(prefix="/prompts", tags=["prompts"])

@prompt_router.get("/list")
def list_prompts():
    """List all available prompts with descriptions."""
    return {
        "prompts": PromptManager.list_prompts(),
        "metadata": PromptManager.get_prompt_metadata()
    }

@prompt_router.get("/{prompt_name}")
def get_prompt_info(prompt_name: str):
    """Get information about a specific prompt."""
    try:
        metadata = PromptManager.get_prompt_metadata().get(prompt_name)
        if not metadata:
            return {"error": f"Prompt '{prompt_name}' not found"}
        
        return {
            "name": prompt_name,
            "metadata": metadata,
            "template": getattr(PromptManager, prompt_name, None)
        }
    except Exception as e:
        return {"error": str(e)}

@prompt_router.post("/validate")
def validate_prompt_format(prompt_name: str, test_data: Dict[str, Any]):
    """Validate that a prompt can be formatted with test data."""
    try:
        formatted_prompt = PromptManager.get_prompt(prompt_name, **test_data)
        return {
            "valid": True,
            "formatted_prompt": formatted_prompt,
            "length": len(formatted_prompt)
        }
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }
