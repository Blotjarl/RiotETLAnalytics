import { useLoaderData } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import DataTable from '../components/DataTable';
import FilterSelect from '../components/FilterSelect';
import ItemIcon from '../components/ItemIcon';

const TIERS = ['CHALLENGER', 'GRANDMASTER', 'MASTER'];

export async function loader({ request }) {
  const url = new URL(request.url);
  const tier = url.searchParams.get('tier') || 'CHALLENGER';

  const { data: championRows, error: championError } = await supabase
    .from('champion_stats_by_tier')
    .select('championname')
    .eq('tier', tier)
    .order('championname', { ascending: true });
  if (championError) throw new Error(championError.message);

  const champions = [...new Set((championRows ?? []).map((r) => r.championname))];
  const champion = url.searchParams.get('champion') || champions[0] || '';

  // item_build_stats is filtered to a single champion+tier here, so the
  // result set is naturally bounded (at most one row per distinct item the
  // game has ever had) -- no pagination/exact-count needed, unlike a
  // hypothetical unfiltered query against this view. "Any Champion" reads
  // from item_stats_by_tier instead -- an ETL-refreshed table, not a live
  // aggregation, since scanning every champion's items in one query is the
  // unfiltered-aggregation shape that isn't safe to run through PostgREST.
  let items = [];
  if (champion === 'ANY') {
    const { data, error } = await supabase
      .from('item_stats_by_tier')
      .select('*')
      .eq('tier', tier)
      .order('playcount', { ascending: false });
    if (error) throw new Error(error.message);
    items = data ?? [];
  } else if (champion) {
    const { data, error } = await supabase
      .from('item_build_stats')
      .select('*')
      .eq('tier', tier)
      .eq('championname', champion)
      .order('playcount', { ascending: false });
    if (error) throw new Error(error.message);
    items = data ?? [];
  }

  return { tier, champion, champions, items };
}

const columns = [
  {
    accessorKey: 'itemid',
    header: 'Item',
    cell: ({ getValue }) => <ItemIcon itemId={getValue()} />,
  },
  { accessorKey: 'winrate', header: 'Win Rate', cell: ({ getValue }) => `${getValue()}%` },
  { accessorKey: 'playcount', header: 'Games' },
  { accessorKey: 'wincount', header: 'Wins' },
];

function ItemBuildsPage() {
  const { tier, champion, champions, items } = useLoaderData();

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-2xl font-semibold">Item Builds</h2>
        <div className="flex gap-4">
          <FilterSelect
            paramName="champion"
            defaultValue={champion}
            options={[{ value: 'ANY', label: 'Any Champion' }, ...champions.map((c) => ({ value: c, label: c }))]}
          />
          <FilterSelect paramName="tier" defaultValue={tier} options={TIERS.map((t) => ({ value: t, label: t }))} />
        </div>
      </div>
      <DataTable columns={columns} data={items} emptyMessage="No item data for this champion/tier yet." />
    </div>
  );
}

export default ItemBuildsPage;
