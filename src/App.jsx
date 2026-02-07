import './App.css';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import MainLayout from './components/MainLayout';
import MapPage from './pages/MapPage';
import TestPage from './pages/TestPage';
import ZonePage from './pages/ZonePage'
import MultiViewerPage from './pages/MultiViewerPage';
import ErrorPage from './pages/ErrorPage';

const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <MainLayout />,
      children: [
        { path: 'map', element: <MapPage /> },
        { path: 'zone', element: <ZonePage /> },
        { path: 'test', element: <TestPage /> },
        { path: 'multiviewer', element: <MultiViewerPage /> },
        { path: '*', element: <ErrorPage /> },
      ],
    },
  ],
  {
    future: {
      v7_relativeSplatPath: true,
    },
  }
);

function App() {
  return (
    <RouterProvider router={router} />
  );
}

export default App;
