'use client';

import { useState, useEffect } from 'react';
import { Settings, Save, RefreshCw, AlertCircle, CheckCircle2, RotateCcw, Zap, Database } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'react-hot-toast';
import type { AdminConfig, AdminStats } from '@/types';

export function AdminPanel() {
  const [config, setConfig] = useState<AdminConfig | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [originalConfig, setOriginalConfig] = useState<AdminConfig | null>(null);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await api.getConfig();
      setConfig(data as unknown as AdminConfig);
      setOriginalConfig(data as unknown as AdminConfig);
      setHasChanges(false);
      toast.success('Configuration loaded');
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Failed to load configuration';
      toast.error(message);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const data = await api.getSystemStats();
      setStats(data as any);
    } catch (error) {
      // Silently fail for stats to not block UI
      console.debug('Failed to load stats:', error);
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    loadConfig();
    loadStats();
    const statsInterval = setInterval(loadStats, 5000); // Refresh stats every 5s
    return () => clearInterval(statsInterval);
  }, []);

  const saveConfig = async () => {
    if (!config) return;
    setSaving(true);
    try {
      let success = true;
      
      // Update thresholds for each currency pair
      for (const [pair, threshold] of Object.entries(config.signal_thresholds)) {
        try {
          await api.updateThreshold(pair, {
            currency_pair: pair,
            buy_threshold: threshold.buy,
            sell_threshold: threshold.sell,
            confidence_threshold: 0.5,
            time_decay_lambda: 0.99
          });
        } catch (error) {
          success = false;
          console.error(`Failed to update threshold for ${pair}:`, error);
        }
      }

      // Update source weights
      for (const [source, weight] of Object.entries(config.source_weights)) {
        try {
          await api.updateSourceWeight(source, weight);
        } catch (error) {
          success = false;
          console.error(`Failed to update weight for ${source}:`, error);
        }
      }

      // Update time windows
      if (config.time_windows.length > 0) {
        try {
          await api.updateTimeWindow('windows', 0, config.time_windows);
        } catch (error) {
          success = false;
          console.error('Failed to update time windows:', error);
        }
      }

      if (success) {
        setOriginalConfig(config);
        setHasChanges(false);
        toast.success('Configuration saved successfully');
      } else {
        toast.error('Some settings failed to save');
      }
    } catch (error: any) {
      const message = error?.response?.data?.detail || 'Failed to save configuration';
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  const resetConfig = () => {
    if (window.confirm('Are you sure? This will discard all unsaved changes.')) {
      if (originalConfig) {
        setConfig(JSON.parse(JSON.stringify(originalConfig)));
        setHasChanges(false);
        toast.success('Configuration reset to last saved');
      }
    }
  };

  const updateThreshold = (pair: string, field: keyof typeof config.signal_thresholds[string], value: number) => {
    if (!config) return;
    const updated = {
      ...config,
      signal_thresholds: {
        ...config.signal_thresholds,
        [pair]: {
          ...config.signal_thresholds[pair],
          [field]: value,
        },
      },
    };
    setConfig(updated);
    setHasChanges(true);
  };

  const updateSourceWeight = (source: string, weight: number) => {
    if (!config) return;
    const updated = {
      ...config,
      source_weights: {
        ...config.source_weights,
        [source]: weight,
      },
    };
    setConfig(updated);
    setHasChanges(true);
  };

  if (loading && !config) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-12">
        <button
          onClick={loadConfig}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Load Configuration
        </button>
      </div>
    );
  }

  const getStatusIcon = (status?: string) => {
    if (status === 'healthy') return <CheckCircle2 className="w-5 h-5 text-green-600" />;
    if (status === 'degraded') return <AlertCircle className="w-5 h-5 text-yellow-600" />;
    return <AlertCircle className="w-5 h-5 text-red-600" />;
  };

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (days > 0) return `${days}d ${hours}h`;
    if (hours > 0) return `${hours}h ${mins}m`;
    return `${mins}m`;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Settings className="w-6 h-6" />
          System Configuration
        </h2>
        <div className="flex gap-2">
          {hasChanges && (
            <div className="text-sm text-amber-600 flex items-center gap-1">
              <AlertCircle className="w-4 h-4" />
              Unsaved changes
            </div>
          )}
          <button
            onClick={loadConfig}
            disabled={loading}
            className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={resetConfig}
            disabled={!hasChanges}
            className="px-3 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>
          <button
            onClick={saveConfig}
            disabled={saving || !hasChanges}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* System Health */}
      {stats && (
        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900 flex items-center gap-2">
              <Zap className="w-5 h-5" />
              System Health
            </h3>
            <div className="flex items-center gap-2">
              {getStatusIcon(stats.status)}
              <span className="text-sm font-medium capitalize">{stats.status}</span>
            </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <p className="text-sm text-gray-600 mb-1">CPU Usage</p>
              <p className="text-2xl font-bold text-gray-900">{stats.cpu_percent.toFixed(1)}%</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Memory</p>
              <p className="text-2xl font-bold text-gray-900">{stats.memory_percent.toFixed(1)}%</p>
              <p className="text-xs text-gray-500">{stats.memory_mb}MB</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Uptime</p>
              <p className="text-2xl font-bold text-gray-900">{formatUptime(stats.uptime_seconds)}</p>
            </div>
            <div>
              <p className="text-sm text-gray-600 mb-1">Last Update</p>
              <p className="text-xs text-gray-500">{new Date(stats.last_update).toLocaleTimeString()}</p>
            </div>
          </div>
        </div>
      )}

      {/* Signal Generation Thresholds */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Signal Generation Thresholds</h3>
        <div className="space-y-6">
          {Object.entries(config.signal_thresholds).map(([pair, threshold]) => (
            <div key={pair} className="border-b border-gray-200 pb-6 last:border-0">
              <h4 className="font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <Database className="w-4 h-4" />
                {pair}
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Buy Threshold (0-100)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={threshold.buy}
                    onChange={(e) => updateThreshold(pair, 'buy', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Trigger BUY signal</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Hold Threshold (0-100)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={threshold.hold}
                    onChange={(e) => updateThreshold(pair, 'hold', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Neutral zone</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Sell Threshold (0-100)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="100"
                    value={threshold.sell}
                    onChange={(e) => updateThreshold(pair, 'sell', parseInt(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  />
                  <p className="text-xs text-gray-500 mt-1">Trigger SELL signal</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Source Credibility Weights */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Source Credibility Weights</h3>
        <p className="text-sm text-gray-600 mb-4">Higher weights = more influence on signal generation (0.5-2.0)</p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {Object.entries(config.source_weights).map(([source, weight]) => (
            <div key={source} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <span className="font-medium text-gray-900 capitalize">{source}</span>
                <span className="text-lg font-bold text-blue-600">{(weight as number).toFixed(1)}x</span>
              </div>
              <input
                type="range"
                min="0.5"
                max="2.0"
                step="0.1"
                value={weight as number}
                onChange={(e) => updateSourceWeight(source, parseFloat(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0.5</span>
                <span>1.0</span>
                <span>2.0</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Time Windows */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Time Windows (seconds)</h3>
        <p className="text-sm text-gray-600 mb-4">Aggregation windows for sentiment calculation</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Window 1</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="60"
                step="60"
                value={config.time_windows[0] || 900}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
              />
              <span className="text-sm text-gray-600 whitespace-nowrap">
                ({((config.time_windows[0] || 900) / 60).toFixed(0)}m)
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Window 2</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="60"
                step="60"
                value={config.time_windows[1] || 3600}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
              />
              <span className="text-sm text-gray-600 whitespace-nowrap">
                ({((config.time_windows[1] || 3600) / 60).toFixed(0)}m)
              </span>
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Window 3</label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="60"
                step="60"
                value={config.time_windows[2] || 14400}
                readOnly
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
              />
              <span className="text-sm text-gray-600 whitespace-nowrap">
                ({((config.time_windows[2] || 14400) / 3600).toFixed(1)}h)
              </span>
            </div>
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-4">Time windows are fixed. Contact support to modify.</p>
      </div>

      {/* Confidence Settings */}
      <div className="bg-gray-50 rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4 text-gray-900">Global Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Confidence Threshold: <span className="text-blue-600 font-bold">{config.confidence_threshold}</span>
            </label>
            <p className="text-xs text-gray-600">Signals below this confidence are flagged. Current: {(config.confidence_threshold * 100).toFixed(0)}%</p>
          </div>
        </div>
      </div>
    </div>
  );
}
