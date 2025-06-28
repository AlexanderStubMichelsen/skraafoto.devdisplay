import './App.css';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import MapPage from './pages/MapPage';
import TestPage from './pages/TestPage';
import ZonePage from './pages/ZonePage'
import MultiViewerPage from './pages/MultiViewerPage';
import ErrorPage from './pages/ErrorPage';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route path="map" element={<MapPage />} />
          <Route path="/zone" element={<ZonePage />} />
          <Route path="/test" element={<TestPage />} />
          <Route path="/multiviewer" element={<MultiViewerPage />} />
          <Route path="*" element={<ErrorPage />} />
        </Route>
      </Routes>
      </Router>
  );
}

export default App;