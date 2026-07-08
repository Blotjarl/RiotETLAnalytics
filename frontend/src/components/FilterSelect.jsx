import { useSearchParams } from 'react-router-dom';

// Generic <select> bound to a URL search param, so every filter is a
// shareable/bookmarkable link. `resetParams` lists other params to clear
// when this one changes -- e.g. resetting `page` back to 1 when the tier
// filter changes, so a stale page number can't land on an empty table.
function FilterSelect({ paramName, label, options, defaultValue, resetParams = [] }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const value = searchParams.get(paramName) ?? defaultValue ?? '';

  function handleChange(e) {
    const next = new URLSearchParams(searchParams);
    next.set(paramName, e.target.value);
    resetParams.forEach((p) => next.delete(p));
    setSearchParams(next);
  }

  return (
    <label className="flex items-center gap-2 text-sm text-gray-300">
      {label && <span>{label}</span>}
      <select
        value={value}
        onChange={handleChange}
        className="bg-gray-800 text-white rounded-md px-3 py-2 border border-gray-700 focus:outline-none focus:border-cyan-400"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export default FilterSelect;
