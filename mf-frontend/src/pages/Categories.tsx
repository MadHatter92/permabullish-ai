import { useNavigate } from 'react-router-dom';
import { Header } from '../components/Header';
import { CategoryCard } from '../components/CategoryCard';
import { categories } from '../data/categories';

export function Categories() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-navy-50">
      <Header />

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Hero section */}
        <div className="text-center mb-12">
          <h1 className="font-display text-3xl sm:text-4xl text-navy-900 mb-4">
            Explore Mutual Funds
          </h1>
          <p className="text-navy-600 max-w-2xl mx-auto text-base leading-relaxed">
            Discover mutual funds across categories. Compare returns, analyze performance,
            and find the right funds for your investment goals.
          </p>
        </div>

        {/* Category grid - 4 columns on xl, 3 on lg, 2 on md, 1 on mobile */}
        {/* Using flexbox for better centering of last row */}
        <div className="flex flex-wrap justify-center gap-5">
          {categories.map((category) => (
            <div
              key={category.id}
              className="w-full sm:w-[calc(50%-10px)] lg:w-[calc(33.333%-14px)] xl:w-[calc(25%-15px)]"
            >
              <CategoryCard
                category={category}
                onClick={() => navigate(`/category/${category.id}`)}
              />
            </div>
          ))}
        </div>

        {/* Footer note */}
        <div className="mt-12 text-center">
          <p className="text-sm text-navy-400">
            Data sourced from AMFI. Returns calculated using NAV history.
          </p>
        </div>
      </main>
    </div>
  );
}
