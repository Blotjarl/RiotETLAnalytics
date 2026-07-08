// Riot's public Data Dragon CDN -- no auth, CORS-friendly, versioned by
// patch. We don't try to pin the exact patch a given row was played on;
// the latest version's icons are close enough for display purposes, and
// fetching per-patch data for every row would be wasteful. Everything
// here is fetched once per browser session and cached in module-level
// promises, so repeated calls across components/pages share one fetch.

const DDRAGON_BASE = 'https://ddragon.leagueoflegends.com';

let versionPromise = null;
let championMapPromise = null;
let itemMapPromise = null;

function getLatestVersion() {
  if (!versionPromise) {
    versionPromise = fetch(`${DDRAGON_BASE}/api/versions.json`)
      .then((res) => res.json())
      .then((versions) => versions[0]);
  }
  return versionPromise;
}

// Maps championname (Riot's internal championId, as stored in
// participant_stats) -> { name, iconUrl }. Keyed case-insensitively since
// championname isn't guaranteed to match Data Dragon's `id` field's exact
// casing (e.g. Wukong is stored/returned as "MonkeyKing", not "Wukong" --
// don't assume championname is ever the *display* name).
export function getChampionMap() {
  if (!championMapPromise) {
    championMapPromise = getLatestVersion().then(async (version) => {
      const res = await fetch(`${DDRAGON_BASE}/cdn/${version}/data/en_US/champion.json`);
      const { data } = await res.json();
      const map = new Map();
      for (const champ of Object.values(data)) {
        map.set(champ.id.toLowerCase(), {
          name: champ.name,
          iconUrl: `${DDRAGON_BASE}/cdn/${version}/img/champion/${champ.image.full}`,
        });
      }
      return map;
    });
  }
  return championMapPromise;
}

// Maps numeric item id -> { name, iconUrl }. item0-item6 in participant_stats
// are raw Data Dragon item ids; 0 means an empty slot and should be filtered
// by the caller before ever reaching this map.
export function getItemMap() {
  if (!itemMapPromise) {
    itemMapPromise = getLatestVersion().then(async (version) => {
      const res = await fetch(`${DDRAGON_BASE}/cdn/${version}/data/en_US/item.json`);
      const { data } = await res.json();
      const map = new Map();
      for (const [itemId, item] of Object.entries(data)) {
        map.set(Number(itemId), {
          name: item.name,
          iconUrl: `${DDRAGON_BASE}/cdn/${version}/img/item/${item.image.full}`,
        });
      }
      return map;
    });
  }
  return itemMapPromise;
}

export function resolveChampion(championMap, championName) {
  if (!championMap || !championName) return null;
  return championMap.get(championName.toLowerCase()) ?? null;
}

export function resolveItem(itemMap, itemId) {
  if (!itemMap || !itemId) return null;
  return itemMap.get(itemId) ?? null;
}
