import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import DashboardLayout from './layouts/DashboardLayout';
import Auth from './pages/Auth';
import Landing from './pages/Landing';
import Generate from './pages/Generate';
import History from './pages/History';
import Profile from './pages/Profile';
import Pricing from './pages/Pricing';
import VisualBuilder from './pages/VisualBuilder';
import ParticleCursorEffect from './components/ParticleCursorEffect';

const ProtectedRoute = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/auth" replace />;
  }
  return children;
};

// Redirect root to dashboard layout
// If we had a landing page, root would be landing and dashboard would be /app
// But here root / is the generator.

function App() {
  return (
    <BrowserRouter>
      <ParticleCursorEffect />
      <Routes>
        <Route path="/auth" element={<Auth />} />

        {/* Post-login landing page */}
        <Route path="/landing" element={
          <ProtectedRoute>
            <Landing />
          </ProtectedRoute>
        } />

        <Route path="/" element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }>
          <Route index element={<Generate />} />
          <Route path="history" element={<History />} />
          <Route path="profile" element={<Profile />} />
          <Route path="pricing" element={<Pricing />} />
          <Route path="builder" element={<VisualBuilder />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
