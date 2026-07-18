"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import api from "../../../lib/api";
import { User, Repository, RepositoryStats, RepositoryFile } from "../../../types/api";
import Header from "../../../components/Header";

interface PageProps {
  params: Promise<{ id: string }> | { id: string };
}

export default function RepositoryDetails({ params }: PageProps) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [stats, setStats] = useState<RepositoryStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Files Table State
  const [files, setFiles] = useState<RepositoryFile[]>([]);
  const [filesPage, setFilesPage] = useState(1);
  const [filesPageSize] = useState(50);
  const [hasNextFilesPage, setHasNextFilesPage] = useState(false);
  const [isFilesLoading, setIsFilesLoading] = useState(false);

  // Search & Filter State
  const [searchPrefix, setSearchPrefix] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState("");
  const [languagesList, setLanguagesList] = useState<string[]>([]);

  // Resolve params Promise for compatibility
  useEffect(() => {
    if (params && typeof (params as any).then === "function") {
      Promise.resolve(params).then((p) => setId(p.id));
    } else if (params) {
      setId((params as any).id);
    }
  }, [params]);

  // Auth guard & Load Repository Metadata
  useEffect(() => {
    if (!id) return;

    const loadData = async () => {
      const token = localStorage.getItem("codedna_jwt");
      if (!token) {
        router.push("/");
        return;
      }

      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);

        const repository = await api.getRepository(id);
        setRepo(repository);

        if (repository.status === "ready") {
          const repositoryStats = await api.getRepositoryStats(id);
          setStats(repositoryStats);

          if (repositoryStats.languages) {
            setLanguagesList(Object.keys(repositoryStats.languages));
          }
        }
      } catch (err: any) {
        console.error("Failed to load repository details", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [id, router]);

  // Load files when filters or page change
  useEffect(() => {
    if (!id || !repo || repo.status !== "ready") return;

    const fetchFiles = async () => {
      setIsFilesLoading(true);
      try {
        const filesResponse = await api.getRepositoryFiles(id, {
          page: filesPage,
          page_size: filesPageSize,
          language: selectedLanguage || undefined,
          path_prefix: searchPrefix || undefined,
        });

        setFiles(filesResponse.files || []);
        setHasNextFilesPage(filesResponse.has_next_page);
      } catch (err) {
        console.error("Failed to load repository files", err);
      } finally {
        setIsFilesLoading(false);
      }
    };

    fetchFiles();
  }, [id, repo, filesPage, selectedLanguage, searchPrefix, filesPageSize]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleLogout = () => {
    localStorage.removeItem("codedna_jwt");
    setUser(null);
    router.push("/");
  };

  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin" />
          <span className="text-[15px] text-slate-gray">Analyzing codebase...</span>
        </div>
      </div>
    );
  }

  if (!repo) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <h3 className="text-xl font-w500 text-ink-black mb-2">Repository Not Found</h3>
        <p className="text-slate-gray mb-6">This repository is not registered or you do not have permission.</p>
        <Link href="/dashboard" className="text-ink-black hover:underline">
          Back to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-paper-white text-ink-black font-sohne">
      <Header user={user} onLogout={handleLogout} />

      <main className="flex-1 w-full max-w-[1200px] mx-auto px-[24px] py-[32px]">
        <div className="mb-[24px] flex items-center justify-between">
          <Link
            href="/dashboard"
            className="text-[15px] font-sohne text-slate-gray hover:text-ink-black transition-colors inline-flex items-center gap-[6px]"
          >
            ← Back to Dashboard
          </Link>
          <span className="text-xs font-mono text-ash-gray">
            ID: {repo.id}
          </span>
        </div>

        <div className="border-b border-mist-gray pb-[24px] mb-[32px] text-left">
          <div className="flex flex-wrap items-center gap-[12px] mb-[8px]">
            <h1 className="text-[32px] md:text-[44px] font-signifier font-w400 leading-tight text-ink-black tracking-[-0.66px]">
              {repo.name}
            </h1>
            <span className="px-[10px] py-[4px] text-[11px] font-w500 rounded-buttons uppercase tracking-wider bg-emerald-50 text-emerald-700 border border-emerald-200/50">
              {repo.status}
            </span>
            <span className="px-[10px] py-[4px] text-[11px] font-w500 rounded-buttons uppercase tracking-wider bg-mist-gray text-slate-gray border border-ink-black/[0.05]">
              {repo.visibility}
            </span>
          </div>
          <p className="text-[17px] font-w400 text-slate-gray">
            Owner: <span className="font-w500 text-ink-black">{repo.full_name.split("/")[0]}</span> &bull; Default Branch: <code>{repo.default_branch}</code>
          </p>
        </div>

        {repo.status !== "ready" ? (
          <div className="border border-dashed border-ink-black/[0.08] rounded-cards p-[64px] text-center max-w-2xl mx-auto my-[48px] bg-fog-white">
            <span className="text-3xl block mb-[16px]">🗂️</span>
            <h3 className="text-[20px] font-sohne font-w500 text-ink-black mb-[8px]">
              Codebase Indexing Required
            </h3>
            <p className="text-[15px] text-slate-gray max-w-md mx-auto mb-[24px]">
              This repository is currently in the <strong>{repo.status}</strong> state. You must run or wait for the indexing background process to finish before viewing the file registry or statistics.
            </p>
            <Link
              href="/dashboard"
              className="h-[40px] px-[20px] rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-95 transition-all text-[15px] font-w500 inline-flex items-center justify-center cursor-pointer"
            >
              Start indexing from dashboard
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-[32px] items-start">
            <div className="lg:col-span-4 space-y-[24px]">
              <div className="bg-fog-white border border-ink-black/[0.05] shadow-subtle p-[20px] rounded-cards text-left">
                <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider">
                  Telemetry Summary
                </span>
                
                {stats && (
                  <div className="mt-[16px] space-y-[16px]">
                    <div>
                      <span className="text-[14px] text-slate-gray font-w400">Total Scan Size</span>
                      <h3 className="text-[26px] font-sohne font-w500 text-ink-black tracking-tight mt-[2px]">
                        {formatBytes(stats.total_size_bytes)}
                      </h3>
                    </div>
                    
                    <div className="grid grid-cols-2 gap-[16px] border-t border-mist-gray pt-[16px]">
                      <div>
                        <span className="text-[13px] text-slate-gray font-w400">Source Files</span>
                        <p className="text-[18px] font-sohne font-w500 text-ink-black mt-[2px]">
                          {stats.source_files}
                        </p>
                      </div>
                      <div>
                        <span className="text-[13px] text-slate-gray font-w400">Binary Assets</span>
                        <p className="text-[18px] font-sohne font-w500 text-ink-black mt-[2px]">
                          {stats.binary_files}
                        </p>
                      </div>
                    </div>

                    <div className="border-t border-mist-gray pt-[16px] text-[12px] text-ash-gray">
                      Last Scan: {new Date(stats.last_scan_at).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              <div className="bg-blush-peach border border-sienna-brown/15 p-[20px] rounded-cards text-left text-sienna-brown">
                <span className="text-[12px] font-sohne font-w500 text-sienna-brown/70 uppercase tracking-wider">
                  Language Signature
                </span>

                {stats?.languages && (
                  <div className="mt-[16px] space-y-[12px]">
                    {Object.entries(stats.languages)
                      .sort((a, b) => b[1] - a[1])
                      .map(([lang, count]) => {
                        const total = Object.values(stats.languages).reduce((sum, val) => sum + val, 0);
                        const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0";

                        return (
                          <div key={lang} className="text-[14px] font-sohne">
                            <div className="flex items-center justify-between font-w500">
                              <span>{lang}</span>
                              <span>{pct}% ({count})</span>
                            </div>
                            <div className="w-full bg-sienna-brown/10 h-[6px] rounded-full mt-[6px] overflow-hidden">
                              <div
                                className="bg-sienna-brown h-full rounded-full"
                                style={{ width: `${pct}%` }}
                              />
                            </div>
                          </div>
                        );
                      })}
                  </div>
                )}
              </div>
            </div>

            <div className="lg:col-span-8 space-y-[24px]">
              <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-[16px] bg-fog-white border border-ink-black/[0.05] p-[16px] rounded-cards">
                <div className="relative flex-1">
                  <input
                    type="text"
                    placeholder="Search folder/file prefix (e.g. src/)..."
                    value={searchPrefix}
                    onChange={(e) => {
                      setSearchPrefix(e.target.value);
                      setFilesPage(1);
                    }}
                    className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black placeholder-smoke-gray focus:outline-none focus:ring-1 focus:ring-ink-black transition-all"
                  />
                </div>

                <div className="flex-shrink-0">
                  <select
                    value={selectedLanguage}
                    onChange={(e) => {
                      setSelectedLanguage(e.target.value);
                      setFilesPage(1);
                    }}
                    className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all cursor-pointer"
                  >
                    <option value="">All Languages</option>
                    {languagesList.map((lang) => (
                      <option key={lang} value={lang}>
                        {lang}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-[20px]">
                <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block mb-[16px]">
                  Discovered File Index
                </span>

                {isFilesLoading && files.length === 0 ? (
                  <div className="py-[80px] text-center text-slate-gray">Cataloging files...</div>
                ) : files.length === 0 ? (
                  <div className="py-[80px] text-center text-slate-gray">No files match your filters.</div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left border-collapse text-[14px] font-sohne">
                      <thead>
                        <tr className="border-b border-mist-gray pb-[8px] text-ash-gray font-w500 tracking-wider">
                          <th className="py-[8px] px-[8px]">Path</th>
                          <th className="py-[8px] px-[8px]">Language</th>
                          <th className="py-[8px] px-[8px]">Size</th>
                          <th className="py-[8px] px-[8px] text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-mist-gray">
                        {files.map((file) => (
                          <tr key={file.id} className="hover:bg-fog-white transition-colors">
                            <td className="py-[12px] px-[8px] font-mono text-[12px] text-ink-black truncate max-w-[280px]">
                              {file.path}
                            </td>
                            <td className="py-[12px] px-[8px]">
                              {file.is_binary ? (
                                <span className="text-[12px] text-smoke-gray uppercase tracking-wider">Binary</span>
                              ) : (
                                file.language || "Unknown"
                              )}
                            </td>
                            <td className="py-[12px] px-[8px] text-slate-gray">
                              {formatBytes(file.size_bytes)}
                            </td>
                            <td className="py-[12px] px-[8px] text-right">
                              <button
                                onClick={() => alert(`File Details:\nPath: ${file.path}\nSize: ${formatBytes(file.size_bytes)}\nSHA-256: ${file.sha256}`)}
                                className="text-[13px] text-slate-gray hover:text-ink-black transition-colors"
                              >
                                View Meta
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                <div className="flex items-center justify-between border-t border-mist-gray mt-[24px] pt-[16px] text-[13px] text-slate-gray">
                  <span>Showing page {filesPage}</span>
                  
                  <div className="flex items-center gap-[8px]">
                    <button
                      disabled={filesPage === 1}
                      onClick={() => setFilesPage((p) => Math.max(1, p - 1))}
                      className="h-[32px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-50 disabled:cursor-not-allowed transition-all text-[13px]"
                    >
                      Previous
                    </button>
                    <button
                      disabled={!hasNextFilesPage}
                      onClick={() => setFilesPage((p) => p + 1)}
                      className="h-[32px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-50 disabled:cursor-not-allowed transition-all text-[13px]"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {repo.status === "ready" && (
          <div className="mt-[64px] border-t border-mist-gray pt-[48px] flex flex-col items-center">
            <h4 className="text-[16px] font-sohne font-w500 text-ink-black mb-[16px]">
              Query Codebase Structure
            </h4>
            
            <div className="bg-paper-white rounded-inputs border border-ink-black/[0.08] shadow-subtle-2 p-[14px] w-full max-w-xl text-left">
              <div className="flex items-center gap-[12px]">
                <div className="flex items-center gap-[6px] text-ash-gray">
                  <button className="w-[32px] h-[32px] rounded-full flex items-center justify-center hover:bg-mist-gray transition-colors text-[15px]">
                    @
                  </button>
                  <button className="w-[32px] h-[32px] rounded-full flex items-center justify-center hover:bg-mist-gray transition-colors text-[15px]">
                    ⓘ
                  </button>
                </div>

                <input
                  type="text"
                  placeholder={`Ask anything about ${repo.name}...`}
                  className="flex-1 bg-transparent border-none outline-none text-[15px] font-sohne text-ink-black placeholder-smoke-gray"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      alert("Software Intelligence querying is planned for the next milestone. Stay tuned!");
                    }
                  }}
                />

                <button
                  onClick={() => alert("Software Intelligence querying is planned for the next milestone. Stay tuned!")}
                  className="w-[40px] h-[40px] rounded-full bg-ink-black text-paper-white flex items-center justify-center hover:bg-ink-black/90 active:scale-95 transition-all"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth="2.5"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
