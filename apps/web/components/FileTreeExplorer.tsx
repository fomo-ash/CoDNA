"use client";

import React, { useState, useMemo, useCallback } from "react";
import { RepositoryFile } from "../types/api";

/* ───────────────────────────── Types ───────────────────────────── */

interface TreeNode {
  name: string;
  path: string;           // full path for this segment
  isFolder: boolean;
  children: TreeNode[];
  file?: RepositoryFile;  // only on leaf files
}

interface FileTreeExplorerProps {
  files: RepositoryFile[];
  isLoading: boolean;
  filesSearch: string;
  setFilesSearch: (v: string) => void;
  filesLanguageFilter: string;
  setFilesLanguageFilter: (v: string) => void;
  languagesList: string[];
  filesPage: number;
  setFilesPage: (fn: (p: number) => number) => void;
  hasNextFilesPage: boolean;
  formatBytes: (bytes: number) => string;
}

/* ────────────────────── Icon & Color Helpers ───────────────────── */

const EXT_ICON_MAP: Record<string, { icon: string; color: string }> = {
  ts:    { icon: "TS",  color: "#3178c6" },
  tsx:   { icon: "TS",  color: "#3178c6" },
  js:    { icon: "JS",  color: "#f0db4f" },
  jsx:   { icon: "JS",  color: "#f0db4f" },
  py:    { icon: "PY",  color: "#3572a5" },
  rs:    { icon: "RS",  color: "#dea584" },
  go:    { icon: "GO",  color: "#00add8" },
  java:  { icon: "JV",  color: "#b07219" },
  rb:    { icon: "RB",  color: "#cc342d" },
  php:   { icon: "PH",  color: "#4f5d95" },
  css:   { icon: "CS",  color: "#563d7c" },
  scss:  { icon: "SC",  color: "#c6538c" },
  html:  { icon: "HT",  color: "#e34c26" },
  json:  { icon: "{}",  color: "#a8a832" },
  yaml:  { icon: "YM",  color: "#cb171e" },
  yml:   { icon: "YM",  color: "#cb171e" },
  md:    { icon: "MD",  color: "#519aba" },
  toml:  { icon: "TM",  color: "#9c4221" },
  lock:  { icon: "LK",  color: "#8b8b8b" },
  sh:    { icon: "SH",  color: "#4eaa25" },
  sql:   { icon: "SQ",  color: "#e38c00" },
  prisma:{ icon: "PR",  color: "#2d3748" },
  env:   { icon: "EV",  color: "#ecd53f" },
  dockerfile: { icon: "DK", color: "#384d54" },
  gitignore:  { icon: "GI", color: "#f05032" },
};

function getFileIcon(filename: string): { icon: string; color: string } {
  const lower = filename.toLowerCase();

  // special full-name matches
  if (lower === "dockerfile" || lower.startsWith("dockerfile."))
    return EXT_ICON_MAP.dockerfile;
  if (lower === ".gitignore" || lower === ".dockerignore")
    return EXT_ICON_MAP.gitignore;
  if (lower.startsWith(".env"))
    return EXT_ICON_MAP.env;

  const ext = lower.split(".").pop() || "";
  return EXT_ICON_MAP[ext] || { icon: "FL", color: "#777b86" };
}

/* ────────────────────── Tree Builder ──────────────────────────── */

function buildTree(files: RepositoryFile[]): TreeNode[] {
  const root: TreeNode = {
    name: "",
    path: "",
    isFolder: true,
    children: [],
  };

  for (const file of files) {
    const parts = file.path.split("/");
    let current = root;

    for (let i = 0; i < parts.length; i++) {
      const part = parts[i];
      const isLast = i === parts.length - 1;
      const fullPath = parts.slice(0, i + 1).join("/");

      if (isLast) {
        // file leaf
        current.children.push({
          name: part,
          path: fullPath,
          isFolder: false,
          children: [],
          file,
        });
      } else {
        // folder
        let folder = current.children.find(
          (c) => c.isFolder && c.name === part
        );
        if (!folder) {
          folder = {
            name: part,
            path: fullPath,
            isFolder: true,
            children: [],
          };
          current.children.push(folder);
        }
        current = folder;
      }
    }
  }

  // Sort: folders first (alphabetical), then files (alphabetical)
  const sortNodes = (nodes: TreeNode[]): TreeNode[] => {
    const folders = nodes
      .filter((n) => n.isFolder)
      .sort((a, b) => a.name.localeCompare(b.name));
    const fileNodes = nodes
      .filter((n) => !n.isFolder)
      .sort((a, b) => a.name.localeCompare(b.name));

    folders.forEach((f) => {
      f.children = sortNodes(f.children);
    });

    return [...folders, ...fileNodes];
  };

  return sortNodes(root.children);
}

