"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter } from "next/navigation";
import api from "../../lib/api";
import { User, Repository, GitHubRepository, RepositoryStatus } from "../../types/api";
import Header from "../../components/Header";

type Tab = "my-repos" | "import-github";

export default function Dashboard() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("my-repos");

  // Repositories States
  const [importedRepos, setImportedRepos] = useState<Repository[]>([]);
  const [isReposLoading, setIsReposLoading] = useState(false);

  // GitHub Discover States
  const [githubRepos, setGithubRepos] = useState<GitHubRepository[]>([]);
  const [githubSearch, setGithubSearch] = useState("");
  const [githubFilter, setGithubFilter] = useState<"all" | "public" | "private">("all");
  const [isGithubLoading, setIsGithubLoading] = useState(false);
  const [githubPage, setGithubPage] = useState(1);
  const [hasNextGithubPage, setHasNextGithubPage] = useState(false);

  // Indexing status mapping (job_id -> status/info)
  const [activeJobs, setActiveJobs] = useState<Record<string, { repoId: string; status: string; error?: string }>>({});

  // Polling intervals
  const pollingRef = useRef<NodeJS.Timeout | null>(null);

  // Auth Guard
  useEffect(() => {
    const fetchProfile = async () => {
      const token = localStorage.getItem("codedna_jwt");
      if (!token) {
        router.push("/");
        return;
      }
      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
        // Load initial imported repos
        fetchImportedRepositories();
      } catch (err) {
        console.error("Auth check failed, logging out", err);
        localStorage.removeItem("codedna_jwt");
        router.push("/");
      } finally {
        setIsLoading(false);
      }
    };

    fetchProfile();
  }, [router]);

  // Fetch imported repos from database
  const fetchImportedRepositories = async () => {
    setIsReposLoading(true);
    try {
      const repos = await api.getImportedRepositories();
      setImportedRepos(Array.isArray(repos) ? repos : []);
    } catch (err: any) {
      console.error("Failed to load imported repos", err);
    } finally {
      setIsReposLoading(false);
    }
  };

  // Poll imported repos to update statuses live (cloning, indexing)
  useEffect(() => {
    const startPolling = () => {
      if (pollingRef.current) clearInterval(pollingRef.current);

      pollingRef.current = setInterval(async () => {
        const hasActiveJobs = importedRepos.some(
          (r) => r.status === "cloning" || r.status === "indexing" || r.status === "registered" && activeJobs[r.id]
        );

        if (hasActiveJobs || Object.keys(activeJobs).length > 0) {
          try {
            const repos = await api.getImportedRepositories();
            setImportedRepos(Array.isArray(repos) ? repos : []);

            for (const [jobId, jobInfo] of Object.entries(activeJobs)) {
              if (jobInfo.status === "queued" || jobInfo.status === "running") {
                try {
                  const job = await api.getJobStatus(jobId);
                  setActiveJobs((prev) => ({
                    ...prev,
                    [jobId]: {
                      repoId: jobInfo.repoId,
                      status: job.status,
                      error: job.error_message || undefined,
                    },
                  }));

                  if (job.status === "completed" || job.status === "failed") {
                    setTimeout(() => {
                      setActiveJobs((prev) => {
                        const copy = { ...prev };
                        delete copy[jobId];
                        return copy;
                      });
                    }, 5000);
                  }
                } catch (e) {
                  console.error("Job status check failed for " + jobId, e);
                }
              }
            }
          } catch (err) {
            console.error("Polling error", err);
          }
        }
      }, 2000);
    };

    if (importedRepos.length > 0) {
      startPolling();
    }

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [importedRepos, activeJobs]);

  // Fetch repositories from user GitHub profile
  const fetchGithubRepositories = async (page = 1) => {
    setIsGithubLoading(true);
    try {
      const response = await api.getGithubRepositories({
        visibility: githubFilter,
        page,
        per_page: 15,
      });
      if (page === 1) {
        setGithubRepos(response.repositories || []);
      } else {
        setGithubRepos((prev) => [...prev, ...(response.repositories || [])]);
      }
      setGithubPage(page);
      setHasNextGithubPage(response.has_next_page);
    } catch (err: any) {
      console.error("Failed to load GitHub repos", err);
    } finally {
      setIsGithubLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === "import-github") {
      fetchGithubRepositories(1);
    }
  }, [activeTab, githubFilter]);

  const handleLogout = () => {
    localStorage.removeItem("codedna_jwt");
    setUser(null);
    router.push("/");
  };

  const handleImportRepository = async (repo: GitHubRepository) => {
    try {
      await api.importRepository({ full_name: repo.full_name });
      alert(`Imported ${repo.full_name} successfully!`);
      fetchImportedRepositories();
      setActiveTab("my-repos");
    } catch (err: any) {
      alert(err.message || `Failed to import ${repo.full_name}`);
    }
  };

  const handleStartIndexing = async (repoId: string) => {
    try {
      const response = await api.startIndexing(repoId);
      setActiveJobs((prev) => ({
        ...prev,
        [response.job_id]: {
          repoId: repoId,
          status: response.status,
        },
      }));
      setImportedRepos((prev) =>
        prev.map((r) => (r.id === repoId ? { ...r, status: "indexing" as RepositoryStatus } : r))
      );
    } catch (err: any) {
      alert(err.message || "Failed to start indexing.");
    }
  };

  const filteredGithubRepos = githubRepos.filter((repo) =>
    repo.name.toLowerCase().includes(githubSearch.toLowerCase()) ||
    repo.full_name.toLowerCase().includes(githubSearch.toLowerCase())
  );

  const getStatusBadgeClass = (status: RepositoryStatus) => {
    switch (status) {
      case "ready":
        return "bg-emerald-50 text-emerald-700 border border-emerald-200/50";
      case "indexing":
      case "cloning":
        return "bg-amber-50 text-amber-700 border border-amber-200/50 animate-pulse";
      case "registered":
        return "bg-mist-gray text-slate-gray border border-ink-black/[0.05]";
      case "failed":
        return "bg-red-50 text-red-700 border border-red-200/50";
      default:
        return "bg-mist-gray text-ink-black";
    }
  };

  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin" />
          <span className="text-[15px] text-slate-gray">Loading profile...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-paper-white text-ink-black font-sohne">
      <Header user={user} onLogout={handleLogout} />

      <main className="flex-1 w-full max-w-[1200px] mx-auto px-[24px] py-[48px]">
        <div className="mb-[40px] text-left border-b border-mist-gray pb-[32px]">
          <span className="text-[14px] font-w400 text-ash-gray uppercase tracking-wider block mb-[8px]">
            Control Console
          </span>
          <h1 className="text-[44px] font-signifier font-w400 leading-tight text-ink-black tracking-[-0.66px]">
            Welcome back, <span className="italic">{user?.name || user?.username}</span>
          </h1>
          <p className="text-[17px] font-w400 text-slate-gray mt-[8px] max-w-xl">
            Register new GitHub codebases, monitor background indexing cycles, or dive into fully inventoried repository catalogs.
          </p>
        </div>

        <div className="flex items-center gap-[8px] mb-[32px] border-b border-mist-gray pb-[16px] z-10 relative">
          <button
            onClick={() => setActiveTab("my-repos")}
            className={`h-[36px] px-[16px] rounded-buttons text-[15px] font-sohne transition-all ${
              activeTab === "my-repos"
                ? "bg-ink-black text-paper-white font-w500"
                : "bg-transparent text-slate-gray hover:text-ink-black font-w400"
            }`}
          >
            My Codebases ({importedRepos.length})
          </button>
          <button
            onClick={() => setActiveTab("import-github")}
            className={`h-[36px] px-[16px] rounded-buttons text-[15px] font-sohne transition-all ${
              activeTab === "import-github"
                ? "bg-ink-black text-paper-white font-w500"
                : "bg-transparent text-slate-gray hover:text-ink-black font-w400"
            }`}
          >
            Import from GitHub
          </button>
        </div>

        {activeTab === "my-repos" && (
          <div className="space-y-[24px]">
            {isReposLoading && importedRepos.length === 0 ? (
              <div className="py-[80px] text-center text-slate-gray">Loading codebases...</div>
            ) : importedRepos.length === 0 ? (
              <div className="border border-dashed border-ink-black/[0.08] rounded-cards p-[64px] text-center max-w-2xl mx-auto my-[48px] bg-fog-white">
                <span className="text-3xl block mb-[16px]">🧬</span>
                <h3 className="text-[20px] font-sohne font-w500 text-ink-black mb-[8px]">
                  No Codebases Registered
                </h3>
                <p className="text-[15px] text-slate-gray max-w-md mx-auto mb-[24px]">
                  Before you can audit structures or search code, you need to import repository scopes from your authorized GitHub profile.
                </p>
                <button
                  onClick={() => setActiveTab("import-github")}
                  className="h-[40px] px-[20px] rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-95 transition-all text-[15px] font-w500 inline-flex items-center justify-center cursor-pointer"
                >
                  Import Repository
                </button>
              </div>
            ) : (
              <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-[24px] overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="border-b border-mist-gray pb-[12px] text-ash-gray text-[12px] uppercase font-w500 tracking-wider">
                        <th className="py-[12px] px-[16px] font-w500">Repository Name</th>
                        <th className="py-[12px] px-[16px] font-w500">Status</th>
                        <th className="py-[12px] px-[16px] font-w500">Default Branch</th>
                        <th className="py-[12px] px-[16px] font-w500">Scope</th>
                        <th className="py-[12px] px-[16px] font-w500 text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-mist-gray">
                      {importedRepos.map((repo) => {
                        const associatedJob = Object.values(activeJobs).find((j) => j.repoId === repo.id);
                        const jobStatus = associatedJob?.status || null;
                        const jobError = associatedJob?.error || null;

                        return (
                          <tr key={repo.id} className="hover:bg-fog-white transition-colors duration-150">
                            <td className="py-[16px] px-[16px]">
                              <div className="flex flex-col">
                                <span className="text-[16px] font-sohne font-w500 text-ink-black">
                                  {repo.name}
                                </span>
                                <span className="text-[13px] text-slate-gray font-w400 mt-[2px]">
                                  {repo.full_name}
                                </span>
                              </div>
                            </td>
                            <td className="py-[16px] px-[16px]">
                              <div className="flex items-center gap-[8px]">
                                <span className={`px-[10px] py-[4px] text-[11px] font-w500 rounded-buttons uppercase tracking-wider ${getStatusBadgeClass(repo.status)}`}>
                                  {repo.status}
                                </span>

                                {(repo.status === "indexing" || repo.status === "cloning" || jobStatus === "queued" || jobStatus === "running") && (
                                  <span className="text-[12px] text-amber-600 font-w400 italic">
                                    ({jobStatus || "indexing"}...)
                                  </span>
                                )}
                              </div>
                              {jobError && (
                                <div className="text-[11px] text-red-500 mt-[4px] max-w-[200px] truncate">
                                  {jobError}
                                </div>
                              )}
                            </td>
                            <td className="py-[16px] px-[16px] text-[15px] text-slate-gray">
                              <code>{repo.default_branch}</code>
                            </td>
                            <td className="py-[16px] px-[16px] text-[15px] text-slate-gray capitalize">
                              {repo.visibility}
                            </td>
                            <td className="py-[16px] px-[16px] text-right">
                              <div className="flex items-center justify-end gap-[12px]">
                                {repo.status === "registered" && (
                                  <button
                                    onClick={() => handleStartIndexing(repo.id)}
                                    className="h-[36px] px-[16px] rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 text-[14px] font-w500 active:scale-95 transition-all flex items-center justify-center cursor-pointer"
                                  >
                                    Start Indexing
                                  </button>
                                )}

                                {(repo.status === "indexing" || repo.status === "cloning") && (
                                  <button
                                    disabled
                                    className="h-[36px] px-[16px] rounded-buttons bg-mist-gray text-slate-gray text-[14px] font-w400 cursor-not-allowed flex items-center justify-center gap-[8px]"
                                  >
                                    <span className="w-[14px] h-[14px] rounded-full border border-slate-gray border-t-transparent animate-spin" />
                                    Indexing
                                  </button>
                                )}

                                {repo.status === "ready" && (
                                  <button
                                    onClick={() => router.push(`/repositories/${repo.id}`)}
                                    className="h-[36px] px-[16px] rounded-buttons bg-transparent text-ink-black border border-ink-black hover:bg-mist-gray text-[14px] font-w500 active:scale-95 transition-all flex items-center justify-center cursor-pointer"
                                  >
                                    Explore Catalog →
                                  </button>
                                )}

                                {repo.status === "failed" && (
                                  <button
                                    onClick={() => handleStartIndexing(repo.id)}
                                    className="h-[36px] px-[16px] rounded-buttons bg-red-50 text-red-700 hover:bg-red-100 text-[14px] font-w500 active:scale-95 transition-all flex items-center justify-center cursor-pointer"
                                  >
                                    Retry Index
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === "import-github" && (
          <div className="space-y-6">
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 bg-fog-white border border-ink-black/[0.05] p-4 rounded-cards">
              <div className="relative flex-1">
                <input
                  type="text"
                  placeholder="Filter GitHub repositories..."
                  value={githubSearch}
                  onChange={(e) => setGithubSearch(e.target.value)}
                  className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-4 py-2.5 text-[14px] font-sohne text-ink-black placeholder-smoke-gray focus:outline-none focus:ring-1 focus:ring-ink-black transition-all"
                />
              </div>

              <div className="flex items-center gap-1 bg-mist-gray p-1 rounded-buttons self-start md:self-auto">
                <button
                  onClick={() => setGithubFilter("all")}
                  className={`px-3 py-1.5 rounded-buttons text-xs font-sohne font-w500 transition-all ${
                    githubFilter === "all" ? "bg-paper-white text-ink-black shadow-sm" : "text-slate-gray hover:text-ink-black"
                  }`}
                >
                  All
                </button>
                <button
                  onClick={() => setGithubFilter("public")}
                  className={`px-3 py-1.5 rounded-buttons text-xs font-sohne font-w500 transition-all ${
                    githubFilter === "public" ? "bg-paper-white text-ink-black shadow-sm" : "text-slate-gray hover:text-ink-black"
                  }`}
                >
                  Public
                </button>
                <button
                  onClick={() => setGithubFilter("private")}
                  className={`px-3 py-1.5 rounded-buttons text-xs font-sohne font-w500 transition-all ${
                    githubFilter === "private" ? "bg-paper-white text-ink-black shadow-sm" : "text-slate-gray hover:text-ink-black"
                  }`}
                >
                  Private
                </button>
              </div>
            </div>

            {isGithubLoading && githubRepos.length === 0 ? (
              <div className="py-20 text-center text-slate-gray">Searching GitHub profile...</div>
            ) : filteredGithubRepos.length === 0 ? (
              <div className="text-center py-20 text-slate-gray border border-dashed border-ink-black/[0.08] rounded-cards bg-fog-white">
                No matching repositories found on your GitHub profile.
              </div>
            ) : (
              <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-6">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {filteredGithubRepos.map((repo) => {
                    const isAlreadyImported = importedRepos.some((r) => r.github_id === repo.github_id || r.full_name === repo.full_name);

                    return (
                      <div
                        key={repo.github_id}
                        className="border border-mist-gray p-4 rounded-smallcards hover:bg-fog-white transition-all flex items-center justify-between gap-4"
                      >
                        <div className="flex flex-col truncate pr-2">
                          <span className="text-[16px] font-sohne font-w500 text-ink-black truncate">
                            {repo.name}
                          </span>
                          <span className="text-[13px] text-slate-gray truncate mt-0.5">
                            {repo.full_name}
                          </span>
                          <div className="flex items-center gap-3 mt-2 text-[12px] text-ash-gray">
                            <span className="capitalize">{repo.visibility}</span>
                            <span>&bull;</span>
                            <span>{repo.default_branch}</span>
                          </div>
                        </div>

                        <div className="flex-shrink-0">
                          {isAlreadyImported ? (
                            <button
                              disabled
                              className="h-9 px-4 rounded-buttons bg-mist-gray text-slate-gray text-[13px] font-w400 cursor-not-allowed flex items-center justify-center"
                            >
                              Imported
                            </button>
                          ) : (
                            <button
                              onClick={() => handleImportRepository(repo)}
                              className="h-9 px-4 rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 text-[13px] font-w500 active:scale-95 transition-all flex items-center justify-center cursor-pointer"
                            >
                              Import
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>

                {hasNextGithubPage && (
                  <div className="mt-8 flex justify-center border-t border-mist-gray pt-6">
                    <button
                      onClick={() => fetchGithubRepositories(githubPage + 1)}
                      className="h-10 px-6 rounded-buttons bg-transparent text-ink-black border border-ink-black hover:bg-mist-gray text-[14px] font-w500 active:scale-95 transition-all flex items-center justify-center cursor-pointer"
                    >
                      {isGithubLoading ? "Loading..." : "Load More Repositories"}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
