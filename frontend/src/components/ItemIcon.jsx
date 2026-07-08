import { useEffect, useState } from 'react';
import { getItemMap, resolveItem } from '../lib/ddragon';

// itemId of 0 or null/undefined means an empty item slot -- callers should
// generally avoid rendering this component for those, but it degrades to an
// empty placeholder rather than an error either way.
function ItemIcon({ itemId, size = 24 }) {
  const [entry, setEntry] = useState(null);

  useEffect(() => {
    let cancelled = false;
    if (!itemId) return undefined;
    getItemMap().then((map) => {
      if (!cancelled) setEntry(resolveItem(map, itemId));
    });
    return () => {
      cancelled = true;
    };
  }, [itemId]);

  if (!itemId || !entry) {
    return (
      <span
        className="inline-flex items-center justify-center rounded bg-gray-800 border border-gray-700 shrink-0"
        style={{ width: size, height: size }}
      />
    );
  }

  return (
    <img
      src={entry.iconUrl}
      alt={entry.name}
      title={entry.name}
      width={size}
      height={size}
      className="rounded shrink-0"
    />
  );
}

export default ItemIcon;
