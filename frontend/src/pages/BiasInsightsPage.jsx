import { useLoaderData, useSearchParams } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import DataTable from '../components/DataTable';
import FilterSelect from '../components/FilterSelect';
import ChampionIcon from '../components/ChampionIcon';
import ItemIcon from '../components/ItemIcon';

const TIERS = ['CHALLENGER', 'GRANDMASTER', 'MASTER'];
const ROLES = [
  { value: 'TOP', label: 'Top' },
  { value: 'JUNGLE', label: 'Jungle' },
  { value: 'MIDDLE', label: 'Mid' },
  { value: 'BOTTOM', label: 'Bottom' },
  { value: 'UTILITY', label: 'Support' },
];

// Minimum sample size before a selection_effect is shown -- a page whose
// point is statistical rigor shouldn't display noisy swings from a handful
// of games. Applied at query time (not baked into the table) so it's easy
// to tune later.
const MIN_GAMES_PLAYED = 30;

export async function loader({ request }) {
  const url = new URL(request.url);
  const tier = url.searchParams.get('tier') || 'CHALLENGER';
  const role = url.searchParams.get('role') || 'TOP';
  const drillChampion = url.searchParams.get('champion') || '';

  const [biasResult, championListResult] = await Promise.all([
    supabase
      .from('champion_matchup_bias')
      .select('*')
      .eq('tier', tier)
      .eq('teamposition', role)
      .gte('games_played', MIN_GAMES_PLAYED)
      .order('selection_effect', { ascending: false }),
    supabase
      .from('champion_stats_by_tier')
      .select('championname')
      .eq('tier', tier)
      .order('championname', { ascending: true }),
  ]);
  if (biasResult.error) throw new Error(biasResult.error.message);
  if (championListResult.error) throw new Error(championListResult.error.message);

  const matchupBias = biasResult.data ?? [];
  const champions = [...new Set((championListResult.data ?? []).map((r) => r.championname))];
  const itemChampion = url.searchParams.get('itemChampion') || champions[0] || '';

  const [drillResult, itemResult] = await Promise.all([
    drillChampion
      ? supabase
          .from('champion_matchup_stats')
          .select('*')
          .eq('tier', tier)
          .eq('teamposition', role)
          .eq('championname', drillChampion)
          .order('playcount', { ascending: false })
      : Promise.resolve({ data: [], error: null }),
    itemChampion === 'ANY'
      ? supabase.from('item_stats_by_tier_firstblood').select('*').eq('tier', tier)
      : itemChampion
        ? supabase
            .from('item_build_stats_by_firstblood')
            .select('*')
            .eq('tier', tier)
            .eq('championname', itemChampion)
        : Promise.resolve({ data: [], error: null }),
  ]);
  if (drillResult.error) throw new Error(drillResult.error.message);
  if (itemResult.error) throw new Error(itemResult.error.message);

  return {
    tier,
    role,
    drillChampion,
    matchupBias,
    matchupDetail: drillResult.data ?? [],
    champions,
    itemChampion,
    itemStats: pivotItemStats(itemResult.data ?? []),
  };
}

// item_build_stats_by_firstblood / item_stats_by_tier_firstblood have one
// row per (item, firstbloodkill) pair -- pivot into one row per item with
// both states side by side, so the gap between them is directly visible
// instead of split across two lookups. Uses explicit === true/false checks
// (not truthy/falsy) so a null/unknown firstbloodkill is skipped rather
// than silently folded into the "no first blood" bucket -- shouldn't occur
// in practice since both source queries already filter firstbloodkill IS
// NOT NULL, but the check costs nothing and makes the intent explicit.
function pivotItemStats(rows) {
  const byItem = new Map();
  for (const row of rows) {
    if (row.firstbloodkill !== true && row.firstbloodkill !== false) continue;
    const entry = byItem.get(row.itemid) ?? { itemid: row.itemid };
    if (row.firstbloodkill === true) {
      entry.fbWinrate = row.winrate;
      entry.fbGames = row.playcount;
    } else {
      entry.noFbWinrate = row.winrate;
      entry.noFbGames = row.playcount;
    }
    byItem.set(row.itemid, entry);
  }
  return [...byItem.values()].sort((a, b) => (b.fbGames ?? 0) + (b.noFbGames ?? 0) - ((a.fbGames ?? 0) + (a.noFbGames ?? 0)));
}

