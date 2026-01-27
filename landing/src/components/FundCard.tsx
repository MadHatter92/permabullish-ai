import { TrendingUp, TrendingDown, Info, ChevronRight, Bookmark } from 'lucide-react';

export interface FundCardProps {
  schemeCode: number;
  schemeName: string;
  fundHouse: string;
  category: string;
  aum?: number; // in crores
  nav?: number;
  returns?: {
    return1Y?: number;
    return3Y?: number;
    return5Y?: number;
  };
  riskLevel?: 'Low' | 'Moderate' | 'High' | 'Very High';
  inceptionDate?: string;
  expenseRatio?: number;
  onClick?: () => void;
  onBookmark?: () => void;
  isBookmarked?: boolean;
  variant?: 'default' | 'compact' | 'detailed';
}

// Risk level configuration
const riskConfig = {
  'Low': { color: 'bg-green-500', textColor: 'text-green-700', bgColor: 'bg-green-50', position: 'left-[10%]' },
  'Moderate': { color: 'bg-yellow-500', textColor: 'text-yellow-700', bgColor: 'bg-yellow-50', position: 'left-[35%]' },
  'High': { color: 'bg-orange-500', textColor: 'text-orange-700', bgColor: 'bg-orange-50', position: 'left-[60%]' },
  'Very High': { color: 'bg-red-500', textColor: 'text-red-700', bgColor: 'bg-red-50', position: 'left-[85%]' },
};

// Format large numbers
const formatAUM = (aum: number): string => {
  if (aum >= 10000) return `₹${(aum / 1000).toFixed(1)}K Cr`;
  if (aum >= 1000) return `₹${(aum / 1000).toFixed(2)}K Cr`;
  return `₹${aum.toFixed(0)} Cr`;
};

// Format return percentage
const formatReturn = (value?: number): string => {
  if (value === undefined || value === null) return '-';
  return `${value >= 0 ? '+' : ''}${value.toFixed(1)}%`;
};

// Return color based on value
const getReturnColor = (value?: number): string => {
  if (value === undefined || value === null) return 'text-gray-400';
  return value >= 0 ? 'text-green-600' : 'text-red-600';
};

// Category badge colors
const getCategoryStyle = (category: string): string => {
  const lowerCategory = category.toLowerCase();
  if (lowerCategory.includes('equity') || lowerCategory.includes('large cap')) {
    return 'bg-blue-50 text-blue-700 border-blue-200';
  }
  if (lowerCategory.includes('debt') || lowerCategory.includes('liquid')) {
    return 'bg-green-50 text-green-700 border-green-200';
  }
  if (lowerCategory.includes('hybrid')) {
    return 'bg-purple-50 text-purple-700 border-purple-200';
  }
  if (lowerCategory.includes('elss') || lowerCategory.includes('tax')) {
    return 'bg-orange-50 text-orange-700 border-orange-200';
  }
  return 'bg-gray-50 text-gray-700 border-gray-200';
};

// Shorten scheme name for display
const shortenName = (name: string, maxLength: number = 45): string => {
  if (name.length <= maxLength) return name;
  return name.substring(0, maxLength) + '...';
};

