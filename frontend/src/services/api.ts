import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  SignalResponse,
  NewsItemResponse,
  SentimentTrend,
  BacktestResult,
  SystemConfig,
  SystemStats,
  ThresholdConfig,
} from '@/types';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

class APIService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response) {
          // Server responded with error status
          console.error('API Error:', error.response.data);
        } else if (error.request) {
          // Request made but no response
          console.error('Network Error:', error.message);
        } else {
          console.error('Error:', error.message);
        }
        return Promise.reject(error);
      }
    );
  }

  // Health check
  async healthCheck() {
    const response = await this.client.get('/api/health');
    return response.data;
  }

  async detailedHealthCheck() {
    const response = await this.client.get('/api/health/detailed');
    return response.data;
  }

  // Signals
  async getSignals(params?: {
    currency_pair?: string;
    direction?: 'buy' | 'sell' | 'hold';
    time_window?: '15min' | '1hour' | '4hour';
    limit?: number;
  }): Promise<SignalResponse[]> {
    const response = await this.client.get('/api/signals', { params });
    return response.data;
  }

  async getLatestSignals(currencyPairs?: string[], timeWindow = '1hour'): Promise<SignalResponse[]> {
    const params: any = { time_window: timeWindow };
    if (currencyPairs && currencyPairs.length > 0) {
      params.currency_pairs = currencyPairs;
    }
    const response = await this.client.get('/api/signals/latest', { params });
    return response.data;
  }

  async getAggregatedSignals(currencyPair: string, timeWindow = '1hour') {
    const response = await this.client.get(`/api/signals/aggregate/${currencyPair}`, {
      params: { time_window: timeWindow },
    });
    return response.data;
  }

  async getSignalHistory(currencyPair: string, hours = 24, timeWindow = '1hour') {
    const response = await this.client.get(`/api/signals/history/${currencyPair}`, {
      params: { hours, time_window: timeWindow },
    });
    return response.data;
  }

  async getAvailablePairs() {
    const response = await this.client.get('/api/signals/pairs');
    return response.data;
  }

  // News
  async getNews(params?: {
    source?: 'newsapi' | 'twitter' | 'reddit' | 'telegram';
    currency_pair?: string;
    sentiment?: 'positive' | 'negative' | 'neutral';
    limit?: number;
    hours?: number;
  }): Promise<NewsItemResponse[]> {
    const response = await this.client.get('/api/news', { params });
    return response.data;
  }

  async getLatestNews(limit = 20) {
    const response = await this.client.get('/api/news/latest', { params: { limit } });
    return response.data;
  }

  async getSentimentTrend(currencyPair: string, hours = 24, interval = '1hour'): Promise<SentimentTrend> {
    const response = await this.client.get(`/api/news/sentiment/trend/${currencyPair}`, {
      params: { hours, interval },
    });
    return response.data;
  }

  async getNewsSources() {
    const response = await this.client.get('/api/news/sources');
    return response.data;
  }

  async searchNews(query: string, limit = 20) {
    const response = await this.client.get('/api/news/search', { params: { query, limit } });
    return response.data;
  }

  // Admin
  async getConfig(): Promise<SystemConfig> {
    const response = await this.client.get('/api/admin/config');
    return response.data;
  }

  async getThresholds() {
    const response = await this.client.get('/api/admin/thresholds');
    return response.data;
  }

  async updateThreshold(currencyPair: string, config: ThresholdConfig) {
    const response = await this.client.put(`/api/admin/thresholds/${currencyPair}`, config);
    return response.data;
  }

  async getSourceWeights() {
    const response = await this.client.get('/api/admin/source-weights');
    return response.data;
  }

  async updateSourceWeight(source: string, weight: number) {
    const response = await this.client.put('/api/admin/source-weights', { source, weight });
    return response.data;
  }

  async getTimeWindows() {
    const response = await this.client.get('/api/admin/time-windows');
    return response.data;
  }

  async updateTimeWindow(name: string, minutes: number) {
    const response = await this.client.put('/api/admin/time-windows', { name, minutes });
    return response.data;
  }

  async getAPIKeys() {
    const response = await this.client.get('/api/admin/api-keys');
    return response.data;
  }

  async getSystemStats(): Promise<SystemStats> {
    const response = await this.client.get('/api/admin/stats');
    return response.data;
  }

  async resetSystem() {
    const response = await this.client.post('/api/admin/reset');
    return response.data;
  }

  // Backtest
  async runBacktest(params: {
    currency_pair?: string;
    start_date?: string;
    end_date?: string;
    initial_capital?: number;
    risk_per_trade?: number;
  }): Promise<BacktestResult> {
    const response = await this.client.post('/api/backtest/run', params);
    return response.data;
  }

  async getBacktestResults(params?: {
    currency_pair?: string;
    start_date?: string;
    end_date?: string;
    limit?: number;
  }): Promise<BacktestResult[]> {
    const response = await this.client.get('/api/backtest', { params });
    return response.data;
  }
}

export const api = new APIService();
export default api;
