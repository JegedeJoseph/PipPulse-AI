'use client';

import { TrendingUp, TrendingDown, Minus, Clock, Activity } from 'lucide-react';
import type { TradingSignal } from '@/types';

interface SignalCardProps {
  signal: TradingSignal;
}

export function SignalCard({ signal }: SignalCardProps) {
  const getDirectionColor = (direction: string) => {
    switch (direction) {
      case 'buy':
        return 'bg-success-100 text-success-700 border-success-300';
      case 'sell':
        return 'bg-danger-100 text-danger-700 border-danger-300';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-300';
    }
  };

  const getDirectionIcon = (direction: string) => {
    switch (direction) {
      case 'buy':
        return <TrendingUp className="w-5 h-5" />;
      case 'sell':
        return <TrendingDown className="w-5 h-5" />;
      default:
        return <Minus className="w-5 h-5" />;
    }
  };

  const getStrengthColor = (strength: number) => {
    if (strength >= 70) return 'text-success-600';
    if (strength >= 40) return 'text-primary-600';
    return 'text-gray-600';
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 70) return 'bg-success-500';
    if (confidence >= 40) return 'bg-primary-500';
    return 'bg-gray-500';
  };

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 p-4 hover:shadow-lg transition-shadow">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-3 py-1 rounded-full text-sm font-semibold border ${getDirectionColor(signal.direction)}`}>
            <div className="flex items-center gap-1">
              {getDirectionIcon(signal.direction)}
              <span className="uppercase">{signal.direction}</span>
            </div>
          </span>
          <span className="text-lg font-bold text-gray-900">{signal.currency_pair}</span>
        </div>
        <div className="flex items-center gap-1 text-sm text-gray-500">
          <Clock className="w-4 h-4" />
          <span>{formatTime(signal.timestamp)}</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-3">
        <div>
          <div className="text-sm text-gray-500 mb-1">Strength</div>
          <div className={`text-2xl font-bold ${getStrengthColor(signal.strength)}`}>
            {signal.strength.toFixed(1)}
          </div>
        </div>
        <div>
          <div className="text-sm text-gray-500 mb-1">Confidence</div>
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-gray-200 rounded-full h-2">
              <div
                className={`h-2 rounded-full ${getConfidenceColor(signal.confidence)}`}
                style={{ width: `${signal.confidence}%` }}
              />
            </div>
            <span className="text-sm font-semibold">{signal.confidence.toFixed(0)}%</span>
          </div>
        </div>
      </div>

      <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
        <div className="flex items-center gap-1">
          <Activity className="w-4 h-4" />
          <span>{signal.volume} items</span>
        </div>
        <div>
          Consensus: {(signal.consensus_factor * 100).toFixed(0)}%
        </div>
      </div>

      {signal.supporting_headlines && signal.supporting_headlines.length > 0 && (
        <div className="border-t border-gray-200 pt-3">
          <div className="text-sm font-medium text-gray-700 mb-2">Key Headlines:</div>
          <ul className="space-y-1">
            {signal.supporting_headlines.slice(0, 2).map((headline, index) => (
              <li key={index} className="text-sm text-gray-600 truncate">
                • {headline}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
