"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { api, type Project } from "@/lib/api";
import { cn } from "@/lib/utils";

export default function StudioPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newProjectTitle, setNewProjectTitle] = useState("");
  const [newProjectDesc, setNewProjectDesc] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  async function loadProjects() {
    try {
      setLoading(true);
      const res = await api.listProjects();
      setProjects(res.items);
    } catch (err) {
      console.error("Failed to load projects:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateProject(e: React.FormEvent) {
    e.preventDefault();
    if (!newProjectTitle.trim()) return;

    try {
      setCreating(true);
      const res = await api.createProject({
        title: newProjectTitle,
        description: newProjectDesc,
        script: "",
      });
      setProjects([res, ...projects]);
      setNewProjectTitle("");
      setNewProjectDesc("");
      setShowNewProjectModal(false);
    } catch (err) {
      console.error("Failed to create project:", err);
    } finally {
      setCreating(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 to-slate-900">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50 backdrop-blur">
        <div className="mx-auto max-w-7xl px-6 py-8">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-4xl font-bold text-white">Studio</h1>
              <p className="mt-2 text-slate-400">Create cinematic films with AI</p>
            </div>
            <button
              onClick={() => setShowNewProjectModal(true)}
              className={cn(
                "rounded-lg px-6 py-3 font-medium transition-all",
                "bg-gradient-to-r from-cyan-500 to-blue-500 text-white",
                "hover:from-cyan-600 hover:to-blue-600",
                "shadow-lg hover:shadow-xl"
              )}
            >
              New Project
            </button>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div className="mx-auto max-w-7xl px-6 py-12">
        {loading ? (
          <div className="flex justify-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-slate-700 border-t-cyan-500" />
          </div>
        ) : projects.length === 0 ? (
          <div className="rounded-xl border border-slate-800 bg-slate-800/30 px-12 py-16 text-center">
            <h3 className="text-xl font-semibold text-slate-300">No projects yet</h3>
            <p className="mt-2 text-slate-400">Create your first film to get started</p>
            <button
              onClick={() => setShowNewProjectModal(true)}
              className="mt-6 rounded-lg bg-cyan-500/20 px-4 py-2 text-cyan-400 hover:bg-cyan-500/30 transition-colors"
            >
              Create Project
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {projects.map((project) => (
              <Link key={project.id} href={`/studio/${project.id}`}>
                <div className="group cursor-pointer rounded-xl border border-slate-700 bg-slate-800/50 p-6 transition-all hover:border-slate-600 hover:bg-slate-800">
                  {/* Thumbnail placeholder */}
                  <div className="mb-4 aspect-video rounded-lg bg-gradient-to-br from-slate-700 to-slate-900 group-hover:from-slate-600 group-hover:to-slate-800 transition-colors" />

                  <h3 className="truncate font-semibold text-white group-hover:text-cyan-400 transition-colors">
                    {project.title}
                  </h3>

                  <p className="mt-1 line-clamp-2 text-sm text-slate-400">
                    {project.description || "No description"}
                  </p>

                  <div className="mt-4 flex items-center justify-between">
                    <div className="text-sm text-slate-500">
                      {project.total_shots} shot{project.total_shots !== 1 ? "s" : ""}
                    </div>
                    <div
                      className={cn(
                        "rounded-full px-3 py-1 text-xs font-medium",
                        project.status === "done"
                          ? "bg-green-500/20 text-green-400"
                          : project.status === "processing"
                            ? "bg-yellow-500/20 text-yellow-400"
                            : project.status === "failed"
                              ? "bg-red-500/20 text-red-400"
                              : "bg-slate-700 text-slate-300"
                      )}
                    >
                      {project.status}
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* New Project Modal */}
      {showNewProjectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-8 shadow-xl">
            <h2 className="text-2xl font-bold text-white">New Project</h2>
            <form onSubmit={handleCreateProject} className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300">Title</label>
                <input
                  type="text"
                  value={newProjectTitle}
                  onChange={(e) => setNewProjectTitle(e.target.value)}
                  placeholder="My first film..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  autoFocus
                  disabled={creating}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300">Description</label>
                <textarea
                  value={newProjectDesc}
                  onChange={(e) => setNewProjectDesc(e.target.value)}
                  placeholder="What is this film about?"
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-4 py-2 text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
                  rows={3}
                  disabled={creating}
                />
              </div>
              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowNewProjectModal(false)}
                  disabled={creating}
                  className="flex-1 rounded-lg border border-slate-700 px-4 py-2 text-slate-300 hover:bg-slate-800 transition-colors disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!newProjectTitle.trim() || creating}
                  className="flex-1 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-500 px-4 py-2 text-white font-medium hover:from-cyan-600 hover:to-blue-600 transition-all disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
