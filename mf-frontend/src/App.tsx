import { Routes, Route } from 'react-router-dom';
import { Categories } from './pages/Categories';
import { SubCategories } from './pages/SubCategories';
import { FundList } from './pages/FundList';

function App() {
  return (
    <Routes>
      <Route path="/" element={<Categories />} />
      <Route path="/category/:categoryId" element={<SubCategories />} />
      <Route path="/category/:categoryId/:subCategoryId" element={<FundList />} />
      {/* TODO: Add fund detail page */}
      {/* <Route path="/fund/:schemeCode" element={<FundDetail />} /> */}
    </Routes>
  );
}

export default App;
