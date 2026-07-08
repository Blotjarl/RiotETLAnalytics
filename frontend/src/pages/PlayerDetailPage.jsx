import { useLoaderData } from 'react-router-dom';
import { supabase } from '../lib/supabaseClient';
import ChampionIcon from '../components/ChampionIcon';

export async function loader({ params }) {
  const { puuid } = params;

  const { data: player, error: playerError } = await supabase
    .from('players')
    .select('*')
    .eq('puuid', puuid)
    .maybeSingle();
  if (playerError) throw new Error(playerError.message);
  if (!player) throw new Response('Player not found', { status: 404 });

  const { data: identity, error: identityError } = await supabase
    .from('player_current_identity')
    .select('riotidgamename, riotidtagline')
    .eq('puuid', puuid)
    .maybeSingle();
  if (identityError) throw new Error(identityError.message);

  const { data: matchHistory, error: historyError } = await supabase
    .from('participant_stats')
    .select('*, matches(gamecreation, gameduration, patch, gamemode)')
    .eq('puuid', puuid)
    .order('gamecreation', { foreignTable: 'matches', ascending: false })
    .limit(20);
  if (historyError) throw new Error(historyError.message);

  return { player, identity, matchHistory: matchHistory ?? [] };
}

function PlayerDetailPage() {
  const { player, identity, matchHistory } = useLoaderData();
  const displayName = identity
    ? `${identity.riotidgamename}#${identity.riotidtagline}`
    : `Rank #${player.leaderboardrank}`;

  return (
    <div>
      <div className="mb-6 border-l-4 border-cyan-400 pl-4">
        <h2 className="text-2xl font-semibold">{displayName}</h2>
        <p className="text-gray-400">
          {player.tier} &middot; {player.leaguepoints} LP &middot; {player.wins}W {player.losses}L
        </p>
      </div>

      <h3 className="text-lg font-semibold mb-2">Recent Matches</h3>
      {matchHistory.length === 0 ? (
        <p className="text-gray-400">No crawled match history yet for this player.</p>
      ) : (
        <div className="space-y-2">
          {matchHistory.map((m) => (
            <div
              key={m.matchid}
              className={`flex items-center gap-4 rounded-lg px-4 py-3 border-l-4 ${
                m.win ? 'border-green-500 bg-green-950/30' : 'border-red-500 bg-red-950/30'
              }`}
            >
              <ChampionIcon championName={m.championname} size={32} />
              <div className="flex-1">
                <p className="font-medium">{m.championname}</p>
                <p className="text-xs text-gray-400">
                  {m.matches?.patch ? `Patch ${m.matches.patch}` : ''}
                  {m.matches?.gamecreation ? ` · ${new Date(m.matches.gamecreation).toLocaleDateString()}` : ''}
                </p>
              </div>
              <div className="text-sm tabular-nums text-right">
                <p>
                  {m.kills}/{m.deaths}/{m.assists}
                </p>
                {m.goldearned != null && (
                  <p className="text-gray-400 text-xs">{m.goldearned.toLocaleString()} gold</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default PlayerDetailPage;
