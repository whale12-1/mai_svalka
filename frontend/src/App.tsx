import { BrowserRouter, Routes, Route } from "react-router-dom";
import SearchPage from "./pages/SearchPage";
import MaterialPage from "./pages/MaterialPage";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<SearchPage />} />
        <Route path="/m/:id" element={<MaterialPage />} />
      </Routes>
    </BrowserRouter>
  );
}