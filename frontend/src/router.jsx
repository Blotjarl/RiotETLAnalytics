import { createBrowserRouter } from 'react-router-dom';
import RootLayout from './layout/RootLayout';
import RouteError from './layout/RouteError';
import HydrateFallback from './layout/HydrateFallback';
import HomePage from './pages/HomePage';
import ChampionStatsPage, { loader as championStatsLoader } from './pages/ChampionStatsPage';
import ChampionRolePage, { loader as championRoleLoader } from './pages/ChampionRolePage';
import MetaTrendsPage, { loader as metaTrendsLoader } from './pages/MetaTrendsPage';
import PlayerLeaderboardPage, { loader as playerLeaderboardLoader } from './pages/PlayerLeaderboardPage';
import PlayerDetailPage, { loader as playerDetailLoader } from './pages/PlayerDetailPage';
import ItemBuildsPage, { loader as itemBuildsLoader } from './pages/ItemBuildsPage';
import BiasInsightsPage, { loader as biasInsightsLoader } from './pages/BiasInsightsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootLayout />,
    hydrateFallbackElement: <HydrateFallback />,
    // errorElement is defined per child (not on this parent route) so a
    // loader failure on one page replaces only the Outlet content -- the
    // nav stays usable instead of the whole layout vanishing.
    children: [
      { index: true, element: <HomePage />, errorElement: <RouteError /> },
      { path: 'champions', element: <ChampionStatsPage />, loader: championStatsLoader, errorElement: <RouteError /> },
      {
        path: 'champions/by-role',
        element: <ChampionRolePage />,
        loader: championRoleLoader,
        errorElement: <RouteError />,
      },
      { path: 'meta-trends', element: <MetaTrendsPage />, loader: metaTrendsLoader, errorElement: <RouteError /> },
      {
        path: 'players',
        element: <PlayerLeaderboardPage />,
        loader: playerLeaderboardLoader,
        errorElement: <RouteError />,
      },
      {
        path: 'players/:puuid',
        element: <PlayerDetailPage />,
        loader: playerDetailLoader,
        errorElement: <RouteError />,
      },
      { path: 'items', element: <ItemBuildsPage />, loader: itemBuildsLoader, errorElement: <RouteError /> },
      {
        path: 'bias-insights',
        element: <BiasInsightsPage />,
        loader: biasInsightsLoader,
        errorElement: <RouteError />,
      },
    ],
  },
]);
