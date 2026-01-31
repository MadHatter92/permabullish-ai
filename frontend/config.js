/**
 * Permabullish Frontend Configuration
 * Automatically detects environment based on hostname
 */

(function() {
    'use strict';

    // Detect environment based on hostname
    const hostname = window.location.hostname;

    let API_BASE;
    let ENVIRONMENT;

    if (hostname === 'localhost' || hostname === '127.0.0.1') {
        // Local development
        API_BASE = 'http://localhost:8000/api';
        ENVIRONMENT = 'development';
    } else if (hostname.includes('staging') || hostname.includes('-staging')) {
        // Staging environment
        API_BASE = 'https://permabullish-api-staging.onrender.com/api';
        ENVIRONMENT = 'staging';
    } else if (hostname === 'permabullish.com' || hostname === 'www.permabullish.com') {
        // Production with custom domain
        API_BASE = 'https://api.permabullish.com/api';
        ENVIRONMENT = 'production';
    } else {
        // Default to Render production URLs
        API_BASE = 'https://permabullish-api.onrender.com/api';
        ENVIRONMENT = 'production';
    }

    // Export for use in other files
    window.API_BASE = API_BASE;
    window.ENVIRONMENT = ENVIRONMENT;

    // Configuration object for more complex use cases
    window.CONFIG = {
        API_BASE: API_BASE,
        ENVIRONMENT: ENVIRONMENT,

        // Feature flags
        features: {
            stockResearch: true,
            watchlist: true,
        },

        // Subscription tiers (informational, actual limits enforced server-side)
        // Guest (anonymous) users: 1 report
        tiers: {
            guest: {
                limit: 1,
                isLifetime: true,
                label: 'Guest'
            },
            free: {
                limit: 5,
                isLifetime: true,  // Lifetime limit for free tier
                label: 'Free'
            },
            basic: {
                limit: 50,
                isLifetime: false,  // Monthly limit
                label: 'Basic'
            },
            pro: {
                limit: 100,
                isLifetime: false,  // Monthly limit
                label: 'Pro'
            },
            enterprise: {
                limit: 10000,
                isLifetime: false,
                label: 'Enterprise'
            }
        },

        // Report freshness threshold (days)
        reportFreshnessDays: 15,

        // Cashfree Payment Form URLs
        paymentForms: {
            basic: {
                monthly: 'https://payments.cashfree.com/forms/PermabullishBasicMonthly',
                '6months': 'https://payments.cashfree.com/forms/PermabullishBasic6Months',
                yearly: 'https://payments.cashfree.com/forms/PermabullishBasicYearly'
            },
            pro: {
                monthly: 'https://payments.cashfree.com/forms/PermabullishProMonthly',
                '6months': 'https://payments.cashfree.com/forms/Pro6Months',
                yearly: 'https://payments.cashfree.com/forms/PermabullishProYearly'
            }
        }
    };

    // Log configuration in development
    if (ENVIRONMENT === 'development') {
        console.log('Permabullish Config:', {
            API_BASE: API_BASE,
            ENVIRONMENT: ENVIRONMENT,
            hostname: hostname
        });
    }
})();
