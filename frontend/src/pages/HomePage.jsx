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
          Rift Insights tracks Challenger, Grandmaster, and Master ranked play in League of Legends.
          A daily job pulls match data straight from Riot's API into Postgres, and the site reads it
          from there. No scraping, no manual updates.
        </p>
        <p className="text-gray-400 leading-relaxed mt-3 text-sm">
          Most of it is what you'd expect: win rates, item builds, patch trends. <Link to="/bias-insights" className="text-cyan-400 hover:underline">Bias Insights</Link> is
          the odd one out. It digs into where those win rates are actually misleading and corrects
          for it.
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
