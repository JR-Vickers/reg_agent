'use client';

import { useEffect, useState } from 'react';
import { getTask, getRegulation, getGapAnalysis, updateTask } from '@/lib/api';
import type { Task, Regulation, GapAnalysis, TaskStatus, TaskPriority } from '@/lib/types';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';

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

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const taskId = params.id as string;

  const [task, setTask] = useState<Task | null>(null);
  const [regulation, setRegulation] = useState<Regulation | null>(null);
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updateError, setUpdateError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const taskData = await getTask(taskId);
        setTask(taskData);

        const [regData, gaData] = await Promise.all([
          getRegulation(taskData.regulation_id),
          getGapAnalysis(taskData.gap_analysis_id),
        ]);
        setRegulation(regData);
        setGapAnalysis(gaData);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to fetch task');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [taskId]);

  async function handleStatusChange(newStatus: TaskStatus) {
    if (!task || updating) return;
    setUpdating(true);
    setUpdateError(null);
    try {
      const updated = await updateTask(task.id, { status: newStatus });
      setTask(updated);
    } catch (e) {
      setUpdateError(e instanceof Error ? e.message : 'Failed to update status');
    } finally {
      setUpdating(false);
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-zinc-200 dark:bg-zinc-800 rounded w-1/3"></div>
          <div className="h-4 bg-zinc-200 dark:bg-zinc-800 rounded w-2/3"></div>
          <div className="h-32 bg-zinc-200 dark:bg-zinc-800 rounded"></div>
        </div>
      </div>
    );
  }

  if (error || !task) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
          <p className="text-red-800 dark:text-red-200">Error: {error || 'Task not found'}</p>
        </div>
        <Link href="/tasks" className="mt-4 inline-block text-blue-600 hover:text-blue-800 dark:text-blue-400">
          ← Back to Tasks
        </Link>
      </div>
    );
  }

  const affectedControl = gapAnalysis?.affected_controls?.controls?.find(
    (c) => c.control_id === task.control_id
  );

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <Link href="/tasks" className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 mb-4 inline-block">
        ← Back to Tasks
      </Link>

      <div className="bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 overflow-hidden">
        <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1">
              <h1 className="text-xl font-bold text-zinc-900 dark:text-zinc-100">{task.title}</h1>
              <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">{task.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 text-xs font-medium rounded ${priorityColors[task.priority]}`}>
                {task.priority}
              </span>
            </div>
          </div>

          <div className="mt-6 flex flex-wrap gap-4 text-sm">
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Team:</span>{' '}
              <span className="font-medium text-zinc-900 dark:text-zinc-100">{task.assigned_team}</span>
            </div>
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Control:</span>{' '}
              <span className="font-medium text-zinc-900 dark:text-zinc-100">{task.control_id}</span>
            </div>
            <div>
              <span className="text-zinc-500 dark:text-zinc-400">Due:</span>{' '}
              <span className="font-medium text-zinc-900 dark:text-zinc-100">
                {task.due_date ? new Date(task.due_date).toLocaleDateString() : 'Not set'}
              </span>
            </div>
          </div>

          <div className="mt-6">
            <label className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2">
              Status
            </label>
            {updateError && (
              <p className="text-sm text-red-600 dark:text-red-400 mb-2">{updateError}</p>
            )}
            <div className="flex gap-2">
              {statusOptions.map((s) => (
                <button
                  key={s}
                  onClick={() => handleStatusChange(s)}
                  disabled={updating || task.status === s}
                  className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                    task.status === s
                      ? statusColors[s] + ' ring-2 ring-offset-2 ring-zinc-400 dark:ring-offset-zinc-900'
                      : 'bg-zinc-100 text-zinc-600 hover:bg-zinc-200 dark:bg-zinc-800 dark:text-zinc-400 dark:hover:bg-zinc-700'
                  } ${updating ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {s.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>
        </div>

        {regulation && (
          <div className="p-6 border-b border-zinc-200 dark:border-zinc-800">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-3">Source Regulation</h2>
            <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4">
              <p className="font-medium text-zinc-900 dark:text-zinc-100">{regulation.title}</p>
              <div className="mt-2 flex gap-4 text-sm">
                <span className="text-zinc-500 dark:text-zinc-400">
                  Source: <span className="text-zinc-700 dark:text-zinc-300">{regulation.source.toUpperCase()}</span>
                </span>
                {regulation.published_date && (
                  <span className="text-zinc-500 dark:text-zinc-400">
                    Published: <span className="text-zinc-700 dark:text-zinc-300">{new Date(regulation.published_date).toLocaleDateString()}</span>
                  </span>
                )}
              </div>
              <a
                href={regulation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400"
              >
                View Original Document →
              </a>
            </div>
          </div>
        )}

        {gapAnalysis && (
          <div className="p-6">
            <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100 mb-3">Gap Analysis</h2>
            <div className="bg-zinc-50 dark:bg-zinc-800/50 rounded-lg p-4 space-y-4">
              <div>
                <p className="text-sm text-zinc-700 dark:text-zinc-300">{gapAnalysis.analysis_summary}</p>
              </div>

              {affectedControl && (
                <div className="border-t border-zinc-200 dark:border-zinc-700 pt-4">
                  <h3 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-2">
                    Control: {affectedControl.control_id}
                  </h3>
                  <p className="text-sm text-zinc-700 dark:text-zinc-300 mb-2">{affectedControl.gap_description}</p>
                  <div className="flex gap-4 text-xs text-zinc-500 dark:text-zinc-400">
                    <span>Effort Level: <span className="text-zinc-700 dark:text-zinc-300">{affectedControl.effort_level}</span></span>
                  </div>
                  <div className="mt-3">
                    <h4 className="text-xs font-semibold text-zinc-500 dark:text-zinc-400 uppercase mb-1">Remediation Action</h4>
                    <p className="text-sm text-zinc-700 dark:text-zinc-300">{affectedControl.remediation_action}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
