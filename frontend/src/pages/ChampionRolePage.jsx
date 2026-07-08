import { useLoaderData } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import DataTable from '../components/DataTable';
import FilterSelect from '../components/FilterSelect';
import ChampionIcon from '../components/ChampionIcon';

const TIERS = ['CHALLENGER', 'GRANDMASTER', 'MASTER'];
const ROLES = [
  { value: 'TOP', label: 'Top' },
  { value: 'JUNGLE', label: 'Jungle' },
  { value: 'MIDDLE', label: 'Mid' },
  { value: 'BOTTOM', label: 'Bottom' },
  { value: 'UTILITY', label: 'Support' },
];

export async function loader({ request }) {
  const url = new URL(request.url);
  const tier = url.searchParams.get('tier') || 'CHALLENGER';
  const role = url.searchParams.get('role') || 'TOP';

  const { data, error } = await supabase
    .from('champion_stats_by_role')
    .select('*')
    .eq('tier', tier)
    .eq('teamposition', role)
    .order('playcount', { ascending: false });

  if (error) throw new Error(error.message);

  return { tier, role, championStats: data ?? [] };
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
  { accessorKey: 'winrate', header: 'Win Rate', cell: ({ getValue }) => `${getValue()}%` },
  { accessorKey: 'playcount', header: 'Games' },
  { accessorKey: 'wincount', header: 'Wins' },
];

function ChampionRolePage() {
  const { tier, role, championStats } = useLoaderData();

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-2xl font-semibold">Champion Stats by Role</h2>
        <div className="flex gap-4">
          <FilterSelect paramName="role" defaultValue={role} options={ROLES} />
          <FilterSelect paramName="tier" defaultValue={tier} options={TIERS.map((t) => ({ value: t, label: t }))} />
        </div>
      </div>
      <DataTable columns={columns} data={championStats} emptyMessage="No data for this role/tier yet." />
    </div>
  );
}

export default ChampionRolePage;
