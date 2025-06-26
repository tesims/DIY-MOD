/**
 * WebSocket Connector Module
 * 
 * Provides WebSocket-based communication with the backend for real-time processing.
 */

import { logger } from '@/utils/logger';
import { config } from '@/shared/config';
import { InterceptedRequest, Platform } from '@/shared/types';

interface PendingRequest {
  id: string;
  resolve: (value: any) => void;
  reject: (error: Error) => void;
  timestamp: number;
}

/**
 * WebSocket-based API connector for real-time content processing
 */
export class WebSocketConnector {
  private ws: WebSocket | null = null;
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private isConnected = false;
  private connectionPromise: Promise<void> | null = null;
  private userId: string;

  constructor(userId: string) {
    this.userId = userId;
    this.connectionPromise = this.connect();
  }

  /**
   * Establish WebSocket connection
   */
  private async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const wsUrl = config.api.baseUrl.replace('http', 'ws') + `/ws/${this.userId}`;
        logger.content.info(`Connecting to WebSocket: ${wsUrl}`);
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
          logger.content.info('WebSocket connected successfully');
          this.isConnected = true;
          this.reconnectAttempts = 0;
          
          // Send connection confirmation
          this.sendMessage({
            type: 'connection',
            message: 'Extension connected',
            timestamp: new Date().toISOString()
          });
          
          resolve(); // Resolve the promise when connection is established
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };

        this.ws.onclose = () => {
          logger.content.warn('WebSocket connection closed');
          this.isConnected = false;
          this.handleReconnection();
        };

        this.ws.onerror = (error) => {
          logger.content.error('WebSocket error:', error);
          this.isConnected = false;
          reject(error); // Reject the promise on error
        };

        // Set connection timeout
        setTimeout(() => {
          if (!this.isConnected) {
            reject(new Error('WebSocket connection timeout'));
          }
        }, 10000); // 10 second timeout

      } catch (error) {
        logger.content.error('Failed to establish WebSocket connection:', error);
        reject(error);
        this.handleReconnection();
      }
    });
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: string): void {
    try {
      const message = JSON.parse(data);
      
      // Handle processing responses
      if (message.type === 'processing_response' && message.requestId) {
        const pendingRequest = this.pendingRequests.get(message.requestId);
        if (pendingRequest) {
          pendingRequest.resolve(message.data);
          this.pendingRequests.delete(message.requestId);
        }
      }
      
      // Handle errors
      if (message.type === 'error' && message.requestId) {
        const pendingRequest = this.pendingRequests.get(message.requestId);
        if (pendingRequest) {
          pendingRequest.reject(new Error(message.error));
          this.pendingRequests.delete(message.requestId);
        }
      }

      // Handle general responses
      if (message.type === 'echo') {
        logger.content.debug('Received echo from server:', message.message);
      }

    } catch (error) {
      logger.content.error('Error parsing WebSocket message:', error);
    }
  }

  /**
   * Handle WebSocket reconnection
   */
  private handleReconnection(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      logger.content.error('Max reconnection attempts reached. Falling back to HTTP polling.');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    logger.content.info(`Attempting to reconnect WebSocket in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Send a message through WebSocket
   */
  private sendMessage(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      logger.content.warn('WebSocket not ready, message queued');
    }
  }

  /**
   * Process an intercepted request through WebSocket
   */
  public async processRequest(data: InterceptedRequest, platform: Platform): Promise<any> {
    // Wait for connection to be established if it's still connecting
    if (this.connectionPromise && !this.isConnected) {
      try {
        await this.connectionPromise;
      } catch (error) {
        throw new Error('Failed to establish WebSocket connection');
      }
    }

    return new Promise((resolve, reject) => {
      const requestId = `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      
      // Store pending request
      this.pendingRequests.set(requestId, {
        id: requestId,
        resolve,
        reject,
        timestamp: Date.now()
      });

      // Send processing request
      const message = {
        type: 'process_feed',
        requestId,
        data: {
          url: data.url,
          platform: platform,
          response: data.response,
          startTime: data.startTime,
          userId: this.userId
        }
      };

      if (this.isConnected) {
        this.sendMessage(message);
        logger.content.info(`Sent WebSocket processing request: ${requestId}`);
      } else {
        // Fallback to HTTP if WebSocket not connected
        logger.content.warn('WebSocket not connected, falling back to HTTP');
        reject(new Error('WebSocket not connected'));
      }

      // Set timeout for request
      setTimeout(() => {
        if (this.pendingRequests.has(requestId)) {
          this.pendingRequests.delete(requestId);
          reject(new Error('WebSocket request timeout'));
        }
      }, config.api.requestTimeoutMs);
    });
  }

  /**
   * Check if WebSocket is connected
   */
  public isWebSocketConnected(): boolean {
    return this.isConnected && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Clean up pending requests on timeout
   */
  public cleanupExpiredRequests(): void {
    const now = Date.now();
    const timeout = config.api.requestTimeoutMs;

    for (const [requestId, request] of this.pendingRequests.entries()) {
      if (now - request.timestamp > timeout) {
        request.reject(new Error('Request expired'));
        this.pendingRequests.delete(requestId);
      }
    }
  }

  /**
   * Close WebSocket connection
   */
  public disconnect(): void {
    if (this.ws) {
      this.ws.close();
      this.isConnected = false;
    }
  }
}

// Singleton instance
let wsConnector: WebSocketConnector | null = null;

/**
 * Get or create WebSocket connector instance
 */
export function getWebSocketConnector(userId: string): WebSocketConnector {
  if (!wsConnector) {
    wsConnector = new WebSocketConnector(userId);
    
    // Clean up expired requests periodically
    setInterval(() => {
      wsConnector?.cleanupExpiredRequests();
    }, 30000);
  }
  return wsConnector;
}

/**
 * Process an intercepted request using WebSocket with HTTP fallback
 */
export async function processWithWebSocket(data: InterceptedRequest, platform: Platform): Promise<any> {
  // Check if WebSocket is enabled in configuration
  if (!config.api.websocketEnabled) {
    logger.content.info('WebSocket disabled in config, using HTTP polling');
    const { processInterceptedRequest } = await import('./api-connector');
    return await processInterceptedRequest(data, platform);
  }

  const userId = config.userId || 'unknown';
  const connector = getWebSocketConnector(userId);

  try {
    // Try WebSocket first - this will now wait for connection to be established
    logger.content.info(`Processing via WebSocket: ${data.type}`);
    return await connector.processRequest(data, platform);
  } catch (error) {
    logger.content.warn('WebSocket processing failed, falling back to HTTP:', error);
    
    // Fallback to HTTP polling
    const { processInterceptedRequest } = await import('./api-connector');
    return await processInterceptedRequest(data, platform);
  }
} 