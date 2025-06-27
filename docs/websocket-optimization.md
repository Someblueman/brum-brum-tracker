# WebSocket Reconnection Optimization

## Overview

The WebSocket reconnection logic has been optimized to provide better reliability and user experience. The new `WebSocketReconnectionManager` class provides enhanced features beyond the basic reconnection logic.

## Features

### 1. Enhanced Exponential Backoff
- Configurable initial delay, max delay, and backoff factor
- Jitter added to prevent thundering herd problem
- Smooth progression from fast retries to slower retries

### 2. Connection Health Monitoring
- Heartbeat mechanism using ping/pong messages
- Automatic detection of dead connections
- Configurable ping interval and pong timeout

### 3. Network State Awareness
- Monitors online/offline events
- Attempts reconnection when network comes back online
- Integrates with Page Visibility API

### 4. User Activity Detection
- Optional reconnection triggered by user activity
- Helps conserve resources when user is inactive
- Reconnects quickly when user returns

### 5. Better Error Handling
- Distinguishes between different close codes
- Doesn't reconnect on clean closure (code 1000)
- Configurable max retry attempts

### 6. Event System
- Emit events for connection state changes
- Easy integration with UI updates
- Separate handlers for different events

## Usage Example

```javascript
import { WebSocketReconnectionManager } from './js/websocket-reconnection.js';

// Create connection manager
const wsManager = new WebSocketReconnectionManager(WEBSOCKET_URL, {
    initialDelay: 1000,
    maxDelay: 30000,
    backoffFactor: 1.5,
    jitterFactor: 0.3,
    maxRetries: null, // Unlimited retries
    pingInterval: 30000,
    pongTimeout: 5000,
    reconnectOnUserActivity: true
});

// Register event handlers
wsManager.on('open', (event) => {
    console.log('Connected to WebSocket');
    updateConnectionStatus('connected');
});

wsManager.on('message', (event) => {
    const data = JSON.parse(event.data);
    handleMessage(data);
});

wsManager.on('close', (event) => {
    console.log('Disconnected from WebSocket');
    updateConnectionStatus('disconnected');
});

wsManager.on('reconnecting', ({ attempt, delay }) => {
    console.log(`Reconnecting... Attempt ${attempt} in ${delay}ms`);
    updateConnectionStatus('reconnecting');
});

wsManager.on('reconnected', ({ attempts }) => {
    console.log(`Reconnected after ${attempts} attempts`);
});

wsManager.on('maxRetriesReached', ({ attempts }) => {
    console.error(`Failed to reconnect after ${attempts} attempts`);
    updateConnectionStatus('error');
});

// Connect
wsManager.connect();

// Send messages
wsManager.send({ type: 'ping' });

// Get connection stats
const stats = wsManager.getStats();
console.log('Connection stats:', stats);

// Clean shutdown
wsManager.close();
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `initialDelay` | 1000ms | Initial reconnection delay |
| `maxDelay` | 30000ms | Maximum reconnection delay |
| `backoffFactor` | 1.5 | Exponential backoff multiplier |
| `jitterFactor` | 0.3 | Jitter factor (0-1) to add randomness |
| `maxRetries` | null | Maximum retry attempts (null = unlimited) |
| `pingInterval` | 30000ms | Heartbeat ping interval |
| `pongTimeout` | 5000ms | Timeout waiting for pong response |
| `reconnectOnUserActivity` | true | Reconnect when user becomes active |

## Benefits

1. **Reliability**: Better detection and recovery from connection failures
2. **Performance**: Optimized retry strategy reduces unnecessary connection attempts
3. **Battery Life**: Respects device state and user activity
4. **User Experience**: Faster recovery when conditions improve
5. **Debugging**: Comprehensive event system and statistics

## Migration Guide

To migrate from the existing WebSocket implementation:

1. Import the new manager class
2. Replace direct WebSocket creation with manager instance
3. Update event handlers to use the event system
4. Remove manual reconnection logic
5. Use `wsManager.send()` instead of `websocket.send()`

## Testing

The reconnection logic can be tested by:

1. **Network Disconnection**: Disable network and re-enable
2. **Server Restart**: Stop and start the WebSocket server
3. **Page Visibility**: Switch tabs and return
4. **Long Idle**: Leave page idle for extended period
5. **Rapid Failures**: Cause multiple quick disconnections

## Future Enhancements

1. Message queue for offline messages
2. Automatic message retry on reconnection
3. Connection quality metrics
4. Adaptive retry strategies based on failure patterns
5. Integration with service workers for background reconnection