import { Link, isRouteErrorResponse, useRouteError } from 'react-router-dom';

function RouteError() {
  const error = useRouteError();
  const message = isRouteErrorResponse(error)
    ? error.statusText || error.data
    : error?.message || 'Something went wrong loading this page.';

  return (
    <div className="max-w-7xl mx-auto px-6 py-16 text-center">
      <h2 className="text-2xl font-semibold text-red-400 mb-2">Couldn't load this page</h2>
      <p className="text-gray-400 mb-6">{String(message)}</p>
      <Link to="/" className="text-cyan-400 hover:underline">
        Back to Champion Stats
      </Link>
    </div>
  );
}

export default RouteError;
