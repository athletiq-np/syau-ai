"use client";
import { useState } from "react";
import { VideoForm } from "@/components/video-form";
import { JobCard } from "@/components/job-card";
import type { Job } from "@/lib/api";

export default function VideoPage() {
  const [currentJob, setCurrentJob] = useState<Job | null>(null);

  return (
    <div className="flex h-[calc(100vh-49px)]">
      <div className="w-[400px] min-w-[340px] border-r border-border overflow-y-auto p-6">
        <h1 className="text-lg font-semibold mb-2">Generate Video</h1>
        <p className="text-sm text-muted-foreground mb-5">
          Create realistic videos using Wan 2.2. Choose between text-to-video for generating from scratch, or image-to-video to transform images into motion.
        </p>
        <VideoForm onJobStarted={setCurrentJob} />
      </div>

      <div className="flex-1 overflow-y-auto p-6 flex items-start justify-center">
        {currentJob ? (
          <div className="w-full max-w-2xl">
            <JobCard job={currentJob} expanded />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-muted-foreground gap-3">
            <div className="w-24 h-24 border-2 border-dashed border-border rounded-lg flex items-center justify-center text-3xl">
              ▶
            </div>
            <p className="text-sm">Your video preview will appear here</p>
          </div>
        )}
      </div>
    </div>
  );
}
