"use client";
import { useEffect, useState } from "react";
import { api, type Job } from "@/lib/api";
import { JobGrid } from "@/components/job-grid";

export default function HistoryPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const PAGE_SIZE = 40;
  const hasActiveJobs = jobs.some((job) => job.status === "pending" || job.status === "running");

  useEffect(() => {
    setLoading(true);
    api.listJobs({
      page,
      page_size: PAGE_SIZE,
      type: typeFilter || undefined,
      status: statusFilter || undefined,
    })
      .then((res) => {
        setJobs(res.items);
        setTotal(res.total);
      })
      .finally(() => setLoading(false));
  }, [page, statusFilter, typeFilter]);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, typeFilter]);

  useEffect(() => {
    if (!hasActiveJobs) {
      return;
    }

    const timer = window.setInterval(() => {
      api.listJobs({
        page,
        page_size: PAGE_SIZE,
        type: typeFilter || undefined,
        status: statusFilter || undefined,
      }).then((res) => {
        setJobs(res.items);
        setTotal(res.total);
      });
    }, 3000);

    return () => window.clearInterval(timer);
  }, [PAGE_SIZE, hasActiveJobs, page, statusFilter, typeFilter]);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="p-6 flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-semibold">History</h1>
        <span className="text-sm text-muted-foreground">
          {total} jobs{hasActiveJobs ? " · live refresh on" : ""}
        </span>
      </div>

      <div className="flex flex-wrap gap-3">
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground"
        >
          <option value="">All types</option>
          <option value="image">Image</option>
          <option value="video">Video</option>
          <option value="chat">Chat</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-card border border-border rounded-md px-3 py-2 text-sm text-foreground"
        >
          <option value="">All statuses</option>
          <option value="pending">Pending</option>
          <option value="running">Running</option>
          <option value="done">Done</option>
          <option value="failed">Failed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {loading ? (
        <div className="text-center text-muted-foreground py-16 text-sm">Loading...</div>
      ) : (
        <JobGrid jobs={jobs} />
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-3 mt-4">
          <button
            disabled={page === 1}
            onClick={() => setPage((p) => p - 1)}
            className="px-3 py-1.5 text-sm border border-border rounded disabled:opacity-40 hover:bg-accent"
          >
            Previous
          </button>
          <span className="text-sm text-muted-foreground">
            {page} / {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setPage((p) => p + 1)}
            className="px-3 py-1.5 text-sm border border-border rounded disabled:opacity-40 hover:bg-accent"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
