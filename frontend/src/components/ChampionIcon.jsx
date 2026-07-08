import { useEffect, useState } from 'react';
import { getChampionMap, resolveChampion } from '../lib/ddragon';

// Renders a champion icon resolved through Data Dragon's champion.json map,
// with a text-badge fallback for a miss (unmapped/renamed champion) instead
// of a broken image -- don't assume championname is ever a valid image URL
// fragment on its own (see ddragon.js for the Wukong/MonkeyKing example).
function ChampionIcon({ championName, size = 24 }) {
  const [entry, setEntry] = useState(null);

  useEffect(() => {
    let cancelled = false;
    getChampionMap().then((map) => {
      if (!cancelled) setEntry(resolveChampion(map, championName));
    });
    return () => {
      cancelled = true;
    };
  }, [championName]);

  if (!entry) {
    return (
      <span
        className="inline-flex items-center justify-center rounded-full bg-gray-700 text-[10px] text-gray-300 shrink-0"
        style={{ width: size, height: size }}
        title={championName}
      >
        {championName ? championName.slice(0, 2).toUpperCase() : '?'}
      </span>
    );
  }

  return (
    <img
      src={entry.iconUrl}
      alt={entry.name}
      title={entry.name}
      width={size}
      height={size}
      className="rounded-full shrink-0"
    />
  );
}

export default ChampionIcon;
