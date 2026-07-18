"use client";

import React from "react";

// 1. Region Table (top-left)
export function RegionTableArtifact() {
  const mockFiles = [
    { path: "src/main.py", lang: "Python", size: "12.4 KB", status: "ready" },
    { path: "app/core/config.py", lang: "Python", size: "4.8 KB", status: "ready" },
    { path: "web/app/page.tsx", lang: "TypeScript", size: "18.1 KB", status: "ready" },
    { path: "package.json", lang: "JSON", size: "1.2 KB", status: "ready" },
    { path: "README.md", lang: "Markdown", size: "2.5 KB", status: "ready" },
  ];

  return (
    <div className="bg-paper-white rounded-elevatedcards border border-ink-black/[0.05] shadow-subtle-3 p-[16px] w-[288px] max-w-full text-left transition-transform duration-500 hover:-translate-y-1 hover:rotate-1">
      <div className="flex items-center justify-between mb-[12px] border-b border-mist-gray pb-[8px]">
        <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider">
          Source Inventory
        </span>
        <span className="w-[8px] h-[8px] rounded-full bg-emerald-500 animate-pulse" />
      </div>
      <div className="space-y-[8px]">
        {mockFiles.map((file, i) => (
          <div key={i} className="flex items-center justify-between text-[13px] font-sohne py-[4px]">
            <div className="flex flex-col truncate pr-[8px]">
              <span className="text-ink-black font-w500 truncate">{file.path}</span>
              <span className="text-ash-gray text-[11px]">{file.lang}</span>
            </div>
            <div className="flex items-center gap-[8px] flex-shrink-0">
              <span className="text-slate-gray text-[12px]">{file.size}</span>
              <span className="px-[6px] py-[2px] text-[10px] rounded-buttons bg-emerald-50 text-emerald-700 font-w500 uppercase tracking-wide">
                {file.status}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// 2. Registration / Presence Card (right)
export function RegistrationCardArtifact() {
  return (
    <div className="bg-paper-white rounded-elevatedcards border border-ink-black/[0.05] shadow-subtle-3 p-[16px] w-[260px] max-w-full text-left relative transition-transform duration-500 hover:-translate-y-1 hover:-rotate-1">
      <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider block mb-[8px]">
        Active Session
      </span>
      <h4 className="text-[16px] font-sohne font-w500 text-ink-black mb-[16px]">
        fomo-ash/CoDNA
      </h4>

      <div className="flex items-center gap-[12px]">
        {/* Avatars */}
        <div className="flex -space-x-[8px]">
          <div className="relative group">
            <div className="w-[36px] h-[36px] rounded-full bg-[#dcfce7] text-[#15803d] flex items-center justify-center text-xs font-sohne font-w500 border-2 border-paper-white">
              JB
            </div>
            <svg
              className="absolute -top-[4px] -left-[4px] w-[16px] h-[16px] text-emerald-600 drop-shadow"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M4 4l11.733 11.733-3.733 1.067 2.667 5.333-2.133 1.067-2.667-5.333-3.733 3.733z" />
            </svg>
          </div>

          <div className="relative group">
            <div className="w-[36px] h-[36px] rounded-full bg-[#dbeafe] text-[#1d4ed8] flex items-center justify-center text-xs font-sohne font-w500 border-2 border-paper-white">
              AF
            </div>
            <svg
              className="absolute -bottom-[4px] -right-[4px] w-[16px] h-[16px] text-blue-600 drop-shadow rotate-90"
              fill="currentColor"
              viewBox="0 0 24 24"
            >
              <path d="M4 4l11.733 11.733-3.733 1.067 2.667 5.333-2.133 1.067-2.667-5.333-3.733 3.733z" />
            </svg>
          </div>
        </div>

        <div className="text-[13px] font-sohne text-slate-gray">
          <span className="font-w500 text-ink-black">2 collaborators</span> scanning
        </div>
      </div>

      <div className="mt-[16px] pt-[12px] border-t border-mist-gray flex items-center justify-between text-[11px] font-sohne text-ash-gray">
        <span>Cloned 5m ago</span>
        <span className="text-sienna-brown font-w500">Ready for query</span>
      </div>
    </div>
  );
}

// 3. Activation Chart (bottom-left)
export function ActivationChartArtifact() {
  return (
    <div className="bg-paper-white rounded-elevatedcards border border-ink-black/[0.05] shadow-subtle-3 p-[20px] w-[240px] max-w-full text-left transition-transform duration-500 hover:-translate-y-1 hover:rotate-1">
      <div className="flex flex-col mb-[8px]">
        <span className="text-[12px] font-sohne font-w500 text-ash-gray uppercase tracking-wider">
          Source Files Scan
        </span>
        <div className="flex items-baseline gap-[8px] mt-[4px]">
          <span className="text-[24px] font-sohne font-w500 text-ink-black tracking-tight">
            1,483
          </span>
          <span className="text-[12px] font-sohne font-w500 text-emerald-600">
            ↑ 5.5x
          </span>
        </div>
        <span className="text-[11px] font-sohne text-slate-gray">
          vs last repository
        </span>
      </div>

      <div className="h-[64px] w-full mt-[8px] relative">
        <svg className="w-full h-full overflow-visible" viewBox="0 0 100 30">
          <path
            d="M0,25 Q15,10 30,18 T60,5 T90,20 T100,8"
            fill="none"
            stroke="var(--color-sienna-brown)"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <circle cx="100" cy="8" r="3.5" fill="var(--color-sienna-brown)" className="animate-ping" />
          <circle cx="100" cy="8" r="2.5" fill="var(--color-sienna-brown)" />
        </svg>
      </div>
    </div>
  );
}

// 4. AI Composer (bottom-center)
export function AIComposerArtifact() {
  return (
    <div className="bg-paper-white rounded-inputs border border-ink-black/[0.06] shadow-subtle-2 p-[14px] w-[420px] max-w-full text-left transition-transform duration-500 hover:-translate-y-1">
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
          readOnly
          placeholder="Ask anything..."
          className="flex-1 bg-transparent border-none outline-none text-[15px] font-sohne text-ink-black placeholder-smoke-gray"
        />

        <button className="w-[40px] h-[40px] rounded-full bg-ink-black text-paper-white flex items-center justify-center hover:bg-ink-black/90 active:scale-95 transition-all">
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
  );
}