function signedPercent(value) {
  if (value == null) return 'N/A';
  const rounded = Math.round(value * 10) / 10;
  const color = rounded > 0 ? 'text-green-400' : rounded < 0 ? 'text-red-400' : 'text-gray-400';
  return <span className={color}>{rounded > 0 ? '+' : ''}{rounded}%</span>;
}

const biasColumns = [
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
  { accessorKey: 'games_played', header: 'Games' },
  { accessorKey: 'observed_winrate', header: 'Observed WR', cell: ({ getValue }) => `${getValue()}%` },
  { accessorKey: 'expected_winrate', header: 'Expected WR', cell: ({ getValue }) => `${getValue()}%` },
  {
    accessorKey: 'selection_effect',
    header: 'Selection Effect',
    cell: ({ getValue }) => signedPercent(getValue()),
  },
];

const matchupDetailColumns = [
  {
    accessorKey: 'opponent_championname',
    header: 'Opponent',
    cell: ({ getValue }) => (
      <div className="flex items-center gap-2">
        <ChampionIcon championName={getValue()} />
        <span className="font-medium">{getValue()}</span>
      </div>
    ),
  },
  { accessorKey: 'playcount', header: 'Games' },
  { accessorKey: 'winrate', header: 'Win Rate', cell: ({ getValue }) => `${getValue()}%` },
];

const itemColumns = [
  { accessorKey: 'itemid', header: 'Item', cell: ({ getValue }) => <ItemIcon itemId={getValue()} /> },
  {
    id: 'firstBlood',
    header: 'First Blood WR',
    accessorFn: (row) => row.fbWinrate ?? null,
    cell: ({ row }) =>
      row.original.fbWinrate != null ? `${row.original.fbWinrate}% (${row.original.fbGames})` : 'N/A',
  },
  {
    id: 'noFirstBlood',
    header: 'No First Blood WR',
    accessorFn: (row) => row.noFbWinrate ?? null,
    cell: ({ row }) =>
      row.original.noFbWinrate != null ? `${row.original.noFbWinrate}% (${row.original.noFbGames})` : 'N/A',
  },
  {
    id: 'gap',
    header: 'Gap',
    accessorFn: (row) => (row.fbWinrate != null && row.noFbWinrate != null ? row.fbWinrate - row.noFbWinrate : null),
    cell: ({ getValue }) => signedPercent(getValue()),
  },
];

