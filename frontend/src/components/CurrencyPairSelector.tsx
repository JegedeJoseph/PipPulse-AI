'use client';

import { useStore } from '@/store/useStore';

const CURRENCY_PAIRS = [
  'EUR/USD',
  'GBP/USD',
  'USD/JPY',
  'USD/CHF',
  'AUD/USD',
  'USD/CAD',
  'NZD/USD',
  'USD/SGD',
];

export function CurrencyPairSelector() {
  const { selectedCurrencyPair, setSelectedCurrencyPair } = useStore();

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="currency-pair" className="text-sm font-medium text-gray-700">
        Currency Pair:
      </label>
      <select
        id="currency-pair"
        value={selectedCurrencyPair}
        onChange={(e) => setSelectedCurrencyPair(e.target.value)}
        className="px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 bg-white"
      >
        {CURRENCY_PAIRS.map((pair) => (
          <option key={pair} value={pair}>
            {pair}
          </option>
        ))}
      </select>
    </div>
  );
}
