"use client";

import React from "react";
import Link from "next/link";
import { User } from "../types/api";

interface HeaderProps {
  user?: User | null;
  onLogout?: () => void;
  onOpenLoginModal?: () => void;
}

export default function Header({ user, onLogout, onOpenLoginModal }: HeaderProps) {
  const getInitials = (name: string | null, username: string) => {
    const text = name || username;
    if (!text) return "CD";
    const parts = text.split(" ");
    if (parts.length >= 2) {
      return (parts[0][0] + parts[1][0]).toUpperCase();
    }
    return text.slice(0, 2).toUpperCase();
  };

  return (
    <header className="w-full max-w-[1200px] mx-auto px-6 pt-6 pb-2 flex items-center justify-between bg-transparent z-40 relative">
      <Link href={user ? "/dashboard" : "/"} className="flex items-center gap-[8px] group">
        <span className="text-2xl text-ink-black font-signifier flex items-center gap-1.5 font-medium tracking-tight">
          <svg
            className="w-6 h-6 text-ink-black group-hover:rotate-12 transition-transform duration-300"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
            />
          </svg>
          CoDNA
        </span>
      </Link>

      <div className="flex items-center gap-[16px]">
        {user ? (
          <div className="flex items-center gap-[16px]">
            <div className="relative group cursor-pointer">
              <div className="w-[40px] h-[40px] rounded-buttons bg-blush-peach border border-sienna-brown/20 flex items-center justify-center text-[14px] font-sohne font-w500 text-sienna-brown transition-transform hover:scale-105">
                {getInitials(user.name, user.username)}
              </div>
              <div className="absolute -bottom-1 -right-1 bg-ink-black text-paper-white w-4 h-4 rounded-full flex items-center justify-center border border-paper-white text-[9px] shadow-sm">
                ↗
              </div>
              <div className="absolute right-0 top-12 bg-white text-ink-black text-xs py-1.5 px-3 rounded-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity duration-200 border border-mist-gray shadow-subtle whitespace-nowrap">
                Logged in as <span className="font-semibold">@{user.username}</span>
              </div>
            </div>

            <button
              onClick={onLogout}
              className="text-[16px] font-sohne font-w400 text-slate-gray hover:text-ink-black transition-colors"
            >
              Sign out
            </button>
          </div>
        ) : (
          <div className="flex items-center gap-[16px]">
            <button
              onClick={onOpenLoginModal}
              className="text-[16px] font-sohne font-w400 text-ink-black hover:underline hover:underline-offset-4 decoration-1 transition-all py-2"
            >
              Book a demo
            </button>
            <button
              onClick={onOpenLoginModal}
              className="h-[40px] px-[20px] rounded-buttons bg-ink-black text-paper-white hover:bg-ink-black/90 active:scale-[0.98] transition-all text-[16px] font-sohne font-w400 flex items-center justify-center"
            >
              Continue with GitHub
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