function BiasInsightsPage() {
  const { tier, role, drillChampion, matchupBias, matchupDetail, champions, itemChampion, itemStats } =
    useLoaderData();
  const [searchParams, setSearchParams] = useSearchParams();

  function drillInto(championname) {
    const next = new URLSearchParams(searchParams);
    next.set('champion', championname);
    setSearchParams(next);
  }

  return (
    <div>
      <div className="max-w-3xl mb-8">
        <h2 className="text-2xl font-semibold mb-2">Bias Insights</h2>
        <p className="text-sm text-gray-400 leading-relaxed">
          Raw win-rate stats are misleading in specific, well-understood ways. The two sections below
          quantify two of them: champions picked deliberately into favorable matchups, and items bought
          after a player is already winning.
        </p>
      </div>

      {/* --- Matchup selection bias --- */}
      <section className="mb-12">
        <div className="flex flex-wrap items-center justify-between gap-4 mb-2 border-l-4 border-cyan-400 pl-4">
          <h3 className="text-xl font-semibold">Champion Matchup Selection Bias</h3>
          <div className="flex gap-4">
            <FilterSelect
              paramName="role"
              defaultValue={role}
              resetParams={['champion']}
              options={ROLES}
            />
            <FilterSelect
              paramName="tier"
              defaultValue={tier}
              resetParams={['champion']}
              options={TIERS.map((t) => ({ value: t, label: t }))}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 pl-4 mb-4 max-w-3xl">
          <strong className="text-gray-400">Observed win rate</strong> is a champion's actual win rate,
          weighted by the opponents players actually chose to face them with. <strong className="text-gray-400">Expected
          win rate</strong> reweights those same per-opponent win rates by how common each opponent is
          overall in this role and tier, so it shows what the champion's win rate would look like if
          matchups were random instead of chosen. The gap between them
          (<strong className="text-gray-400">selection effect</strong>) is how much of the win rate comes
          from favorable matchup selection rather than raw strength. It's the same standardization
          technique used for opponent-adjusted stats in sports analytics. Only champions with at least
          {' '}{MIN_GAMES_PLAYED} games in this role and tier are shown. Click a row to see the matchups
          behind the number.
        </p>
        <details className="pl-4 mb-4 max-w-3xl text-xs text-gray-500">
          <summary className="cursor-pointer text-cyan-400 hover:underline w-fit">
            Show the full methodology
          </summary>
          <div className="mt-3 space-y-3 leading-relaxed">
            <p>
              For a champion C, in a given role and tier, against every opponent they've faced:
            </p>
            <pre className="bg-gray-800 rounded p-3 overflow-x-auto text-gray-300">
{`observed_winrate(C) = Σ [ N(C,O) × WR(C,O) ] / Σ N(C,O)
expected_winrate(C) = Σ [ P(O)   × WR(C,O) ] / Σ P(O)

selection_effect(C) = observed_winrate(C) − expected_winrate(C)`}
            </pre>
            <p>
              where, for each opponent O: <strong className="text-gray-400">WR(C,O)</strong> is C's win
              rate specifically against O, <strong className="text-gray-400">N(C,O)</strong> is how many
              times C actually faced O, and <strong className="text-gray-400">P(O)</strong> is O's overall
              play rate in this role and tier, regardless of who they're facing.
            </p>
            <p>
              <code className="text-gray-300">observed_winrate</code> is just the number everyone already
              reports: wins over games. Because players choose their matchups, it's implicitly weighted by
              N(C,O), how often C's players actually sought out or avoided each opponent.{' '}
              <code className="text-gray-300">expected_winrate</code> recomputes the same average, but
              swaps that self-selected weighting for P(O), how common each opponent naturally is in this
              role and tier, regardless of who's playing C. That answers a different question: what would
              C's win rate look like if matchups were assigned at random instead of chosen?
            </p>
            <p>
              This is called <strong className="text-gray-400">direct standardization</strong>, or
              reweighting. Epidemiologists use the same technique to compare disease rates across
              populations with different age distributions, and it's the same idea behind opponent-adjusted
              or strength-of-schedule-adjusted stats in sports analytics. The principle is simple: don't
              compare two raw averages when the underlying exposure differs between them (here, which
              opponents were faced). Reweight both to a shared, neutral distribution first, then compare.
            </p>
            <p>
              A <strong className="text-green-400">positive</strong> selection_effect means the champion's
              raw win rate is inflated because they're picked into favorable matchups more often than the
              population would predict. A <strong className="text-red-400">negative</strong> selection_effect
              means the opposite: raw stats understate the champion because they're disproportionately
              played into unfavorable matchups, possibly by players who don't realize it.
            </p>
          </div>
        </details>
        <DataTable
          columns={biasColumns}
          data={matchupBias}
          onRowClick={(row) => drillInto(row.championname)}
          emptyMessage="Not enough data for this role/tier yet."
        />

        {drillChampion && (
          <div className="mt-6">
            <h4 className="text-lg font-semibold mb-2">
              {drillChampion}: per-opponent breakdown
            </h4>
            <DataTable
              columns={matchupDetailColumns}
              data={matchupDetail}
              emptyMessage="No matchup data for this champion yet."
            />
          </div>
        )}
      </section>

      {/* --- Item snowball bias --- */}
      <section>
        <div className="flex flex-wrap items-center justify-between gap-4 mb-2 border-l-4 border-cyan-400 pl-4">
          <h3 className="text-xl font-semibold">Item Snowball Bias</h3>
          <div className="flex gap-4">
            <FilterSelect
              paramName="itemChampion"
              defaultValue={itemChampion}
              options={[{ value: 'ANY', label: 'Any Champion' }, ...champions.map((c) => ({ value: c, label: c }))]}
            />
          </div>
        </div>
        <p className="text-xs text-gray-500 pl-4 mb-4 max-w-3xl">
          Some items look strong mainly because players buy them after they're already ahead. The item is
          a symptom of winning, not the cause. <strong className="text-gray-400">First blood</strong> is
          used here as a rough, partial signal for "was already ahead early." This isn't a full fix. The
          rigorous version would need game state at the exact moment of purchase (Riot's match-timeline
          API, which this site doesn't currently fetch), not just a single early-game proxy. Treat a large
          first-blood/no-first-blood gap as a hint worth investigating, not as proof of a causal effect.
        </p>
        <DataTable columns={itemColumns} data={itemStats} emptyMessage="No item data for this champion yet." />
      </section>
    </div>
  );
}

export default BiasInsightsPage;
