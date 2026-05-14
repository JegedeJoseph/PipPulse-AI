'use client';

import { useState, useEffect } from 'react';
import { CurrencyPairSelector } from '@/components/CurrencyPairSelector';
import { SignalCard } from '@/components/SignalCard';
import { NewsFeed } from '@/components/NewsFeed';
import { SentimentChart } from '@/components/SentimentChart';
import { useSignals } from '@/hooks/useSignals';
import { useNews } from '@/hooks/useNews';
import { Activity, TrendingUp, TrendingDown, BarChart3 } from 'lucide-react';

export default function DashboardPage() {
  const [selectedPair, setSelectedPair] = useState<string>('EUR/USD');
  const { signals, loading: signalsLoading } = useSignals(selectedPair);
  const { news, loading: newsLoading } = useNews(selectedPair);

  const stats = {
    totalSignals: signals.length,
    buySignals: signals.filter(s => s.direction === 'buy').length,
    sellSignals: signals.filter(s => s.direction === 'sell').length,
    avgConfidence: signals.length > 0
      ? (signals.reduce((sum, s) => sum + s.confidence, 0) / signals.length).toFixed(1)
      : '0'
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-800/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white">PipPulse AI</h1>
              <p className="text-slate-400 text-sm mt-1">Real-Time Sentiment Analysis for Forex Trading</p>
            </div>
            <Activity className="h-8 w-8 text-blue-400" />
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Currency Pair Selector */}
        <div className="mb-8">
          <CurrencyPairSelector selectedPair={selectedPair} onSelectPair={setSelectedPair} />
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Total Signals</p>
                <p className="text-3xl font-bold text-white mt-1">{stats.totalSignals}</p>
              </div>
              <BarChart3 className="h-8 w-8 text-blue-400 opacity-50" />
            </div>
          </div>

          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Buy Signals</p>
                <p className="text-3xl font-bold text-green-400 mt-1">{stats.buySignals}</p>
              </div>
              <TrendingUp className="h-8 w-8 text-green-400 opacity-50" />
            </div>
          </div>

          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Sell Signals</p>
                <p className="text-3xl font-bold text-red-400 mt-1">{stats.sellSignals}</p>
              </div>
              <TrendingDown className="h-8 w-8 text-red-400 opacity-50" />
            </div>
          </div>

          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-slate-400 text-sm">Avg Confidence</p>
                <p className="text-3xl font-bold text-purple-400 mt-1">{stats.avgConfidence}%</p>
              </div>
              <Activity className="h-8 w-8 text-purple-400 opacity-50" />
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Signals and Chart */}
          <div className="lg:col-span-2 space-y-8">
            {/* Latest Signals */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4">Latest Signals</h2>
              {signalsLoading ? (
                <div className="text-slate-400">Loading signals...</div>
              ) : signals.length > 0 ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {signals.slice(0, 5).map((signal, idx) => (
                    <SignalCard key={idx} signal={signal} />
                  ))}
                </div>
              ) : (
                <div className="text-slate-400">No signals available for {selectedPair}</div>
              )}
            </div>

            {/* Sentiment Chart */}
            <div className="bg-slate-800 border border-slate-700 rounded-lg p-6">
              <h2 className="text-xl font-bold text-white mb-4">Sentiment Trend</h2>
              <SentimentChart signals={signals} pair={selectedPair} />
            </div>
          </div>

          {/* Right Column - News Feed */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 h-fit lg:sticky lg:top-8">
            <h2 className="text-xl font-bold text-white mb-4">News Feed</h2>
            {newsLoading ? (
              <div className="text-slate-400">Loading news...</div>
            ) : news.length > 0 ? (
              <NewsFeed news={news} />
            ) : (
              <div className="text-slate-400">No news available for {selectedPair}</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
