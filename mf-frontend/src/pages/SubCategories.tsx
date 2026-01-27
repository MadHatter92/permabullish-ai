import { useParams, useNavigate } from 'react-router-dom';
import { Header } from '../components/Header';
import { SubCategoryCard } from '../components/SubCategoryCard';
import { getCategoryById } from '../data/categories';
import {
  TrendingUp,
  Shield,
  Scale,
  BarChart3,
  Layers,
  Target,
  Gem,
  LucideIcon
} from 'lucide-react';

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

export function SubCategories() {
  const { categoryId } = useParams<{ categoryId: string }>();
  const navigate = useNavigate();

  const category = categoryId ? getCategoryById(categoryId) : undefined;

  if (!category) {
    return (
      <div className="min-h-screen bg-navy-50">
        <Header showBack onBack={() => navigate('/')} />
        <main className="max-w-7xl mx-auto px-4 py-8 text-center">
          <h1 className="font-display text-2xl text-navy-900">Category not found</h1>
          <button
            onClick={() => navigate('/')}
            className="btn-primary mt-4"
          >
            Go back to categories
          </button>
        </main>
      </div>
    );
  }

  const IconComponent = iconMap[category.icon] || TrendingUp;

  return (
    <div className="min-h-screen bg-navy-50">
      <Header
        title={category.name}
        showBack
        onBack={() => navigate('/')}
      />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Category header */}
        <div className="relative bg-white rounded-2xl border border-gray-100 shadow-card p-6 mb-8 overflow-hidden">
          {/* Top accent gradient */}
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1e3a5f] via-[#334e68] to-[#e8913a]" />

          <div className="flex items-start gap-4 pt-2">
            <div
              className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0"
              style={{ backgroundColor: `${category.color}15` }}
            >
              <IconComponent
                size={28}
                style={{ color: category.color }}
              />
            </div>
            <div>
              <h1 className="font-display text-2xl text-navy-900 mb-2">
                {category.name}
              </h1>
              <p className="text-navy-600">
                {category.description}
              </p>
            </div>
          </div>
        </div>

        {/* Sub-category header */}
        <h2 className="font-semibold text-navy-800 mb-4">
          Select a sub-category ({category.subCategories.length})
        </h2>

        {/* Sub-category list */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {category.subCategories.map((subCategory) => (
            <SubCategoryCard
              key={subCategory.id}
              subCategory={subCategory}
              categoryColor={category.color}
              onClick={() => navigate(`/category/${categoryId}/${subCategory.id}`)}
              // TODO: Add actual fund count from API
            />
          ))}
        </div>
      </main>
    </div>
  );
}
