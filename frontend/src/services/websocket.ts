import { io, Socket } from 'socket.io-client';
import type { WebSocketMessage, TradingSignal, NewsItemResponse } from '@/types';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

type EventHandler = (data: any) => void;

class WebSocketService {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private eventHandlers: Map<string, Set<EventHandler>> = new Map();

  connect() {
    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    console.log('Connecting to WebSocket...', WS_URL);

    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionDelay: this.reconnectDelay,
      reconnectionAttempts: this.maxReconnectAttempts,
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.emit('connected', { timestamp: new Date().toISOString() });
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      this.emit('disconnected', { reason, timestamp: new Date().toISOString() });
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error);
      this.reconnectAttempts++;
      this.emit('error', { error: error.message, timestamp: new Date().toISOString() });
    });

    // Handle incoming messages
    this.socket.on('message', (message: WebSocketMessage) => {
      this.handleMessage(message);
    });

    // Handle signal updates
    this.socket.on('signal', (signal: TradingSignal) => {
      this.emit('signal', signal);
    });

    // Handle news updates
    this.socket.on('news', (news: NewsItemResponse) => {
      this.emit('news', news);
    });

    // Handle errors
    this.socket.on('error', (error: any) => {
      this.emit('error', error);
    });

    // Handle heartbeat
    this.socket.on('heartbeat', (data: any) => {
      this.emit('heartbeat', data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      console.log('WebSocket disconnected');
    }
  }

  private handleMessage(message: WebSocketMessage) {
    const { type, data } = message;
    this.emit(type, data);
  }

  on(event: string, handler: EventHandler) {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, new Set());
    }
    this.eventHandlers.get(event)!.add(handler);
  }

  off(event: string, handler: EventHandler) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.delete(handler);
      if (handlers.size === 0) {
        this.eventHandlers.delete(event);
      }
    }
  }

  private emit(event: string, data: any) {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          console.error(`Error in event handler for ${event}:`, error);
        }
      });
    }
  }

  send(event: string, data?: any) {
    if (this.socket?.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn('Cannot send message: WebSocket not connected');
    }
  }

  subscribe(subscriptions: Record<string, boolean>) {
    this.send('subscribe', { subscriptions });
  }

  unsubscribe(messageType: string) {
    this.send('unsubscribe', { message_type: messageType });
  }

  isConnected(): boolean {
    return this.socket?.connected ?? false;
  }
}

export const ws = new WebSocketService();
export default ws;
