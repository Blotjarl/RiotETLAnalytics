import { useSearchParams } from 'react-router-dom';

// Pass `totalPages` for page-number pagination (cheap exact counts, e.g.
// the ~11k-row players table). Pass `hasNextPage` instead for prev/next-only
// pagination against views over much larger aggregated tables, where an
// exact count would be wasteful to compute on every request.
function Pagination({ page, totalPages, hasNextPage, paramName = 'page' }) {
  const [searchParams, setSearchParams] = useSearchParams();

  function goToPage(newPage) {
    const next = new URLSearchParams(searchParams);
    next.set(paramName, String(newPage));
    setSearchParams(next);
  }

  const canGoPrev = page > 1;
  const canGoNext = totalPages != null ? page < totalPages : Boolean(hasNextPage);

  return (
    <div className="flex items-center justify-center gap-4 py-4 text-sm">
      <button
        type="button"
        onClick={() => goToPage(page - 1)}
        disabled={!canGoPrev}
        className="px-3 py-1 rounded-md bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-gray-700"
      >
        Prev
      </button>
      <span className="text-gray-400">
        Page {page}
        {totalPages != null ? ` of ${totalPages}` : ''}
      </span>
      <button
        type="button"
        onClick={() => goToPage(page + 1)}
        disabled={!canGoNext}
        className="px-3 py-1 rounded-md bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed hover:enabled:bg-gray-700"
      >
        Next
      </button>
    </div>
  );
}

export default Pagination;
