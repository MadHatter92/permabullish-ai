import { useState, useEffect } from 'react';
import {
  ArrowRight,
  Wallet,
  Target,
  TrendingUp,
  PieChart,
  Briefcase,
  ChevronRight,
  Sparkles,
  ArrowLeft,
  IndianRupee,
  Calendar,
  Zap,
  Share2,
  Download,
  Copy,
  Check,
  Bookmark,
  MessageCircle,
  Search
} from 'lucide-react';
// Production URLs for the three modules
const STOCK_RESEARCH_URL = 'https://permabullish-web.onrender.com';
const MF_ANALYTICS_URL = '#'; // Coming soon
const PMS_TRACKER_URL = '#'; // Coming soon

// Types for our flow states
type FlowState =
  | 'initial'
  | 'path1-amount'
  | 'path1-risk'
  | 'path1-allocation'
  | 'path2-goal'
  | 'path2-risk'
  | 'path2-projection';

// Preset amounts for Path 1
const amountPresets = [
  { label: '₹10 Lakhs', value: 1000000 },
  { label: '₹25 Lakhs', value: 2500000 },
  { label: '₹50 Lakhs', value: 5000000 },
  { label: '₹1 Crore', value: 10000000 },
  { label: '₹2 Crore+', value: 20000000 },
];

// Preset goals for Path 2
const goalPresets = [
  { label: 'Retirement Corpus', icon: '🏖️', defaultAmount: 50000000, defaultYears: 20 },
  { label: 'Child Education', icon: '🎓', defaultAmount: 10000000, defaultYears: 15 },
  { label: 'House Down Payment', icon: '🏠', defaultAmount: 5000000, defaultYears: 7 },
  { label: 'Financial Freedom', icon: '🚀', defaultAmount: 100000000, defaultYears: 25 },
];

// Format currency
const formatCurrency = (amount: number): string => {
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)} Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)} L`;
  return `₹${amount.toLocaleString('en-IN')}`;
};

// Calculate allocation based on amount and risk
const calculateAllocation = (amount: number, riskLevel: number) => {
  const isHighValue = amount >= 5000000; // 50L+

  if (riskLevel < 33) {
    // Conservative
    if (isHighValue) {
      return {
        pms: { percent: 20, amount: amount * 0.2, label: 'PMS', description: 'Conservative, low-volatility strategies', color: 'purple' },
        mf: { percent: 50, amount: amount * 0.5, label: 'Debt Mutual Funds', description: 'Stable returns with capital protection', color: 'blue' },
        fd: { percent: 30, amount: amount * 0.3, label: 'Fixed Deposits', description: 'Guaranteed returns, zero risk', color: 'green' },
      };
    }
    return {
      mf: { percent: 60, amount: amount * 0.6, label: 'Debt Mutual Funds', description: 'Stable returns with capital protection', color: 'blue' },
      fd: { percent: 40, amount: amount * 0.4, label: 'Fixed Deposits', description: 'Guaranteed returns, zero risk', color: 'green' },
    };
  } else if (riskLevel < 66) {
    // Moderate
    if (isHighValue) {
      return {
        pms: { percent: 30, amount: amount * 0.3, label: 'PMS', description: 'Balanced growth strategies', color: 'purple' },
        mf: { percent: 50, amount: amount * 0.5, label: 'Equity Mutual Funds', description: 'Diversified exposure across market caps', color: 'blue' },
        stocks: { percent: 20, amount: amount * 0.2, label: 'Direct Stocks', description: 'Select high-conviction picks', color: 'emerald' },
      };
    }
    return {
      mf: { percent: 70, amount: amount * 0.7, label: 'Equity Mutual Funds', description: 'Diversified exposure across market caps', color: 'blue' },
      stocks: { percent: 30, amount: amount * 0.3, label: 'Direct Stocks', description: 'Select high-conviction picks', color: 'emerald' },
    };
  } else {
    // Aggressive
    if (isHighValue) {
      return {
        pms: { percent: 40, amount: amount * 0.4, label: 'PMS', description: 'High-growth, concentrated strategies', color: 'purple' },
        mf: { percent: 35, amount: amount * 0.35, label: 'Small/Mid Cap MFs', description: 'High growth potential funds', color: 'blue' },
        stocks: { percent: 25, amount: amount * 0.25, label: 'Direct Stocks', description: 'Aggressive stock picks for alpha', color: 'emerald' },
      };
    }
    return {
      mf: { percent: 60, amount: amount * 0.6, label: 'Small/Mid Cap MFs', description: 'High growth potential funds', color: 'blue' },
      stocks: { percent: 40, amount: amount * 0.4, label: 'Direct Stocks', description: 'Aggressive stock picks for alpha', color: 'emerald' },
    };
  }
};

// Calculate projected returns based on risk
const calculateProjection = (amount: number, years: number = 5, riskLevel: number) => {
  let conservativeRate, aggressiveRate;

  if (riskLevel < 33) {
    conservativeRate = 0.07;
    aggressiveRate = 0.09;
  } else if (riskLevel < 66) {
    conservativeRate = 0.10;
    aggressiveRate = 0.14;
  } else {
    conservativeRate = 0.12;
    aggressiveRate = 0.18;
  }

  return {
    conservative: amount * Math.pow(1 + conservativeRate, years),
    aggressive: amount * Math.pow(1 + aggressiveRate, years),
  };
};

// Calculate SIP needed for goal
const calculateSIPForGoal = (goalAmount: number, years: number, riskLevel: number) => {
  const expectedReturn = riskLevel < 33 ? 0.08 : riskLevel < 66 ? 0.12 : 0.15;
  const monthlyRate = expectedReturn / 12;
  const months = years * 12;
  const sip = goalAmount * monthlyRate / (Math.pow(1 + monthlyRate, months) - 1) / (1 + monthlyRate);
  return Math.ceil(sip / 100) * 100;
};

// Animated number component
function AnimatedNumber({ value, prefix = '', suffix = '' }: { value: number; prefix?: string; suffix?: string }) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1000;
    const steps = 30;
    const stepValue = value / steps;
    let current = 0;

    const timer = setInterval(() => {
      current += stepValue;
      if (current >= value) {
        setDisplayValue(value);
        clearInterval(timer);
      } else {
        setDisplayValue(Math.floor(current));
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [value]);

  return <span>{prefix}{displayValue.toLocaleString('en-IN')}{suffix}</span>;
}

// Fade-in animation wrapper
function FadeIn({ children, delay = 0, className = '' }: { children: React.ReactNode; delay?: number; className?: string }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), delay);
    return () => clearTimeout(timer);
  }, [delay]);

  return (
    <div
      className={`transition-all duration-500 ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'} ${className}`}
    >
      {children}
    </div>
  );
}

