"use client";

import { ApiStatus } from "@/components/api-status";

export default function Home() {
  const cards = [
    {
      href: "/studio",
      label: "Studio",
      title: "Create cinematic films",
      body: "Script to shots to video. Break your script into shots, generate each with AI, and stitch into a complete film with character consistency.",
    },
    {
      href: "/generate",
      label: "Image",
      title: "Generate mock images",
      body: "Use the image worker to validate prompts, status updates, MinIO uploads, and result rendering.",
    },
    {
      href: "/video",
      label: "Video",
      title: "Render animated previews",
      body: "Exercise the video queue with lightweight animated outputs before the GPU inference path is wired in.",
    },
    {
      href: "/chat",
      label: "Chat",
      title: "Iterate with creative chat",
      body: "Generate copy, naming directions, and concept notes through the chat worker and saved transcript flow.",
    },
    {
      href: "/history",
      label: "History",
      title: "Review every job",
      body: "Filter image, video, and chat jobs in one place and inspect outputs, timings, and failure states.",
    },
  ];

  return (
    <div className="min-h-[calc(100vh-49px)] bg-[radial-gradient(circle_at_top,rgba(72,115,255,0.14),transparent_35%),linear-gradient(180deg,rgba(255,255,255,0.02),transparent_40%)]">
      <div className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-14">
        <section className="max-w-3xl">
          <div className="mb-4">
            <ApiStatus />
          </div>
          <div className="mb-4 inline-flex rounded-full border border-border bg-card/70 px-3 py-1 text-xs uppercase tracking-[0.24em] text-muted-foreground">
            Phase 1 Studio
          </div>
          <h1 className="text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
            Self-hosted AI creative studio for image, video, and chat workflows.
          </h1>
          <p className="mt-4 max-w-2xl text-base leading-7 text-muted-foreground">
            SYAU AI is now far enough along that you can test every core queue from one place. Pick a lane below,
            generate an output, and use History to inspect the full pipeline.
          </p>
        </section>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {cards.map((card) => (
            <a
              key={card.href}
              href={card.href}
              className="group rounded-2xl border border-border bg-card/70 p-5 transition-transform transition-colors hover:-translate-y-1 hover:bg-card"
            >
              <div className="mb-4 text-xs uppercase tracking-[0.24em] text-muted-foreground">{card.label}</div>
              <h2 className="text-lg font-semibold text-foreground">{card.title}</h2>
              <p className="mt-3 text-sm leading-6 text-muted-foreground">{card.body}</p>
              <div className="mt-6 text-sm text-foreground">Open workspace →</div>
            </a>
          ))}
        </section>

        <section className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-border bg-card/60 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Queues</div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Image, video, and chat jobs now complete end to end with WebSocket progress and MinIO-backed outputs.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card/60 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Local Mode</div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Mock handlers keep local development fast while preserving the backend contracts needed for GPU workers later.
            </p>
          </div>
          <div className="rounded-2xl border border-border bg-card/60 p-5">
            <div className="text-xs uppercase tracking-[0.24em] text-muted-foreground">Next Step</div>
            <p className="mt-3 text-sm leading-6 text-muted-foreground">
              Remaining polish work is mostly UX refinement, better detail views, and stability hardening rather than missing core plumbing.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
