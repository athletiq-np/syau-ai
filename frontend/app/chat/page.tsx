"use client";
import { useState } from "react";
import { ChatForm } from "@/components/chat-form";
import { ChatWindow } from "@/components/chat-window";
import type { Job } from "@/lib/api";

export default function ChatPage() {
  const [currentJob, setCurrentJob] = useState<Job | null>(null);

  return (
    <div className="grid h-[calc(100vh-49px)] grid-cols-1 lg:grid-cols-[400px_minmax(0,1fr)]">
      <div className="border-r border-border overflow-y-auto p-6">
        <h1 className="text-lg font-semibold mb-2">Creative Chat</h1>
        <p className="text-sm text-muted-foreground mb-5">
          Use the chat worker for concepting, naming, launch copy, and creative iteration.
        </p>
        <ChatForm onJobStarted={setCurrentJob} />
      </div>

      <div className="p-6 overflow-y-auto">
        <ChatWindow job={currentJob} />
      </div>
    </div>
  );
}