// Staggered cards animation
function StaggeredCards({ children, className = '' }: { children: React.ReactNode[]; className?: string }) {
  return (
    <div className={className}>
      {children.map((child, index) => (
        <FadeIn key={index} delay={index * 150}>
          {child}
        </FadeIn>
      ))}
    </div>
  );
}

export default function Landing() {
  const [flowState, setFlowState] = useState<FlowState>('initial');
  const [selectedAmount, setSelectedAmount] = useState<number>(0);
  const [selectedGoal, setSelectedGoal] = useState<typeof goalPresets[0] | null>(null);
  const [goalAmount, setGoalAmount] = useState<number>(50000000);
  const [goalYears, setGoalYears] = useState<number>(15);
  const [riskLevel, setRiskLevel] = useState<number>(50);
  const [copied, setCopied] = useState(false);
  const [showShareMenu, setShowShareMenu] = useState(false);

  const handleBack = () => {
    switch (flowState) {
      case 'path1-amount':
      case 'path2-goal':
        setFlowState('initial');
        break;
      case 'path1-risk':
        setFlowState('path1-amount');
        break;
      case 'path1-allocation':
        setFlowState('path1-risk');
        break;
      case 'path2-risk':
        setFlowState('path2-goal');
        break;
      case 'path2-projection':
        setFlowState('path2-risk');
        break;
    }
  };

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleWhatsAppShare = () => {
    const text = flowState.startsWith('path1')
      ? `Check out my investment plan for ${formatCurrency(selectedAmount)} on Permabullish!`
      : `I just created a plan to reach ${formatCurrency(goalAmount)} in ${goalYears} years. Check it out!`;
    window.open(`https://wa.me/?text=${encodeURIComponent(text + ' ' + window.location.href)}`, '_blank');
  };

  const allocation = selectedAmount > 0 ? calculateAllocation(selectedAmount, riskLevel) : null;
  const projection = selectedAmount > 0 ? calculateProjection(selectedAmount, 5, riskLevel) : null;
  const sipNeeded = calculateSIPForGoal(goalAmount, goalYears, riskLevel);
  const totalInvested = sipNeeded * goalYears * 12;
  const wealthCreated = goalAmount - totalInvested;

  const getRiskLabel = (level: number) => {
    if (level < 33) return { emoji: '🛡️', label: 'Conservative', description: 'You prefer stability over high returns. Lower risk, steadier growth.' };
    if (level < 66) return { emoji: '⚖️', label: 'Moderate', description: 'You\'re comfortable with some volatility for better returns.' };
    return { emoji: '🚀', label: 'Aggressive', description: 'You can handle market swings for potentially higher returns.' };
  };

  const riskInfo = getRiskLabel(riskLevel);

  // Share/Save Plan Component
  const ShareSavePlan = ({ title }: { title: string }) => (
    <FadeIn delay={600} className="mt-8">
      <div className="bg-gradient-to-r from-[#1e3a5f] to-[#243b53] rounded-2xl p-6 border border-[#334e68]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-[#e8913a]" />
              {title}
            </h3>
            <p className="text-[#9fb3c8] text-sm mt-1">Save this plan or share it with family</p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowShareMenu(!showShareMenu)}
              className="flex items-center gap-2 px-4 py-2 bg-[#e8913a] hover:bg-[#d97316] text-white rounded-xl transition-all duration-200 hover:scale-105"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
            <button className="flex items-center gap-2 px-4 py-2 bg-[#334e68] hover:bg-[#486581] text-white rounded-xl transition-all duration-200 hover:scale-105">
              <Bookmark className="w-4 h-4" />
              Save
            </button>
          </div>
        </div>

        {/* Share Menu */}
        {showShareMenu && (
          <FadeIn className="mt-4 pt-4 border-t border-[#334e68]">
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleCopyLink}
                className="flex items-center gap-2 px-4 py-2 bg-[#243b53] hover:bg-[#334e68] text-white rounded-lg transition-colors"
              >
                {copied ? <Check className="w-4 h-4 text-green-400" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy Link'}
              </button>
              <button
                onClick={handleWhatsAppShare}
                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
              >
                <MessageCircle className="w-4 h-4" />
                WhatsApp
              </button>
              <button className="flex items-center gap-2 px-4 py-2 bg-[#243b53] hover:bg-[#334e68] text-white rounded-lg transition-colors">
                <Download className="w-4 h-4" />
                Download PDF
              </button>
            </div>
          </FadeIn>
        )}
      </div>
    </FadeIn>
  );

  return (
    <div className="min-h-screen bg-[#102a43]">
      {/* Header */}
      <header className="bg-[#1e3a5f] border-b border-[#334e68] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <a href="/landing" className="flex items-center gap-3">
              <img
                src="/assets/permabullish-logo.png"
                alt="Permabullish"
                className="w-10 h-10 rounded-full"
              />
              <div className="hidden sm:block">
                <span className="text-xl font-bold text-white">Perma</span>
                <span className="text-xl font-bold text-[#e8913a]">bullish</span>
              </div>
            </a>
            <button className="px-4 py-2 bg-[#e8913a] text-white rounded-xl hover:bg-[#d97316] transition-colors font-medium">
              Sign In
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">

        {/* Back Button (when not on initial) */}
        {flowState !== 'initial' && (
          <FadeIn>
            <button
              onClick={handleBack}
              className="flex items-center gap-2 text-[#9fb3c8] hover:text-white transition-colors mb-8 group"
            >
              <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
              Back
            </button>
          </FadeIn>
        )}

        {/* ============ INITIAL STATE - Two Paths ============ */}
        {flowState === 'initial' && (
          <div className="space-y-12">
            {/* Hero */}
            <FadeIn className="text-center space-y-6">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 backdrop-blur-sm rounded-full border border-white/20">
                <Sparkles className="w-4 h-4 text-[#f19338]" />
                <span className="text-sm font-display text-white/90">Your Personal Investment Banker</span>
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-display text-white">
                Where would you like
                <br />
                <span className="text-[#f19338]">to begin?</span>
              </h1>

              <p className="text-lg font-display text-[#9fb3c8] max-w-2xl mx-auto">
                No jargon. No overwhelming choices. Just three clear paths to start your journey.
              </p>
            </FadeIn>

            {/* Three Path Cards */}
            <div className="grid md:grid-cols-3 gap-6">
              <FadeIn delay={200}>
                <button
                  onClick={() => setFlowState('path1-amount')}
                  className="w-full h-full group relative bg-gradient-to-br from-[#1e3a5f] to-[#243b53] rounded-3xl p-8 border border-[#334e68] hover:border-[#e8913a]/50 transition-all duration-300 text-left overflow-hidden hover:scale-[1.02] hover:shadow-xl hover:shadow-[#e8913a]/10"
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#e8913a]/10 rounded-full blur-3xl group-hover:bg-[#e8913a]/20 transition-all" />

                  <div className="relative space-y-4">
                    <div className="w-14 h-14 bg-[#e8913a]/20 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                      <Wallet className="w-7 h-7 text-[#e8913a]" />
                    </div>

                    <h2 className="text-2xl font-display text-white">
                      I have money
                      <br />to invest
                    </h2>

                    <p className="text-[#9fb3c8]">
                      You have capital ready. Let's find the right mix of PMS, Mutual Funds, and Stocks for you.
                    </p>

                    <div className="flex items-center gap-2 text-[#e8913a] font-medium">
                      Show me how
                      <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </button>
              </FadeIn>

              <FadeIn delay={350}>
                <button
                  onClick={() => setFlowState('path2-goal')}
                  className="w-full h-full group relative bg-gradient-to-br from-[#1e3a5f] to-[#243b53] rounded-3xl p-8 border border-[#334e68] hover:border-[#e8913a]/50 transition-all duration-300 text-left overflow-hidden hover:scale-[1.02] hover:shadow-xl hover:shadow-[#e8913a]/10"
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#e8913a]/10 rounded-full blur-3xl group-hover:bg-[#e8913a]/20 transition-all" />

                  <div className="relative space-y-4">
                    <div className="w-14 h-14 bg-[#e8913a]/20 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                      <Target className="w-7 h-7 text-[#e8913a]" />
                    </div>

                    <h2 className="text-2xl font-display text-white">
                      I have a goal
                      <br />to reach
                    </h2>

                    <p className="text-[#9fb3c8]">
                      You know where you want to be. Let's map out exactly how to get there.
                    </p>

                    <div className="flex items-center gap-2 text-[#e8913a] font-medium">
                      Plan my path
                      <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </button>
              </FadeIn>

              <FadeIn delay={500}>
                <a
                  href={STOCK_RESEARCH_URL}
                  className="block w-full h-full group relative bg-gradient-to-br from-[#1e3a5f] to-[#243b53] rounded-3xl p-8 border border-[#334e68] hover:border-[#e8913a]/50 transition-all duration-300 text-left overflow-hidden hover:scale-[1.02] hover:shadow-xl hover:shadow-[#e8913a]/10"
                >
                  <div className="absolute top-0 right-0 w-32 h-32 bg-[#e8913a]/10 rounded-full blur-3xl group-hover:bg-[#e8913a]/20 transition-all" />

                  <div className="relative space-y-4">
                    <div className="w-14 h-14 bg-[#e8913a]/20 rounded-2xl flex items-center justify-center group-hover:scale-110 transition-transform">
                      <Search className="w-7 h-7 text-[#e8913a]" />
                    </div>

                    <h2 className="text-2xl font-display text-white">
                      There is a stock
                      <br />I want to research
                    </h2>

                    <p className="text-[#9fb3c8]">
                      Got a company in mind? Let our AI analyze it and give you the complete picture.
                    </p>

                    <div className="flex items-center gap-2 text-[#e8913a] font-medium">
                      Start researching
                      <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
                    </div>
                  </div>
                </a>
              </FadeIn>
            </div>

            {/* Explore escape hatch */}
            <FadeIn delay={650} className="text-center">
              <p className="text-[#829ab1] mb-3">or start researching stocks now</p>
              <a
                href={STOCK_RESEARCH_URL}
                className="inline-flex items-center gap-2 px-6 py-3 bg-[#243b53] hover:bg-[#334e68] text-white rounded-xl transition-all duration-200 hover:scale-105"
              >
                Go to Stock Research
                <ArrowRight className="w-4 h-4" />
              </a>
            </FadeIn>
          </div>
        )}

        {/* ============ PATH 1: Amount Selection ============ */}
        {flowState === 'path1-amount' && (
          <div className="space-y-8">
            <FadeIn className="text-center space-y-4">
              <div className="w-16 h-16 bg-[#e8913a]/20 rounded-2xl flex items-center justify-center mx-auto">
                <IndianRupee className="w-8 h-8 text-[#e8913a]" />
              </div>
              <h2 className="text-3xl sm:text-4xl font-display text-white">
                How much would you like to invest?
              </h2>
              <p className="text-[#9fb3c8]">
                Select an amount to see your personalized allocation
              </p>
            </FadeIn>

            <StaggeredCards className="grid grid-cols-2 sm:grid-cols-3 gap-4 max-w-2xl mx-auto">
              {amountPresets.map((preset) => (
                <button
                  key={preset.value}
                  onClick={() => {
                    setSelectedAmount(preset.value);
                    setFlowState('path1-risk');
                  }}
                  className="p-6 rounded-2xl border-2 transition-all duration-200 hover:scale-105 bg-[#1e3a5f] border-[#334e68] text-white hover:border-[#e8913a]/50 hover:shadow-lg hover:shadow-[#e8913a]/10"
                >
                  <span className="text-xl font-bold">{preset.label}</span>
                </button>
              ))}
            </StaggeredCards>

            <FadeIn delay={600} className="text-center text-[#829ab1] text-sm">
              💡 Tip: For amounts ₹50L+, we'll include PMS (Portfolio Management Services) in your allocation
            </FadeIn>
          </div>
        )}

        {/* ============ PATH 1: Risk Assessment ============ */}
        {flowState === 'path1-risk' && (
          <div className="space-y-8">
            <FadeIn className="text-center space-y-4">
              <h2 className="text-3xl sm:text-4xl font-display text-white">
                What's your risk appetite?
              </h2>
              <p className="text-[#9fb3c8]">
                This helps us recommend the right mix for your <span className="text-[#e8913a] font-semibold">{formatCurrency(selectedAmount)}</span>
              </p>
            </FadeIn>

            <FadeIn delay={200} className="max-w-xl mx-auto space-y-8">
              {/* Risk Slider */}
              <div className="space-y-6">
                <div className="flex justify-between text-sm">
                  <span className="text-green-400 font-medium">Conservative</span>
                  <span className="text-yellow-400 font-medium">Moderate</span>
                  <span className="text-red-400 font-medium">Aggressive</span>
                </div>

                <input
                  type="range"
                  min="0"
                  max="100"
                  value={riskLevel}
                  onChange={(e) => setRiskLevel(Number(e.target.value))}
                  className="w-full h-3 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110"
                />

                <div className="bg-[#1e3a5f] rounded-xl p-5 border border-[#334e68] transition-all duration-300">
                  <p className="text-[#9fb3c8] text-sm mb-2">Your risk profile:</p>
                  <p className="text-2xl font-semibold text-white">
                    {riskInfo.emoji} {riskInfo.label}
                  </p>
                  <p className="text-[#829ab1] text-sm mt-2">
                    {riskInfo.description}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setFlowState('path1-allocation')}
                className="w-full py-4 bg-[#e8913a] hover:bg-[#d97316] text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 hover:scale-[1.02] hover:shadow-lg hover:shadow-[#e8913a]/30"
              >
                Show my allocation
                <ArrowRight className="w-5 h-5" />
              </button>
            </FadeIn>
          </div>
        )}

        {/* ============ PATH 1: Allocation Visualization ============ */}
        {flowState === 'path1-allocation' && allocation && projection && (
          <div className="space-y-8">
            <FadeIn className="text-center space-y-4">
              <h2 className="text-3xl sm:text-4xl font-display text-white">
                Here's how <span className="text-[#f19338]">{formatCurrency(selectedAmount)}</span> could work for you
              </h2>
              <p className="text-[#9fb3c8]">
                A {riskInfo.label.toLowerCase()} allocation tailored to your risk appetite
              </p>
            </FadeIn>

            {/* Allocation Cards */}
            <StaggeredCards className={`grid gap-4 ${Object.keys(allocation).length === 3 ? 'md:grid-cols-3' : 'md:grid-cols-2'}`}>
              {Object.entries(allocation).map(([key, item]) => (
                <div
                  key={key}
                  className="bg-gradient-to-br from-[#1e3a5f] to-[#243b53] rounded-2xl p-6 border border-[#334e68] hover:border-[#e8913a]/30 transition-all duration-300 hover:scale-[1.02]"
                >
                  <div className="flex items-center gap-3 mb-4">
                    <div className={`w-12 h-12 bg-${item.color}-500/20 rounded-xl flex items-center justify-center`}>
                      {key === 'pms' && <Briefcase className={`w-6 h-6 text-purple-400`} />}
                      {key === 'mf' && <PieChart className={`w-6 h-6 text-blue-400`} />}
                      {key === 'stocks' && <TrendingUp className={`w-6 h-6 text-emerald-400`} />}
                      {key === 'fd' && <Bookmark className={`w-6 h-6 text-green-400`} />}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{item.label}</h3>
                      <p className="text-[#9fb3c8] text-sm">{item.percent}%</p>
                    </div>
                  </div>
                  <p className="text-2xl font-bold text-white mb-2">{formatCurrency(item.amount)}</p>
                  <p className="text-sm text-[#829ab1]">{item.description}</p>
                </div>
              ))}
            </StaggeredCards>

            {/* Projection */}
            <FadeIn delay={450}>
              <div className="bg-gradient-to-r from-[#e8913a]/20 to-[#d97316]/20 rounded-2xl p-6 border border-[#e8913a]/30">
                <div className="flex items-center gap-3 mb-4">
                  <Zap className="w-6 h-6 text-[#e8913a]" />
                  <h3 className="text-lg font-semibold text-white">5-Year Projection</h3>
                </div>
                <p className="text-[#bcccdc] mb-2">Based on historical returns for a {riskInfo.label.toLowerCase()} portfolio:</p>
                <p className="text-3xl font-display text-white">
                  <AnimatedNumber value={Math.round(projection.conservative)} prefix="₹" /> — <AnimatedNumber value={Math.round(projection.aggressive)} prefix="₹" />
                </p>
                <p className="text-sm text-[#829ab1] mt-2">
                  That's potentially <span className="text-green-400 font-semibold">{formatCurrency(projection.aggressive - selectedAmount)}</span> in wealth created!
                </p>
              </div>
            </FadeIn>

            {/* CTA */}
            <FadeIn delay={600} className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="px-8 py-4 bg-[#e8913a] hover:bg-[#d97316] text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 hover:scale-[1.02] hover:shadow-lg hover:shadow-[#e8913a]/30">
                Show me top recommendations
                <ArrowRight className="w-5 h-5" />
              </button>
              <button
                onClick={() => setFlowState('path1-risk')}
                className="px-8 py-4 bg-[#243b53] hover:bg-[#334e68] text-white rounded-xl font-medium transition-colors"
              >
                Adjust risk level
              </button>
            </FadeIn>

            {/* Share/Save Plan */}
            <ShareSavePlan title="Like this allocation?" />
          </div>
        )}

        {/* ============ PATH 2: Goal Selection ============ */}
        {flowState === 'path2-goal' && (
          <div className="space-y-8">
            <FadeIn className="text-center space-y-4">
              <div className="w-16 h-16 bg-[#e8913a]/20 rounded-2xl flex items-center justify-center mx-auto">
                <Target className="w-8 h-8 text-[#e8913a]" />
              </div>
              <h2 className="text-3xl sm:text-4xl font-display text-white">
                What are you saving for?
              </h2>
              <p className="text-[#9fb3c8]">
                Select a goal or create your own
              </p>
            </FadeIn>

            <StaggeredCards className="grid sm:grid-cols-2 gap-4 max-w-2xl mx-auto">
              {goalPresets.map((goal) => (
                <button
                  key={goal.label}
                  onClick={() => {
                    setSelectedGoal(goal);
                    setGoalAmount(goal.defaultAmount);
                    setGoalYears(goal.defaultYears);
                    setFlowState('path2-risk');
                  }}
                  className="flex items-center gap-4 p-6 bg-[#1e3a5f] rounded-2xl border-2 border-[#334e68] hover:border-[#e8913a]/50 transition-all duration-200 text-left group hover:scale-[1.02] hover:shadow-lg hover:shadow-[#e8913a]/10"
                >
                  <span className="text-4xl group-hover:scale-110 transition-transform">{goal.icon}</span>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-white group-hover:text-[#e8913a] transition-colors">
                      {goal.label}
                    </h3>
                    <p className="text-[#829ab1] text-sm">
                      {formatCurrency(goal.defaultAmount)} in {goal.defaultYears} years
                    </p>
                  </div>
                  <ChevronRight className="w-5 h-5 text-[#829ab1] group-hover:text-[#e8913a] group-hover:translate-x-1 transition-all" />
                </button>
              ))}
            </StaggeredCards>

            {/* Custom Goal */}
            <FadeIn delay={600} className="max-w-2xl mx-auto">
              <div className="bg-[#1e3a5f] rounded-2xl p-6 border border-[#334e68]">
                <h3 className="text-lg font-semibold text-white mb-4">Or set a custom goal</h3>
                <div className="grid sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm text-[#9fb3c8] mb-2">Target Amount</label>
                    <div className="relative">
                      <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#829ab1]">₹</span>
                      <input
                        type="number"
                        value={goalAmount}
                        onChange={(e) => setGoalAmount(Number(e.target.value))}
                        className="w-full pl-8 pr-4 py-3 bg-[#243b53] border border-[#334e68] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-[#e8913a]/50 transition-all"
                        placeholder="50,00,000"
                      />
                    </div>
                  </div>
                  <div>
                    <label className="block text-sm text-[#9fb3c8] mb-2">Time Horizon</label>
                    <div className="relative">
                      <input
                        type="number"
                        value={goalYears}
                        onChange={(e) => setGoalYears(Number(e.target.value))}
                        className="w-full px-4 py-3 bg-[#243b53] border border-[#334e68] rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-[#e8913a]/50 transition-all"
                        placeholder="15"
                      />
                      <span className="absolute right-4 top-1/2 -translate-y-1/2 text-[#829ab1]">years</span>
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setSelectedGoal(null);
                    setFlowState('path2-risk');
                  }}
                  className="mt-4 w-full py-3 bg-[#e8913a] hover:bg-[#d97316] text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 hover:scale-[1.02]"
                >
                  Continue with custom goal
                  <ArrowRight className="w-5 h-5" />
                </button>
              </div>
            </FadeIn>
          </div>
        )}

        {/* ============ PATH 2: Risk Assessment ============ */}
        {flowState === 'path2-risk' && (
          <div className="space-y-8">
            <FadeIn className="text-center space-y-4">
              <h2 className="text-3xl sm:text-4xl font-display text-white">
                How much risk can you handle?
              </h2>
              <p className="text-[#9fb3c8]">
                This helps us recommend the right mix of investments
              </p>
            </FadeIn>

            <FadeIn delay={200} className="max-w-xl mx-auto space-y-8">
              {/* Goal Summary */}
              <div className="bg-[#1e3a5f] rounded-2xl p-6 border border-[#334e68]">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-[#9fb3c8] text-sm">Your Goal</p>
                    <p className="text-2xl font-bold text-white">{formatCurrency(goalAmount)}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[#9fb3c8] text-sm">Timeline</p>
                    <p className="text-2xl font-bold text-white">{goalYears} years</p>
                  </div>
                </div>
              </div>

              {/* Risk Slider */}
              <div className="space-y-6">
                <div className="flex justify-between text-sm">
                  <span className="text-green-400 font-medium">Conservative</span>
                  <span className="text-yellow-400 font-medium">Moderate</span>
                  <span className="text-red-400 font-medium">Aggressive</span>
                </div>

                <input
                  type="range"
                  min="0"
                  max="100"
                  value={riskLevel}
                  onChange={(e) => setRiskLevel(Number(e.target.value))}
                  className="w-full h-3 bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full appearance-none cursor-pointer [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-6 [&::-webkit-slider-thumb]:h-6 [&::-webkit-slider-thumb]:bg-white [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110"
                />

                <div className="bg-[#1e3a5f] rounded-xl p-5 border border-[#334e68]">
                  <p className="text-[#9fb3c8] text-sm mb-2">Your risk profile:</p>
                  <p className="text-2xl font-semibold text-white">
                    {riskInfo.emoji} {riskInfo.label}
                  </p>
                  <p className="text-[#829ab1] text-sm mt-2">
                    {riskInfo.description}
                  </p>
                </div>
              </div>

              <button
                onClick={() => setFlowState('path2-projection')}
                className="w-full py-4 bg-[#e8913a] hover:bg-[#d97316] text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 hover:scale-[1.02] hover:shadow-lg hover:shadow-[#e8913a]/30"
              >
                Show me my path
                <ArrowRight className="w-5 h-5" />
              </button>
            </FadeIn>
          </div>
        )}

        {/* ============ PATH 2: Projection & Plan ============ */}
        {flowState === 'path2-projection' && (
          <div className="space-y-8">
            <FadeIn className="text-center space-y-4">
              <h2 className="text-3xl sm:text-4xl font-display text-white">
                Your path to <span className="text-[#f19338]">{formatCurrency(goalAmount)}</span>
              </h2>
              <p className="text-[#9fb3c8]">
                Here's exactly how to reach your goal with a {riskInfo.label.toLowerCase()} approach
              </p>
            </FadeIn>

            {/* The Big Number */}
            <FadeIn delay={200}>
              <div className="bg-gradient-to-br from-[#e8913a]/20 to-[#d97316]/10 rounded-3xl p-8 border border-[#e8913a]/30 text-center">
                <p className="text-[#bcccdc] mb-2">You need to invest monthly</p>
                <p className="text-5xl sm:text-6xl font-display text-white mb-2">
                  ₹<AnimatedNumber value={sipNeeded} />
                </p>
                <p className="text-[#9fb3c8]">
                  for {goalYears} years at ~{riskLevel < 33 ? '8' : riskLevel < 66 ? '12' : '15'}% expected returns
                </p>
              </div>
            </FadeIn>

            {/* Wealth Creation Insight */}
            <FadeIn delay={350}>
              <div className="bg-[#1e3a5f] rounded-2xl p-6 border border-[#334e68]">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Sparkles className="w-5 h-5 text-[#e8913a]" />
                  The Power of Compounding
                </h3>
                <div className="grid sm:grid-cols-3 gap-4 text-center">
                  <div className="p-4 bg-[#243b53] rounded-xl">
                    <p className="text-[#829ab1] text-sm mb-1">You Invest</p>
                    <p className="text-xl font-bold text-white">{formatCurrency(totalInvested)}</p>
                  </div>
                  <div className="p-4 bg-[#243b53] rounded-xl">
                    <p className="text-[#829ab1] text-sm mb-1">Wealth Created</p>
                    <p className="text-xl font-bold text-green-400">+{formatCurrency(wealthCreated)}</p>
                  </div>
                  <div className="p-4 bg-gradient-to-r from-[#e8913a]/20 to-[#d97316]/20 rounded-xl border border-[#e8913a]/30">
                    <p className="text-[#829ab1] text-sm mb-1">You Get</p>
                    <p className="text-xl font-bold text-[#e8913a]">{formatCurrency(goalAmount)}</p>
                  </div>
                </div>
              </div>
            </FadeIn>

            {/* Visual Timeline */}
            <FadeIn delay={500}>
              <div className="bg-[#1e3a5f] rounded-2xl p-6 border border-[#334e68]">
                <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                  <Calendar className="w-5 h-5 text-[#e8913a]" />
                  Your Wealth Journey
                </h3>
                <div className="relative">
                  <div className="h-3 bg-[#334e68] rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-[#e8913a] to-[#f19338] rounded-full transition-all duration-1000"
                      style={{ width: '100%' }}
                    />
                  </div>
                  <div className="flex justify-between mt-4">
                    <div className="text-center">
                      <p className="text-lg font-bold text-white">₹0</p>
                      <p className="text-xs text-[#829ab1]">Today</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-[#9fb3c8]">{formatCurrency(goalAmount * 0.25)}</p>
                      <p className="text-xs text-[#829ab1]">Year {Math.round(goalYears * 0.25)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-[#9fb3c8]">{formatCurrency(goalAmount * 0.5)}</p>
                      <p className="text-xs text-[#829ab1]">Year {Math.round(goalYears * 0.5)}</p>
                    </div>
                    <div className="text-center">
                      <p className="text-lg font-bold text-[#e8913a]">{formatCurrency(goalAmount)}</p>
                      <p className="text-xs text-[#829ab1]">Year {goalYears} 🎉</p>
                    </div>
                  </div>
                </div>
              </div>
            </FadeIn>

            {/* Suggested Allocation */}
            <FadeIn delay={650}>
              <div className="bg-[#1e3a5f] rounded-2xl p-6 border border-[#334e68]">
                <h3 className="text-lg font-semibold text-white mb-4">Suggested Allocation</h3>
                <div className="space-y-3">
                  {riskLevel >= 33 && (
                    <div className="flex items-center justify-between p-3 bg-[#243b53] rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded bg-blue-500" />
                        <span className="text-white">Equity Mutual Funds</span>
                      </div>
                      <span className="text-white font-semibold">{riskLevel < 66 ? '60%' : '70%'}</span>
                    </div>
                  )}
                  {riskLevel < 33 && (
                    <div className="flex items-center justify-between p-3 bg-[#243b53] rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded bg-blue-500" />
                        <span className="text-white">Debt Mutual Funds</span>
                      </div>
                      <span className="text-white font-semibold">70%</span>
                    </div>
                  )}
                  {riskLevel < 66 && riskLevel >= 33 && (
                    <div className="flex items-center justify-between p-3 bg-[#243b53] rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded bg-green-500" />
                        <span className="text-white">Debt Funds</span>
                      </div>
                      <span className="text-white font-semibold">30%</span>
                    </div>
                  )}
                  {riskLevel < 33 && (
                    <div className="flex items-center justify-between p-3 bg-[#243b53] rounded-xl">
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 rounded bg-yellow-500" />
                        <span className="text-white">Fixed Deposits</span>
                      </div>
                      <span className="text-white font-semibold">30%</span>
                    </div>
                  )}
                  {riskLevel >= 66 && (
                    <>
                      <div className="flex items-center justify-between p-3 bg-[#243b53] rounded-xl">
                        <div className="flex items-center gap-3">
                          <div className="w-4 h-4 rounded bg-emerald-500" />
                          <span className="text-white">Direct Stocks</span>
                        </div>
                        <span className="text-white font-semibold">20%</span>
                      </div>
                      <div className="flex items-center justify-between p-3 bg-[#243b53] rounded-xl">
                        <div className="flex items-center gap-3">
                          <div className="w-4 h-4 rounded bg-purple-500" />
                          <span className="text-white">Small Cap Funds</span>
                        </div>
                        <span className="text-white font-semibold">10%</span>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </FadeIn>

            {/* CTA */}
            <FadeIn delay={800} className="flex flex-col sm:flex-row gap-4 justify-center">
              <button className="px-8 py-4 bg-[#e8913a] hover:bg-[#d97316] text-white rounded-xl font-medium transition-all duration-200 flex items-center justify-center gap-2 hover:scale-[1.02] hover:shadow-lg hover:shadow-[#e8913a]/30">
                Show me recommended funds
                <ArrowRight className="w-5 h-5" />
              </button>
              <button
                onClick={() => setFlowState('path2-risk')}
                className="px-8 py-4 bg-[#243b53] hover:bg-[#334e68] text-white rounded-xl font-medium transition-colors"
              >
                Adjust my plan
              </button>
            </FadeIn>

            {/* Share/Save Plan */}
            <ShareSavePlan title="Love this plan?" />
          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="border-t border-[#243b53] py-8 mt-16">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <img
                src="/assets/permabullish-logo.png"
                alt="Permabullish"
                className="w-8 h-8 rounded-full"
              />
              <div>
                <span className="text-white font-bold">Perma</span>
                <span className="text-[#e8913a] font-bold">bullish</span>
              </div>
            </div>
            <p className="text-sm text-[#829ab1]">
              Data sourced from AMFI & SEBI. For informational purposes only.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
