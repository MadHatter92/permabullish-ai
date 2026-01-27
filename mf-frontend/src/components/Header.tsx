import { Link, useLocation } from 'react-router-dom';
import { ArrowLeft, Search } from 'lucide-react';

interface HeaderProps {
  title?: string;
  showBack?: boolean;
  onBack?: () => void;
}

export function Header({ title, showBack, onBack }: HeaderProps) {
  const location = useLocation();
  const isHome = location.pathname === '/';

  return (
    <header className="sticky top-0 z-50 bg-navy-900 text-white shadow-lg">
      {/* Top accent line like the cards */}
      <div className="h-1 bg-gradient-to-r from-[#1e3a5f] via-[#334e68] to-[#e8913a]" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left section */}
          <div className="flex items-center gap-4">
            {showBack && (
              <button
                onClick={onBack}
                className="p-2 -ml-2 hover:bg-navy-800 rounded-xl transition-colors"
                aria-label="Go back"
              >
                <ArrowLeft size={20} />
              </button>
            )}

            <Link to="/" className="flex items-center gap-3">
              {/* Logo text - matching landing page style */}
              <div className="flex items-center">
                <span className="font-display text-xl text-white">Perma</span>
                <span className="font-display text-xl text-saffron-500">bullish</span>
              </div>

              {/* Module indicator */}
              {isHome && (
                <div className="hidden sm:flex items-center gap-2">
                  <span className="text-navy-400">|</span>
                  <span className="text-sm font-medium text-navy-200">MF Analytics</span>
                </div>
              )}
            </Link>

            {title && !isHome && (
              <>
                <span className="text-navy-400 hidden sm:inline">|</span>
                <span className="font-display text-lg hidden sm:inline">{title}</span>
              </>
            )}
          </div>

          {/* Right section */}
          <div className="flex items-center gap-3">
            <button
              className="p-2 hover:bg-navy-800 rounded-xl transition-colors"
              aria-label="Search funds"
            >
              <Search size={20} className="text-navy-200 hover:text-white" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
