"use client";

import React, { useCallback, useEffect, useRef, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import api from "../../../../lib/api";
import { User, Repository, RepositoryQuestionResponse } from "../../../../types/api";
import Header from "../../../../components/Header";
import ImpactPathAutocomplete from "../../../../components/ImpactPathAutocomplete";

interface PageProps {
  params: Promise<{ id: string }> | { id: string };
}

function SearchContent({ repositoryId }: { repositoryId: string }) {
  const router = useRouter();
  const loadedRouteRef = useRef<string | null>(null);
  
  const [user, setUser] = useState<User | null>(null);
  const [repo, setRepo] = useState<Repository | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  const [question, setQuestion] = useState("");
  const [impactPath, setImpactPath] = useState("");
  const [impactDepth, setImpactDepth] = useState(2);
  const [answer, setAnswer] = useState<RepositoryQuestionResponse | null>(null);
  const [isAsking, setIsAsking] = useState(false);
  const [answerError, setAnswerError] = useState("");

  useEffect(() => {
    if (loadedRouteRef.current === repositoryId) {
      return;
    }
    loadedRouteRef.current = repositoryId;

    const token = localStorage.getItem("codedna_jwt");
    if (!token) {
      setIsLoading(false);
      router.replace("/");
      return;
    }

    const loadRepo = async () => {
      try {
        const currentUser = await api.getCurrentUser();
        setUser(currentUser);
        
        const repository = await api.getRepository(repositoryId);
        setRepo(repository);
      } catch (err) {
        console.error("Failed to load repo for Q&A", err);
      } finally {
        setIsLoading(false);
      }
    };

    loadRepo();
  }, [repositoryId, router]);

  const handleQuestionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;
    setIsAsking(true); setAnswerError("");
    try {
      const response = await (api as any).askRepositoryQuestion(repositoryId, {
        question, impact_path: impactPath || undefined, impact_depth: impactDepth,
      });
      setAnswer(response);
    } catch (err: any) {
      setAnswerError(err.message || "Question answering is unavailable. Please try again.");
    } finally { setIsAsking(false); }
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
        <div className={`transition-all duration-500 ease-in-out flex flex-col items-center justify-center text-center ${answer || isAsking || answerError ? "mt-4 mb-8" : "mt-20 mb-12"}`}>
          <div className="w-12 h-12 bg-ink-black text-paper-white rounded-xl flex items-center justify-center mb-6 shadow-subtle -rotate-3 hover:rotate-0 transition-transform cursor-default">
             <span className="font-signifier text-2xl italic">C</span>
          </div>
          <h1 className="text-[36px] md:text-[44px] font-signifier font-w400 leading-tight text-ink-black tracking-[-0.02em] mb-3">
            What do you want to know about <span className="italic">{repo.name}</span>?
          </h1>
          <p className="text-[15px] text-slate-gray max-w-[500px]">
            Ask about architecture, find code patterns, or explore dependencies.
          </p>
        </div>

        {/* Q&A Form */}
        <section className={`transition-all duration-500 ease-in-out w-full max-w-[760px] mx-auto ${answer || isAsking || answerError ? "" : "scale-105"}`}>
          <form onSubmit={handleQuestionSubmit} className="relative group mb-8">
            <div className="absolute -inset-1 bg-gradient-to-r from-ink-black/[0.04] to-ink-black/[0.01] rounded-[24px] blur opacity-75 group-hover:opacity-100 transition duration-500"></div>
            <div className="relative bg-paper-white border border-ink-black/[0.08] rounded-[24px] shadow-subtle flex flex-col transition-all focus-within:border-ink-black/[0.2] focus-within:shadow-md">
              <textarea 
                required 
                value={question} 
                onChange={(e) => setQuestion(e.target.value)} 
                placeholder="e.g. How is authentication handled in this project?" 
                className="w-full min-h-[140px] bg-transparent border-none px-6 py-5 text-[15px] leading-relaxed resize-none focus:outline-none focus:ring-0 placeholder-slate-400 text-ink-black" 
              />
              
              <div className="px-4 py-3 bg-fog-white/60 border-t border-ink-black/[0.04] rounded-b-[24px] flex flex-col md:flex-row items-center gap-3 relative z-10">
                <div className="flex-1 w-full flex items-center gap-2">
                  <ImpactPathAutocomplete
                    repositoryId={repositoryId}
                    value={impactPath}
                    onChange={setImpactPath}
                    className="w-full bg-paper-white/80 border border-ink-black/[0.08] rounded-xl px-3 py-2.5 text-[13px] focus:outline-none focus:bg-paper-white focus:border-ink-black/[0.2] transition-colors"
                  />
                  <select value={impactDepth} onChange={(e) => setImpactDepth(Number(e.target.value))} className="bg-paper-white/80 border border-ink-black/[0.08] rounded-xl px-3 py-2.5 text-[13px] focus:outline-none focus:bg-paper-white focus:border-ink-black/[0.2] cursor-pointer">
                    <option value={1}>Direct impact</option><option value={2}>Depth 2</option><option value={3}>Depth 3</option>
                  </select>
                </div>
                <button type="submit" disabled={isAsking} className="w-full md:w-auto px-6 py-2.5 rounded-xl bg-ink-black text-paper-white text-[14px] font-w500 shadow-sm disabled:opacity-70 hover:bg-ink-black/90 active:scale-95 transition-all whitespace-nowrap">
                  {isAsking ? "Analyzing..." : "Ask CoDNA"}
                </button>
              </div>
            </div>
          </form>
          {answerError && (
            <div className="mt-4 rounded-inputs border border-amber-300/80 bg-amber-50/90 p-4 text-[13px] leading-relaxed text-amber-950 shadow-subtle">
              <p className="font-w500 text-amber-900">{answerError}</p>
            </div>
          )}
          {answer && (
            <div className="mt-6 border-t border-mist-gray pt-5">
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-w500 uppercase tracking-wider">
                <span className="rounded-buttons bg-ink-black px-2.5 py-1 text-paper-white">Answer</span>
                <span className="rounded-buttons border border-mist-gray bg-paper-white px-2.5 py-1 text-ash-gray">{answer.cached ? "Cached" : "Fresh"}</span>
                <span className={`rounded-buttons px-2.5 py-1 ${answer.vector_search_used ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-700"}`}>{answer.vector_search_used ? "Hybrid evidence" : "Lexical evidence"}</span>
              </div>
              <article className="mt-4 rounded-xl border border-ink-black/[0.06] bg-paper-white p-5 shadow-subtle">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    h1: ({ children }) => <h2 className="mt-6 first:mt-0 text-[20px] font-w500 text-ink-black">{children}</h2>,
                    h2: ({ children }) => <h3 className="mt-6 first:mt-0 text-[17px] font-w500 text-ink-black">{children}</h3>,
                    h3: ({ children }) => <h4 className="mt-5 first:mt-0 text-[15px] font-w500 text-ink-black">{children}</h4>,
                    p: ({ children }) => <p className="mt-3 first:mt-0 text-[14px] leading-6 text-ink-black">{children}</p>,
                    ul: ({ children }) => <ul className="mt-3 list-disc space-y-1.5 pl-5 text-[14px] leading-6 text-ink-black">{children}</ul>,
                    ol: ({ children }) => <ol className="mt-3 list-decimal space-y-1.5 pl-5 text-[14px] leading-6 text-ink-black">{children}</ol>,
                    li: ({ children }) => <li className="pl-1">{children}</li>,
                    a: ({ children, href }) => <a href={href} target="_blank" rel="noreferrer" className="text-ink-black underline decoration-ink-black/30 underline-offset-2 hover:decoration-ink-black">{children}</a>,
                    code: ({ children, className }) => {
                      return <code className={className ? `${className} block whitespace-pre-wrap` : "rounded bg-mist-gray px-1 py-0.5 font-mono text-[12px] text-ink-black"}>{children}</code>;
                    },
                    pre: ({ children }) => <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-950 p-4 font-mono text-[12px] leading-6 text-slate-100">{children}</pre>,
                    blockquote: ({ children }) => <blockquote className="mt-4 border-l-2 border-ink-black/20 pl-4 text-slate-gray">{children}</blockquote>,
                  }}
                >
                  {answer.answer}
                </ReactMarkdown>
              </article>
              {answer.citations.length > 0 && (
                <div className="mt-5">
                  <div className="flex items-baseline justify-between gap-3">
                     <span className="text-[11px] font-w500 text-ash-gray uppercase tracking-wider">Evidence</span>
                     <span className="text-[12px] text-slate-gray">Open a record to inspect the exact indexed chunk.</span>
                   </div>
                   <div className="mt-2 grid grid-cols-1 gap-2 md:grid-cols-2">
                     {answer.citations.map((citation) => (
                       <Link key={citation.chunk_id} href={`/repositories/${repo.id}?tab=chunks&chunkId=${citation.chunk_id}`} className="rounded-lg border border-mist-gray bg-paper-white px-3 py-2 text-[12px] text-ink-black transition-colors hover:bg-fog-white">
                         <span className="mr-2 font-mono text-ash-gray">[{citation.index}]</span>
                         <span className="font-mono break-all">{citation.path}:{citation.start_line ?? 1}</span>
                       </Link>
                     ))}
                   </div>
                 </div>
               )}
             </div>
           )}
         </section>
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
