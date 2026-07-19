"use client";

import React, { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import api from "../../../lib/api";

function CallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [errorMsg, setErrorMsg] = useState("");

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");

    if (!code || !state) {
      setStatus("error");
      setErrorMsg("Missing OAuth authorization code or state token. Please try again.");
      return;
    }

    const exchangeToken = async () => {
      try {
        const response = await api.githubCallback(code, state);
        localStorage.setItem("codedna_jwt", response.access_token);
        setStatus("success");
        // Brief timeout for transition effect
        setTimeout(() => {
          router.push("/dashboard");
        }, 1500);
      } catch (err: any) {
        console.error("Token exchange failed:", err);
        setStatus("error");
        setErrorMsg(err.message || "Failed to exchange GitHub authorization code for CodeDNA token.");
      }
    };

    exchangeToken();
  }, [searchParams, router]);

  const handleRetry = () => {
    router.push("/");
  };

  return (
    <div className="bg-paper-white w-full max-w-[480px] rounded-cards p-[36px] shadow-subtle-2 border border-ink-black/[0.06] text-center z-10 relative">
      {status === "loading" && (
        <div className="flex flex-col items-center gap-[24px] py-[24px]">
          <div className="w-[48px] h-[48px] rounded-full border-[3px] border-slate-gray/30 border-t-ink-black animate-spin" />
          <div>
            <h2 className="text-[20px] font-sohne font-w500 text-ink-black mb-[8px]">
              Authorizing with GitHub
            </h2>
            <p className="text-[15px] text-slate-gray max-w-sm">
              We are securely exchanging your credentials and establishing your workspace session...
            </p>
          </div>
        </div>
      )}

      {status === "success" && (
        <div className="flex flex-col items-center gap-[24px] py-[24px] animate-in fade-in zoom-in-95 duration-200">
          <div className="w-[48px] h-[48px] rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200 flex items-center justify-center text-xl font-bold">
            ✓
          </div>
          <div>
            <h2 className="text-[20px] font-sohne font-w500 text-ink-black mb-[8px]">
              Session Established
            </h2>
            <p className="text-[15px] text-slate-gray">
              Redirecting you to your Control Console...
            </p>
          </div>
        </div>
      )}

      {status === "error" && (
        <div className="flex flex-col items-center gap-[24px] py-[16px] animate-in fade-in zoom-in-95 duration-200">
          <div className="w-[48px] h-[48px] rounded-full bg-red-50 text-red-600 border border-red-200 flex items-center justify-center text-2xl font-light">
            !
          </div>
          <div>
            <h2 className="text-[20px] font-sohne font-w500 text-ink-black mb-[8px]">
              Authentication Failed
            </h2>
            <p className="text-[14px] text-red-600 bg-red-50/50 border border-red-100 p-[12px] rounded-xl text-left leading-relaxed mb-[24px] font-mono">
              {errorMsg}
            </p>
            <button
              onClick={handleRetry}
              className="h-[44px] px-[24px] rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-95 transition-all text-[15px] font-w500 inline-flex items-center justify-center cursor-pointer"
            >
              Retry Login
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function CallbackPage() {
  return (
    <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne relative p-[16px]">
      {/* Sleek Gradient Backdrop matching Landing Page */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[90%] max-w-[800px] h-[500px] rounded-full bg-gradient-to-tr from-[#ebdfff]/45 via-[#fbe1d1]/55 via-[#fff9db]/45 to-[#dff2fd]/45 blur-[120px] opacity-90 pointer-events-none z-0" />
      
      <Suspense fallback={
        <div className="bg-paper-white w-full max-w-[480px] rounded-cards p-[36px] shadow-subtle-2 border border-ink-black/[0.06] text-center z-10">
          <div className="flex flex-col items-center gap-[24px] py-[24px]">
            <div className="w-[48px] h-[48px] rounded-full border-[3px] border-slate-gray/30 border-t-ink-black animate-spin" />
            <span className="text-[15px] text-slate-gray font-w400">Loading OAuth flow...</span>
          </div>
        </div>
      }>
        <CallbackContent />
      </Suspense>
    </div>
  );
}
