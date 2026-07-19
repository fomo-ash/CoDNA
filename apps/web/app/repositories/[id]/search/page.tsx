"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import api from "../../../../lib/api";
import { User, Repository, RepositorySearchResult, RepositorySearchResponse } from "../../../../types/api";
import Header from "../../../../components/Header";

interface PageProps {
  params: Promise<{ id: string }> | { id: string };
}

function SearchContent({ repositoryId }: { repositoryId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  
  const [user, setUser] = useState<User | null>(null);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Search parameters
  const [queryInput, setQueryInput] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [chunkType, setChunkType] = useState("");
  const [limit, setLimit] = useState(20);
  
  // Search results
  const [searchResults, setSearchResults] = useState<RepositorySearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [searched, setSearched] = useState(false);
  const [vectorSearchUsed, setVectorSearchUsed] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem("codedna_jwt");
    if (!token) {
      router.push("/");
      return;
    }

    const loadRepo = async () => {
      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
        
        const repository = await api.getRepository(repositoryId);
        setRepo(repository);
        
        // Grab initial query from URL search parameters if present
        const urlQ = searchParams.get("q");
        if (urlQ) {
          setQueryInput(urlQ);
          executeSearch(urlQ, sourceType, chunkType, limit);
        }
      } catch (err) {
        console.error("Failed to load repo for search", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadRepo();
  }, [repositoryId, searchParams, router]);

  const executeSearch = async (q: string, srcT: string, chkT: string, lim: number) => {
    if (!q.trim()) return;
    setIsSearching(true);
    setSearchError("");
    setSearched(true);
    try {
      const response = await api.searchRepository(repositoryId, q, {
        source_type: srcT || undefined,
        chunk_type: chkT || undefined,
        limit: lim,
      });
      setSearchResults(response.results || []);
      setVectorSearchUsed(response.vector_search_used);
      
      // Update URL silently
      const url = new URL(window.location.href);
      url.searchParams.set("q", q);
      window.history.pushState({}, "", url.toString());
    } catch (err: any) {
      console.error("Retrieval search failed", err);
      setSearchError(err.message || "Retrieval engine is currently unavailable. Please wait or try re-indexing.");
    } finally {
      setIsSearching(false);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch(queryInput, sourceType, chunkType, limit);
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
          <span className="text-[15px] text-slate-gray">Waking retrieval engine...</span>
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

      <main className="flex-1 w-full max-w-[1000px] mx-auto px-[24px] py-[32px]">
        {/* Back Link */}
        <div className="mb-[24px] text-left">
          <Link
            href={`/repositories/${repo.id}`}
            className="text-[15px] text-slate-gray hover:text-ink-black transition-colors inline-flex items-center gap-[6px] cursor-pointer"
          >
            ← Back to Explorer
          </Link>
        </div>

        {/* Title */}
        <div className="mb-[32px] text-left">
          <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block mb-[6px]">
            Hybrid Retrieval Search
          </span>
          <h1 className="text-[32px] md:text-[40px] font-signifier font-w400 leading-tight text-ink-black tracking-[-0.66px]">
            Explore <span className="italic">{repo.name}</span>
          </h1>
          <p className="text-[15px] text-slate-gray mt-[4px]">
            Execute lexical queries and pgvector semantic searches across index segments.
          </p>
        </div>

        {/* Search & Filters form */}
        <form onSubmit={handleSearchSubmit} className="space-y-4 mb-8 bg-fog-white border border-ink-black/[0.05] p-5 rounded-cards text-left">
          <div className="flex gap-3">
            <input
              type="text"
              required
              placeholder="Enter search terms, class names, or function signatures..."
              value={queryInput}
              onChange={(e) => setQueryInput(e.target.value)}
              className="flex-1 bg-paper-white border border-ink-black/[0.1] rounded-inputs px-4 py-2.5 text-[14px] font-sohne text-ink-black placeholder-smoke-gray focus:outline-none focus:ring-1 focus:ring-ink-black transition-all shadow-sm"
            />
            <button
              type="submit"
              disabled={isSearching}
              className="h-[40px] px-6 rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-95 transition-all text-[14px] font-w500 flex items-center justify-center cursor-pointer shadow-sm disabled:opacity-75"
            >
              {isSearching ? "Searching..." : "Search"}
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
            <div>
              <label className="text-[11px] font-w500 text-ash-gray uppercase tracking-wider block mb-1.5">Source Type</label>
              <select
                value={sourceType}
                onChange={(e) => setSourceType(e.target.value)}
                className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-3 py-2 text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
              >
                <option value="">All Sources</option>
                <option value="source_code">Source Code</option>
                <option value="documentation">Documentation</option>
                <option value="database_schema">Database Schema</option>
                <option value="configuration">Configuration</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-w500 text-ash-gray uppercase tracking-wider block mb-1.5">Chunk Type</label>
              <select
                value={chunkType}
                onChange={(e) => setChunkType(e.target.value)}
                className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-3 py-2 text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
              >
                <option value="">All Types</option>
                <option value="class">Class</option>
                <option value="function">Function</option>
                <option value="documentation_section">Doc Section</option>
                <option value="configuration">Config</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-w500 text-ash-gray uppercase tracking-wider block mb-1.5">Result Limit</label>
              <select
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs px-3 py-2 text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black cursor-pointer"
              >
                <option value="10">10 results</option>
                <option value="20">20 results</option>
                <option value="50">50 results</option>
                <option value="100">100 results</option>
              </select>
            </div>
          </div>
        </form>

        {/* Results layout */}
        <div className="space-y-4 text-left">
          {isSearching ? (
            <div className="py-20 text-center text-slate-gray">
              <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin mx-auto mb-4" />
              Scanning vectors and lexical tokens...
            </div>
          ) : searchError ? (
            <div className="bg-red-50 border border-red-200 rounded-cards p-5 text-red-700 text-center animate-in fade-in duration-200">
              <span className="text-2xl block mb-2">⚠️</span>
              <h4 className="font-w500 mb-1">Search Retrieval Interrupted</h4>
              <p className="text-xs text-red-600 font-mono mt-2">{searchError}</p>
            </div>
          ) : !searched ? (
            <div className="border border-dashed border-ink-black/[0.08] bg-fog-white rounded-cards py-16 text-center text-slate-gray pl-6 pr-6">
              Enter your terms and filters above to pull matched chunk evidence records.
            </div>
          ) : searchResults.length === 0 ? (
            <div className="border border-dashed border-ink-black/[0.08] bg-fog-white rounded-cards py-16 text-center text-slate-gray pl-6 pr-6">
              No matching chunks found in the index. Try modifying your terms or filters.
            </div>
          ) : (
            <>
              {/* Hybrid indicators */}
              <div className="flex items-center justify-between text-xs text-ash-gray pb-2 border-b border-mist-gray/40 mb-4">
                <span>Pulled {searchResults.length} matched segments</span>
                {vectorSearchUsed && (
                  <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 border border-emerald-100 rounded-buttons uppercase tracking-wider text-[10px] font-bold">
                    pgvector hybrid search active
                  </span>
                )}
              </div>

              {/* Cards List */}
              <div className="space-y-4">
                {searchResults.map((result, idx) => {
                  const chunk = result.chunk;
                  const scorePct = Math.round(result.score * 100);
                  const lexicalPct = Math.round(result.lexical_score * 100);
                  const vectorPct = result.vector_score !== null ? Math.round(result.vector_score * 100) : null;

                  return (
                    <div
                      key={chunk.id}
                      onClick={() => router.push(`/repositories/${repo.id}?tab=chunks&chunkId=${chunk.id}`)}
                      className="border border-mist-gray p-5 rounded-cards hover:bg-fog-white transition-all cursor-pointer shadow-subtle flex flex-col gap-4 text-left"
                    >
                      <div className="flex flex-col md:flex-row justify-between md:items-start gap-3">
                        <div className="space-y-1 truncate pr-2">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="px-2 py-0.5 text-[10px] uppercase font-bold tracking-wider bg-mist-gray text-slate-gray rounded-buttons">
                              {chunk.source_type.replace("_", " ")} / {chunk.chunk_type.replace("_", " ")}
                            </span>
                            <span className="text-xs text-ash-gray font-mono">
                              Lines {chunk.start_line}-{chunk.end_line}
                            </span>
                          </div>
                          <h3 className="text-[17px] font-w500 text-ink-black hover:underline truncate">
                            {chunk.title}
                          </h3>
                          <p className="text-[12px] text-slate-gray font-mono truncate">
                            File: {chunk.path}
                          </p>
                        </div>

                        {/* Relevance Scores Panel */}
                        <div className="flex-shrink-0 bg-fog-white border border-ink-black/[0.05] p-3 rounded-xl min-w-[140px] space-y-1.5 text-xs">
                          <div className="flex items-center justify-between font-w500">
                            <span className="text-ink-black">Relevance</span>
                            <span className="text-ink-black font-bold font-mono">{scorePct}%</span>
                          </div>
                          <div className="w-full bg-ink-black/[0.06] h-1.5 rounded-full overflow-hidden">
                            <div className="bg-ink-black h-full rounded-full" style={{ width: `${scorePct}%` }} />
                          </div>
                          <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between">
                            <span>Lexical: {lexicalPct}%</span>
                            {vectorPct !== null && <span>Vector: {vectorPct}%</span>}
                          </div>
                        </div>
                      </div>

                      {/* Small Snippet */}
                      <pre className="p-3 bg-slate-950 text-slate-100 font-mono text-[12px] rounded-lg overflow-x-auto select-none leading-relaxed max-h-[120px]">
                        {chunk.content.split("\n").slice(0, 3).join("\n")}
                        {chunk.content.split("\n").length > 3 && "\n..."}
                      </pre>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default function SearchPage({ params }: PageProps) {
  const [resolvedId, setResolvedId] = useState<string | null>(null);

  useEffect(() => {
    if (params && typeof (params as any).then === "function") {
      Promise.resolve(params).then((p) => setResolvedId(p.id));
    } else if (params) {
      setResolvedId((params as any).id);
    }
  }, [params]);

  if (!resolvedId) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin" />
          <span className="text-[15px] text-slate-gray font-w400">Loading details...</span>
        </div>
      </div>
    );
  }

  return (
    <Suspense fallback={
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin" />
          <span className="text-[15px] text-slate-gray font-w400">Loading details...</span>
        </div>
      </div>
    }>
      <SearchContent repositoryId={resolvedId} />
    </Suspense>
  );
}
