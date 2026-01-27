const express = require('express');
const cors = require('cors');
const Database = require('better-sqlite3');
const path = require('path');

const app = express();
const PORT = 3001;

// Database path
const dbPath = path.join(__dirname, '../../../MFAnalytics/data/mf.db');
const db = new Database(dbPath, { readonly: true });

app.use(cors());
app.use(express.json());

// Get category statistics (fund counts per category)
app.get('/api/categories/stats', (req, res) => {
  try {
    const stats = db.prepare(`
      SELECT
        category,
        sub_category,
        COUNT(*) as count
      FROM mutual_funds
      WHERE category IS NOT NULL
        AND category != 'uncategorized'
        AND category != 'fmp'
      GROUP BY category, sub_category
      ORDER BY category, count DESC
    `).all();

    res.json(stats);
  } catch (error) {
    console.error('Error fetching category stats:', error);
    res.status(500).json({ error: 'Failed to fetch category stats' });
  }
});

// Get funds by category and sub-category
app.get('/api/funds', (req, res) => {
  try {
    const { category, sub_category, plan = 'direct', option = 'growth', limit = 100, offset = 0 } = req.query;

    let whereConditions = ['category IS NOT NULL'];
    const params = {};

    if (category) {
      whereConditions.push('category = @category');
      params.category = category;
    }

    if (sub_category) {
      whereConditions.push('sub_category = @sub_category');
      params.sub_category = sub_category;
    }

    // Filter by plan type (Direct/Regular)
    if (plan === 'direct') {
      whereConditions.push("scheme_name LIKE '%Direct%'");
    } else if (plan === 'regular') {
      whereConditions.push("scheme_name LIKE '%Regular%'");
    }

    // Filter by option type (Growth/Dividend)
    if (option === 'growth') {
      whereConditions.push("scheme_name LIKE '%Growth%'");
    } else if (option === 'dividend') {
      whereConditions.push("(scheme_name LIKE '%IDCW%' OR scheme_name LIKE '%Dividend%')");
    }

    // Exclude FMPs by default
    whereConditions.push("category != 'fmp'");

    const whereClause = whereConditions.join(' AND ');

    const funds = db.prepare(`
      SELECT
        mf.scheme_code,
        mf.scheme_name,
        mf.amc,
        mf.category,
        mf.sub_category,
        (SELECT nav FROM nav_records WHERE scheme_code = mf.scheme_code ORDER BY date DESC LIMIT 1) as nav,
        (SELECT date FROM nav_records WHERE scheme_code = mf.scheme_code ORDER BY date DESC LIMIT 1) as nav_date,
        cr.returns_1m,
        cr.returns_3m,
        cr.returns_6m,
        cr.returns_1y,
        cr.returns_3y,
        cr.returns_5y
      FROM mutual_funds mf
      LEFT JOIN calculated_returns cr ON mf.scheme_code = cr.scheme_code
      WHERE ${whereClause}
      ORDER BY mf.scheme_name
      LIMIT @limit OFFSET @offset
    `).all({ ...params, limit: parseInt(limit), offset: parseInt(offset) });

    // Get total count for pagination
    const countResult = db.prepare(`
      SELECT COUNT(*) as total
      FROM mutual_funds
      WHERE ${whereClause}
    `).get(params);

    res.json({
      funds,
      total: countResult.total,
      limit: parseInt(limit),
      offset: parseInt(offset)
    });
  } catch (error) {
    console.error('Error fetching funds:', error);
    res.status(500).json({ error: 'Failed to fetch funds' });
  }
});

// Get single fund details
app.get('/api/funds/:schemeCode', (req, res) => {
  try {
    const { schemeCode } = req.params;

    const fund = db.prepare(`
      SELECT
        mf.*,
        cr.returns_1m,
        cr.returns_3m,
        cr.returns_6m,
        cr.returns_1y,
        cr.returns_3y,
        cr.returns_5y,
        cr.calculated_at
      FROM mutual_funds mf
      LEFT JOIN calculated_returns cr ON mf.scheme_code = cr.scheme_code
      WHERE mf.scheme_code = ?
    `).get(schemeCode);

    if (!fund) {
      return res.status(404).json({ error: 'Fund not found' });
    }

    res.json(fund);
  } catch (error) {
    console.error('Error fetching fund:', error);
    res.status(500).json({ error: 'Failed to fetch fund' });
  }
});

// Search funds
app.get('/api/search', (req, res) => {
  try {
    const { q, limit = 20 } = req.query;

    if (!q || q.length < 2) {
      return res.json([]);
    }

    const funds = db.prepare(`
      SELECT
        scheme_code,
        scheme_name,
        amc,
        category,
        sub_category
      FROM mutual_funds
      WHERE scheme_name LIKE @query
        AND category != 'fmp'
        AND scheme_name LIKE '%Direct%'
        AND scheme_name LIKE '%Growth%'
      ORDER BY scheme_name
      LIMIT @limit
    `).all({ query: `%${q}%`, limit: parseInt(limit) });

    res.json(funds);
  } catch (error) {
    console.error('Error searching funds:', error);
    res.status(500).json({ error: 'Search failed' });
  }
});

app.listen(PORT, () => {
  console.log(`MF Analytics API running on http://localhost:${PORT}`);
});
