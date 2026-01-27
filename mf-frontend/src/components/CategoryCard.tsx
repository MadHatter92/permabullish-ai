import { Category } from '../data/categories';
import {
  TrendingUp,
  Shield,
  Scale,
  BarChart3,
  Layers,
  Target,
  Gem,
  ChevronRight,
  LucideIcon
} from 'lucide-react';

interface CategoryCardProps {
  category: Category;
  onClick: () => void;
  fundCount?: number;
}

// Map icon names to components
const iconMap: Record<string, LucideIcon> = {
  TrendingUp,
  Shield,
  Scale,
  BarChart3,
  Layers,
  Target,
  Gem,
};

// Risk level labels
const riskLabels = ['Very Low', 'Low', 'Moderate', 'High', 'Very High'];

export function CategoryCard({ category, onClick, fundCount }: CategoryCardProps) {
  const IconComponent = iconMap[category.icon] || TrendingUp;

  return (
    <div
      className="relative bg-white rounded-2xl border border-gray-100 shadow-card hover:shadow-card-hover transition-all duration-300 ease-out cursor-pointer group overflow-hidden"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      {/* Top accent gradient - matching landing page FundCard */}
      <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1e3a5f] via-[#334e68] to-[#e8913a]" />

      {/* Card content */}
      <div className="p-5 pt-6">
        {/* Header with icon */}
        <div className="flex items-start justify-between mb-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center transition-transform duration-300 group-hover:scale-110"
            style={{ backgroundColor: `${category.color}15` }}
          >
            <IconComponent
              size={24}
              style={{ color: category.color }}
            />
          </div>
          <ChevronRight
            size={20}
            className="text-navy-300 group-hover:text-saffron-500 group-hover:translate-x-1 transition-all duration-200"
          />
        </div>

        {/* Category name - using font-display class */}
        <h3 className="font-display text-xl text-navy-900 mb-2 group-hover:text-navy-800 transition-colors">
          {category.name}
        </h3>

        {/* Description */}
        <p className="text-sm text-navy-600 leading-relaxed mb-4 line-clamp-2">
          {category.description}
        </p>

        {/* Footer with risk and fund count */}
        <div className="flex items-center justify-between pt-4 border-t border-gray-100">
          {/* Risk indicator */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-navy-400 font-medium uppercase tracking-wider">Risk</span>
            <div className="flex gap-1">
              {[1, 2, 3, 4, 5].map((level) => (
                <div
                  key={level}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    level <= category.riskLevel
                      ? 'bg-saffron-500'
                      : 'bg-navy-200'
                  }`}
                />
              ))}
            </div>
            <span className="text-xs text-navy-500 font-medium">
              {riskLabels[category.riskLevel - 1]}
            </span>
          </div>

          {/* Fund count */}
          {fundCount !== undefined && (
            <span className="text-xs text-navy-400 font-medium">
              {fundCount.toLocaleString()} funds
            </span>
          )}
        </div>
      </div>

      {/* Hover overlay effect - matching landing page */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-[#1e3a5f]/0 to-[#e8913a]/0 group-hover:from-[#1e3a5f]/[0.02] group-hover:to-[#e8913a]/[0.02] transition-all duration-300 pointer-events-none" />
    </div>
  );
}
