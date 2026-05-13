'use client';

import { useState } from 'react';
import { Settings, Save, RefreshCw } from 'lucide-react';
import api from '@/services/api';
import { toast } from 'react-hot-toast';

export function AdminPanel() {
  const [config, setConfig] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadConfig = async () => {
    setLoading(true);
    try {
      const data = await api.getConfig();
      setConfig(data);
    } catch (error) {
      toast.error('Failed to load configuration');
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    setSaving(true);
    try {
      if (config?.signal) {
        for (const [pair, threshold] of Object.entries(config.signal.thresholds || {})) {
          await api.updateThreshold(pair, threshold);
        }
      }
      toast.success('Configuration saved successfully');
    } catch (error) {
      toast.error('Failed to save configuration');
    } finally {
      setSaving(false);
    }
  };

  const updateThreshold = (pair: string, field: string, value: number) => {
    setConfig((prev: any) => ({
      ...prev,
      signal: {
        ...prev.signal,
        thresholds: {
          ...prev.signal.thresholds,
          [pair]: {
            ...prev.signal.thresholds[pair],
            [field]: value,
          },
        },
      },
    }));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    );
  }

  if (!config) {
    return (
      <div className="text-center py-12">
        <button
          onClick={loadConfig}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          Load Configuration
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <Settings className="w-6 h-6" />
          System Configuration
        </h2>
        <div className="flex gap-2">
          <button
            onClick={loadConfig}
            className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
          <button
            onClick={saveConfig}
            disabled={saving}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors flex items-center gap-2 disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Signal Generation Thresholds</h3>
        <div className="space-y-4">
          {Object.entries(config.signal?.thresholds || {}).map(([pair, threshold]: [string, any]) => (
            <div key={pair} className="border-b border-gray-200 pb-4 last:border-0">
              <h4 className="font-medium text-gray-900 mb-3">{pair}</h4>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Buy Threshold</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={threshold.buy_threshold}
                    onChange={(e) => updateThreshold(pair, 'buy_threshold', parseFloat(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Sell Threshold</label>
                  <input
                    type="number"
                    step="0.1"
                    min="-1"
                    max="0"
                    value={threshold.sell_threshold}
                    onChange={(e) => updateThreshold(pair, 'sell_threshold', parseFloat(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Confidence Threshold</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    max="1"
                    value={threshold.confidence_threshold}
                    onChange={(e) => updateThreshold(pair, 'confidence_threshold', parseFloat(e.target.value))}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Source Credibility Weights</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {Object.entries(config.source_weights || {}).map(([source, weight]) => (
            <div key={source} className="flex items-center justify-between">
              <span className="font-medium text-gray-900 capitalize">{source}</span>
              <div className="flex items-center gap-2">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={weight as number}
                  onChange={(e) => {
                    setConfig((prev: any) => ({
                      ...prev,
                      source_weights: {
                        ...prev.source_weights,
                        [source]: parseFloat(e.target.value),
                      },
                    }));
                  }}
                  className="w-32"
                />
                <span className="w-12 text-right font-mono">{(weight as number).toFixed(1)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold mb-4">Time Windows (minutes)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(config.time_windows || {}).map(([window, minutes]) => (
            <div key={window}>
              <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">{window}</label>
              <input
                type="number"
                min="1"
                value={minutes as number}
                onChange={(e) => {
                  setConfig((prev: any) => ({
                    ...prev,
                    time_windows: {
                      ...prev.time_windows,
                      [window]: parseInt(e.target.value),
                    },
                  }));
                }}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