export default function FundCard({
  schemeCode,
  schemeName,
  fundHouse,
  category,
  aum,
  nav,
  returns,
  riskLevel = 'Moderate',
  inceptionDate,
  expenseRatio,
  onClick,
  onBookmark,
  isBookmarked = false,
  variant = 'default',
}: FundCardProps) {
  const risk = riskConfig[riskLevel];

  return (
    <div
      onClick={onClick}
      className={`
        relative bg-white rounded-2xl border border-gray-100
        shadow-card hover:shadow-card-hover
        transition-all duration-300 ease-out
        cursor-pointer group
        ${variant === 'compact' ? 'p-4' : 'p-5'}
      `}
    >
      {/* Top accent line */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1e3a5f] via-[#334e68] to-[#e8913a] rounded-t-2xl" />

      {/* Header Section */}
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="flex-1 min-w-0">
          {/* Fund House */}
          <p className="text-xs font-medium text-[#d97316] uppercase tracking-wide mb-1">
            {fundHouse || 'Fund House'}
          </p>

          {/* Scheme Name */}
          <h3 className="text-base font-display font-semibold text-[#1e3a5f] leading-tight mb-2 group-hover:text-[#334e68] transition-colors">
            {shortenName(schemeName)}
          </h3>

          {/* Category Badge */}
          {category && (
            <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium border ${getCategoryStyle(category)}`}>
              {category.length > 30 ? category.substring(0, 30) + '...' : category}
            </span>
          )}
        </div>

        {/* Bookmark Button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            onBookmark?.();
          }}
          className={`
            p-2 rounded-full transition-all duration-200
            ${isBookmarked
              ? 'bg-[#fdecd4] text-[#d97316]'
              : 'bg-gray-50 text-gray-400 hover:bg-gray-100 hover:text-gray-600'
            }
          `}
        >
          <Bookmark className={`w-5 h-5 ${isBookmarked ? 'fill-current' : ''}`} />
        </button>
      </div>

      {/* Returns Section */}
      <div className="grid grid-cols-3 gap-3 mb-4">
        <div className="text-center p-3 bg-gray-50 rounded-xl">
          <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">1Y Return</p>
          <p className={`text-lg font-bold ${getReturnColor(returns?.return1Y)}`}>
            {formatReturn(returns?.return1Y)}
          </p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-xl">
          <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">3Y Return</p>
          <p className={`text-lg font-bold ${getReturnColor(returns?.return3Y)}`}>
            {formatReturn(returns?.return3Y)}
          </p>
        </div>
        <div className="text-center p-3 bg-gray-50 rounded-xl">
          <p className="text-[10px] font-medium text-gray-500 uppercase tracking-wider mb-1">5Y Return</p>
          <p className={`text-lg font-bold ${getReturnColor(returns?.return5Y)}`}>
            {formatReturn(returns?.return5Y)}
          </p>
        </div>
      </div>

      {/* Risk Meter */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-gray-600">Risk Level</span>
          <span className={`text-xs font-semibold ${risk.textColor}`}>{riskLevel}</span>
        </div>
        <div className="relative h-2 bg-gradient-to-r from-green-400 via-yellow-400 via-orange-400 to-red-500 rounded-full">
          <div
            className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-4 h-4 bg-white border-2 border-[#1e3a5f] rounded-full shadow-md ${risk.position}`}
          />
        </div>
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-gray-400">Low</span>
          <span className="text-[9px] text-gray-400">Very High</span>
        </div>
      </div>

      {/* Bottom Stats */}
      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
        <div className="flex items-center gap-4">
          {/* AUM */}
          {aum !== undefined && (
            <div>
              <p className="text-[10px] font-medium text-gray-400 uppercase">AUM</p>
              <p className="text-sm font-semibold text-[#243b53]">{formatAUM(aum)}</p>
            </div>
          )}

          {/* NAV */}
          {nav !== undefined && (
            <div>
              <p className="text-[10px] font-medium text-gray-400 uppercase">NAV</p>
              <p className="text-sm font-semibold text-[#243b53]">₹{nav.toFixed(2)}</p>
            </div>
          )}

          {/* Expense Ratio */}
          {expenseRatio !== undefined && (
            <div>
              <p className="text-[10px] font-medium text-gray-400 uppercase">Expense</p>
              <p className="text-sm font-semibold text-[#243b53]">{expenseRatio.toFixed(2)}%</p>
            </div>
          )}
        </div>

        {/* View Details Arrow */}
        <div className="flex items-center text-[#e8913a] group-hover:text-[#d97316] transition-colors">
          <span className="text-xs font-medium mr-1 hidden sm:inline">View Details</span>
          <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </div>
      </div>

      {/* Hover overlay effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[#1e3a5f]/0 to-[#e8913a]/0 group-hover:from-[#1e3a5f]/[0.02] group-hover:to-[#e8913a]/[0.02] transition-all duration-300 pointer-events-none" />
    </div>
  );
}

// Compact variant for lists
export function FundCardCompact({
  schemeCode,
  schemeName,
  fundHouse,
  category,
  returns,
  onClick,
}: Pick<FundCardProps, 'schemeCode' | 'schemeName' | 'fundHouse' | 'category' | 'returns' | 'onClick'>) {
  return (
    <div
      onClick={onClick}
      className="flex items-center gap-4 p-4 bg-white rounded-xl border border-gray-100 shadow-card hover:shadow-card-hover transition-all duration-300 cursor-pointer group"
    >
      {/* Return indicator */}
      <div className={`
        w-12 h-12 rounded-xl flex items-center justify-center
        ${(returns?.return1Y ?? 0) >= 0 ? 'bg-green-50' : 'bg-red-50'}
      `}>
        {(returns?.return1Y ?? 0) >= 0
          ? <TrendingUp className="w-6 h-6 text-green-600" />
          : <TrendingDown className="w-6 h-6 text-red-600" />
        }
      </div>

      {/* Fund info */}
      <div className="flex-1 min-w-0">
        <p className="text-xs text-[#d97316] font-medium">{fundHouse}</p>
        <h4 className="text-sm font-display font-semibold text-[#1e3a5f] truncate">{schemeName}</h4>
        <p className="text-xs text-gray-500">{category}</p>
      </div>

      {/* Returns */}
      <div className="text-right">
        <p className={`text-lg font-bold ${getReturnColor(returns?.return1Y)}`}>
          {formatReturn(returns?.return1Y)}
        </p>
        <p className="text-[10px] text-gray-400 uppercase">1Y Return</p>
      </div>

      <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-[#e8913a] group-hover:translate-x-1 transition-all" />
    </div>
  );
}
