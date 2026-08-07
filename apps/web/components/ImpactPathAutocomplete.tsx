"use client";

import React, { useState, useEffect, useRef } from "react";
import api from "../lib/api";

// Trie Implementation for fast prefix-based path searching
class TrieNode {
  children: Record<string, TrieNode> = {};
  isEndOfPath = false;
  fullPath = "";
}

class PathTrie {
  root = new TrieNode();
  allPaths: string[] = []; // Keep a flat list for fallback substring search

  insert(path: string) {
    this.allPaths.push(path);
    let node = this.root;
    const lowerPath = path.toLowerCase();
    for (const char of lowerPath) {
      if (!node.children[char]) {
        node.children[char] = new TrieNode();
      }
      node = node.children[char];
    }
    node.isEndOfPath = true;
    node.fullPath = path; // keep original case for display
  }

  search(query: string, limit = 20): string[] {
    if (!query) return [];
    
    // 1. Try Prefix Search (Trie)
    let node = this.root;
    let isPrefixMatch = true;
    const lowerQuery = query.toLowerCase();
    for (const char of lowerQuery) {
      if (!node.children[char]) {
        isPrefixMatch = false;
        break;
      }
      node = node.children[char];
    }

    const results = new Set<string>();

    if (isPrefixMatch) {
      const dfs = (currentNode: TrieNode) => {
        if (results.size >= limit) return;
        if (currentNode.isEndOfPath) results.add(currentNode.fullPath);
        for (const char in currentNode.children) {
          dfs(currentNode.children[char]);
        }
      };
      dfs(node);
    }

    // 2. Substring fallback if Trie yields fewer results
    if (results.size < limit) {
      const lowerQuery = query.toLowerCase();
      for (const path of this.allPaths) {
        if (results.size >= limit) break;
        if (path.toLowerCase().includes(lowerQuery)) {
          results.add(path);
        }
      }
    }

    return Array.from(results);
  }
}

interface ImpactPathAutocompleteProps {
  repositoryId: string;
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export default function ImpactPathAutocomplete({
  repositoryId,
  value,
  onChange,
  className = "",
}: ImpactPathAutocompleteProps) {
  const [trie, setTrie] = useState<PathTrie | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Load files and build Trie
  useEffect(() => {
    let isMounted = true;
    
    const loadFiles = async () => {
      try {
        let allFiles: {path: string}[] = [];
        let page = 1;
        let hasNextPage = true;
        
        while (hasNextPage && page <= 50) { // Limit to 50 pages (5000 files) to be safe
          const res = await api.getRepositoryFiles(repositoryId, { page, page_size: 100 });
          if (!isMounted) return;
          
          allFiles.push(...res.files);
          hasNextPage = res.has_next_page;
          page++;
        }
        
        const newTrie = new PathTrie();
        allFiles.forEach(file => {
          newTrie.insert(file.path);
        });
        setTrie(newTrie);
      } catch (err) {
        console.error("Failed to load files for autocomplete", err);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };
    
    loadFiles();
    
    return () => { isMounted = false; };
  }, [repositoryId]);

  // Handle outside click to close dropdown
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Update suggestions on input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    onChange(val);
    
    if (val && trie) {
      setSuggestions(trie.search(val));
      setIsOpen(true);
    } else {
      setSuggestions([]);
      setIsOpen(false);
    }
  };

  const handleSelect = (path: string) => {
    onChange(path);
    setIsOpen(false);
  };

  return (
    <div ref={wrapperRef} className="relative flex-1 min-w-[200px]">
      <input
        type="text"
        value={value}
        onChange={handleInputChange}
        onFocus={() => { if (value && suggestions.length > 0) setIsOpen(true); }}
        placeholder={isLoading ? "Loading paths..." : "Optional impact path, e.g. Dockerfile"}
        className={className}
        disabled={isLoading}
        autoComplete="off"
      />
      
      {isOpen && suggestions.length > 0 && (
        <div className="absolute z-10 w-full mt-1 bg-paper-white border border-mist-gray rounded-cards shadow-subtle max-h-60 overflow-y-auto">
          <ul className="py-1 text-[13px] font-mono text-ink-black">
            {suggestions.map((path) => {
              // Highlight matched part loosely
              const idx = path.toLowerCase().indexOf(value.toLowerCase());
              if (idx >= 0) {
                const before = path.slice(0, idx);
                const match = path.slice(idx, idx + value.length);
                const after = path.slice(idx + value.length);
                return (
                  <li
                    key={path}
                    onClick={() => handleSelect(path)}
                    className="px-3 py-1.5 hover:bg-fog-white cursor-pointer truncate transition-colors"
                  >
                    {before}<span className="bg-amber-100 font-bold">{match}</span>{after}
                  </li>
                );
              }
              
              return (
                <li
                  key={path}
                  onClick={() => handleSelect(path)}
                  className="px-3 py-1.5 hover:bg-fog-white cursor-pointer truncate transition-colors"
                >
                  {path}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
