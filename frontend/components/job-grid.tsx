"use client";
import Link from "next/link";
import { JobCard } from "./job-card";
import type { Job } from "@/lib/api";

interface Props {
  jobs: Job[];
}

export function JobGrid({ jobs }: Props) {
  if (jobs.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-16">
        No jobs yet. Head to{" "}
        <Link href="/generate" className="underline hover:text-foreground">
          Generate
        </Link>{" "}
        to create your first image, video preview, or chat output.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} />
      ))}
    </div>
  );
}
