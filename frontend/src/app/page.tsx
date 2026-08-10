'use client';

import { useState, useEffect } from 'react';
import { CurrencyPairSelector } from '@/components/CurrencyPairSelector';
import { SignalCard } from '@/components/SignalCard';
import { NewsFeed } from '@/components/NewsFeed';
import { SentimentChart } from '@/components/SentimentChart';
import { useSignals } from '@/hooks/useSignals';
import { useNews } from '@/hooks/useNews';
import { Activity, TrendingUp, TrendingDown, BarChart3, Search, X } from 'lucide-react';

export default function DashboardPage() {
  const [selectedPair, setSelectedPair] = useState<string>('EUR/USD');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isSearchActive, setIsSearchActive] = useState(false);

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

  // Handle search
  const handleSearch = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);

    if (query.trim().length < 2) {
      setSearchResults([]);
      setIsSearchActive(false);
      return;
    }

    try {
      setIsSearching(true);
      setIsSearchActive(true);
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/news/search?query=${encodeURIComponent(query)}&limit=20`
      );

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      setSearchResults(data.items || []);
    } catch (error) {
      console.error('Error searching news:', error);
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  // Clear search
  const clearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setIsSearchActive(false);
  };

  // Display content based on search state
  const displayNews = isSearchActive ? searchResults : news;
  const isLoadingNews = isSearchActive ? isSearching : newsLoading;
  const newsTitle = isSearchActive ? `Search Results (${searchResults.length})` : 'News Feed';

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

          {/* Right Column - News Feed with Search */}
          <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 h-fit lg:sticky lg:top-8">
            <div className="mb-4">
              <h2 className="text-xl font-bold text-white mb-4">{newsTitle}</h2>
              
              {/* Search Input */}
              <div className="relative mb-4">
                <div className="flex items-center bg-slate-700 rounded-lg px-3 py-2 border border-slate-600 focus-within:border-blue-500 transition-colors">
                  <Search className="h-4 w-4 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Search news (e.g., USD, EUR)"
                    value={searchQuery}
                    onChange={handleSearch}
                    className="ml-2 flex-1 bg-transparent text-white placeholder-slate-400 outline-none text-sm"
                  />
                  {searchQuery && (
                    <button
                      onClick={clearSearch}
                      className="ml-2 p-1 hover:bg-slate-600 rounded transition-colors"
                      aria-label="Clear search"
                    >
                      <X className="h-4 w-4 text-slate-400" />
                    </button>
                  )}
                </div>
              </div>

              {/* Results Count */}
              {isSearchActive && (
                <div className="text-xs text-slate-400 mb-3">
                  {searchResults.length === 0 ? 'No results found' : `${searchResults.length} result${searchResults.length !== 1 ? 's' : ''} found`}
                </div>
              )}
            </div>

            {/* News Feed */}
            {isLoadingNews ? (
              <div className="text-slate-400 text-sm">Loading news...</div>
            ) : displayNews.length > 0 ? (
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {displayNews.map((item, idx) => (
                  <div
                    key={idx}
                    className="bg-slate-700 border border-slate-600 rounded p-3 hover:border-blue-500 transition-colors cursor-pointer"
                  >
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <span className="text-xs font-medium text-slate-300 uppercase">
                        {item.source || 'News'}
                      </span>
                      {item.sentiment && (
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-medium ${
                            item.sentiment === 'positive'
                              ? 'bg-green-900/30 text-green-400'
                              : item.sentiment === 'negative'
                              ? 'bg-red-900/30 text-red-400'
                              : 'bg-slate-600 text-slate-300'
                          }`}
                        >
                          {item.sentiment}
                        </span>
                      )}
                    </div>
                    <h3 className="text-sm font-semibold text-white line-clamp-2 mb-1">
                      {item.title}
                    </h3>
                    <p className="text-xs text-slate-300 line-clamp-2 mb-2">
                      {item.content}
                    </p>
                    {item.currency_pairs && item.currency_pairs.length > 0 && (
                      <div className="flex gap-1 flex-wrap">
                        {item.currency_pairs.slice(0, 2).map((pair) => (
                          <span
                            key={pair}
                            className="px-1.5 py-0.5 bg-slate-600 rounded text-xs text-slate-300"
                          >
                            {pair}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-400 text-sm">
                {isSearchActive
                  ? 'No results found. Try a different search term.'
                  : `No news available for ${selectedPair}`}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
