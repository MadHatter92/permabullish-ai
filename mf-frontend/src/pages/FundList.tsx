import { useState, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Header } from '../components/Header';
import { getCategoryById, getSubCategoryById } from '../data/categories';
import { ArrowUpRight, ArrowDownRight, Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import { API_BASE_URL } from '../config';

type SortColumn = 'scheme_name' | 'nav' | 'returns_1m' | 'returns_3m' | 'returns_1y' | 'returns_3y' | 'returns_5y';
type SortDirection = 'asc' | 'desc';

// Types for fund data
interface Fund {
  scheme_code: number;
  scheme_name: string;
  amc: string;
  nav: number | null;
  nav_date: string | null;
  returns_1m: number | null;
  returns_3m: number | null;
  returns_6m: number | null;
  returns_1y: number | null;
  returns_3y: number | null;
  returns_5y: number | null;
}

interface FundsResponse {
  funds: Fund[];
  total: number;
  limit: number;
  offset: number;
}

// Map frontend sub-category IDs to database sub-category names
const subCategoryMap: Record<string, string> = {
  'large-cap': 'Large Cap',
  'mid-cap': 'Mid Cap',
  'small-cap': 'Small Cap',
  'flexi-cap': 'Flexi Cap',
  'focused': 'Focused',
  'elss': 'ELSS',
  'value': 'Value & Contra',
  'liquid': 'Liquid',
  'short-duration': 'Short Duration',
  'corporate-bond': 'Corporate Bond',
  'gilt': 'Gilt',
  'dynamic-bond': 'Dynamic Bond',
  'aggressive-hybrid': 'Aggressive Hybrid',
  'conservative-hybrid': 'Conservative Hybrid',
  'balanced-advantage': 'Balanced Advantage',
  'arbitrage': 'Arbitrage',
  'multi-asset': 'Multi Asset',
  'nifty-50': 'Nifty 50',
  'sensex': 'Sensex',
  'nifty-next-50': 'Nifty Next 50',
  'sector-index': 'Sector Index',
  'international': 'International Index',
  'banking': 'Banking & Financial',
  'technology': 'Technology',
  'pharma-healthcare': 'Pharma & Healthcare',
  'infrastructure': 'Infrastructure',
  'consumption': 'Consumption',
  'manufacturing': 'Manufacturing & PSU',
  'esg': 'ESG',
  'retirement': 'Retirement',
  'children': 'Children',
  'gold-fund': 'Gold',
  'silver': 'Silver',
  'commodity': 'Commodity',
};

async function fetchFunds(categoryId: string, subCategoryId: string, directOnly: boolean, growthOnly: boolean): Promise<Fund[]> {
  const dbSubCategory = subCategoryMap[subCategoryId] || subCategoryId;

  const params = new URLSearchParams({
    category: categoryId,
    sub_category: dbSubCategory,
    plan: directOnly ? 'direct' : 'all',
    option: growthOnly ? 'growth' : 'all',
    limit: '500',
  });

  const response = await fetch(`${API_BASE_URL}/api/mf/funds?${params}`);

  if (!response.ok) {
    throw new Error('Failed to fetch funds');
  }

  const data: FundsResponse = await response.json();
  return data.funds;
}

function ReturnCell({ value }: { value: number | null }) {
  if (value === null) {
    return <span className="text-navy-300 block text-right">-</span>;
  }

  const isPositive = value >= 0;
  const Icon = isPositive ? ArrowUpRight : ArrowDownRight;

  return (
    <span className={`flex items-center justify-end gap-0.5 ${isPositive ? 'text-positive' : 'text-negative'}`}>
      <Icon size={14} />
      {Math.abs(value).toFixed(1)}%
    </span>
  );
}

export function FundList() {
  const { categoryId, subCategoryId } = useParams<{ categoryId: string; subCategoryId: string }>();
  const navigate = useNavigate();
  const [sortColumn, setSortColumn] = useState<SortColumn>('returns_1y');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [directOnly, setDirectOnly] = useState(true);
  const [growthOnly, setGrowthOnly] = useState(true);

  const category = categoryId ? getCategoryById(categoryId) : undefined;
  const subCategory = categoryId && subCategoryId
    ? getSubCategoryById(categoryId, subCategoryId)
    : undefined;

  const { data: funds, isLoading, error } = useQuery({
    queryKey: ['funds', categoryId, subCategoryId, directOnly, growthOnly],
    queryFn: () => fetchFunds(categoryId!, subCategoryId!, directOnly, growthOnly),
    enabled: !!categoryId && !!subCategoryId,
  });

  // Sort funds
  const sortedFunds = useMemo(() => {
    if (!funds) return [];

    return [...funds].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      // Handle nulls - push them to the end
      if (aVal === null && bVal === null) return 0;
      if (aVal === null) return 1;
      if (bVal === null) return -1;

      // Compare values
      let comparison = 0;
      if (typeof aVal === 'string' && typeof bVal === 'string') {
        comparison = aVal.localeCompare(bVal);
      } else {
        comparison = (aVal as number) - (bVal as number);
      }

      return sortDirection === 'asc' ? comparison : -comparison;
    });
  }, [funds, sortColumn, sortDirection]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(column);
      setSortDirection('desc'); // Default to descending for new column
    }
  };

  const SortHeader = ({ column, children, align = 'right' }: { column: SortColumn; children: React.ReactNode; align?: 'left' | 'right' }) => (
    <th
      className={`px-3 py-3 font-medium cursor-pointer hover:bg-navy-100 transition-colors select-none ${align === 'right' ? 'text-right' : 'text-left'} ${column === 'scheme_name' ? 'px-5' : ''}`}
      onClick={() => handleSort(column)}
    >
      <div className={`flex items-center gap-1 ${align === 'right' ? 'justify-end' : ''}`}>
        <span>{children}</span>
        {sortColumn === column && (
          sortDirection === 'asc' ? <ChevronUp size={14} /> : <ChevronDown size={14} />
        )}
      </div>
    </th>
  );

  if (!category || !subCategory) {
    return (
      <div className="min-h-screen bg-navy-50">
        <Header showBack onBack={() => navigate('/')} />
        <main className="max-w-7xl mx-auto px-4 py-8 text-center">
          <h1 className="font-display text-2xl text-navy-900">Category not found</h1>
          <button
            onClick={() => navigate('/')}
            className="btn-primary mt-4"
          >
            Go back to categories
          </button>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-navy-50">
      <Header
        title={subCategory.name}
        showBack
        onBack={() => navigate(`/category/${categoryId}`)}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <nav className="flex items-center gap-2 text-sm text-navy-500 mb-4">
          <button
            onClick={() => navigate('/')}
            className="hover:text-saffron-500 transition-colors"
          >
            Categories
          </button>
          <span>/</span>
          <button
            onClick={() => navigate(`/category/${categoryId}`)}
            className="hover:text-saffron-500 transition-colors"
          >
            {category.name}
          </button>
          <span>/</span>
          <span className="text-navy-700 font-medium">{subCategory.name}</span>
        </nav>

        {/* Sub-category info */}
        <div className="relative bg-white rounded-2xl border border-gray-100 shadow-card p-5 mb-6 overflow-hidden">
          {/* Top accent gradient */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1e3a5f] via-[#334e68] to-[#e8913a]" />

          <div className="flex items-center gap-2 mb-2 pt-2">
            <div
              className="w-1 h-5 rounded-full"
              style={{ backgroundColor: category.color }}
            />
            <h1 className="font-display text-xl text-navy-900">
              {subCategory.name}
            </h1>
          </div>
          <p className="text-sm text-navy-600 pl-3">
            {subCategory.description}
          </p>
        </div>

        {/* Fund table */}
        <div className="relative bg-white rounded-2xl border border-gray-100 shadow-card overflow-hidden">
          {/* Top accent gradient */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1e3a5f] via-[#334e68] to-[#e8913a] z-10" />

          {/* Table header with filters */}
          <div className="bg-navy-50 px-5 py-3 border-b border-navy-100 flex items-center justify-between flex-wrap gap-3">
            <h2 className="font-semibold text-navy-800">
              Funds {funds && `(${funds.length})`}
            </h2>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 text-sm text-navy-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={directOnly}
                  onChange={(e) => setDirectOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-navy-300 text-saffron-500 focus:ring-saffron-500"
                />
                Direct
              </label>
              <label className="flex items-center gap-2 text-sm text-navy-700 cursor-pointer">
                <input
                  type="checkbox"
                  checked={growthOnly}
                  onChange={(e) => setGrowthOnly(e.target.checked)}
                  className="w-4 h-4 rounded border-navy-300 text-saffron-500 focus:ring-saffron-500"
                />
                Growth
              </label>
            </div>
          </div>

          {/* Loading state */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-saffron-500" size={32} />
            </div>
          )}

          {/* Error state */}
          {error && (
            <div className="text-center py-12">
              <p className="text-red-600 mb-4">Failed to load funds</p>
              <button
                onClick={() => window.location.reload()}
                className="btn-primary"
              >
                Retry
              </button>
            </div>
          )}

          {/* Fund list */}
          {funds && funds.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-navy-500 uppercase tracking-wider border-b border-navy-100">
                    <SortHeader column="scheme_name" align="left">Fund Name</SortHeader>
                    <SortHeader column="nav">NAV</SortHeader>
                    <SortHeader column="returns_1m">1M</SortHeader>
                    <SortHeader column="returns_3m">3M</SortHeader>
                    <SortHeader column="returns_1y">1Y</SortHeader>
                    <SortHeader column="returns_3y">3Y CAGR</SortHeader>
                    <SortHeader column="returns_5y">5Y CAGR</SortHeader>
                  </tr>
                </thead>
                <tbody className="divide-y divide-navy-50">
                  {sortedFunds.map((fund) => (
                    <tr
                      key={fund.scheme_code}
                      className="hover:bg-navy-50/50 cursor-pointer transition-colors"
                      onClick={() => navigate(`/fund/${fund.scheme_code}`)}
                    >
                      <td className="px-5 py-4">
                        <div>
                          <p className="font-medium text-navy-900 text-sm">
                            {fund.scheme_name}
                          </p>
                          <p className="text-xs text-navy-400 mt-0.5">
                            {fund.amc}
                          </p>
                        </div>
                      </td>
                      <td className="px-3 py-4 text-right">
                        <span className="font-medium text-navy-900">
                          {fund.nav ? `₹${fund.nav.toFixed(2)}` : '-'}
                        </span>
                      </td>
                      <td className="px-3 py-4 text-right text-sm">
                        <ReturnCell value={fund.returns_1m} />
                      </td>
                      <td className="px-3 py-4 text-right text-sm">
                        <ReturnCell value={fund.returns_3m} />
                      </td>
                      <td className="px-3 py-4 text-right text-sm">
                        <ReturnCell value={fund.returns_1y} />
                      </td>
                      <td className="px-3 py-4 text-right text-sm">
                        <ReturnCell value={fund.returns_3y} />
                      </td>
                      <td className="px-3 py-4 text-right text-sm">
                        <ReturnCell value={fund.returns_5y} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Empty state */}
          {funds && funds.length === 0 && (
            <div className="text-center py-12">
              <p className="text-navy-500">No funds found in this category</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
