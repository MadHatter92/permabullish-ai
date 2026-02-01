/**
 * Permabullish Analytics Module
 * Comprehensive GA4 tracking for user behavior and conversions
 */

const GA_MEASUREMENT_ID = 'G-75Y271369Q';

// Initialize GA4
window.dataLayer = window.dataLayer || [];
function gtag() { dataLayer.push(arguments); }
gtag('js', new Date());
gtag('config', GA_MEASUREMENT_ID, {
    send_page_view: true,
    cookie_flags: 'SameSite=None;Secure'
});

/**
 * Set user properties for segmentation
 * Call this after user logs in or on page load if logged in
 */
function setUserProperties(user) {
    if (!user) return;

    gtag('set', 'user_properties', {
        subscription_tier: user.subscription_tier || 'free',
        account_type: user.google_id ? 'google' : 'email',
        reports_generated: user.reports_generated || 0
    });

    // Set user ID for cross-session tracking
    if (user.id) {
        gtag('set', { 'user_id': user.id.toString() });
    }
}

/**
 * Track user registration
 * @param {string} method - 'email' or 'google'
 */
function trackRegistration(method) {
    gtag('event', 'sign_up', {
        method: method
    });

    // Mark as conversion
    gtag('event', 'conversion', {
        event_category: 'engagement',
        event_label: 'registration_complete'
    });
}

/**
 * Track user login
 * @param {string} method - 'email' or 'google'
 */
function trackLogin(method) {
    gtag('event', 'login', {
        method: method
    });
}

/**
 * Track report generation
 * @param {string} ticker - Stock ticker symbol
 * @param {string} companyName - Company name
 * @param {boolean} success - Whether generation succeeded
 * @param {boolean} cached - Whether report was from cache
 */
function trackReportGeneration(ticker, companyName, success, cached = false) {
    gtag('event', 'generate_report', {
        event_category: 'reports',
        ticker: ticker,
        company_name: companyName,
        success: success,
        from_cache: cached
    });

    if (success) {
        // Track as conversion for first report
        gtag('event', 'conversion', {
            event_category: 'engagement',
            event_label: 'report_generated'
        });
    }
}

/**
 * Track report view
 * @param {string} ticker - Stock ticker
 * @param {string} recommendation - AI recommendation
 * @param {boolean} isOwner - Whether viewer generated this report
 */
function trackReportView(ticker, recommendation, isOwner) {
    gtag('event', 'view_report', {
        event_category: 'reports',
        ticker: ticker,
        recommendation: recommendation,
        is_owner: isOwner
    });
}

/**
 * Track share actions
 * @param {string} platform - 'whatsapp', 'twitter', 'telegram', 'copy_link'
 * @param {string} ticker - Stock ticker being shared
 */
function trackShare(platform, ticker) {
    gtag('event', 'share', {
        method: platform,
        content_type: 'report',
        item_id: ticker
    });
}

/**
 * Track stock search
 * @param {string} query - Search query
 * @param {number} resultsCount - Number of results returned
 */
function trackSearch(query, resultsCount) {
    gtag('event', 'search', {
        search_term: query,
        results_count: resultsCount
    });
}

/**
 * Track watchlist actions
 * @param {string} action - 'add' or 'remove'
 * @param {string} ticker - Stock ticker
 */
function trackWatchlist(action, ticker) {
    gtag('event', 'watchlist_' + action, {
        event_category: 'watchlist',
        ticker: ticker
    });
}

/**
 * Track subscription purchase (E-commerce)
 * @param {string} plan - 'basic' or 'pro'
 * @param {string} period - 'monthly', '6months', 'yearly'
 * @param {number} value - Purchase amount in INR
 */
function trackPurchase(plan, period, value) {
    // GA4 E-commerce purchase event
    gtag('event', 'purchase', {
        transaction_id: Date.now().toString(), // Unique ID
        value: value,
        currency: 'INR',
        items: [{
            item_id: `${plan}_${period}`,
            item_name: `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan - ${period}`,
            item_category: 'subscription',
            price: value,
            quantity: 1
        }]
    });

    // Mark as conversion
    gtag('event', 'conversion', {
        event_category: 'revenue',
        event_label: 'subscription_purchase',
        value: value
    });
}

/**
 * Track pricing page view with plan interest
 * @param {string} plan - Plan user is viewing
 */
function trackPricingView(plan) {
    gtag('event', 'view_item', {
        currency: 'INR',
        items: [{
            item_id: plan,
            item_name: `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan`,
            item_category: 'subscription'
        }]
    });
}

/**
 * Track checkout initiation
 * @param {string} plan - 'basic' or 'pro'
 * @param {string} period - 'monthly', '6months', 'yearly'
 * @param {number} value - Amount in INR
 */
function trackBeginCheckout(plan, period, value) {
    gtag('event', 'begin_checkout', {
        currency: 'INR',
        value: value,
        items: [{
            item_id: `${plan}_${period}`,
            item_name: `${plan.charAt(0).toUpperCase() + plan.slice(1)} Plan - ${period}`,
            item_category: 'subscription',
            price: value,
            quantity: 1
        }]
    });
}

/**
 * Track upgrade nudge interactions
 * @param {string} action - 'view', 'click', 'dismiss'
 * @param {string} location - Where the nudge appeared
 */
function trackUpgradeNudge(action, location) {
    gtag('event', 'upgrade_nudge_' + action, {
        event_category: 'monetization',
        location: location
    });
}

/**
 * Track featured report clicks (for new users)
 * @param {string} ticker - Stock ticker
 */
function trackFeaturedReportClick(ticker) {
    gtag('event', 'featured_report_click', {
        event_category: 'engagement',
        ticker: ticker
    });
}

/**
 * Track errors for debugging
 * @param {string} errorType - Type of error
 * @param {string} errorMessage - Error message
 * @param {string} location - Where error occurred
 */
function trackError(errorType, errorMessage, location) {
    gtag('event', 'exception', {
        description: `${errorType}: ${errorMessage}`,
        fatal: false,
        error_location: location
    });
}

// Export for use in other scripts
window.analytics = {
    setUserProperties,
    trackRegistration,
    trackLogin,
    trackReportGeneration,
    trackReportView,
    trackShare,
    trackSearch,
    trackWatchlist,
    trackPurchase,
    trackPricingView,
    trackBeginCheckout,
    trackUpgradeNudge,
    trackFeaturedReportClick,
    trackError
};
