import { getTasks, getTeams } from '@/lib/api';
import type { Task, TaskStatus, TaskPriority } from '@/lib/types';
import Link from 'next/link';

const statusColors: Record<TaskStatus, string> = {
  pending: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
};

const priorityColors: Record<TaskPriority, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  low: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
};

const statusOptions: TaskStatus[] = ['pending', 'in_progress', 'completed'];
const priorityOptions: TaskPriority[] = ['critical', 'high', 'medium', 'low'];

export default async function TasksPage({
  searchParams,
}: {
  searchParams: Promise<{ status?: string; team?: string; priority?: string; page?: string }>;
}) {
  const params = await searchParams;
  const status = params.status as TaskStatus | undefined;
  const team = params.team;
  const priority = params.priority as TaskPriority | undefined;
  const page = parseInt(params.page || '1', 10);
  const limit = 25;
  const offset = (page - 1) * limit;

  let tasks: Task[] = [];
  let teams: string[] = [];
  let error: string | null = null;

  try {
    const [tasksResult, teamsResult] = await Promise.all([
      getTasks({ status, assigned_team: team, priority, limit, offset }),
      getTeams(),
    ]);
    tasks = tasksResult;
    teams = teamsResult.teams;
  } catch (e) {
    error = e instanceof Error ? e.message : 'Failed to fetch tasks';
  }

  const buildFilterUrl = (key: string, value: string | undefined) => {
    const newParams = new URLSearchParams();
    if (status && key !== 'status') newParams.set('status', status);
    if (team && key !== 'team') newParams.set('team', team);
    if (priority && key !== 'priority') newParams.set('priority', priority);
    if (value) newParams.set(key, value);
    const query = newParams.toString();
    return `/tasks${query ? `?${query}` : ''}`;
  };

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
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Tasks</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          Compliance tasks generated from gap analyses
        </p>
      </div>

      <div className="mb-6 space-y-4">
        <div className="flex flex-wrap gap-4">
          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Status</label>
            <div className="flex gap-1">
              <Link
                href={buildFilterUrl('status', undefined)}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  !status ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                }`}
              >
                All
              </Link>
              {statusOptions.map((s) => (
                <Link
                  key={s}
                  href={buildFilterUrl('status', s)}
                  className={`px-3 py-1.5 text-xs font-medium rounded ${
                    status === s ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                  }`}
                >
                  {s.replace('_', ' ')}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Priority</label>
            <div className="flex gap-1">
              <Link
                href={buildFilterUrl('priority', undefined)}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  !priority ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                }`}
              >
                All
              </Link>
              {priorityOptions.map((p) => (
                <Link
                  key={p}
                  href={buildFilterUrl('priority', p)}
                  className={`px-3 py-1.5 text-xs font-medium rounded ${
                    priority === p ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                  }`}
                >
                  {p}
                </Link>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-zinc-500 dark:text-zinc-400 mb-1">Team</label>
            <div className="flex gap-1 flex-wrap">
              <Link
                href={buildFilterUrl('team', undefined)}
                className={`px-3 py-1.5 text-xs font-medium rounded ${
                  !team ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                }`}
              >
                All
              </Link>
              {teams.map((t) => (
                <Link
                  key={t}
                  href={buildFilterUrl('team', t)}
                  className={`px-3 py-1.5 text-xs font-medium rounded ${
                    team === t ? 'bg-zinc-900 text-white dark:bg-zinc-100 dark:text-zinc-900' : 'bg-zinc-100 text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300'
                  }`}
                >
                  {t}
                </Link>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden">
        <table className="min-w-full divide-y divide-zinc-200 dark:divide-zinc-800">
          <thead className="bg-zinc-50 dark:bg-zinc-800">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Task
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Team
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Priority
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-zinc-500 dark:text-zinc-400 uppercase tracking-wider">
                Due Date
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {tasks.map((task) => (
              <tr key={task.id} className="hover:bg-zinc-50 dark:hover:bg-zinc-800/50 cursor-pointer group">
                <td className="px-6 py-4">
                  <Link href={`/tasks/${task.id}`} className="block">
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 group-hover:text-blue-600 dark:group-hover:text-blue-400">
                      {task.title}
                    </p>
                    {task.description && (
                      <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1 truncate max-w-md">
                        {task.description}
                      </p>
                    )}
                  </Link>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500 dark:text-zinc-400">
                  {task.assigned_team}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded ${priorityColors[task.priority]}`}>
                    {task.priority}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 py-1 text-xs font-medium rounded ${statusColors[task.status]}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-zinc-500 dark:text-zinc-400">
                  {task.due_date ? new Date(task.due_date).toLocaleDateString() : '-'}
                </td>
              </tr>
            ))}
            {tasks.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-8 text-center text-sm text-zinc-500 dark:text-zinc-400">
                  No tasks found
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="mt-4 flex justify-between items-center">
        <p className="text-sm text-zinc-500 dark:text-zinc-400">
          Showing {tasks.length} tasks
        </p>
        <div className="flex gap-2">
          {page > 1 && (
            <Link
              href={`/tasks?${status ? `status=${status}&` : ''}${team ? `team=${team}&` : ''}${priority ? `priority=${priority}&` : ''}page=${page - 1}`}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-zinc-100 text-zinc-700 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-300"
            >
              Previous
            </Link>
          )}
          {tasks.length === limit && (
            <Link
              href={`/tasks?${status ? `status=${status}&` : ''}${team ? `team=${team}&` : ''}${priority ? `priority=${priority}&` : ''}page=${page + 1}`}
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
