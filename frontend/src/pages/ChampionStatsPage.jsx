import { useLoaderData } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import DataTable from '../components/DataTable';
import FilterSelect from '../components/FilterSelect';
import ChampionIcon from '../components/ChampionIcon';

const TIERS = ['CHALLENGER', 'GRANDMASTER', 'MASTER'];

export async function loader({ request }) {
  const url = new URL(request.url);
  const tier = url.searchParams.get('tier') || 'CHALLENGER';

  const { data, error } = await supabase
    .from('champion_stats_by_tier')
    .select('*')
    .eq('tier', tier)
    .order('playcount', { ascending: false });

  if (error) throw new Error(error.message);

  return { tier, championStats: data ?? [] };
}

const columns = [
  {
    accessorKey: 'championname',
    header: 'Champion',
    cell: ({ getValue }) => (
      <div className="flex items-center gap-2">
        <ChampionIcon championName={getValue()} />
        <span className="font-medium">{getValue()}</span>
      </div>
    ),
  },
  {
    accessorKey: 'winrate',
    header: 'Win Rate',
    cell: ({ getValue }) => `${getValue()}%`,
  },
  { accessorKey: 'playcount', header: 'Games' },
  { accessorKey: 'wincount', header: 'Wins' },
];

function ChampionStatsPage() {
  const { tier, championStats } = useLoaderData();

  return (
    <div>
      <div className="flex items-center justify-between mb-4 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-2xl font-semibold">Champion Stats</h2>
        <FilterSelect paramName="tier" defaultValue={tier} options={TIERS.map((t) => ({ value: t, label: t }))} />
      </div>
      <DataTable columns={columns} data={championStats} />
    </div>
  );
}

export default ChampionStatsPage;
