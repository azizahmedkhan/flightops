# LLM Message Tracking Feature

This document describes the LLM message tracking feature that has been added to the FlightOps system to display all prompts and responses from LLM interactions across all pages.

## Overview

The LLM message tracking feature provides real-time visibility into all LLM interactions across the FlightOps system. It displays prompts sent to the LLM and the responses received, along with metadata such as timing, token usage, and service information.

## Components

### Frontend Components

#### 1. LLMMessageDisplay Component
- **Location**: `ui/web/src/app/components/LLMMessageDisplay.tsx`
- **Purpose**: Displays LLM messages in a collapsible panel
- **Features**:
  - Real-time message updates
  - Service-specific color coding
  - Copy to clipboard functionality
  - Message filtering and search
  - Clear all messages
  - Refresh messages from backend

#### 2. LLMTestComponent
- **Location**: `ui/web/src/app/components/LLMTestComponent.tsx`
- **Purpose**: Test component to trigger LLM calls for testing
- **Features**:
  - One-click LLM call testing
  - Real-time message tracking verification

#### 3. LLM API Service
- **Location**: `ui/web/src/app/services/llmApi.ts`
- **Purpose**: API client for LLM message operations
- **Features**:
  - Fetch messages from backend
  - Track new messages
  - Clear messages
  - Custom event dispatching

### Backend Components

#### 1. LLM Tracker
- **Location**: `services/shared/llm_tracker.py`
- **Purpose**: Centralized LLM message tracking utilities
- **Features**:
  - Message creation and formatting
  - Timing and token usage tracking
  - Service metadata collection
  - Decorator for automatic tracking

#### 2. Gateway API Endpoints
- **Location**: `services/gateway-api/main.py`
- **Endpoints**:
  - `POST /llm/track` - Track a new LLM message
  - `GET /llm/messages` - Retrieve LLM messages
  - `DELETE /llm/messages` - Clear all messages

#### 3. Service Integration
- **Modified Services**:
  - `agent-svc` - Tracks rebooking optimization LLM calls
  - `comms-svc` - Tracks tone rewriting, translation, and sentiment analysis
  - `gateway-api` - Central message collection and API endpoints

## Implementation Details

### Message Structure

Each LLM message contains:
```json
{
  "id": "unique-message-id",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "agent-svc",
  "prompt": "The prompt sent to the LLM",
  "response": "The response from the LLM",
  "model": "gpt-4o-mini",
  "tokens_used": 150,
  "duration_ms": 1250,
  "metadata": {
    "function": "optimize_rebooking_with_llm",
    "flight_no": "NZ123",
    "passenger_count": 150
  }
}
```

### Service Integration

#### Agent Service
- Tracks LLM calls in `optimize_rebooking_with_llm` function
- Includes flight and passenger context in metadata
- Returns LLM message in API responses

#### Communications Service
- Tracks LLM calls in:
  - `llm_rewrite_for_tone` - Tone adjustment
  - `translate_communication` - Translation
  - `analyze_sentiment_with_llm` - Sentiment analysis
- Includes language and context metadata

#### Gateway API
- Collects LLM messages from all services
- Provides REST API for message management
- Stores messages in memory (configurable for production)

## Usage

### Viewing LLM Messages

1. **Fixed Position Display**: The LLM message display appears as a fixed panel in the bottom-right corner of all pages
2. **Expandable Panel**: Click the chevron icon to expand/collapse the message list
3. **Real-time Updates**: Messages appear automatically as LLM calls are made
4. **Service Filtering**: Messages are color-coded by service for easy identification

### Testing the Feature

1. **Test Component**: Use the "Test LLM Call" button on the home page
2. **Real Usage**: Navigate to any page and perform actions that trigger LLM calls:
   - Query page: Ask flight questions
   - Communications page: Draft communications
   - Search page: Search for policies

### API Usage

#### Fetch Messages
```javascript
const response = await fetch('/llm/messages?limit=50&service=agent-svc')
const data = await response.json()
```

#### Track New Message
```javascript
const message = {
  id: 'unique-id',
  timestamp: new Date().toISOString(),
  service: 'my-service',
  prompt: 'Test prompt',
  response: 'Test response',
  model: 'gpt-4'
}

await fetch('/llm/track', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(message)
})
```

## Configuration

### Environment Variables

- `NEXT_PUBLIC_GATEWAY_URL`: Gateway API URL for frontend
- `OPENAI_API_KEY`: OpenAI API key for LLM calls
- `CHAT_MODEL`: LLM model to use (default: gpt-4o-mini)

### Service Configuration

Each service can be configured to track LLM messages by:
1. Importing the `LLMTracker` from `services/shared/llm_tracker.py`
2. Wrapping LLM calls with tracking
3. Including the LLM message in API responses

## Production Considerations

### Scalability
- **Current**: In-memory storage (suitable for development)
- **Production**: Consider Redis or database storage
- **Persistence**: Implement message persistence for historical analysis

### Performance
- **Message Limit**: Currently limited to 1000 messages in memory
- **Real-time Updates**: Uses custom events for immediate updates
- **API Rate Limiting**: Consider rate limiting for message endpoints

### Security
- **PII Scrubbing**: Ensure sensitive data is scrubbed from prompts
- **Access Control**: Implement proper authentication for message endpoints
- **Data Retention**: Consider data retention policies for compliance

## Troubleshooting

### Common Issues

1. **Messages Not Appearing**:
   - Check if services are running
   - Verify API endpoints are accessible
   - Check browser console for errors

2. **LLM Calls Not Tracked**:
   - Ensure services are using the LLMTracker
   - Check that LLM calls are wrapped with tracking
   - Verify API responses include LLM messages

3. **Performance Issues**:
   - Reduce message limit if memory usage is high
   - Implement message pagination
   - Consider message archiving

### Debug Mode

Enable debug logging by setting environment variables:
```bash
DEBUG_LLM_TRACKING=true
LOG_LEVEL=debug
```

## Future Enhancements

1. **Message Search**: Add search functionality for messages
2. **Analytics Dashboard**: Create analytics for LLM usage patterns
3. **Message Export**: Export messages for analysis
4. **Real-time Collaboration**: Share messages across team members
5. **Performance Metrics**: Track LLM performance and costs
6. **Message Templates**: Save and reuse common prompts
7. **Integration Monitoring**: Monitor LLM service health

## Contributing

When adding new LLM calls to services:

1. Import `LLMTracker` from `services/shared/llm_tracker.py`
2. Wrap LLM calls with timing and tracking
3. Include relevant metadata in the message
4. Return LLM message in API responses
5. Test the integration with the frontend display

## Support

For issues or questions about the LLM message tracking feature:
1. Check the troubleshooting section above
2. Review service logs for errors
3. Verify API endpoints are working
4. Test with the provided test component
