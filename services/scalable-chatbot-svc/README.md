# Scalable Chatbot Service

A high-performance, scalable chatbot service designed to handle 1000+ concurrent chat sessions with efficient ChatGPT integration and real-time WebSocket communication.

## 🚀 Features

- **High Concurrency**: Handles 1000+ simultaneous chat sessions
- **Real-time Communication**: WebSocket-based streaming responses
- **Intelligent Caching**: Redis-based response caching to reduce API costs
- **Context Awareness**: Integrates with flight data and policy documents
- **Rate Limiting**: Prevents API abuse and ensures fair usage
- **Health Monitoring**: Built-in health checks and metrics
- **Comprehensive Testing**: Full test suite with load testing capabilities

## 🏗️ Architecture

### Core Components

1. **WebSocket Manager**: Manages real-time connections
2. **Redis Manager**: Handles session context and response caching
3. **Rate Limiter**: Controls ChatGPT API usage
4. **LLM Client**: Efficient integration with OpenAI's ChatGPT
5. **Connection Pool**: Optimized connection management

### Scalability Features

- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Efficient resource utilization
- **Response Streaming**: Real-time user experience
- **Batch Processing**: Optimized API calls
- **Memory Management**: Efficient session handling

## 🛠️ Installation & Setup

### Prerequisites

- Docker and Docker Compose
- Redis server
- OpenAI API key
- Python 3.11+

### Environment Variables

```bash
# Required
OPENAI_API_KEY=your_openai_api_key_here
REDIS_URL=redis://redis:6379

# Optional
CHAT_MODEL=gpt-4o-mini
RETRIEVAL_URL=http://knowledge-engine:8081
AGENT_URL=http://agent-svc:8082
COMMS_URL=http://comms-svc:8083
```

### Docker Setup

```bash
# Build and start the service
docker compose up --build scalable-chatbot-svc

# Check service health
curl http://localhost:8088/health
```

### Manual Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (if not using Docker)
redis-server

# Run the service
uvicorn main:app --host 0.0.0.0 --port 8088
```

## 📡 API Endpoints

### REST API

#### Create Session
```http
POST /chat/session
Content-Type: application/json

{
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "flight_no": "NZ123",
  "date": "2025-01-17"
}
```

#### Send Message (REST)
```http
POST /chat/message
Content-Type: application/json

{
  "session_id": "session-uuid",
  "message": "Hello, I need help with my flight",
  "client_id": "client-uuid"
}
```

#### Get Session Info
```http
GET /chat/session/{session_id}
```

#### Health Check
```http
GET /health
```

#### Metrics
```http
GET /metrics
```

### WebSocket API

#### Connect to Chat
```javascript
const ws = new WebSocket('ws://localhost:8088/ws/{session_id}/{client_id}');

// Send message
ws.send(JSON.stringify({
  message: "Hello, I need help with my flight"
}));

// Receive responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'chunk') {
    // Handle streaming chunk
  } else if (data.type === 'complete') {
    // Handle complete response
  }
};
```

## 🧪 Testing

### Unit Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_chatbot.py -v

# Run with coverage
python -m pytest tests/ --cov=main --cov-report=html
```

### Load Testing

```bash
# Run comprehensive test suite
python tests/run_tests.py --test all --users 100

# Run specific load test
python tests/run_tests.py --test load --users 500

# Run stress test
python tests/run_tests.py --test stress
```

### Performance Benchmarks

The service is designed to handle:

- **Small Load**: 10 users, 30 seconds - 90%+ success rate
- **Medium Load**: 100 users, 60 seconds - 80%+ success rate  
- **High Load**: 500 users, 120 seconds - 70%+ success rate
- **Extreme Load**: 1000 users, 180 seconds - 60%+ success rate

## 🔧 Configuration

### Rate Limiting

```python
# Default rate limits
RATE_LIMITS = {
    "chatgpt_per_session": 30,  # requests per minute
    "session_ttl": 3600,        # seconds
    "response_cache_ttl": 1800  # seconds
}
```

### Redis Configuration

```python
# Session context TTL
SESSION_TTL = 3600  # 1 hour

# Response cache TTL  
CACHE_TTL = 1800    # 30 minutes

# Connection pool settings
REDIS_POOL_SIZE = 10
REDIS_MAX_CONNECTIONS = 100
```

### WebSocket Settings

```python
# Connection management
MAX_CONNECTIONS_PER_SESSION = 10
CONNECTION_TIMEOUT = 300  # seconds
HEARTBEAT_INTERVAL = 30   # seconds
```

## 📊 Monitoring

### Health Checks

The service provides comprehensive health monitoring:

```bash
# Basic health check
curl http://localhost:8088/health

# Detailed metrics
curl http://localhost:8088/metrics
```

### Key Metrics

- **Active Connections**: Current WebSocket connections
- **Active Sessions**: Unique chat sessions
- **Response Times**: P95, P99 latency metrics
- **Success Rates**: Request success percentages
- **Cache Hit Rates**: Redis cache efficiency
- **Rate Limit Usage**: API usage tracking

### Logging

The service uses structured logging with the following levels:

- **INFO**: General operational messages
- **WARNING**: Non-critical issues
- **ERROR**: Error conditions
- **DEBUG**: Detailed debugging information

## 🚦 Performance Optimization

### Best Practices

1. **Connection Pooling**: Reuse HTTP connections
2. **Response Caching**: Cache frequent responses
3. **Batch Processing**: Group API calls when possible
4. **Async Operations**: Use async/await throughout
5. **Memory Management**: Clean up expired sessions
6. **Rate Limiting**: Prevent API abuse

### Scaling Guidelines

1. **Horizontal Scaling**: Run multiple service instances
2. **Load Balancing**: Distribute WebSocket connections
3. **Redis Clustering**: Use Redis cluster for high availability
4. **Connection Limits**: Monitor and adjust connection limits
5. **Resource Monitoring**: Track CPU, memory, and network usage

## 🔒 Security

### Data Protection

- **PII Scrubbing**: Automatic removal of sensitive data
- **Input Sanitization**: Clean user inputs
- **Rate Limiting**: Prevent abuse
- **Session Isolation**: Secure session management

### Access Control

- **API Key Management**: Secure OpenAI API key handling
- **Connection Validation**: Validate WebSocket connections
- **Request Validation**: Validate all incoming requests

## 🐛 Troubleshooting

### Common Issues

1. **WebSocket Connection Fails**
   - Check if service is running on port 8088
   - Verify Redis connection
   - Check firewall settings

2. **High Response Times**
   - Monitor ChatGPT API response times
   - Check Redis performance
   - Review rate limiting settings

3. **Memory Usage High**
   - Check for session leaks
   - Monitor connection cleanup
   - Review caching strategies

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --host 0.0.0.0 --port 8088 --log-level debug
```

## 📈 Performance Tuning

### Redis Optimization

```bash
# Redis configuration for high performance
redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
```

### Python Optimization

```bash
# Use optimized Python interpreter
python -O main.py

# Enable JIT compilation (if available)
python -X jit main.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the troubleshooting section
2. Review the test suite for usage examples
3. Open an issue on GitHub
4. Contact the development team

---

**Built with ❤️ for high-performance chat applications**