function countFiles(node: TreeNode): number {
  if (!node.isFolder) return 1;
  return node.children.reduce((sum, c) => sum + countFiles(c), 0);
}

function collectAllFolderPaths(nodes: TreeNode[]): Set<string> {
  const paths = new Set<string>();
  const walk = (list: TreeNode[]) => {
    for (const n of list) {
      if (n.isFolder) {
        paths.add(n.path);
        walk(n.children);
      }
    }
  };
  walk(nodes);
  return paths;
}

/* ───────────────────── SVG Icons ──────────────────────────────── */

function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 16 16"
      fill="none"
      className={`file-tree-chevron ${open ? "file-tree-chevron--open" : ""}`}
    >
      <path
        d="M6 4L10 8L6 12"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function FolderIcon({ open }: { open: boolean }) {
  if (open) {
    return (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
        <path
          d="M2 6C2 4.89543 2.89543 4 4 4H9L11 6H20C21.1046 6 22 6.89543 22 8V9H4V6Z"
          fill="#d4a537"
          opacity="0.85"
        />
        <path
          d="M3 9H21L19.5 19H4.5L3 9Z"
          fill="#d4a537"
        />
      </svg>
    );
  }
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
      <path
        d="M2 6C2 4.89543 2.89543 4 4 4H9L11 6H20C21.1046 6 22 6.89543 22 8V18C22 19.1046 21.1046 20 20 20H4C2.89543 20 2 19.1046 2 18V6Z"
        fill="#d4a537"
      />
    </svg>
  );
}

/* ───────────────────── Tree Row Component ─────────────────────── */

interface TreeRowProps {
  node: TreeNode;
  depth: number;
  expandedPaths: Set<string>;
  toggleFolder: (path: string) => void;
  selectedPath: string | null;
  setSelectedPath: (path: string | null) => void;
  formatBytes: (bytes: number) => string;
}

function TreeRow({
  node,
  depth,
  expandedPaths,
  toggleFolder,
  selectedPath,
  setSelectedPath,
  formatBytes,
}: TreeRowProps) {
  const isExpanded = expandedPaths.has(node.path);
  const isSelected = selectedPath === node.path;
  const fileCount = node.isFolder ? countFiles(node) : 0;
  const iconInfo = node.isFolder ? null : getFileIcon(node.name);

  const handleClick = () => {
    if (node.isFolder) {
      toggleFolder(node.path);
    } else {
      setSelectedPath(node.path === selectedPath ? null : node.path);
    }
  };

  return (
    <>
      <div
        className={`file-tree-row ${isSelected ? "file-tree-row--selected" : ""}`}
        onClick={handleClick}
        role="treeitem"
        aria-expanded={node.isFolder ? isExpanded : undefined}
        title={node.path}
      >
        {/* Indent guides */}
        {Array.from({ length: depth }).map((_, i) => (
          <span key={i} className="file-tree-indent-guide" />
        ))}

        {/* Chevron / spacer */}
        {node.isFolder ? (
          <span className="file-tree-chevron-wrap">
            <ChevronIcon open={isExpanded} />
          </span>
        ) : (
          <span className="file-tree-chevron-spacer" />
        )}

        {/* Icon */}
        {node.isFolder ? (
          <span className="file-tree-icon-wrap">
            <FolderIcon open={isExpanded} />
          </span>
        ) : (
          <span
            className="file-tree-file-badge"
            style={{ backgroundColor: iconInfo!.color }}
          >
            {iconInfo!.icon}
          </span>
        )}

        {/* Name */}
        <span className={`file-tree-name ${node.isFolder ? "file-tree-name--folder" : ""}`}>
          {node.name}
        </span>

        {/* Meta (right side) */}
        <span className="file-tree-meta">
          {node.isFolder ? (
            <span className="file-tree-count-badge">{fileCount}</span>
          ) : node.file ? (
            <span className="file-tree-size">{formatBytes(node.file.size_bytes)}</span>
          ) : null}
        </span>
      </div>

      {/* Render children if folder is expanded */}
      {node.isFolder && (
        <div
          className={`file-tree-children ${isExpanded ? "file-tree-children--open" : ""}`}
        >
          <div className="file-tree-children-inner">
            {node.children.map((child) => (
              <TreeRow
                key={child.path}
                node={child}
                depth={depth + 1}
                expandedPaths={expandedPaths}
                toggleFolder={toggleFolder}
                selectedPath={selectedPath}
                setSelectedPath={setSelectedPath}
                formatBytes={formatBytes}
              />
            ))}
          </div>
        </div>
      )}
    </>
  );
}

