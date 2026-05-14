'use client';

import { useState } from 'react';
import { api } from '@/services/api';
import { BarChart3, TrendingUp, TrendingDown, Activity } from 'lucide-react';
import toast from 'react-hot-toast';

export default function BacktestingPage() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [formData, setFormData] = useState({
    currency_pair: 'EUR/USD',
    start_date: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    initial_capital: 10000,
    risk_per_trade: 0.02
  });

  const handleRunBacktest = async () => {
    setLoading(true);
    try {
      const response = await api.post('/backtesting/run', {
        currency_pair: formData.currency_pair || undefined,
        start_date: formData.start_date,
        end_date: formData.end_date,
        initial_capital: parseFloat(formData.initial_capital.toString()),
        risk_per_trade: parseFloat(formData.risk_per_trade.toString())
      });
      setResults(response.data.result);
      toast.success('Backtest completed successfully');
    } catch (error) {
      toast.error('Failed to run backtest');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleFetchHistory = async () => {
    try {
      const response = await api.get('/backtesting/history');
      setHistory(response.data.backtests);
    } catch (error) {
      toast.error('Failed to fetch backtest history');
      console.error(error);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">Backtesting</h1>
              <p className="text-slate-400 text-sm mt-1">Test trading strategies against historical data</p>
            </div>
            <BarChart3 className="h-8 w-8 text-blue-400" />
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Configuration */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <h2 className="text-xl font-bold text-white mb-4">Configuration</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Currency Pair
                </label>
                <select
                  value={formData.currency_pair}
                  onChange={(e) => setFormData({ ...formData, currency_pair: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Pairs</option>
                  <option value="EUR/USD">EUR/USD</option>
                  <option value="GBP/USD">GBP/USD</option>
                  <option value="USD/JPY">USD/JPY</option>
                  <option value="USD/CHF">USD/CHF</option>
                  <option value="AUD/USD">AUD/USD</option>
                  <option value="USD/CAD">USD/CAD</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Start Date
                </label>
                <input
                  type="date"
                  value={formData.start_date}
                  onChange={(e) => setFormData({ ...formData, start_date: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  End Date
                </label>
                <input
                  type="date"
                  value={formData.end_date}
                  onChange={(e) => setFormData({ ...formData, end_date: e.target.value })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Initial Capital ($)
                </label>
                <input
                  type="number"
                  value={formData.initial_capital}
                  onChange={(e) => setFormData({ ...formData, initial_capital: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  Risk Per Trade
                </label>
                <input
                  type="number"
                  min="0.01"
                  max="0.1"
                  step="0.01"
                  value={formData.risk_per_trade}
                  onChange={(e) => setFormData({ ...formData, risk_per_trade: parseFloat(e.target.value) })}
                  className="w-full px-3 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              <button
                onClick={handleRunBacktest}
                disabled={loading}
                className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-900 text-white font-semibold py-2 px-4 rounded transition-colors"
              >
                {loading ? 'Running...' : 'Run Backtest'}
              </button>

              <button
                onClick={handleFetchHistory}
                className="w-full bg-slate-700 hover:bg-slate-600 text-white font-semibold py-2 px-4 rounded transition-colors"
              >
                View History
              </button>
            </div>
          </div>

          {/* Results */}
          <div className="lg:col-span-2">
            {results ? (
              <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
                <h2 className="text-xl font-bold text-white mb-4">Results</h2>
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Currency Pair</p>
                    <p className="text-lg font-bold text-white mt-1">{results.currency_pair}</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Total Return</p>
                    <p className={`text-lg font-bold mt-1 ${results.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {results.total_return?.toFixed(2)}%
                    </p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Win Rate</p>
                    <p className="text-lg font-bold text-white mt-1">{results.win_rate?.toFixed(1)}%</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Sharpe Ratio</p>
                    <p className="text-lg font-bold text-white mt-1">{results.sharpe_ratio?.toFixed(2)}</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Max Drawdown</p>
                    <p className="text-lg font-bold text-red-400 mt-1">{results.max_drawdown?.toFixed(2)}%</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Total Trades</p>
                    <p className="text-lg font-bold text-white mt-1">{results.total_trades}</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Winning Trades</p>
                    <p className="text-lg font-bold text-green-400 mt-1">{results.winning_trades}</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Losing Trades</p>
                    <p className="text-lg font-bold text-red-400 mt-1">{results.losing_trades}</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Initial Capital</p>
                    <p className="text-lg font-bold text-white mt-1">${results.initial_capital?.toFixed(2)}</p>
                  </div>

                  <div className="bg-slate-700/50 rounded p-4">
                    <p className="text-slate-400 text-sm">Final Capital</p>
                    <p className={`text-lg font-bold mt-1 ${results.final_capital >= results.initial_capital ? 'text-green-400' : 'text-red-400'}`}>
                      ${results.final_capital?.toFixed(2)}
                    </p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 text-center">
                <Activity className="h-12 w-12 text-slate-600 mx-auto mb-3" />
                <p className="text-slate-400">Run a backtest to see results</p>
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 mt-8">
                <h2 className="text-xl font-bold text-white mb-4">Recent Backtests</h2>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {history.map((bt, idx) => (
                    <div key={idx} className="flex justify-between items-center bg-slate-700/50 p-3 rounded">
                      <div>
                        <p className="text-white font-semibold">{bt.currency_pair}</p>
                        <p className="text-slate-400 text-xs">{new Date(bt.created_at).toLocaleString()}</p>
                      </div>
                      <p className={bt.total_return >= 0 ? 'text-green-400' : 'text-red-400'}>
                        {bt.total_return?.toFixed(2)}%
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
