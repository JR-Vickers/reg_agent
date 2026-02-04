import { getPriorityRegulations, getTasks, getHealth } from '@/lib/api';
import type { PriorityRegulation, Task } from '@/lib/types';
import Link from 'next/link';

const severityColors: Record<string, string> = {
  critical: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  high: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  medium: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  low: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
};

const statusColors: Record<string, string> = {
  pending: 'bg-zinc-100 text-zinc-800 dark:bg-zinc-800 dark:text-zinc-200',
  in_progress: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
};

function StatCard({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) {
  return (
    <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">{title}</h3>
      <p className="mt-2 text-3xl font-semibold text-zinc-900 dark:text-zinc-100">{value}</p>
      {subtitle && <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>}
    </div>
  );
}

export default async function Dashboard() {
  let priorityRegs: PriorityRegulation[] = [];
  let tasks: Task[] = [];
  let health = { status: 'unknown', database: 'unknown' };
  let error: string | null = null;

  try {
    [priorityRegs, tasks, health] = await Promise.all([
      getPriorityRegulations(),
      getTasks({ limit: 10 }),
      getHealth(),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : 'Failed to fetch data';
  }

  const pendingTasks = tasks.filter(t => t.status === 'pending').length;
  const inProgressTasks = tasks.filter(t => t.status === 'in_progress').length;
  const criticalItems = priorityRegs.filter(r => r.gap_severity === 'critical').length;

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">Error loading dashboard: {error}</p>
          <p className="text-sm text-red-600 dark:text-red-400 mt-2">
            Make sure the backend is running at {process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">Dashboard</h1>
        <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
          BSA/AML Regulatory Intelligence Overview
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        <StatCard title="Priority Regulations" value={priorityRegs.length} subtitle="Requiring attention" />
        <StatCard title="Critical Items" value={criticalItems} subtitle="Immediate action needed" />
        <StatCard title="Pending Tasks" value={pendingTasks} subtitle="Awaiting assignment" />
        <StatCard title="In Progress" value={inProgressTasks} subtitle="Currently being worked" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
          <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Priority Regulations</h2>
            <Link href="/regulations" className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400">
              View all
            </Link>
          </div>
          <div className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {priorityRegs.slice(0, 5).map((reg) => (
              <div key={reg.id} className="px-6 py-4">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                      {reg.title}
                    </p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      {reg.source.toUpperCase()} &middot; {reg.published_date ? new Date(reg.published_date).toLocaleDateString() : 'Unknown date'}
                    </p>
                  </div>
                  {reg.gap_severity && (
                    <span className={`ml-2 px-2 py-1 text-xs font-medium rounded ${severityColors[reg.gap_severity]}`}>
                      {reg.gap_severity}
                    </span>
                  )}
                </div>
              </div>
            ))}
            {priorityRegs.length === 0 && (
              <p className="px-6 py-4 text-sm text-zinc-500 dark:text-zinc-400">No priority regulations found</p>
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800">
          <div className="px-6 py-4 border-b border-zinc-200 dark:border-zinc-800 flex justify-between items-center">
            <h2 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">Recent Tasks</h2>
            <Link href="/tasks" className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400">
              View all
            </Link>
          </div>
          <div className="divide-y divide-zinc-200 dark:divide-zinc-800">
            {tasks.slice(0, 5).map((task) => (
              <Link key={task.id} href={`/tasks/${task.id}`} className="block px-6 py-4 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-zinc-900 dark:text-zinc-100 truncate">
                      {task.title}
                    </p>
                    <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
                      {task.assigned_team} &middot; Due {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'No date'}
                    </p>
                  </div>
                  <span className={`ml-2 px-2 py-1 text-xs font-medium rounded ${statusColors[task.status]}`}>
                    {task.status.replace('_', ' ')}
                  </span>
                </div>
              </Link>
            ))}
            {tasks.length === 0 && (
              <p className="px-6 py-4 text-sm text-zinc-500 dark:text-zinc-400">No tasks found</p>
            )}
          </div>
        </div>
      </div>

      <div className="mt-8 text-xs text-zinc-400 dark:text-zinc-600">
        System: {health.status} | Database: {health.database}
      </div>
    </div>
  );
}