/* ──────────────── File Detail Panel ───────────────────────────── */

function FileDetailPanel({
  file,
  formatBytes,
  onClose,
}: {
  file: RepositoryFile;
  formatBytes: (b: number) => string;
  onClose: () => void;
}) {
  const iconInfo = getFileIcon(file.filename || file.path.split("/").pop() || "");

  return (
    <div className="file-tree-detail-panel">
      <div className="file-tree-detail-header">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="file-tree-file-badge"
            style={{ backgroundColor: iconInfo.color }}
          >
            {iconInfo.icon}
          </span>
          <span className="font-medium text-ink-black truncate text-[14px]">
            {file.filename || file.path.split("/").pop()}
          </span>
        </div>
        <button
          onClick={onClose}
          className="file-tree-detail-close"
          title="Close"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>
      <div className="file-tree-detail-body">
        <div className="file-tree-detail-row">
          <span className="file-tree-detail-label">Full Path</span>
          <span className="file-tree-detail-value font-mono">{file.path}</span>
        </div>
        <div className="file-tree-detail-row">
          <span className="file-tree-detail-label">Language</span>
          <span className="file-tree-detail-value">
            {file.is_binary ? "Binary" : file.language || "Unknown"}
          </span>
        </div>
        <div className="file-tree-detail-row">
          <span className="file-tree-detail-label">Size</span>
          <span className="file-tree-detail-value">{formatBytes(file.size_bytes)}</span>
        </div>
        <div className="file-tree-detail-row">
          <span className="file-tree-detail-label">Extension</span>
          <span className="file-tree-detail-value font-mono">{file.extension || "—"}</span>
        </div>
        <div className="file-tree-detail-row">
          <span className="file-tree-detail-label">Discovered</span>
          <span className="file-tree-detail-value">
            {new Date(file.discovered_at).toLocaleDateString()}
          </span>
        </div>
      </div>
    </div>
  );
}

/* ────────────────── Main Component ────────────────────────────── */

