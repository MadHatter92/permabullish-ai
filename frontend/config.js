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

        // Feature flags (can be expanded based on user subscription)
        features: {
            stockResearch: true,
            mfAnalytics: false,  // Phase 3
            pmsTracker: false,   // Phase 2
        },

        // Report limits (informational, actual limits enforced server-side)
        limits: {
            anonymous: 3,
            free: 20,
            pro: 100,
            enterprise: 1000,
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
