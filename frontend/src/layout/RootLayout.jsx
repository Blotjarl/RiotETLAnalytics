import { NavLink, Outlet, useNavigation } from 'react-router-dom';

const NAV_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/champions', label: 'Champions', end: true },
  { to: '/champions/by-role', label: 'By Role' },
  { to: '/meta-trends', label: 'Meta Trends' },
  { to: '/players', label: 'Leaderboard' },
  { to: '/items', label: 'Item Builds' },
  { to: '/bias-insights', label: 'Bias Insights' },
];

function RootLayout() {
  const navigation = useNavigation();
  const isLoading = navigation.state !== 'idle';

  return (
    <div className="bg-gray-900 text-white min-h-screen font-sans">
      <div className="h-0.5">{isLoading && <div className="h-0.5 bg-cyan-400 animate-progress" />}</div>

      <header className="border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight">Rift Insights</h1>
            <p className="text-xs text-gray-500">Challenger / Grandmaster / Master analytics</p>
          </div>

          <nav className="flex flex-wrap gap-6">
            {NAV_LINKS.map(({ to, label, end }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `text-sm font-medium pb-1 border-b-2 transition-colors ${
                    isActive
                      ? 'text-cyan-400 border-cyan-400'
                      : 'text-gray-400 border-transparent hover:text-gray-200'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}

export default RootLayout;