export default function FileTreeExplorer({
  files,
  isLoading,
  filesSearch,
  setFilesSearch,
  filesLanguageFilter,
  setFilesLanguageFilter,
  languagesList,
  filesPage,
  setFilesPage,
  hasNextFilesPage,
  formatBytes,
}: FileTreeExplorerProps) {
  const [expandedPaths, setExpandedPaths] = useState<Set<string>>(new Set());
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [allExpanded, setAllExpanded] = useState(false);

  const tree = useMemo(() => buildTree(files), [files]);

  const allFolderPaths = useMemo(() => collectAllFolderPaths(tree), [tree]);

  // Auto-expand top-level folders on first render
  useMemo(() => {
    if (tree.length > 0 && expandedPaths.size === 0) {
      const topLevel = new Set<string>();
      tree.forEach((n) => {
        if (n.isFolder) topLevel.add(n.path);
      });
      setExpandedPaths(topLevel);
    }
  }, [tree]);

  const toggleFolder = useCallback((path: string) => {
    setExpandedPaths((prev) => {
      const next = new Set(prev);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  }, []);

  const expandAll = useCallback(() => {
    setExpandedPaths(new Set(allFolderPaths));
    setAllExpanded(true);
  }, [allFolderPaths]);

  const collapseAll = useCallback(() => {
    setExpandedPaths(new Set());
    setAllExpanded(false);
  }, []);

  const selectedFile = useMemo(() => {
    if (!selectedPath) return null;
    return files.find((f) => f.path === selectedPath) || null;
  }, [selectedPath, files]);

  return (
    <div className="file-tree-explorer space-y-[24px] animate-in fade-in duration-200">
      {/* Toolbar */}
      <div className="file-tree-toolbar">
        <div className="file-tree-toolbar-left">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" className="text-slate-gray">
            <path strokeLinecap="round" strokeLinejoin="round" d="M2 6C2 4.89543 2.89543 4 4 4H9L11 6H20C21.1046 6 22 6.89543 22 8V18C22 19.1046 21.1046 20 20 20H4C2.89543 20 2 19.1046 2 18V6Z" />
          </svg>
          <span className="file-tree-toolbar-title">Explorer</span>
          <span className="file-tree-toolbar-count">{files.length} files</span>
        </div>
        <div className="file-tree-toolbar-actions">
          <button
            onClick={expandAll}
            className="file-tree-toolbar-btn"
            title="Expand all"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4h16v4M12 4v16M8 20h8" />
            </svg>
          </button>
          <button
            onClick={collapseAll}
            className="file-tree-toolbar-btn"
            title="Collapse all"
          >
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 8V4h16v4M8 12h8" />
            </svg>
          </button>
        </div>
      </div>

      {/* Search & Language Filter */}
      <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-[12px] bg-fog-white border border-ink-black/[0.05] p-[12px] rounded-cards">
        <div className="relative flex-1">
          <svg
            className="absolute left-3 top-1/2 -translate-y-1/2 text-ash-gray pointer-events-none"
            width="15"
            height="15"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            type="text"
            placeholder="Filter by path (e.g. src/utils)..."
            value={filesSearch}
            onChange={(e) => setFilesSearch(e.target.value)}
            className="w-full bg-paper-white border border-ink-black/[0.1] rounded-inputs pl-9 pr-4 py-[7px] text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all"
          />
        </div>
        <select
          value={filesLanguageFilter}
          onChange={(e) => setFilesLanguageFilter(e.target.value)}
          className="bg-paper-white border border-ink-black/[0.1] rounded-inputs px-[14px] py-[7px] text-[13px] font-sohne text-ink-black focus:outline-none focus:ring-1 focus:ring-ink-black transition-all cursor-pointer"
        >
          <option value="">All Languages</option>
          {languagesList.map((lang) => (
            <option key={lang} value={lang}>{lang}</option>
          ))}
        </select>
      </div>

      {/* Tree + Detail Layout */}
      <div className="file-tree-layout">
        {/* Tree Panel */}
        <div className="file-tree-panel">
          {isLoading && files.length === 0 ? (
            <div className="file-tree-empty">
              <div className="w-5 h-5 rounded-full border-2 border-mist-gray border-t-ink-black animate-spin" />
              <span>Cataloging files...</span>
            </div>
          ) : files.length === 0 ? (
            <div className="file-tree-empty">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2" className="text-ash-gray">
                <path strokeLinecap="round" strokeLinejoin="round" d="M2 6C2 4.89543 2.89543 4 4 4H9L11 6H20C21.1046 6 22 6.89543 22 8V18C22 19.1046 21.1046 20 20 20H4C2.89543 20 2 19.1046 2 18V6Z" />
              </svg>
              <span>No files match your filters.</span>
            </div>
          ) : (
            <div className="file-tree-scroll" role="tree">
              {tree.map((node) => (
                <TreeRow
                  key={node.path}
                  node={node}
                  depth={0}
                  expandedPaths={expandedPaths}
                  toggleFolder={toggleFolder}
                  selectedPath={selectedPath}
                  setSelectedPath={setSelectedPath}
                  formatBytes={formatBytes}
                />
              ))}
            </div>
          )}
        </div>

        {/* Detail Panel */}
        {selectedFile && (
          <FileDetailPanel
            file={selectedFile}
            formatBytes={formatBytes}
            onClose={() => setSelectedPath(null)}
          />
        )}
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between border-t border-mist-gray pt-[14px] text-[13px] text-slate-gray">
        <span>Showing page {filesPage}</span>
        <div className="flex items-center gap-[8px]">
          <button
            disabled={filesPage === 1}
            onClick={() => setFilesPage((p) => Math.max(1, p - 1))}
            className="h-[30px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-40 disabled:cursor-not-allowed transition-all text-[12px] cursor-pointer"
          >
            Previous
          </button>
          <button
            disabled={!hasNextFilesPage}
            onClick={() => setFilesPage((p) => p + 1)}
            className="h-[30px] px-[12px] rounded-buttons bg-transparent border border-mist-gray text-slate-gray hover:text-ink-black disabled:opacity-40 disabled:cursor-not-allowed transition-all text-[12px] cursor-pointer"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  );
}
