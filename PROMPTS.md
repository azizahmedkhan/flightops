# FlightOps Copilot - Centralized Prompt Management

This file documents the centralized prompt management system for the FlightOps Copilot microservices. All LLM prompts are now managed from a single location and can be referenced by any service.

## Table of Contents

1. [Centralized Prompt System](#centralized-prompt-system)
2. [Prompt Manager Usage](#prompt-manager-usage)
3. [Available Prompts](#available-prompts)
4. [API Endpoints](#api-endpoints)
5. [Migration Guide](#migration-guide)

---

## Centralized Prompt System

All prompts are now managed in `services/shared/prompt_manager.py` and can be accessed by any service through the `PromptManager` class.

### Key Benefits:
- **Single Source of Truth**: All prompts in one location
- **Consistent Formatting**: Standardized prompt structure
- **Easy Maintenance**: Update prompts without touching service code
- **Type Safety**: Helper methods with proper parameter validation
- **Version Control**: Track prompt changes over time
- **Testing**: Validate prompts with test data

---

## Prompt Manager Usage

### Basic Usage

```python
from prompt_manager import PromptManager

# Get a formatted prompt
prompt = PromptManager.get_prompt('REBOOKING_OPTIMIZATION', 
                                 flight_no='NZ123', 
                                 origin='AKL', 
                                 destination='SYD')

# Use helper methods for complex prompts
prompt = PromptManager.get_rebooking_optimization_prompt(
    flight, impact, passenger_profiles, options
)
```

### Available Methods

1. **`get_prompt(prompt_name, **kwargs)`** - Generic prompt formatter
2. **`get_rebooking_optimization_prompt(...)`** - Agent service helper
3. **`get_tone_rewrite_prompt(...)`** - Comms service helper
4. **`get_translation_prompt(...)`** - Comms service helper
5. **`get_sentiment_analysis_prompt(...)`** - Comms service helper
6. **`get_disruption_prediction_prompt(...)`** - Predictive service helper
7. **`get_crew_analysis_prompt(...)`** - Crew service helper

---

## Available Prompts

### 1. REBOOKING_OPTIMIZATION
- **Service**: agent-svc
- **Purpose**: Optimize airline rebooking options
- **Temperature**: 0.3
- **Format**: JSON

### 2. TONE_REWRITE
- **Service**: comms-svc
- **Purpose**: Rewrite communications to match tone
- **Temperature**: 0.7
- **Format**: Plain Text

### 3. TRANSLATION
- **Service**: comms-svc
- **Purpose**: Translate with cultural adaptation
- **Temperature**: 0.3
- **Format**: Plain Text

### 4. SENTIMENT_ANALYSIS
- **Service**: comms-svc
- **Purpose**: Analyze customer sentiment
- **Temperature**: 0.3
- **Format**: JSON

### 5. DISRUPTION_PREDICTION
- **Service**: predictive-svc
- **Purpose**: Predict flight disruptions
- **Temperature**: 0.3
- **Format**: JSON

### 6. CREW_ANALYSIS
- **Service**: crew-svc
- **Purpose**: Analyze crew situations
- **Temperature**: 0.3
- **Format**: JSON

---

## API Endpoints

Include `prompt_api.py` in any service to add prompt management endpoints:

```python
from prompt_api import prompt_router
app.include_router(prompt_router)
```

### Available Endpoints:
- `GET /prompts/list` - List all prompts
- `GET /prompts/{prompt_name}` - Get specific prompt info
- `POST /prompts/validate` - Validate prompt formatting

---

## Migration Guide

### Before (Old Way):
```python
prompt = f"""
Optimize these airline rebooking options...
Flight: {flight.get('flight_no')} from {flight.get('origin')}...
"""
```

### After (New Way):
```python
from prompt_manager import PromptManager

prompt = PromptManager.get_rebooking_optimization_prompt(
    flight, impact, passenger_profiles, options
)
```

### Benefits of Migration:
1. **Cleaner Code**: No more long prompt strings in service files
2. **Consistency**: All prompts follow the same format
3. **Maintainability**: Update prompts in one place
4. **Testing**: Easy to test prompt formatting
5. **Documentation**: Self-documenting prompt system

---

## Common Patterns and Best Practices

### 1. Temperature Settings
- **0.3**: Used for analytical tasks requiring consistency (risk assessment, optimization)
- **Default (0.7)**: Used for creative tasks (tone rewriting)
- **0.3**: Used for translation and sentiment analysis for consistency

### 2. Response Formats
- **JSON**: Used for structured data that needs to be parsed programmatically
- **Plain Text**: Used for human-readable content (translations, rewrites)

### 3. Error Handling
All prompts include fallback mechanisms:
- If LLM fails, services fall back to rule-based implementations
- JSON parsing errors trigger fallback responses
- API key absence triggers fallback behavior

### 4. Context Preservation
- All prompts include relevant context (flight details, passenger info, etc.)
- Cultural context is provided for translations
- Historical data is included for predictive analysis

### 5. Safety and Guardrails
- Prompts are designed to work within specific domains (airline operations)
- Output formats are constrained to prevent unexpected responses
- Fallback mechanisms ensure system reliability

---

## Usage Notes

1. **API Key Dependency**: All prompts require `OPENAI_API_KEY` environment variable
2. **Model Configuration**: Uses `CHAT_MODEL` environment variable (defaults to GPT-4)
3. **Error Handling**: Each service implements graceful degradation when LLM is unavailable
4. **Rate Limiting**: Consider implementing rate limiting for production use
5. **Monitoring**: All LLM calls are logged for monitoring and debugging

---

## Future Improvements

1. **Few-shot Learning**: Add example inputs/outputs to improve consistency
2. **Prompt Templates**: Create reusable prompt templates for common patterns
3. **A/B Testing**: Implement prompt versioning for optimization
4. **Context Windows**: Optimize for larger context windows as models improve
5. **Streaming**: Implement streaming responses for better user experience
