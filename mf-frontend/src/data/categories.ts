// MF Categories with sub-categories
// Risk levels: 1-5 (1 = Low, 5 = Very High)

export interface SubCategory {
  id: string;
  name: string;
  description: string;
  riskLevel: number;
  keywords: string[];
}

export interface Category {
  id: string;
  name: string;
  description: string;
  icon: string; // Lucide icon name
  riskLevel: number; // Average risk level
  color: string; // Accent color for the category
  subCategories: SubCategory[];
}

export const categories: Category[] = [
  {
    id: 'equity',
    name: 'Equity Funds',
    description: 'Invest primarily in stocks for long-term capital appreciation. Higher risk, higher potential returns.',
    icon: 'TrendingUp',
    riskLevel: 4,
    color: '#e8913a', // saffron-500
    subCategories: [
      {
        id: 'large-cap',
        name: 'Large Cap',
        description: 'Invest in top 100 companies by market capitalization. Stable and relatively lower risk within equity.',
        riskLevel: 3,
        keywords: ['large cap', 'largecap', 'bluechip', 'blue chip', 'top 100', 'frontline equity'],
      },
      {
        id: 'mid-cap',
        name: 'Mid Cap',
        description: 'Invest in companies ranked 101-250 by market cap. Balance of growth potential and stability.',
        riskLevel: 4,
        keywords: ['mid cap', 'midcap', 'mid-cap'],
      },
      {
        id: 'small-cap',
        name: 'Small Cap',
        description: 'Invest in companies ranked 251+ by market cap. High growth potential with higher volatility.',
        riskLevel: 5,
        keywords: ['small cap', 'smallcap', 'small-cap', 'emerging'],
      },
      {
        id: 'flexi-cap',
        name: 'Flexi Cap',
        description: 'Invest across market capitalizations without restrictions. Fund manager decides allocation.',
        riskLevel: 4,
        keywords: ['flexi cap', 'flexicap', 'flexi-cap', 'multi cap', 'multicap'],
      },
      {
        id: 'focused',
        name: 'Focused Funds',
        description: 'Concentrated portfolios with maximum 30 stocks. Higher conviction bets on select companies.',
        riskLevel: 4,
        keywords: ['focused', 'concentrated', 'select', 'special situations'],
      },
      {
        id: 'elss',
        name: 'ELSS (Tax Saver)',
        description: 'Equity funds with 3-year lock-in. Tax deduction under Section 80C up to ₹1.5 lakh.',
        riskLevel: 4,
        keywords: ['elss', 'tax saver', 'tax saving', 'tax advantage', '80c', 'tax plan'],
      },
      {
        id: 'value',
        name: 'Value & Contra',
        description: 'Invest in undervalued stocks or against market trends. Requires patience for returns.',
        riskLevel: 4,
        keywords: ['value', 'contra', 'contrarian', 'dividend yield'],
      },
    ],
  },
  {
    id: 'debt',
    name: 'Debt Funds',
    description: 'Invest in fixed income securities like bonds and government securities. Lower risk, steady returns.',
    icon: 'Shield',
    riskLevel: 2,
    color: '#1e3a5f', // navy-900
    subCategories: [
      {
        id: 'liquid',
        name: 'Liquid Funds',
        description: 'Invest in securities with maturity up to 91 days. Ideal for parking surplus cash.',
        riskLevel: 1,
        keywords: ['liquid', 'money market', 'overnight', 'ultra short'],
      },
      {
        id: 'short-duration',
        name: 'Short Duration',
        description: 'Invest in debt with 1-3 year duration. Balance of safety and returns.',
        riskLevel: 2,
        keywords: ['short duration', 'short term', 'low duration', 'banking and psu'],
      },
      {
        id: 'corporate-bond',
        name: 'Corporate Bond',
        description: 'Invest in high-rated corporate bonds. Better yields than government securities.',
        riskLevel: 2,
        keywords: ['corporate bond', 'credit risk', 'corporate debt'],
      },
      {
        id: 'gilt',
        name: 'Gilt Funds',
        description: 'Invest in government securities. Zero credit risk but interest rate sensitive.',
        riskLevel: 2,
        keywords: ['gilt', 'government securities', 'gsec', 'g-sec', 'constant maturity'],
      },
      {
        id: 'dynamic-bond',
        name: 'Dynamic Bond',
        description: 'Actively manage duration based on interest rate outlook. Flexible allocation.',
        riskLevel: 3,
        keywords: ['dynamic bond', 'dynamic debt', 'strategic bond'],
      },
    ],
  },
  {
    id: 'hybrid',
    name: 'Hybrid Funds',
    description: 'Invest in both equity and debt for balanced risk-return. Suitable for moderate risk appetite.',
    icon: 'Scale',
    riskLevel: 3,
    color: '#627d98', // navy-500
    subCategories: [
      {
        id: 'aggressive-hybrid',
        name: 'Aggressive Hybrid',
        description: '65-80% in equity, rest in debt. Equity taxation benefits with some debt cushion.',
        riskLevel: 4,
        keywords: ['aggressive hybrid', 'equity hybrid', 'balanced advantage'],
      },
      {
        id: 'conservative-hybrid',
        name: 'Conservative Hybrid',
        description: '10-25% in equity, rest in debt. Debt-focused with equity upside.',
        riskLevel: 2,
        keywords: ['conservative hybrid', 'debt hybrid', 'monthly income', 'mip'],
      },
      {
        id: 'balanced-advantage',
        name: 'Balanced Advantage',
        description: 'Dynamic equity allocation based on market valuations. Automatic rebalancing.',
        riskLevel: 3,
        keywords: ['balanced advantage', 'dynamic asset allocation', 'baf'],
      },
      {
        id: 'arbitrage',
        name: 'Arbitrage Funds',
        description: 'Exploit price differences between cash and derivatives market. Low risk equity taxation.',
        riskLevel: 1,
        keywords: ['arbitrage', 'equity savings'],
      },
      {
        id: 'multi-asset',
        name: 'Multi Asset',
        description: 'Invest across equity, debt, and gold/commodities. True diversification.',
        riskLevel: 3,
        keywords: ['multi asset', 'multi-asset', 'asset allocation'],
      },
    ],
  },
  {
    id: 'index',
    name: 'Index & ETFs',
    description: 'Passively track market indices with low expense ratios. Ideal for long-term wealth creation.',
    icon: 'BarChart3',
    riskLevel: 4,
    color: '#f19338', // saffron-400
    subCategories: [
      {
        id: 'nifty-50',
        name: 'Nifty 50',
        description: 'Track the Nifty 50 index representing top 50 companies. Most popular index funds.',
        riskLevel: 3,
        keywords: ['nifty 50', 'nifty50', 'nifty index'],
      },
      {
        id: 'sensex',
        name: 'Sensex',
        description: 'Track the BSE Sensex representing 30 large companies.',
        riskLevel: 3,
        keywords: ['sensex', 'bse 30'],
      },
      {
        id: 'nifty-next-50',
        name: 'Nifty Next 50',
        description: 'Track companies ranked 51-100 by market cap. Higher growth potential.',
        riskLevel: 4,
        keywords: ['nifty next 50', 'junior nifty', 'nifty junior'],
      },
      {
        id: 'sector-index',
        name: 'Sector Index',
        description: 'Track specific sectors like IT, Banking, Pharma. Concentrated sector exposure.',
        riskLevel: 4,
        keywords: ['nifty bank', 'nifty it', 'nifty pharma', 'nifty infra', 'nifty pse', 'sector index'],
      },
      {
        id: 'international',
        name: 'International Index',
        description: 'Track global indices like S&P 500, Nasdaq. Geographic diversification.',
        riskLevel: 4,
        keywords: ['nasdaq', 's&p 500', 'us equity', 'international', 'global', 'world'],
      },
    ],
  },
  {
    id: 'sectoral',
    name: 'Sectoral & Thematic',
    description: 'Concentrate investments in specific sectors or themes. High risk, high reward potential.',
    icon: 'Layers',
    riskLevel: 5,
    color: '#d97316', // saffron-600
    subCategories: [
      {
        id: 'banking',
        name: 'Banking & Financial',
        description: 'Invest in banks, NBFCs, and financial services. Benefit from credit growth.',
        riskLevel: 4,
        keywords: ['banking', 'financial', 'bfsi', 'nbfc', 'bank'],
      },
      {
        id: 'technology',
        name: 'Technology',
        description: 'Invest in IT and technology companies. Growth-oriented sector.',
        riskLevel: 5,
        keywords: ['technology', 'it sector', 'digital', 'tech'],
      },
      {
        id: 'pharma-healthcare',
        name: 'Pharma & Healthcare',
        description: 'Invest in pharmaceutical and healthcare companies. Defensive with growth.',
        riskLevel: 4,
        keywords: ['pharma', 'healthcare', 'health', 'medical'],
      },
      {
        id: 'infrastructure',
        name: 'Infrastructure',
        description: 'Invest in infrastructure, construction, and capital goods. Cyclical theme.',
        riskLevel: 5,
        keywords: ['infrastructure', 'infra', 'construction', 'capital goods', 'power'],
      },
      {
        id: 'consumption',
        name: 'Consumption',
        description: 'Invest in FMCG, consumer durables, and retail. Benefit from rising incomes.',
        riskLevel: 4,
        keywords: ['consumption', 'consumer', 'fmcg', 'retail'],
      },
      {
        id: 'manufacturing',
        name: 'Manufacturing & PSU',
        description: 'Invest in manufacturing and public sector units. Make in India theme.',
        riskLevel: 4,
        keywords: ['manufacturing', 'psu', 'public sector', 'make in india', 'defence', 'defense'],
      },
      {
        id: 'esg',
        name: 'ESG & Sustainable',
        description: 'Invest in companies with strong ESG practices. Sustainable investing theme.',
        riskLevel: 4,
        keywords: ['esg', 'sustainable', 'responsible', 'green', 'climate', 'clean energy'],
      },
    ],
  },
  {
    id: 'solution',
    name: 'Solution Oriented',
    description: 'Goal-based funds for retirement and children\'s education with lock-in periods.',
    icon: 'Target',
    riskLevel: 3,
    color: '#334e68', // navy-700
    subCategories: [
      {
        id: 'retirement',
        name: 'Retirement Funds',
        description: 'Designed for retirement planning with 5-year lock-in. Long-term wealth creation.',
        riskLevel: 3,
        keywords: ['retirement', 'pension', 'senior citizen'],
      },
      {
        id: 'children',
        name: 'Children\'s Funds',
        description: 'Designed for children\'s education and future needs. 5-year lock-in period.',
        riskLevel: 3,
        keywords: ['children', 'child', 'education', 'future'],
      },
    ],
  },
  {
    id: 'gold',
    name: 'Gold & Commodities',
    description: 'Invest in gold and other commodities for portfolio diversification and inflation hedge.',
    icon: 'Gem',
    riskLevel: 3,
    color: '#f6b871', // saffron-300
    subCategories: [
      {
        id: 'gold-fund',
        name: 'Gold Funds',
        description: 'Invest in gold through ETFs or fund of funds. Hedge against uncertainty.',
        riskLevel: 3,
        keywords: ['gold', 'precious metal'],
      },
      {
        id: 'silver',
        name: 'Silver Funds',
        description: 'Invest in silver through ETFs. Industrial and precious metal exposure.',
        riskLevel: 4,
        keywords: ['silver'],
      },
      {
        id: 'commodity',
        name: 'Commodity Funds',
        description: 'Invest in a basket of commodities. Diversification and inflation hedge.',
        riskLevel: 4,
        keywords: ['commodity', 'commodities'],
      },
    ],
  },
];

// Helper function to get all keywords for categorization
export function getAllKeywords(): Map<string, { categoryId: string; subCategoryId: string }> {
  const keywordMap = new Map<string, { categoryId: string; subCategoryId: string }>();

  categories.forEach(category => {
    category.subCategories.forEach(subCategory => {
      subCategory.keywords.forEach(keyword => {
        keywordMap.set(keyword.toLowerCase(), {
          categoryId: category.id,
          subCategoryId: subCategory.id,
        });
      });
    });
  });

  return keywordMap;
}

// Helper to get category by ID
export function getCategoryById(id: string): Category | undefined {
  return categories.find(c => c.id === id);
}

// Helper to get subcategory
export function getSubCategoryById(categoryId: string, subCategoryId: string): SubCategory | undefined {
  const category = getCategoryById(categoryId);
  return category?.subCategories.find(sc => sc.id === subCategoryId);
}
