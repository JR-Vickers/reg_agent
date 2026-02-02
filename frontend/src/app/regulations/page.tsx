import { getRegulations } from '@/lib/api';
import type { Regulation, DocumentSource } from '@/lib/types';
import Link from 'next/link';

const sourceLabels: Record<DocumentSource, string> = {
  fincen: 'FinCEN',
  sec: 'SEC',
  federal_register: 'Federal Register',
  cftc: 'CFTC',
  nydfs: 'NYDFS',
  ofac: 'OFAC',
};

export default async function RegulationsPage({
  searchParams,
}: {
  searchParams: Promise<{ source?: string; page?: string }>;
}) {
  const params = await searchParams;
  const source = params.source as DocumentSource | undefined;
  const page = parseInt(params.page || '1', 10);
  const limit = 25;
  const offset = (page - 1) * limit;

  let regulations: Regulation[] = [];
  let error: string | null = null;

  try {
    regulations = await getRegulations({ source, limit, offset });
  } catch (e) {
    error = e instanceof Error ? e.message : 'Failed to fetch regulations';
  }

  const sources: DocumentSource[] = ['fincen', 'sec', 'federal_register'];

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">Error: {error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Regulations</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Browse and filter regulatory documents
        </p>
      </div>

      <div className="mb-6 flex gap-2">
        <Link
          href="/regulations"
          className={`px-4 py-2 text-sm font-medium rounded-lg ${
            !source
              ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
              : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700'
          }`}
        >
          All
        </Link>
        {sources.map((s) => (
          <Link
            key={s}
            href={`/regulations?source=${s}`}
            className={`px-4 py-2 text-sm font-medium rounded-lg ${
              source === s
                ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900'
                : 'bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300 dark:hover:bg-zinc-700'
            }`}
          >
            {sourceLabels[s]}
          </Link>
        ))}
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden">
        <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800">
          <thead className="bg-zinc-50 dark:bg-zinc-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Title
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Source
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Published
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Ingested
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {regulations.map((reg) => (
              <tr key={reg.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50">
                <td className="px-6 py-4">
                  <a
                    href={reg.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm font-medium text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    {reg.title.length > 80 ? `${reg.title.slice(0, 80)}...` : reg.title}
                  </a>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className="px-2 py-1 text-xs font-medium rounded bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200">
                    {sourceLabels[reg.source] || reg.source}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500 dark:text-zinc-400">
                  {reg.published_date ? new Date(reg.published_date).toLocaleDateString() : '-'}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500 dark:text-zinc-400">
                  {new Date(reg.ingested_at).toLocaleDateString()}
                </td>
              </tr>
            ))}
            {regulations.length === 0 && (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-sm text-zinc-500 dark:text-zinc-400">
                  No regulations found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex justify-between items-center">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Showing {regulations.length} results
        </p>
        <div className="flex gap-2">
          {page > 1 && (
            <Link
              href={`/regulations?${source ? `source=${source}&` : ''}page=${page - 1}`}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300"
            >
              Previous
            </Link>
          )}
          {regulations.length === limit && (
            <Link
              href={`/regulations?${source ? `source=${source}&` : ''}page=${page + 1}`}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300"
            >
              Next
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
