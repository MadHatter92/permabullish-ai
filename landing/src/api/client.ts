import axios from 'axios';
import type {
  MutualFund,
  CalculatedReturns,
  FundSearchParams,
  CategorySummary,
  FundHouseSummary,
  NavRecord,
} from '../../../shared/types';

const api = axios.create({
  baseURL: '/api',
});

export interface FundWithReturns extends MutualFund {
  returns: CalculatedReturns | null;
}

export interface FundsListResponse {
  funds: FundWithReturns[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export interface OverviewStats {
  totalFunds: number;
  totalFundHouses: number;
  totalCategories: number;
  latestNavDate: string | null;
  totalNavRecords: number;
  avgReturn1Y: number | null;
  avgReturn3Y: number | null;
}

export interface FundDetailResponse {
  fund: MutualFund;
  returns: CalculatedReturns | null;
}

export interface NavHistoryResponse {
  schemeCode: number;
  navHistory: NavRecord[];
}

export interface CompareResponse {
  funds: FundWithReturns[];
  navHistory: Record<number, { date: string; nav: number }[]>;
}

// API functions
export async function getOverview(): Promise<OverviewStats> {
  const { data } = await api.get<OverviewStats>('/overview');
  return data;
}

export async function getFunds(params: FundSearchParams): Promise<FundsListResponse> {
  const { data } = await api.get<FundsListResponse>('/funds', {
    params: {
      q: params.query,
      fundHouse: params.fundHouse,
      category: params.category,
      schemeType: params.schemeType,
      planType: params.planType,
      optionType: params.optionType,
      sortBy: params.sortBy,
      sortOrder: params.sortOrder,
      page: params.page,
      pageSize: params.pageSize,
    },
  });
  return data;
}

export async function getFundDetail(schemeCode: number): Promise<FundDetailResponse> {
  const { data } = await api.get<FundDetailResponse>(`/funds/${schemeCode}`);
  return data;
}

export async function getNavHistory(
  schemeCode: number,
  options?: { limit?: number; startDate?: string; endDate?: string }
): Promise<NavHistoryResponse> {
  const { data } = await api.get<NavHistoryResponse>(`/funds/${schemeCode}/nav`, {
    params: options,
  });
  return data;
}

export async function getFundHouses(): Promise<FundHouseSummary[]> {
  const { data } = await api.get<FundHouseSummary[]>('/fund-houses');
  return data;
}

export async function getCategories(): Promise<CategorySummary[]> {
  const { data } = await api.get<CategorySummary[]>('/categories');
  return data;
}

export async function getTopPerformers(options?: {
  category?: string;
  planType?: 'Direct' | 'Regular';
  sortBy?: 'return1Y' | 'return3Y' | 'return5Y';
  limit?: number;
}): Promise<FundWithReturns[]> {
  const { data } = await api.get<FundWithReturns[]>('/top-performers', { params: options });
  return data;
}

export async function compareFunds(schemeCodes: number[]): Promise<CompareResponse> {
  const { data } = await api.get<CompareResponse>('/compare', {
    params: { codes: schemeCodes.join(',') },
  });
  return data;
}
