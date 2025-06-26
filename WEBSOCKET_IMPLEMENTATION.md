# WebSocket Implementation for DIY-MOD

## Overview

The DIY Content Moderation system now supports **real-time WebSocket communication** instead of HTTP polling for processing Reddit and Twitter feeds. This provides significant performance improvements and reduces server load.

## Architecture

### Before (HTTP Polling):
```
Browser Extension → HTTP POST /get_feed → FastAPI Server → Response
```

### After (WebSocket):
```
Browser Extension ↔ WebSocket /ws/{user_id} ↔ FastAPI Server
```

## Key Benefits

1. **Real-time Processing**: Instant communication without polling delays
2. **Reduced Server Load**: No repeated HTTP requests
3. **Better Performance**: Persistent connection eliminates connection overhead
4. **Automatic Fallback**: Falls back to HTTP if WebSocket fails

## Configuration

WebSocket mode is **enabled by default**. To disable it:

```typescript
// In browser extension config
config.api.websocketEnabled = false;
```

## Implementation Details

### Frontend (Browser Extension)

**WebSocket Connector** (`websocket-connector.ts`):
- Establishes WebSocket connection to `/ws/{user_id}`
- Handles reconnection with exponential backoff
- Manages request/response mapping
- Automatic fallback to HTTP polling

**Key Features**:
- Connection management with auto-reconnect
- Request timeout handling
- Error handling and logging
- Graceful degradation to HTTP

### Backend (FastAPI Server)

**WebSocket Endpoint** (`/ws/{user_id}`):
- Accepts real-time connections from extensions
- Processes feed data using existing processors
- Returns processed content immediately
- Handles connection lifecycle

**Message Types**:
- `process_feed`: Feed processing requests
- `processing_response`: Processed feed data
- `connection`: Connection establishment
- `error`: Error responses

## Message Flow

### 1. Connection Establishment
```javascript
// Extension connects
WebSocket connection to ws://localhost:5001/ws/user123

// Server responds
{
  "type": "connection_ack",
  "message": "WebSocket connection established",
  "timestamp": "2025-01-07T15:30:00Z"
}
```

### 2. Feed Processing Request
```javascript
// Extension sends feed data
{
  "type": "process_feed",
  "requestId": "req_1704636600000_abc123",
  "data": {
    "url": "https://www.reddit.com/r/PlasticSurgery",
    "platform": "reddit",
    "response": "<html>...</html>",
    "userId": "user123"
  }
}
```

### 3. Processed Response
```javascript
// Server returns processed content
{
  "type": "processing_response",
  "requestId": "req_1704636600000_abc123",
  "data": {
    "feed": {
      "response": "<html>...processed...</html>"
    },
    "processingTime": "0.34s"
  },
  "timestamp": "2025-01-07T15:30:01Z"
}
```

## Error Handling

### Automatic Fallback
If WebSocket fails, the system automatically falls back to HTTP polling:

```javascript
// WebSocket attempt
try {
  return await connector.processRequest(data, platform);
} catch (error) {
  // Fallback to HTTP
  return await processInterceptedRequest(data, platform);
}
```

### Reconnection Logic
- Exponential backoff: 1s → 2s → 4s → 8s → 16s
- Maximum 5 reconnection attempts
- Falls back to HTTP after max attempts

## Testing

### Enable WebSocket in Production
1. Extension is built with WebSocket enabled by default
2. Server supports WebSocket endpoint `/ws/{user_id}`
3. Load extension and navigate to Reddit/Twitter
4. Check console for WebSocket connection logs

### Logs to Look For

**Extension Console**:
```
DIY-MOD: Connecting to WebSocket: ws://localhost:5001/ws/user123
DIY-MOD: WebSocket connected successfully
DIY-MOD: Processing via WebSocket: home-feed
DIY-MOD: Sent WebSocket processing request: req_1704636600000_abc123
```

**Server Logs**:
```
INFO: Processing WebSocket feed request req_1704636600000_abc123 for user user123
INFO: Successfully processed 24/25 posts
INFO: WebSocket processing completed for req_1704636600000_abc123 in 0.34s
```

## Troubleshooting

### WebSocket Connection Issues
If you see "WebSocket processing failed, falling back to HTTP":
1. Check if server is running on correct port
2. Verify SSH tunnel is active (production)
3. Check browser security settings for WebSocket

### Performance Monitoring
Monitor these metrics:
- WebSocket connection status
- Processing times (should be faster)
- HTTP fallback frequency
- Server logs for WebSocket messages

## Current Status

✅ **WebSocket Implementation**: Complete
✅ **Automatic Fallback**: Working  
✅ **Error Handling**: Implemented
✅ **Extension Built**: Ready for testing
✅ **Server Support**: Available

**Ready for Testing**: Load the extension and check console logs to verify WebSocket usage instead of HTTP polling. 