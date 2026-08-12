import { Link } from 'react-router-dom';

const FEATURES = [
  {
    to: '/champions',
    title: 'Champion Stats',
    description: 'Win rate and pick rate per champion, filterable by tier.',
  },
  {
    to: '/champions/by-role',
    title: 'By Role',
    description: 'The same numbers split by lane, so a champion is judged against others in the same role.',
  },
  {
    to: '/meta-trends',
    title: 'Meta Trends',
    description: 'How a champion’s win rate has moved across recent patches.',
  },
  {
    to: '/players',
    title: 'Leaderboard',
    description: 'The current Challenger / Grandmaster / Master leaderboard, with per-player match history.',
  },
  {
    to: '/items',
    title: 'Item Builds',
    description: 'Which items show up in wins vs. losses for a given champion.',
  },
  {
    to: '/bias-insights',
    title: 'Bias Insights',
    description: 'Where raw win-rate stats mislead, and what the numbers look like once corrected for it.',
  },
];

function HomePage() {
  return (
    <div>
      <div className="mb-10 max-w-3xl">
        <h2 className="text-3xl font-bold mb-3">Rift Insights</h2>
        <p className="text-gray-300 leading-relaxed">
          An analytics platform for League of Legends' Challenger, Grandmaster, and Master tiers.
          A daily pipeline pulls ranked match data directly from Riot's API and loads it into
          Postgres, and this site reads that data live. Nothing here is hand-curated or scraped
          from other stats sites.
        </p>
        <p className="text-gray-400 leading-relaxed mt-3 text-sm">
          Most of what you'll find here is the usual stuff: win rates, item builds, meta trends
          over patches. The <Link to="/bias-insights" className="text-cyan-400 hover:underline">Bias Insights</Link> page
          is the exception. It takes a close look at where those raw win-rate numbers are actually
          misleading, and shows what a corrected version looks like.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {FEATURES.map(({ to, title, description }) => (
          <Link
            key={to}
            to={to}
            className="block rounded-lg border border-gray-700 bg-gray-800 p-5 hover:border-cyan-400 transition-colors"
          >
            <h3 className="text-lg font-semibold text-cyan-400 mb-1">{title}</h3>
            <p className="text-sm text-gray-400">{description}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}

export default HomePage;
