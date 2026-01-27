import { SubCategory } from '../data/categories';
import { ChevronRight } from 'lucide-react';

interface SubCategoryCardProps {
  subCategory: SubCategory;
  categoryColor: string;
  onClick: () => void;
  fundCount?: number;
}

// Risk level labels
const riskLabels = ['Very Low', 'Low', 'Moderate', 'High', 'Very High'];

export function SubCategoryCard({ subCategory, categoryColor, onClick, fundCount }: SubCategoryCardProps) {
  return (
    <div
      className="relative bg-white rounded-2xl border border-gray-100 shadow-card hover:shadow-card-hover transition-all duration-300 ease-out cursor-pointer group overflow-hidden"
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
    >
      {/* Left accent bar */}
      <div
        className="absolute left-0 top-0 bottom-0 w-1 rounded-l-2xl"
        style={{ backgroundColor: categoryColor }}
      />

      <div className="p-5 pl-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            {/* Sub-category name */}
            <h4 className="font-display text-lg text-navy-900 mb-2 group-hover:text-navy-800 transition-colors">
              {subCategory.name}
            </h4>

            {/* Description */}
            <p className="text-sm text-navy-600 leading-relaxed mb-4 line-clamp-2">
              {subCategory.description}
            </p>

            {/* Footer with risk and fund count */}
            <div className="flex items-center gap-4">
              {/* Risk indicator */}
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-navy-400 font-medium uppercase tracking-wider">Risk</span>
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((level) => (
                    <div
                      key={level}
                      className={`w-1.5 h-1.5 rounded-full transition-colors ${
                        level <= subCategory.riskLevel
                          ? 'bg-saffron-500'
                          : 'bg-navy-200'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-xs text-navy-500">
                  {riskLabels[subCategory.riskLevel - 1]}
                </span>
              </div>

              {/* Fund count */}
              {fundCount !== undefined && (
                <span className="text-xs text-navy-400">
                  {fundCount.toLocaleString()} funds
                </span>
              )}
            </div>
          </div>

          {/* Arrow */}
          <ChevronRight
            size={20}
            className="text-navy-300 group-hover:text-saffron-500 group-hover:translate-x-1 transition-all duration-200 mt-1 flex-shrink-0"
          />
        </div>
      </div>

      {/* Hover overlay effect */}
      <div className="absolute inset-0 rounded-2xl bg-gradient-to-r from-transparent to-[#e8913a]/0 group-hover:to-[#e8913a]/[0.02] transition-all duration-300 pointer-events-none" />
    </div>
  );
}
