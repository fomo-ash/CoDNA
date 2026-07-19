"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import api from "../lib/api";
import { User } from "../types/api";
import Header from "../components/Header";
import {
  RegionTableArtifact,
  RegistrationCardArtifact,
  ActivationChartArtifact,
  AIComposerArtifact,
} from "../components/HeroArtifacts";

export default function Home() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loginError, setLoginError] = useState("");
  const [isValidating, setIsValidating] = useState(false);

  // Check if user is already logged in
  useEffect(() => {
    const checkUser = async () => {
      const token = localStorage.getItem("codedna_jwt");
      if (token) {
        try {
          const currentUser = await api.getCurrentUser();
          setUser(currentUser);
          router.push("/dashboard");
        } catch (err) {
          console.error("Token invalid, clearing", err);
          localStorage.removeItem("codedna_jwt");
        }
      }
      setIsLoading(false);
    };

    checkUser();
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("codedna_jwt");
    setUser(null);
    router.refresh();
  };

  const handleLoginStart = async () => {
    setIsValidating(true);
    setLoginError("");
    try {
      const response = await api.getGithubLoginUrl();
      if (response && response.authorization_url) {
        window.location.href = response.authorization_url;
      } else {
        throw new Error("No authorization URL returned.");
      }
    } catch (err: any) {
      console.error("OAuth init failed:", err);
      setLoginError(err.message || "Failed to initialize GitHub OAuth flow.");
      alert(err.message || "Failed to start GitHub sign-in. Please try again.");
    } finally {
      setIsValidating(false);
    }
  };


  if (isLoading) {
    return (
      <div className="flex flex-col flex-1 items-center justify-center min-h-screen bg-paper-white font-sohne">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-full border-2 border-slate-gray border-t-ink-black animate-spin" />
          <span className="text-[15px] text-slate-gray font-w400">Loading CoDNA...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-paper-white text-ink-black font-sohne overflow-x-hidden">
      <Header
        user={user}
        onLogout={handleLogout}
        onOpenLoginModal={handleLoginStart}
      />

      <main className="flex-1 flex flex-col items-center">
        <section className="w-full max-w-[1200px] mx-auto px-6 pt-16 pb-28 text-center relative flex flex-col items-center">
          {/* Subtle Ambient Glow Behind Hero */}
          <div className="absolute top-[10px] left-1/2 -translate-x-1/2 w-[95%] max-w-[1300px] h-[650px] rounded-full bg-gradient-to-tr from-[#ebdfff]/65 via-[#fbe1d1]/85 via-[#fff9db]/75 to-[#dff2fd]/65 blur-[120px] opacity-90 pointer-events-none z-0" />

          <span className="relative z-10 text-[14px] font-w400 text-ash-gray tracking-wider uppercase mb-6 block">
            Software Intelligence System
          </span>

          <h1 className="relative z-10 text-[32px] md:text-[48px] lg:text-[60px] font-signifier font-w400 text-ink-black leading-tight tracking-[-1.5px] md:tracking-[-2px] max-w-4xl mx-auto mb-[24px] px-[16px]">
            Every codebase has a <span className="italic">DNA</span>. We help you decode it.
          </h1>

          <p className="relative z-10 text-[15px] md:text-[18px] font-w400 text-slate-gray leading-relaxed max-w-2xl mx-auto mb-[32px] px-[16px]">
            CoDNA extracts architecture mapping, indexes file parameters, and tracks indexing jobs in the background. It reads like a spread, interacts like an asset.
          </p>

          <div className="relative z-10 flex flex-col sm:flex-row items-center justify-center gap-[16px] mb-[16px] w-full max-w-md sm:max-w-none px-[24px]">
            <button
              onClick={handleLoginStart}
              disabled={isValidating}
              className="w-full sm:w-auto h-[48px] px-[32px] rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-[0.98] transition-all text-[16px] font-medium flex items-center justify-center cursor-pointer shadow-sm disabled:opacity-75 disabled:cursor-not-allowed"
            >
              {isValidating ? (
                <>
                  <span className="w-[16px] h-[16px] rounded-full border border-white border-t-transparent animate-spin mr-[10px]" />
                  Connecting...
                </>
              ) : (
                "Continue with GitHub"
              )}
            </button>
            <button
              onClick={() => alert("Booking a demo is currently offline. Please use GitHub login to explore the dashboard.")}
              className="w-full sm:w-auto h-[48px] px-[32px] rounded-buttons bg-transparent text-ink-black border-2 border-ink-black hover:bg-mist-gray active:scale-[0.98] transition-all text-[16px] font-normal flex items-center justify-center cursor-pointer"
            >
              Book a demo
            </button>
          </div>

          <button
            onClick={handleLoginStart}
            className="relative z-10 text-[13px] text-slate-gray hover:text-ink-black transition-colors underline underline-offset-4 cursor-pointer mb-[64px]"
          >
            Or authenticate with access token / launch demo mode
          </button>

          {/* Collage of Floating Artifacts */}
          <div className="relative z-10 w-full h-[480px] max-w-5xl mx-auto hidden lg:block">
            <div className="absolute top-[20px] left-[2%] z-20">
              <RegionTableArtifact />
            </div>

            <div className="absolute top-[40px] right-[2%] z-20">
              <RegistrationCardArtifact />
            </div>

            <div className="absolute bottom-[40px] left-[10%] z-20">
              <ActivationChartArtifact />
            </div>

            <div className="absolute bottom-[20px] left-[45%] transform -translate-x-1/2 z-30">
              <AIComposerArtifact />
            </div>
          </div>

          <div className="lg:hidden relative z-10 flex flex-col gap-[24px] items-center w-full mt-[24px]">
            <RegionTableArtifact />
            <RegistrationCardArtifact />
            <ActivationChartArtifact />
            <AIComposerArtifact />
          </div>
        </section>

        {/* 2. Alternating Section: Fog White Feature grid */}
        <section className="w-full bg-fog-white py-[96px] border-t border-b border-mist-gray/40">
          <div className="w-full max-w-[1200px] mx-auto px-[24px] text-left">
            <span className="text-[14px] font-w400 text-ash-gray uppercase tracking-wider block mb-[16px]">
              Features
            </span>
            <h2 className="text-[44px] font-signifier font-w400 text-ink-black tracking-tight mb-[16px] max-w-xl">
              Understand the <span className="italic">why</span> of your codebase.
            </h2>
            <p className="text-[17px] font-w400 text-slate-gray max-w-md mb-[64px]">
              A comprehensive tracking pipeline designed for quiet analysis and clear software diagnostics.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-[24px]">
              <div className="bg-mist-gray rounded-cards p-[32px] text-left flex flex-col justify-between min-h-[220px]">
                <div>
                  <span className="text-[14px] font-w400 text-ash-gray block mb-[16px]">01 / DISCOVERY</span>
                  <h3 className="text-[20px] font-w500 text-ink-black mb-[8px]">Automated Discovery</h3>
                  <p className="text-[16px] font-w400 text-slate-gray leading-relaxed">
                    Instantly query your GitHub profile, listing public and private repositories ready for registration and index scoping.
                  </p>
                </div>
                <a href="#" className="text-[16px] font-sohne font-w400 text-ink-black hover:underline hover:underline-offset-4 decoration-1 pt-[24px] inline-flex items-center gap-[4px]">
                  Explore integrations <span className="transition-transform">→</span>
                </a>
              </div>

              <div className="bg-mist-gray rounded-cards p-[32px] text-left flex flex-col justify-between min-h-[220px]">
                <div>
                  <span className="text-[14px] font-w400 text-ash-gray block mb-[16px]">02 / INDEXING</span>
                  <h3 className="text-[20px] font-w500 text-ink-black mb-[8px]">Celery-Backed Scopes</h3>
                  <p className="text-[16px] font-w400 text-slate-gray leading-relaxed">
                    Trigger cloning and indexing with queued background workers. Fetch file catalogs and size aggregates on demand.
                  </p>
                </div>
                <a href="#" className="text-[16px] font-sohne font-w400 text-ink-black hover:underline hover:underline-offset-4 decoration-1 pt-[24px] inline-flex items-center gap-[4px]">
                  View queue metrics <span>→</span>
                </a>
              </div>

              <div className="bg-mist-gray rounded-cards p-[32px] text-left flex flex-col justify-between min-h-[220px]">
                <div>
                  <span className="text-[14px] font-w400 text-ash-gray block mb-[16px]">03 / TELEMETRY</span>
                  <h3 className="text-[20px] font-w500 text-ink-black mb-[8px]">Interactive Inventory</h3>
                  <p className="text-[16px] font-w400 text-slate-gray leading-relaxed">
                    Audit files by detected programming languages and dimensions, utilizing tabular reports that let developers see layout stats.
                  </p>
                </div>
                <a href="#" className="text-[16px] font-sohne font-w400 text-ink-black hover:underline hover:underline-offset-4 decoration-1 pt-[24px] inline-flex items-center gap-[4px]">
                  Read developer spec <span>→</span>
                </a>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Accent Principles Card (Pastel Gradient with ink-black typography) */}
        <section className="w-full max-w-[1200px] mx-auto px-[24px] py-[96px] flex justify-center">
          <div className="bg-gradient-to-tr from-[#ebdfff]/50 via-[#fbe1d1]/75 via-[#fff9db]/65 to-[#dff2fd]/50 rounded-cards text-ink-black p-[40px] md:p-[56px] w-full max-w-4xl border border-ink-black/[0.06] text-center relative overflow-hidden">
            <h4 className="text-[26px] font-sohne font-w500 text-ink-black mb-[24px] tracking-tight">
              An Architectural Spreadsheet
            </h4>
            <p className="text-[18px] md:text-[22px] font-w430 text-ink-black leading-relaxed max-w-2xl mx-auto mb-[32px] font-signifier italic">
              "We believe code analysis shouldn't feel like a heavy dashboard setup. CoDNA surfaces your source files as lightweight, readable documents, creating a layout that matches print design with developer velocity."
            </p>
            <div className="text-[14px] font-sohne font-w500 text-ink-black/70 uppercase tracking-wider">
              — The CoDNA Principles
            </div>
          </div>
        </section>
      </main>

      <footer className="w-full max-w-[1200px] mx-auto px-[24px] py-[48px] border-t border-mist-gray flex flex-col md:flex-row items-center justify-between gap-[24px] text-[15px] font-sohne text-slate-gray">
        <div>
          &copy; {new Date().getFullYear()} CoDNA Systems. All rights reserved.
        </div>
        <div className="flex items-center gap-[24px]">
          <a href="#" className="hover:text-ink-black transition-colors">Privacy Policy</a>
          <a href="#" className="hover:text-ink-black transition-colors">Terms of Service</a>
          <a href="https://github.com" target="_blank" rel="noreferrer" className="hover:text-ink-black transition-colors">GitHub</a>
        </div>
      </footer>

      {loginError && (
        <div className="fixed bottom-6 left-1/2 z-50 w-[min(92vw,520px)] -translate-x-1/2 rounded-cards border border-red-200 bg-red-50 p-4 text-center text-sm text-red-700 shadow-subtle-2">
          {loginError}
        </div>
      )}
    </div>
  );
}
