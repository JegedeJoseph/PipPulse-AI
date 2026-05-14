'use client';

import { useState, useEffect } from 'react';
import { api } from '@/services/api';
import { Settings, Save, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminPage() {
  const [loading, setLoading] = useState(false);
  const [config, setConfig] = useState<any>(null);
  const [formData, setFormData] = useState({
    signal: {
      latency_target: 5,
      max_batch_size: 32,
      confidence_threshold: 0.6,
      time_decay_lambda: 0.1
    },
    source_weights: {
      newsapi: 0.9,
      twitter: 0.7,
      reddit: 0.6,
      telegram: 0.5
    }
  });

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      const response = await api.get('/admin/config');
      setConfig(response.data);
      setFormData(response.data);
    } catch (error) {
      toast.error('Failed to fetch configuration');
      console.error(error);
    }
  };

  const handleSaveConfig = async () => {
    setLoading(true);
    try {
      await api.put('/admin/config', formData);
      toast.success('Configuration updated successfully');
      fetchConfig();
    } catch (error) {
      toast.error('Failed to update configuration');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  if (!config) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center">
        <div className="text-slate-400">Loading configuration...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">Admin Settings</h1>
              <p className="text-slate-400 text-sm mt-1">Manage system configuration and parameters</p>
            </div>
            <Settings className="h-8 w-8 text-blue-400" />
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Signal Configuration */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Signal Generation</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Latency Target (seconds)
                </label>
                <input
                  type="number"
                  value={formData.signal.latency_target}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      signal: { ...formData.signal, latency_target: parseInt(e.target.value) }
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Max Batch Size
                </label>
                <input
                  type="number"
                  value={formData.signal.max_batch_size}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      signal: { ...formData.signal, max_batch_size: parseInt(e.target.value) }
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Confidence Threshold (0-1)
                </label>
                <input
                  type="number"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.signal.confidence_threshold}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      signal: { ...formData.signal, confidence_threshold: parseFloat(e.target.value) }
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Time Decay Lambda
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.signal.time_decay_lambda}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      signal: { ...formData.signal, time_decay_lambda: parseFloat(e.target.value) }
                    })
                  }
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Source Weights */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Source Credibility Weights</h2>
            <div className="space-y-4">
              {Object.entries(formData.source_weights).map(([source, weight]: [string, any]) => (
                <div key={source}>
                  <label className="block text-sm font-medium text-slate-300 mb-1 capitalize">
                    {source} Weight (0-1)
                  </label>
                  <input
                    type="number"
                    min="0"
                    max="1"
                    step="0.1"
                    value={weight}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        source_weights: {
                          ...formData.source_weights,
                          [source]: parseFloat(e.target.value)
                        }
                      })
                    }
                    className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-4 mt-8 justify-end">
          <button
            onClick={fetchConfig}
            className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-2 px-4 rounded transition-colors"
          >
            <RefreshCw className="h-4 w-4" />
            Reset
          </button>
          <button
            onClick={handleSaveConfig}
            disabled={loading}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 text-white font-semibold py-2 px-4 rounded transition-colors"
          >
            <Save className="h-4 w-4" />
            {loading ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}
