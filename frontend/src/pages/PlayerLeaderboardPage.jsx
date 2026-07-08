import { useLoaderData, useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import DataTable from '../components/DataTable';
import FilterSelect from '../components/FilterSelect';
import Pagination from '../components/Pagination';

const TIERS = ['ALL', 'CHALLENGER', 'GRANDMASTER', 'MASTER'];
const PAGE_SIZE = 50;

export async function loader({ request }) {
  const url = new URL(request.url);
  const page = Math.max(1, Number(url.searchParams.get('page')) || 1);
  const tier = url.searchParams.get('tier') || 'ALL';

  let query = supabase
    .from('players')
    .select('puuid, tier, leaderboardrank, leaguepoints, wins, losses', { count: 'exact' })
    .order('leaderboardrank', { ascending: true });

  if (tier !== 'ALL') {
    query = query.eq('tier', tier);
  }

  const from = (page - 1) * PAGE_SIZE;
  const to = from + PAGE_SIZE - 1;

  const { data: players, error, count } = await query.range(from, to);
  if (error) throw new Error(error.message);

  // players has no display-name column -- resolve one via
  // player_current_identity, falling back to rank-only display when a
  // player hasn't had their match history crawled yet (see schema.sql).
  const puuids = (players ?? []).map((p) => p.puuid);
  let identities = [];
  if (puuids.length) {
    const { data, error: identityError } = await supabase
      .from('player_current_identity')
      .select('puuid, riotidgamename, riotidtagline')
      .in('puuid', puuids);
    if (identityError) throw new Error(identityError.message);
    identities = data ?? [];
  }
  const nameByPuuid = new Map(identities.map((i) => [i.puuid, i]));

  const rows = (players ?? []).map((p) => {
    const identity = nameByPuuid.get(p.puuid);
    return {
      ...p,
      displayName: identity ? `${identity.riotidgamename}#${identity.riotidtagline}` : null,
    };
  });

  return {
    tier,
    page,
    totalPages: count ? Math.max(1, Math.ceil(count / PAGE_SIZE)) : 1,
    players: rows,
  };
}

const columns = [
  { accessorKey: 'leaderboardrank', header: 'Rank' },
  {
    accessorKey: 'displayName',
    header: 'Player',
    cell: ({ row }) => row.original.displayName || `Rank #${row.original.leaderboardrank}`,
  },
  { accessorKey: 'tier', header: 'Tier' },
  { accessorKey: 'leaguepoints', header: 'LP' },
  { accessorKey: 'wins', header: 'Wins' },
  { accessorKey: 'losses', header: 'Losses' },
  {
    id: 'winrate',
    header: 'Win Rate',
    accessorFn: (row) => (row.wins + row.losses > 0 ? Math.round((100 * row.wins) / (row.wins + row.losses)) : 0),
    cell: ({ getValue }) => `${getValue()}%`,
  },
];

function PlayerLeaderboardPage() {
  const { tier, page, totalPages, players } = useLoaderData();
  const navigate = useNavigate();

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-4 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-2xl font-semibold">Leaderboard</h2>
        <FilterSelect
          paramName="tier"
          defaultValue={tier}
          resetParams={['page']}
          options={TIERS.map((t) => ({ value: t, label: t === 'ALL' ? 'All Tiers' : t }))}
        />
      </div>
      <DataTable columns={columns} data={players} onRowClick={(row) => navigate(`/players/${row.puuid}`)} />
      <Pagination page={page} totalPages={totalPages} />
    </div>
  );
}

export default PlayerLeaderboardPage;
