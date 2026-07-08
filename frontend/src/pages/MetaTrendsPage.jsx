import { useMemo } from 'react';
import { useLoaderData, useSearchParams } from 'react-router-dom';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
} from 'chart.js';
import { supabase } from '../lib/supabaseClient';
import DataTable from '../components/DataTable';
import FilterSelect from '../components/FilterSelect';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const TIERS = ['CHALLENGER', 'GRANDMASTER', 'MASTER'];

export async function loader({ request }) {
  const url = new URL(request.url);
  const tier = url.searchParams.get('tier') || 'CHALLENGER';

  const { data, error } = await supabase
    .from('champion_stats_by_patch')
    .select('*')
    .eq('tier', tier)
    .order('patch', { ascending: true });

  if (error) throw new Error(error.message);

  return { tier, rows: data ?? [] };
}

const columns = [
  { accessorKey: 'patch', header: 'Patch' },
  { accessorKey: 'winrate', header: 'Win Rate', cell: ({ getValue }) => `${getValue()}%` },
  { accessorKey: 'playcount', header: 'Games' },
  { accessorKey: 'wincount', header: 'Wins' },
];

function MetaTrendsPage() {
  const { tier, rows } = useLoaderData();
  const [searchParams] = useSearchParams();

  const champions = useMemo(() => [...new Set(rows.map((r) => r.championname))].sort(), [rows]);

  const defaultChampion = useMemo(() => {
    if (!rows.length) return '';
    const totals = new Map();
    for (const r of rows) totals.set(r.championname, (totals.get(r.championname) ?? 0) + r.playcount);
    return [...totals.entries()].sort((a, b) => b[1] - a[1])[0][0];
  }, [rows]);

  const selectedChampion = searchParams.get('champion') || defaultChampion;
  const championRows = useMemo(
    () => rows.filter((r) => r.championname === selectedChampion),
    [rows, selectedChampion],
  );

  const chartData = {
    labels: championRows.map((r) => r.patch),
    datasets: [
      {
        label: 'Win Rate %',
        data: championRows.map((r) => r.winrate),
        borderColor: '#22d3ee',
        backgroundColor: '#22d3ee',
        tension: 0.2,
      },
    ],
  };

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-2xl font-semibold">Meta Trends</h2>
        <div className="flex gap-4">
          <FilterSelect
            paramName="champion"
            defaultValue={selectedChampion}
            options={champions.map((c) => ({ value: c, label: c }))}
          />
          <FilterSelect paramName="tier" defaultValue={tier} options={TIERS.map((t) => ({ value: t, label: t }))} />
        </div>
      </div>

      {championRows.length === 0 ? (
        <p className="text-center text-gray-400 py-12">No patch history for this champion/tier yet.</p>
      ) : (
        <>
          <div className="bg-gray-800 rounded-lg p-4 mb-6">
            <Line data={chartData} options={{ scales: { y: { min: 0, max: 100 } } }} />
          </div>
          <DataTable columns={columns} data={championRows} />
        </>
      )}
    </div>
  );
}

export default MetaTrendsPage;
