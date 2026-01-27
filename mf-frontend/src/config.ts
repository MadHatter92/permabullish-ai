// API Configuration
// Uses environment variables in production, localhost in development

export const API_BASE_URL = import.meta.env.PROD
  ? 'https://permabullish-api.onrender.com'
  : 'http://localhost:8000';

// MF API endpoints (now part of the main Permabullish API)
export const MF_API = {
  categoryStats: `${API_BASE_URL}/api/mf/categories/stats`,
  funds: `${API_BASE_URL}/api/mf/funds`,
  fundDetail: (schemeCode: string) => `${API_BASE_URL}/api/mf/funds/${schemeCode}`,
  search: `${API_BASE_URL}/api/mf/search`,
};
