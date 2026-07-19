"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import api from "../../../lib/api";
import {
  User,
  Repository,
  RepositoryStats,
  RepositoryFile,
  RepositoryFileParseRead,
  RepositoryKnowledgeItemRead,
  RepositoryChunkRead,
  RepositoryHistoryArtifact,
} from "../../../types/api";
import Header from "../../../components/Header";

interface PageProps {
  params: Promise<{ id: string }> | { id: string };
}

type TabType = "overview" | "files" | "parse" | "knowledge" | "history" | "chunks";

function RepositoryDetailsContent({ params }: PageProps) {
  const router = useRouter();
  const [id, setId] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [stats, setStats] = useState<RepositoryStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabType>("overview");

  // --- Tab 1: Overview Languages & Stats ---
  const [languagesList, setLanguagesList] = useState<string[]>([]);

  // --- Tab 2: Files Registry States ---
  const [files, setFiles] = useState<RepositoryFile[]>([]);
  const [filesPage, setFilesPage] = useState(1);
  const [filesPageSize] = useState(30);
  const [hasNextFilesPage, setHasNextFilesPage] = useState(false);
  const [isFilesLoading, setIsFilesLoading] = useState(false);
  const [filesSearch, setFilesSearch] = useState("");
  const [filesLanguageFilter, setFilesLanguageFilter] = useState("");

  // --- Tab 3: Parse Results States ---
  const [parseResults, setParseResults] = useState<RepositoryFileParseRead[]>([]);
  const [parsePage, setParsePage] = useState(1);
  const [parsePageSize] = useState(30);
  const [hasNextParsePage, setHasNextParsePage] = useState(false);
  const [isParseLoading, setIsParseLoading] = useState(false);
  const [parseSearch, setParseSearch] = useState("");
  const [parseStatusFilter, setParseStatusFilter] = useState("");
  const [parseLangFilter, setParseLangFilter] = useState("");

  // --- Tab 4: Knowledge Items States ---
  const [knowledgeItems, setKnowledgeItems] = useState<RepositoryKnowledgeItemRead[]>([]);
  const [knowledgePage, setKnowledgePage] = useState(1);
  const [knowledgePageSize] = useState(30);
  const [hasNextKnowledgePage, setHasNextKnowledgePage] = useState(false);
  const [isKnowledgeLoading, setIsKnowledgeLoading] = useState(false);
  const [knowledgeSearch, setKnowledgeSearch] = useState("");
  const [knowledgeSourceFilter, setKnowledgeSourceFilter] = useState("");
  const [knowledgeItemTypeFilter, setKnowledgeItemTypeFilter] = useState("");

  // --- Repository decision history ---
  const [historyArtifacts, setHistoryArtifacts] = useState<RepositoryHistoryArtifact[]>([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(false);
  const [historyTypeFilter, setHistoryTypeFilter] = useState("all");

  // --- Tab 5: Chunks Index States ---
  const [chunks, setChunks] = useState<RepositoryChunkRead[]>([]);
  const [chunksPage, setChunksPage] = useState(1);
  const [chunksPageSize] = useState(20);
  const [hasNextChunksPage, setHasNextChunksPage] = useState(false);
  const [isChunksLoading, setIsChunksLoading] = useState(false);
  const [chunkSourceFilter, setChunkSourceFilter] = useState("");
  const [chunkTypeFilter, setChunkTypeFilter] = useState("");
  const [selectedChunk, setSelectedChunk] = useState<RepositoryChunkRead | null>(null);
  const [isChunkDetailLoading, setIsChunkDetailLoading] = useState(false);

  // Resolve params Promise
  useEffect(() => {
    if (params && typeof (params as any).then === "function") {
      Promise.resolve(params).then((p) => setId(p.id));
    } else if (params) {
      setId((params as any).id);
    }
  }, [params]);

  // Auth guard & Load Main Repository Metadata
  useEffect(() => {
    if (!id) return;

    const loadMetadata = async () => {
      const token = localStorage.getItem("codedna_jwt");
      if (!token) {
        setIsLoading(false);
        router.replace("/");
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
        console.error("Failed to load repository metadata", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadMetadata();
  }, [id, router]);

  // Tab 2: Fetch Files
  useEffect(() => {
    if (!id || !repo || repo.status !== "ready" || activeTab !== "files") return;

    const fetchFiles = async () => {
      setIsFilesLoading(true);
      try {
        const res = await api.getRepositoryFiles(id, {
          page: filesPage,
          page_size: filesPageSize,
          language: filesLanguageFilter || undefined,
          path_prefix: filesSearch || undefined,
        });
        setFiles(res.files || []);
        setHasNextFilesPage(res.has_next_page);
      } catch (err) {
        console.error("Failed to load files", err);
      } finally {
        setIsFilesLoading(false);
      }
    };

    fetchFiles();
  }, [id, repo, activeTab, filesPage, filesLanguageFilter, filesSearch, filesPageSize]);

  // Tab 3: Fetch Parse Results
  useEffect(() => {
    if (!id || !repo || repo.status !== "ready" || activeTab !== "parse") return;

    const fetchParseResults = async () => {
      setIsParseLoading(true);
      try {
        const res = await api.getRepositoryParseResults(id, {
          page: parsePage,
          page_size: parsePageSize,
          status: parseStatusFilter || undefined,
          language: parseLangFilter || undefined,
          path_prefix: parseSearch || undefined,
        });
        setParseResults(res.parse_results || []);
        setHasNextParsePage(res.has_next_page);
      } catch (err) {
        console.error("Failed to load parse results", err);
      } finally {
        setIsParseLoading(false);
      }
    };

    fetchParseResults();
  }, [id, repo, activeTab, parsePage, parseStatusFilter, parseLangFilter, parseSearch, parsePageSize]);

  // Tab 4: Fetch Knowledge Items
  useEffect(() => {
    if (!id || !repo || repo.status !== "ready" || activeTab !== "knowledge") return;

    const fetchKnowledge = async () => {
      setIsKnowledgeLoading(true);
      try {
        const res = await api.getRepositoryKnowledge(id, {
          page: knowledgePage,
          page_size: knowledgePageSize,
          source_type: knowledgeSourceFilter || undefined,
          item_type: knowledgeItemTypeFilter || undefined,
          path_prefix: knowledgeSearch || undefined,
        });
        setKnowledgeItems(res.knowledge_items || []);
        setHasNextKnowledgePage(res.has_next_page);
      } catch (err) {
        console.error("Failed to load knowledge", err);
      } finally {
        setIsKnowledgeLoading(false);
      }
    };

    fetchKnowledge();
  }, [id, repo, activeTab, knowledgePage, knowledgeSourceFilter, knowledgeItemTypeFilter, knowledgeSearch, knowledgePageSize]);

  useEffect(() => {
    if (!id || !repo || repo.status !== "ready" || activeTab !== "history") return;
    const fetchHistory = async () => {
      setIsHistoryLoading(true);
      try {
        const response = await api.getRepositoryHistory(id);
        setHistoryArtifacts(response.artifacts || []);
      } catch (err) {
        console.error("Failed to load repository history", err);
      } finally {
        setIsHistoryLoading(false);
      }
    };
    fetchHistory();
  }, [id, repo, activeTab]);

  // Tab 5: Fetch Chunks
  useEffect(() => {
    if (!id || !repo || repo.status !== "ready" || activeTab !== "chunks") return;

    const fetchChunks = async () => {
      setIsChunksLoading(true);
      try {
        const res = await api.getRepositoryChunks(id, {
          page: chunksPage,
          page_size: chunksPageSize,
          source_type: chunkSourceFilter || undefined,
          chunk_type: chunkTypeFilter || undefined,
        });
        setChunks(res.chunks || []);
        setHasNextChunksPage(res.has_next_page);
      } catch (err) {
        console.error("Failed to load chunks", err);
      } finally {
        setIsChunksLoading(false);
      }
    };

    fetchChunks();
  }, [id, repo, activeTab, chunksPage, chunkSourceFilter, chunkTypeFilter, chunksPageSize]);

  // Fetch full details for a selected chunk
  const handleChunkSelect = async (chunkId: string) => {
    setIsChunkDetailLoading(true);
    try {
      const fullChunk = await api.getChunk(chunkId);
      setSelectedChunk(fullChunk);
    } catch (err) {
      console.error("Failed to load chunk detail", err);
      alert("Failed to fetch chunk detail.");
    } finally {
      setIsChunkDetailLoading(false);
    }
  };

  // Handle deep-linking to specific tab/chunk
  const searchParams = useSearchParams();
  useEffect(() => {
    const urlTab = searchParams.get("tab");
    const urlChunkId = searchParams.get("chunkId");

    if (urlTab === "chunks") {
      setActiveTab("chunks");
      if (urlChunkId) {
        handleChunkSelect(urlChunkId);
      }
    }
  }, [searchParams]);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    alert("Copied the citation ID. Use it to refer to this exact indexed chunk in a question, note, or bug report.");
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
          <span className="text-[15px] text-slate-gray font-w400">Loading codebase...</span>
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
        {/* Persistent Repository Header */}
        <div className="mb-[24px] flex items-center justify-between border-b border-mist-gray/40 pb-[12px]">
          <Link
            href="/dashboard"
            className="text-[15px] text-slate-gray hover:text-ink-black transition-colors inline-flex items-center gap-[6px] cursor-pointer"
          >
            ← Back to Dashboard
          </Link>
          <div className="flex items-center gap-4">
            <Link
              href={`/repositories/${repo.id}/search`}
              className="inline-flex items-center justify-center h-9 px-4 rounded-buttons bg-ink-black text-white hover:bg-ink-black/90 active:scale-95 transition-all text-[13px] font-medium gap-2 cursor-pointer shadow-sm whitespace-nowrap"
            >
              <button className="flex items-center gap-2 bg-[#1F232B] text-white rounded-full px-4 py-2">
                <svg
                  className="w-5 h-5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth="2.5"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                <span>Retrieval Search</span>
              </button>
            </Link>
            <span className="text-[12px] font-mono text-ash-gray">
              ID: {repo.id}
            </span>
          </div>
        </div>

        <div className="border-b border-mist-gray pb-[24px] mb-[24px] text-left flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
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
              {repo.embedding_status && (
                <span className="px-[10px] py-[4px] text-[11px] font-w500 rounded-buttons uppercase tracking-wider bg-blue-50 text-blue-700 border border-blue-200/50">
                  embeddings {repo.embedding_status}{repo.embedding_chunk_count ? ` · ${repo.embedding_chunk_count}` : ""}
                </span>
              )}
            </div>
            <p className="text-[15px] font-w400 text-slate-gray">
              Owner: <span className="font-w500 text-ink-black">{repo.full_name.split("/")[0]}</span> &bull; Default Branch: <code className="font-mono">{repo.default_branch}</code>
            </p>
          </div>
          {repo.last_indexed_at && (
            <div className="text-right text-[13px] text-ash-gray">
              <span>Last Scan Index: {new Date(repo.last_indexed_at).toLocaleString()}</span>
            </div>
          )}
        </div>

        {repo.status !== "ready" ? (
          <div className="border border-dashed border-ink-black/[0.08] rounded-cards p-[64px] text-center max-w-2xl mx-auto my-[48px] bg-fog-white">
            <span className="text-3xl block mb-[16px]">🧬</span>
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
          <>
            {/* Tabs Selector */}
            <div className="flex items-center gap-3 border-b border-mist-gray pb-4 mb-6 z-10 relative overflow-x-auto">
              {(["overview", "files", "parse", "knowledge", "history", "chunks"] as TabType[]).map((tab) => {
                const labels: Record<TabType, string> = {
                  overview: "Overview",
                  files: "Files",
                  parse: "Parse Results",
                  knowledge: "Knowledge Facts",
                  history: "History",
                  chunks: "Chunks",
                };
                return (
                  <button
                    key={tab}
                    onClick={() => setActiveTab(tab)}
                    className={`h-9 px-4 rounded-buttons text-[14px] font-sohne transition-all whitespace-nowrap cursor-pointer ${activeTab === tab
                      ? "bg-ink-black text-paper-white font-medium"
                      : "bg-transparent text-slate-gray hover:text-ink-black font-normal"
                      }`}
                  >
                    {labels[tab]}
                  </button>
                );
              })}
            </div>

            {/* TAB CONTENT: Overview */}
            {activeTab === "overview" && stats && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-[32px] items-start animate-in fade-in duration-200">
                <div className="lg:col-span-5 space-y-[24px]">
                  <div className="bg-fog-white border border-ink-black/[0.05] shadow-subtle p-[24px] rounded-cards text-left">
                    <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block mb-4">
                      Telemetry Details
                    </span>
                    <div className="space-y-[20px]">
                      <div>
                        <span className="text-[13px] text-slate-gray font-w400">Total Scan Size</span>
                        <h3 className="text-[28px] font-sohne font-w500 text-ink-black mt-[2px]">
                          {formatBytes(stats.total_size_bytes)}
                        </h3>
                      </div>
                      <div className="grid grid-cols-2 gap-[16px] border-t border-mist-gray/60 pt-[16px]">
                        <div>
                          <span className="text-[13px] text-slate-gray font-w400">Source Files</span>
                          <p className="text-[20px] font-sohne font-w500 text-ink-black mt-[2px]">
                            {stats.source_files}
                          </p>
                        </div>
                        <div>
                          <span className="text-[13px] text-slate-gray font-w400">Binary Assets</span>
                          <p className="text-[20px] font-sohne font-w500 text-ink-black mt-[2px]">
                            {stats.binary_files}
                          </p>
                        </div>
                      </div>
                      <div className="border-t border-mist-gray/60 pt-[16px]">
                        <span className="text-[13px] text-slate-gray font-w400">Total File Count</span>
                        <p className="text-[20px] font-sohne font-w500 text-ink-black mt-[2px]">
                          {stats.total_files}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="lg:col-span-7 bg-blush-peach border border-sienna-brown/15 p-[24px] rounded-cards text-left text-sienna-brown">
                  <span className="text-[12px] font-sohne font-w500 text-sienna-brown/70 uppercase tracking-wider block mb-4">
                    Language Distributions
                  </span>
                  {stats.languages && (
                    <div className="space-y-[16px]">
                      {Object.entries(stats.languages)
                        .sort((a, b) => b[1] - a[1])
                        .map(([lang, count]) => {
                          const total = Object.values(stats.languages).reduce((sum, val) => sum + val, 0);
                          const pct = total > 0 ? ((count / total) * 100).toFixed(1) : "0";
                          return (
                            <div key={lang} className="text-[14px]">
                              <div className="flex items-center justify-between font-w500">
                                <span>{lang}</span>
                                <span>{pct}% ({count} files)</span>
                              </div>
                              <div className="w-full bg-sienna-brown/10 h-[6px] rounded-full mt-[6px] overflow-hidden">
                                <div
                                  className="bg-sienna-brown h-full rounded-full transition-all duration-500"
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
            )}

            {/* TAB CONTENT: Files */}
            {activeTab === "files" && (
              <div className="space-y-[24px] animate-in fade-in duration-200">
                <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-[16px] bg-fog-white border border-ink-black/[0.05] p-[16px] rounded-cards">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      placeholder="Filter folder or filename (e.g. src/utils)..."
                      value={filesSearch}
                      onChange={(e) => {
                        setFilesSearch(e.target.value);
                        setFilesPage(1);
                      }}
                      className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all"
                    />
                  </div>
                  <div className="flex-shrink-0">
                    <select
                      value={filesLanguageFilter}
                      onChange={(e) => {
                        setFilesLanguageFilter(e.target.value);
                        setFilesPage(1);
                      }}
                      className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all cursor-pointer"
                    >
                      <option value="">All Languages</option>
                      {languagesList.map((lang) => (
                        <option key={lang} value={lang}>{lang}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-[20px]">
                  {isFilesLoading && files.length === 0 ? (
                    <div className="py-[80px] text-center text-slate-gray">Cataloging files...</div>
                  ) : files.length === 0 ? (
                    <div className="py-[80px] text-center text-slate-gray">No files match your filters.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-[14px]">
                        <thead>
                          <tr className="border-b border-mist-gray pb-[8px] text-ash-gray font-w500 tracking-wider">
                            <th className="py-[10px] px-[12px]">Path</th>
                            <th className="py-[10px] px-[12px]">Language</th>
                            <th className="py-[10px] px-[12px]">Size</th>
                            <th className="py-[10px] px-[12px] text-right">Actions</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-mist-gray">
                          {files.map((file) => (
                            <tr key={file.id} className="hover:bg-fog-white transition-colors">
                              <td className="py-[12px] px-[12px] font-mono text-[13px] text-ink-black truncate max-w-[400px]">
                                {file.path}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray">
                                {file.is_binary ? "Binary" : file.language || "Unknown"}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray">
                                {formatBytes(file.size_bytes)}
                              </td>
                              <td className="py-[12px] px-[12px] text-right">
                                <button
                                  onClick={() => alert(`File details:\nPath: ${file.path}\nSize: ${formatBytes(file.size_bytes)}\nType: ${file.is_binary ? "Binary" : file.language || "Unknown"}`)}
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
            )}

            {/* TAB CONTENT: Parse Results */}
            {activeTab === "parse" && (
              <div className="space-y-[24px] animate-in fade-in duration-200">
                <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-[16px] bg-fog-white border border-ink-black/[0.05] p-[16px] rounded-cards">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      placeholder="Search parsed file paths..."
                      value={parseSearch}
                      onChange={(e) => {
                        setParseSearch(e.target.value);
                        setParsePage(1);
                      }}
                      className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all"
                    />
                  </div>
                  <div className="flex flex-wrap items-center gap-[12px]">
                    <select
                      value={parseStatusFilter}
                      onChange={(e) => {
                        setParseStatusFilter(e.target.value);
                        setParsePage(1);
                      }}
                      className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
                    >
                      <option value="">All Statuses</option>
                      <option value="parsed">Parsed</option>
                      <option value="syntax_error">Syntax Errors</option>
                      <option value="unsupported">Unsupported</option>
                      <option value="skipped">Skipped</option>
                      <option value="failed">Failed</option>
                    </select>
                    <select
                      value={parseLangFilter}
                      onChange={(e) => {
                        setParseLangFilter(e.target.value);
                        setParsePage(1);
                      }}
                      className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
                    >
                      <option value="">All Languages</option>
                      {languagesList.map((lang) => (
                        <option key={lang} value={lang}>{lang}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-[20px]">
                  {isParseLoading && parseResults.length === 0 ? (
                    <div className="py-[80px] text-center text-slate-gray">Auditing parse status...</div>
                  ) : parseResults.length === 0 ? (
                    <div className="py-[80px] text-center text-slate-gray">No parse results match your filters.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-[14px]">
                        <thead>
                          <tr className="border-b border-mist-gray pb-[8px] text-ash-gray font-w500 tracking-wider">
                            <th className="py-[10px] px-[12px]">File Path</th>
                            <th className="py-[10px] px-[12px]">Language</th>
                            <th className="py-[10px] px-[12px]">Status</th>
                            <th className="py-[10px] px-[12px]">Symbols</th>
                            <th className="py-[10px] px-[12px]">Imports</th>
                            <th className="py-[10px] px-[12px] text-right">Details</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-mist-gray">
                          {parseResults.map((result) => (
                            <tr key={result.id} className="hover:bg-fog-white transition-colors">
                              <td className="py-[12px] px-[12px] font-mono text-[13px] text-ink-black truncate max-w-[320px]">
                                {result.path}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray">
                                {result.language || "N/A"}
                              </td>
                              <td className="py-[12px] px-[12px]">
                                <span className={`px-2 py-0.5 text-[11px] font-medium uppercase tracking-wider rounded-buttons ${result.status === "parsed"
                                  ? "bg-emerald-50 text-emerald-700 border border-emerald-100"
                                  : result.status === "syntax_error" || result.status === "failed"
                                    ? "bg-red-50 text-red-700 border border-red-100"
                                    : "bg-mist-gray text-slate-gray"
                                  }`}>
                                  {result.status}
                                </span>
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray">
                                {result.symbol_count}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray">
                                {result.import_count}
                              </td>
                              <td className="py-[12px] px-[12px] text-right">
                                <button
                                  onClick={() => alert(`Parse Details:\nParser: ${result.parser || "None"}\nErrors: ${result.error_count}\nMessage: ${result.error_message || "None"}\nSymbols: ${result.symbols.map(s => s.name).join(", ") || "None"}`)}
                                  className="text-[13px] text-slate-gray hover:text-ink-black transition-colors"
                                >
                                  View Log
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="flex items-center justify-between border-t border-mist-gray mt-[24px] pt-[16px] text-[13px] text-slate-gray">
                    <span>Showing page {parsePage}</span>
                    <div className="flex items-center gap-[8px]">
                      <button
                        disabled={parsePage === 1}
                        onClick={() => setParsePage((p) => Math.max(1, p - 1))}
                        className="h-[32px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-50 disabled:cursor-not-allowed transition-all text-[13px]"
                      >
                        Previous
                      </button>
                      <button
                        disabled={!hasNextParsePage}
                        onClick={() => setParsePage((p) => p + 1)}
                        className="h-[32px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-50 disabled:cursor-not-allowed transition-all text-[13px]"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB CONTENT: Knowledge facts */}
            {activeTab === "knowledge" && (
              <div className="space-y-[24px] animate-in fade-in duration-200">
                <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-[16px] bg-fog-white border border-ink-black/[0.05] p-[16px] rounded-cards">
                  <div className="relative flex-1">
                    <input
                      type="text"
                      placeholder="Search knowledge file path prefixes..."
                      value={knowledgeSearch}
                      onChange={(e) => {
                        setKnowledgeSearch(e.target.value);
                        setKnowledgePage(1);
                      }}
                      className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all"
                    />
                  </div>
                  <div className="flex flex-wrap items-center gap-[12px]">
                    <select
                      value={knowledgeSourceFilter}
                      onChange={(e) => {
                        setKnowledgeSourceFilter(e.target.value);
                        setKnowledgePage(1);
                      }}
                      className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[16px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
                    >
                      <option value="">All Sources</option>
                      <option value="source_code">Source Code</option>
                      <option value="documentation">Documentation</option>
                      <option value="database_schema">Database Schema</option>
                      <option value="configuration">Configuration</option>
                    </select>
                    <input
                      type="text"
                      placeholder="Item type (e.g. prisma_model)..."
                      value={knowledgeItemTypeFilter}
                      onChange={(e) => {
                        setKnowledgeItemTypeFilter(e.target.value);
                        setKnowledgePage(1);
                      }}
                      className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[12px] py-[8px] text-[14px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black"
                    />
                  </div>
                </div>

                <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-[20px]">
                  {isKnowledgeLoading && knowledgeItems.length === 0 ? (
                    <div className="py-[80px] text-center text-slate-gray">Extracting architecture facts...</div>
                  ) : knowledgeItems.length === 0 ? (
                    <div className="py-[80px] text-center text-slate-gray">No knowledge items match your filters.</div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-[14px]">
                        <thead>
                          <tr className="border-b border-mist-gray pb-[8px] text-ash-gray font-w500 tracking-wider">
                            <th className="py-[10px] px-[12px]">Name</th>
                            <th className="py-[10px] px-[12px]">Source Type</th>
                            <th className="py-[10px] px-[12px]">Item Type</th>
                            <th className="py-[10px] px-[12px]">Path</th>
                            <th className="py-[10px] px-[12px]">Extractor</th>
                            <th className="py-[10px] px-[12px] text-right">Payload</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-mist-gray">
                          {knowledgeItems.map((item) => (
                            <tr key={item.id} className="hover:bg-fog-white transition-colors">
                              <td className="py-[12px] px-[12px] font-w500 text-ink-black truncate max-w-[200px]">
                                {item.name || "Unnamed"}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray capitalize">
                                {item.source_type.replace("_", " ")}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray font-mono text-[12px]">
                                {item.item_type}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray font-mono text-[12px] truncate max-w-[220px]">
                                {item.path || "N/A"}
                              </td>
                              <td className="py-[12px] px-[12px] text-slate-gray text-xs">
                                {item.extractor}
                              </td>
                              <td className="py-[12px] px-[12px] text-right">
                                <button
                                  onClick={() => alert(`Data Payload:\n${JSON.stringify(item.data, null, 2)}`)}
                                  className="text-[13px] text-slate-gray hover:text-ink-black transition-colors"
                                >
                                  Inspect JSON
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <div className="flex items-center justify-between border-t border-mist-gray mt-[24px] pt-[16px] text-[13px] text-slate-gray">
                    <span>Showing page {knowledgePage}</span>
                    <div className="flex items-center gap-[8px]">
                      <button
                        disabled={knowledgePage === 1}
                        onClick={() => setKnowledgePage((p) => Math.max(1, p - 1))}
                        className="h-[32px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-50 disabled:cursor-not-allowed transition-all text-[13px]"
                      >
                        Previous
                      </button>
                      <button
                        disabled={!hasNextKnowledgePage}
                        onClick={() => setKnowledgePage((p) => p + 1)}
                        className="h-[32px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-50 disabled:cursor-not-allowed transition-all text-[13px]"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {activeTab === "history" && (
              <div className="space-y-5 animate-in fade-in duration-200">
                <div className="flex flex-col gap-3 rounded-cards border border-ink-black/[0.05] bg-fog-white p-4 md:flex-row md:items-center md:justify-between">
                  <div>
                    <span className="text-[12px] font-w500 uppercase tracking-wider text-ash-gray">Repository history</span>
                    <p className="mt-1 text-[13px] text-slate-gray">Commits, pull requests, and issues captured during the latest index.</p>
                  </div>
                  <select value={historyTypeFilter} onChange={(event) => setHistoryTypeFilter(event.target.value)} className="rounded-inputs border border-ink-black/[0.1] bg-paper-white px-3 py-2 text-[13px]">
                    <option value="all">All activity</option>
                    <option value="commit">Commits</option>
                    <option value="pull_request">Pull requests</option>
                    <option value="issue">Issues</option>
                  </select>
                </div>
                {isHistoryLoading ? (
                  <div className="py-20 text-center text-slate-gray">Loading decision history...</div>
                ) : historyArtifacts.filter((artifact) => historyTypeFilter === "all" || artifact.artifact_type === historyTypeFilter).length === 0 ? (
                  <div className="rounded-cards border border-dashed border-ink-black/[0.08] bg-fog-white py-16 text-center text-slate-gray">No history artifacts are available yet. Re-index to refresh commits, pull requests, and issues.</div>
                ) : (
                  <div className="space-y-3">
                    {historyArtifacts.filter((artifact) => historyTypeFilter === "all" || artifact.artifact_type === historyTypeFilter).map((artifact) => (
                      <a key={artifact.id} href={artifact.url} target="_blank" rel="noreferrer" className="block rounded-cards border border-ink-black/[0.05] bg-paper-white p-4 shadow-subtle transition-colors hover:bg-fog-white">
                        <div className="flex flex-wrap items-center gap-2 text-[11px] font-w500 uppercase tracking-wider">
                          <span className="rounded-buttons bg-mist-gray px-2 py-1 text-slate-gray">{artifact.artifact_type.replace("_", " ")}</span>
                          {artifact.data?.state && <span className="rounded-buttons border border-mist-gray px-2 py-1 text-ash-gray">{artifact.data.state}</span>}
                          <span className="font-mono text-ash-gray">#{artifact.external_id.slice(0, 10)}</span>
                        </div>
                        <h3 className="mt-2 text-[15px] font-w500 text-ink-black">{artifact.title || "Untitled artifact"}</h3>
                        <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-slate-gray">
                          {artifact.author_login && <span>@{artifact.author_login}</span>}
                          {artifact.authored_at && <span>Introduced {new Date(artifact.authored_at).toLocaleString()}</span>}
                          <span>Open on GitHub ↗</span>
                        </div>
                      </a>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* TAB CONTENT: Chunks Index & Split Screen Explorer */}
            {activeTab === "chunks" && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start animate-in fade-in duration-200">
                {/* Left Side: Chunks Catalog */}
                <div className="lg:col-span-5 space-y-[20px]">
                  <div className="flex flex-col gap-3 bg-fog-white border border-ink-black/[0.05] p-[16px] rounded-cards text-left">
                    <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block">
                      Filters
                    </span>
                    <div className="grid grid-cols-2 gap-[12px]">
                      <select
                        value={chunkSourceFilter}
                        onChange={(e) => {
                          setChunkSourceFilter(e.target.value);
                          setChunksPage(1);
                        }}
                        className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-3 py-2 text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
                      >
                        <option value="">All Sources</option>
                        <option value="source_code">Source Code</option>
                        <option value="documentation">Documentation</option>
                        <option value="database_schema">Database Schema</option>
                        <option value="configuration">Configuration</option>
                      </select>
                      <select
                        value={chunkTypeFilter}
                        onChange={(e) => {
                          setChunkTypeFilter(e.target.value);
                          setChunksPage(1);
                        }}
                        className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-3 py-2 text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
                      >
                        <option value="">All Types</option>
                        <option value="class">Class</option>
                        <option value="function">Function</option>
                        <option value="documentation_section">Doc Section</option>
                        <option value="configuration">Config</option>
                      </select>
                    </div>
                  </div>

                  <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-4">
                    <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block mb-3 pl-2">
                      Chunk Catalog
                    </span>
                    {isChunksLoading && chunks.length === 0 ? (
                      <div className="py-20 text-center text-slate-gray">Segmenting structures...</div>
                    ) : chunks.length === 0 ? (
                      <div className="py-20 text-center text-slate-gray">No chunks match filters.</div>
                    ) : (
                      <div className="space-y-2">
                        {chunks.map((c) => (
                          <div
                            key={c.id}
                            onClick={() => handleChunkSelect(c.id)}
                            className={`p-3 rounded-xl border text-left cursor-pointer transition-all ${selectedChunk?.id === c.id
                              ? "bg-ink-black border-ink-black text-paper-white shadow-sm"
                              : "bg-paper-white border-mist-gray hover:bg-fog-white text-ink-black"
                              }`}
                          >
                            <h4 className="text-[14px] font-medium font-sohne truncate">
                              {c.title}
                            </h4>
                            <p className={`text-[12px] mt-1 font-mono truncate ${selectedChunk?.id === c.id ? "text-paper-white/70" : "text-slate-gray"
                              }`}>
                              {c.path}
                            </p>
                            <div className="flex items-center justify-between mt-2 text-[10px] uppercase tracking-wider">
                              <span className="font-w500">{c.chunk_type.replace("_", " ")}</span>
                              <span>Lines: {c.start_line}-{c.end_line}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    <div className="flex items-center justify-between border-t border-mist-gray mt-4 pt-4 text-[13px] text-slate-gray pl-2 pr-2">
                      <span>Page {chunksPage}</span>
                      <div className="flex items-center gap-2">
                        <button
                          disabled={chunksPage === 1}
                          onClick={() => setChunksPage((p) => Math.max(1, p - 1))}
                          className="h-8 px-3 rounded-buttons border border-mist-gray disabled:opacity-50 disabled:cursor-not-allowed transition-all text-xs"
                        >
                          Prev
                        </button>
                        <button
                          disabled={!hasNextChunksPage}
                          onClick={() => setChunksPage((p) => p + 1)}
                          className="h-8 px-3 rounded-buttons border border-mist-gray disabled:opacity-50 disabled:cursor-not-allowed transition-all text-xs"
                        >
                          Next
                        </button>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Side: Chunk Inspector / Code Viewer & Relations */}
                <div className="lg:col-span-7 space-y-[24px]">
                  {isChunkDetailLoading ? (
                    <div className="border border-dashed border-ink-black/[0.08] bg-fog-white rounded-cards py-[160px] text-center text-slate-gray">
                      <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin mx-auto mb-4" />
                      Loading chunk details and relationship mapping...
                    </div>
                  ) : !selectedChunk ? (
                    <div className="border border-dashed border-ink-black/[0.08] bg-fog-white rounded-cards py-[160px] text-center text-slate-gray pl-8 pr-8">
                      <div className="w-12 h-12 rounded-full bg-mist-gray flex items-center justify-center mx-auto mb-4">
                        <svg
                          className="w-6 h-6 text-slate-gray"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth="2"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                          />
                        </svg>
                      </div>
                      <h4 className="text-[16px] font-medium text-ink-black mb-1">Inspect Semantic Chunk</h4>
                      <p className="text-[14px] text-slate-gray max-w-sm mx-auto leading-relaxed">
                        Select a code method, class, or documentation section from the registry listing on the left to read source files and view resolved dependency edges.
                      </p>
                    </div>
                  ) : (
                    <div className="bg-paper-white rounded-cards border border-ink-black/[0.05] shadow-subtle p-[24px] space-y-[24px] text-left animate-in fade-in duration-200">
                      {/* Chunk Header details */}
                      <div className="flex flex-col gap-2 pb-4 border-b border-mist-gray/40">
                        <div className="flex flex-wrap items-center justify-between gap-2">
                          <span className="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider rounded-buttons bg-mist-gray text-slate-gray">
                            {selectedChunk.source_type.replace("_", " ")} / {selectedChunk.chunk_type.replace("_", " ")}
                          </span>
                          <span className="text-xs text-ash-gray font-mono">
                            Lines {selectedChunk.start_line}-{selectedChunk.end_line} ({selectedChunk.language || "Text"})
                          </span>
                        </div>
                        <h3 className="text-[20px] font-sohne font-w500 text-ink-black tracking-tight">
                          {selectedChunk.title}
                        </h3>
                        <p className="text-[13px] text-slate-gray font-mono truncate">
                          File: {selectedChunk.path}
                        </p>
                      </div>

                      {/* Stable ID Panel */}
                      <div className="bg-fog-white border border-ink-black/[0.05] p-3.5 rounded-xl flex items-start justify-between gap-4">
                        <div className="min-w-0 pr-2">
                          <span className="text-[10px] font-w500 text-ash-gray uppercase tracking-wider block">Citation ID</span>
                          <p className="text-[11px] text-slate-gray mt-0.5">A stable reference for this exact indexed chunk.</p>
                          <code className="text-[12px] font-mono text-ink-black break-all block mt-1">
                            {selectedChunk.metadata?.stable_symbol_id || selectedChunk.id}
                          </code>
                        </div>
                        <button
                          onClick={() => copyToClipboard(selectedChunk.metadata?.stable_symbol_id || selectedChunk.id)}
                          title="Copy this stable reference to the clipboard"
                          className="h-8 px-3 rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-95 text-xs font-w500 flex-shrink-0 transition-all cursor-pointer"
                        >
                          Copy citation ID
                        </button>
                      </div>

                      {/* Code Viewer Panel */}
                      <div className="space-y-2">
                        <span className="text-[11px] font-w500 text-ash-gray uppercase tracking-wider block">Source Content</span>
                        <div className="border border-mist-gray rounded-xl overflow-hidden bg-slate-950 text-slate-100 font-mono text-[13px] leading-relaxed shadow-sm">
                          {/* File banner */}
                          <div className="bg-slate-900 border-b border-slate-800 px-4 py-2 flex items-center justify-between text-xs text-slate-400">
                            <span>{selectedChunk.path.split("/").pop()}</span>
                            <span>Line range: {selectedChunk.start_line}-{selectedChunk.end_line}</span>
                          </div>
                          {/* Code pre */}
                          <pre className="p-4 overflow-x-auto max-h-[380px] overflow-y-auto block select-text">
                            {selectedChunk.content}
                          </pre>
                        </div>
                      </div>

                      {/* Chunk Relationships section */}
                      <div className="space-y-4 pt-2 border-t border-mist-gray/40">
                        <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block">
                          Resolved Structural Relationships
                        </span>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          {/* Calls / Called By */}
                          <div className="border border-mist-gray/60 p-4 rounded-xl text-left bg-fog-white/30">
                            <span className="text-[11px] font-w500 text-slate-gray uppercase tracking-wider block mb-2">Calls</span>
                            {selectedChunk.metadata?.relationships?.calls?.length > 0 ? (
                              <ul className="space-y-1.5 text-[13px]">
                                {selectedChunk.metadata.relationships.calls.map((c: any, index: number) => (
                                  <li key={index} className="text-ink-black leading-normal flex items-start justify-between gap-3 font-sohne">
                                    <span className="font-medium truncate">{c.symbol}</span>
                                    {c.path ? (
                                      <span className="text-[11px] text-slate-500 font-mono truncate max-w-[120px]" title={c.path}>
                                        ({c.path.split("/").pop()})
                                      </span>
                                    ) : (
                                      <span className="text-[10px] text-slate-400 italic">unresolved fact</span>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-[12px] text-smoke-gray italic font-sohne">No outgoing calls resolved.</span>
                            )}
                          </div>

                          <div className="border border-mist-gray/60 p-4 rounded-xl text-left bg-fog-white/30">
                            <span className="text-[11px] font-w500 text-slate-gray uppercase tracking-wider block mb-2">Called By</span>
                            {selectedChunk.metadata?.relationships?.called_by?.length > 0 ? (
                              <ul className="space-y-1.5 text-[13px]">
                                {selectedChunk.metadata.relationships.called_by.map((c: any, index: number) => (
                                  <li key={index} className="text-ink-black leading-normal flex items-start justify-between gap-3 font-sohne">
                                    <span className="font-medium truncate">{c.symbol}</span>
                                    {c.path ? (
                                      <span className="text-[11px] text-slate-500 font-mono truncate max-w-[120px]" title={c.path}>
                                        ({c.path.split("/").pop()})
                                      </span>
                                    ) : (
                                      <span className="text-[10px] text-slate-400 italic">unresolved fact</span>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-[12px] text-smoke-gray italic font-sohne">No incoming calls resolved.</span>
                            )}
                          </div>

                          {/* Imports / Imported By */}
                          <div className="border border-mist-gray/60 p-4 rounded-xl text-left bg-fog-white/30">
                            <span className="text-[11px] font-w500 text-slate-gray uppercase tracking-wider block mb-2">Imports</span>
                            {selectedChunk.metadata?.relationships?.imports?.length > 0 ? (
                              <ul className="space-y-1.5 text-[13px]">
                                {selectedChunk.metadata.relationships.imports.map((c: any, index: number) => (
                                  <li key={index} className="text-ink-black leading-normal flex items-start justify-between gap-3 font-sohne">
                                    <span className="font-medium truncate">{c.symbol}</span>
                                    {c.path ? (
                                      <span className="text-[11px] text-slate-500 font-mono truncate max-w-[120px]" title={c.path}>
                                        ({c.path.split("/").pop()})
                                      </span>
                                    ) : (
                                      <span className="text-[10px] text-slate-400 italic">unresolved fact</span>
                                    )}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-[12px] text-smoke-gray italic font-sohne">No imports.</span>
                            )}
                          </div>

                          <div className="border border-mist-gray/60 p-4 rounded-xl text-left bg-fog-white/30">
                            <span className="text-[11px] font-w500 text-slate-gray uppercase tracking-wider block mb-2">Imported By</span>
                            {selectedChunk.metadata?.relationships?.imported_by?.length > 0 ? (
                              <ul className="space-y-1.5 text-[13px]">
                                {selectedChunk.metadata.relationships.imported_by.map((c: any, index: number) => (
                                  <li key={index} className="text-ink-black leading-normal font-sohne truncate font-mono text-[12px] text-slate-600">
                                    {c.path}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-[12px] text-smoke-gray italic font-sohne">Not imported.</span>
                            )}
                          </div>

                          {/* Inherits / Exports */}
                          <div className="border border-mist-gray/60 p-4 rounded-xl text-left bg-fog-white/30">
                            <span className="text-[11px] font-w500 text-slate-gray uppercase tracking-wider block mb-2">Inheritance (Inherits/Implements)</span>
                            {selectedChunk.metadata?.relationships?.inherits?.length > 0 || selectedChunk.metadata?.relationships?.implements?.length > 0 ? (
                              <ul className="space-y-1 text-[13px] font-sohne">
                                {(selectedChunk.metadata.relationships.inherits || []).map((c: any, idx: number) => (
                                  <li key={`inh-${idx}`}>Inherits: <span className="font-medium">{c.symbol || c}</span></li>
                                ))}
                                {(selectedChunk.metadata.relationships.implements || []).map((c: any, idx: number) => (
                                  <li key={`impl-${idx}`}>Implements: <span className="font-medium">{c.symbol || c}</span></li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-[12px] text-smoke-gray italic font-sohne">No parent classes or interfaces.</span>
                            )}
                          </div>

                          <div className="border border-mist-gray/60 p-4 rounded-xl text-left bg-fog-white/30">
                            <span className="text-[11px] font-w500 text-slate-gray uppercase tracking-wider block mb-2">Exports</span>
                            {selectedChunk.metadata?.relationships?.exports?.length > 0 ? (
                              <ul className="space-y-1.5 text-[13px] font-sohne">
                                {selectedChunk.metadata.relationships.exports.map((c: any, index: number) => (
                                  <li key={index} className="text-ink-black truncate">
                                    {c.symbol || c}
                                  </li>
                                ))}
                              </ul>
                            ) : (
                              <span className="text-[12px] text-smoke-gray italic font-sohne">No exports.</span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

export default function RepositoryDetails({ params }: PageProps) {
  return (
    <Suspense fallback={
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin" />
          <span className="text-[15px] text-slate-gray font-w400">Loading details...</span>
        </div>
      </div>
    }>
      <RepositoryDetailsContent params={params} />
    </Suspense>
  );
}
