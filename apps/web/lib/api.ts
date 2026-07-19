import {
  User,
  Repository,
  GitHubDiscoveryResponse,
  FilesResponse,
  RepositoryFile,
  RepositoryStats,
  JobResponse,
  JobDetail,
  RepositoryStatus,
  JobStatus,
  AuthTokenResponse,
  RepositoryFileParseRead,
  RepositoryFileParseListResponse,
  RepositoryKnowledgeItemRead,
  RepositoryKnowledgeItemListResponse,
  RepositoryChunkRead,
  RepositoryChunkListResponse,
  RepositorySearchResult,
  RepositorySearchResponse
} from "../types/api";

const API_BASE_URL = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001") : "http://localhost:8001";

// Use the real API and GitHub OAuth flow in local development and deployment.
const USE_MOCK = false;

// --- Mock State Store (in localStorage) ---
const MOCK_STORAGE_KEY = "codna_mock_db";

interface MockDB {
  importedRepos: Repository[];
  jobs: Record<string, JobDetail>;
}

const DEFAULT_MOCK_DB: MockDB = {
  importedRepos: [
    {
      id: "codna-core",
      github_id: "10001",
      name: "CoDNA",
      full_name: "fomo-ash/CoDNA",
      default_branch: "main",
      clone_url: "https://github.com/fomo-ash/CoDNA.git",
      visibility: "private",
      status: "ready",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: "react-ui",
      github_id: "10002",
      name: "react",
      full_name: "facebook/react",
      default_branch: "main",
      clone_url: "https://github.com/facebook/react.git",
      visibility: "public",
      status: "registered",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  ],
  jobs: {}
};

function getMockDB(): MockDB {
  if (typeof window === "undefined") return DEFAULT_MOCK_DB;
  const data = localStorage.getItem(MOCK_STORAGE_KEY);
  if (!data) {
    localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(DEFAULT_MOCK_DB));
    return DEFAULT_MOCK_DB;
  }
  try {
    return JSON.parse(data);
  } catch {
    return DEFAULT_MOCK_DB;
  }
}

function saveMockDB(db: MockDB) {
  if (typeof window === "undefined") return;
  localStorage.setItem(MOCK_STORAGE_KEY, JSON.stringify(db));
}

// Pre-defined GitHub repositories to discover
const MOCK_GITHUB_REPOS = [
  { github_id: "10001", name: "CoDNA", full_name: "fomo-ash/CoDNA", default_branch: "main", clone_url: "https://github.com/fomo-ash/CoDNA.git", visibility: "private", private: true },
  { github_id: "10002", name: "react", full_name: "facebook/react", default_branch: "main", clone_url: "https://github.com/facebook/react.git", visibility: "public", private: false },
  { github_id: "10003", name: "next.js", full_name: "vercel/next.js", default_branch: "canary", clone_url: "https://github.com/vercel/next.js.git", visibility: "public", private: false },
  { github_id: "10004", name: "tailwindcss", full_name: "tailwindlabs/tailwindcss", default_branch: "main", clone_url: "https://github.com/tailwindlabs/tailwindcss.git", visibility: "public", private: false },
  { github_id: "10005", name: "private-secrets", full_name: "fomo-ash/private-secrets", default_branch: "main", clone_url: "https://github.com/fomo-ash/private-secrets.git", visibility: "private", private: true },
  { github_id: "10006", name: "rust-analyzer", full_name: "rust-lang/rust-analyzer", default_branch: "master", clone_url: "https://github.com/rust-lang/rust-analyzer.git", visibility: "public", private: false },
];

// Pre-defined file structures for repos
const MOCK_FILES_BY_REPO: Record<string, { path: string; lang: string; size: number }[]> = {
  "codna-core": [
    { path: "apps/api/app/main.py", lang: "Python", size: 1820 },
    { path: "apps/api/app/core/config.py", lang: "Python", size: 1293 },
    { path: "apps/api/app/modules/auth/service.py", lang: "Python", size: 5229 },
    { path: "apps/api/app/modules/auth/router.py", lang: "Python", size: 1651 },
    { path: "apps/api/app/modules/repositories/router.py", lang: "Python", size: 3120 },
    { path: "apps/web/app/page.tsx", lang: "TypeScript", size: 8432 },
    { path: "apps/web/app/dashboard/page.tsx", lang: "TypeScript", size: 12450 },
    { path: "apps/web/app/globals.css", lang: "CSS", size: 2314 },
    { path: "apps/web/lib/api.ts", lang: "TypeScript", size: 5892 },
    { path: "package.json", lang: "JSON", size: 599 },
    { path: "README.md", lang: "Markdown", size: 1953 },
    { path: "docs/API.md", lang: "Markdown", size: 6427 },
    { path: "docs/FRONTEND_TEAMMATE_WORKPLAN.md", lang: "Markdown", size: 10654 },
  ],
  "react-ui": [
    { path: "packages/react/src/React.js", lang: "JavaScript", size: 4500 },
    { path: "packages/react-dom/src/client/ReactDOM.js", lang: "JavaScript", size: 8200 },
    { path: "packages/shared/ReactTypes.js", lang: "JavaScript", size: 3200 },
    { path: "package.json", lang: "JSON", size: 1200 },
    { path: "README.md", lang: "Markdown", size: 5800 },
  ],
  "default": [
    { path: "src/index.ts", lang: "TypeScript", size: 2400 },
    { path: "src/utils.ts", lang: "TypeScript", size: 1800 },
    { path: "package.json", lang: "JSON", size: 800 },
    { path: "README.md", lang: "Markdown", size: 1400 },
  ]
};

// --- Live fetch helper ---
function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("codedna_jwt");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }
  return headers;
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}/api/v1${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    let errorDetail = "An error occurred";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }

  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// --- Mock API Implementations ---
const mockApi = {
  getGithubLoginUrl: async (): Promise<{ authorization_url: string }> => {
    const mockAuthUrl = typeof window !== "undefined"
      ? `${window.location.origin}/?mock_callback=true`
      : "http://localhost:3000/?mock_callback=true";
    return { authorization_url: mockAuthUrl };
  },

  getCurrentUser: async (): Promise<User> => {
    const token = localStorage.getItem("codedna_jwt");
    if (!token) {
      throw new Error("Missing/invalid CoDNA JWT");
    }
    return {
      id: "13834d99-e025-48fe-a640-067f600bb9a2",
      github_id: "12345",
      username: "octocat",
      email: "octocat@github.com",
      name: "The Octocat",
      avatar_url: "https://avatars.githubusercontent.com/u/583231?v=4",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
  },

  getGithubRepositories: async (
    params: {
      visibility?: string;
      sort?: string;
      page?: number;
      per_page?: number;
    } = {}
  ): Promise<GitHubDiscoveryResponse> => {
    const visibility = params.visibility || "all";
    const filtered = MOCK_GITHUB_REPOS.filter(repo => {
      if (visibility === "public") return !repo.private;
      if (visibility === "private") return repo.private;
      return true;
    });

    const page = params.page || 1;
    const perPage = params.per_page || 15;
    const start = (page - 1) * perPage;
    const end = start + perPage;

    return {
      repositories: filtered.slice(start, end),
      page,
      per_page: perPage,
      has_next_page: end < filtered.length
    };
  },

  importRepository: async (
    payload: { github_id: string } | { full_name: string }
  ): Promise<Repository> => {
    const db = getMockDB();

    const githubRepo = MOCK_GITHUB_REPOS.find(repo => {
      if ("github_id" in payload) return repo.github_id === payload.github_id;
      if ("full_name" in payload) return repo.full_name === payload.full_name;
      return false;
    });

    if (!githubRepo) {
      throw new Error("GitHub repository is not found or inaccessible");
    }

    const exists = db.importedRepos.some(r => r.github_id === githubRepo.github_id);
    if (exists) {
      throw new Error("The caller already imported the GitHub repository");
    }

    const newRepo: Repository = {
      id: githubRepo.name.toLowerCase() + "-id",
      github_id: githubRepo.github_id,
      name: githubRepo.name,
      full_name: githubRepo.full_name,
      default_branch: githubRepo.default_branch,
      clone_url: githubRepo.clone_url,
      visibility: githubRepo.visibility,
      status: "registered",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    db.importedRepos.push(newRepo);
    saveMockDB(db);

    return newRepo;
  },

  retryRepositoryEmbeddings: async (id: string): Promise<Repository> => {
    const db = getMockDB();
    const repository = db.importedRepos.find((item) => item.id === id);
    if (!repository) throw new Error("Repository not found");
    repository.embedding_status = "completed";
    repository.embedding_error_message = null;
    saveMockDB(db);
    return repository;
  },

  getImportedRepositories: async (): Promise<Repository[]> => {
    const db = getMockDB();
    return db.importedRepos;
  },

  getRepository: async (id: string): Promise<Repository> => {
    const db = getMockDB();
    const repo = db.importedRepos.find(r => r.id === id);
    if (!repo) {
      throw new Error("Repository not found");
    }
    return repo;
  },

  startIndexing: async (id: string): Promise<JobResponse> => {
    const db = getMockDB();
    const repoIndex = db.importedRepos.findIndex(r => r.id === id);
    if (repoIndex === -1) {
      throw new Error("Repository not found");
    }

    const jobId = "job-" + Math.floor(Math.random() * 100000);

    db.importedRepos[repoIndex].status = "indexing";

    db.jobs[jobId] = {
      id: jobId,
      repository_id: id,
      status: "queued",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };
    saveMockDB(db);

    let steps: JobStatus[] = ["running", "completed"];
    let delay = 2000;

    steps.forEach((step, idx) => {
      setTimeout(() => {
        const currentDb = getMockDB();
        if (currentDb.jobs[jobId]) {
          currentDb.jobs[jobId].status = step;
          currentDb.jobs[jobId].updated_at = new Date().toISOString();

          if (step === "completed") {
            const currentRepoIdx = currentDb.importedRepos.findIndex(r => r.id === id);
            if (currentRepoIdx !== -1) {
              currentDb.importedRepos[currentRepoIdx].status = "ready";
              currentDb.importedRepos[currentRepoIdx].last_cloned_at = new Date().toISOString();
              currentDb.importedRepos[currentRepoIdx].last_indexed_at = new Date().toISOString();
            }
          }
          saveMockDB(currentDb);
        }
      }, delay * (idx + 1));
    });

    return {
      repository_id: id,
      job_id: jobId,
      status: "queued",
    };
  },

  getRepositoryFiles: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      language?: string;
      extension?: string;
      path_prefix?: string;
    } = {}
  ): Promise<FilesResponse> => {
    const mockFiles = MOCK_FILES_BY_REPO[id] || MOCK_FILES_BY_REPO["default"];

    let list: RepositoryFile[] = mockFiles.map((f, index) => ({
      id: `${id}-file-${index}`,
      repository_id: id,
      path: f.path,
      filename: f.path.split("/").pop() || "",
      extension: f.path.split(".").pop() || "",
      language: f.lang,
      size_bytes: f.size,
      is_binary: f.lang === "Binary",
      discovered_at: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }));

    if (params.language) {
      list = list.filter(f => f.language?.toLowerCase() === params.language?.toLowerCase());
    }

    if (params.path_prefix) {
      list = list.filter(f => f.path.toLowerCase().includes(params.path_prefix!.toLowerCase()));
    }

    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    const start = (page - 1) * pageSize;
    const end = start + pageSize;

    return {
      files: list.slice(start, end),
      page,
      page_size: pageSize,
      has_next_page: end < list.length
    };
  },

  getRepositoryStats: async (id: string): Promise<RepositoryStats> => {
    const mockFiles = MOCK_FILES_BY_REPO[id] || MOCK_FILES_BY_REPO["default"];
    const totalFiles = mockFiles.length;
    const binaryFiles = mockFiles.filter(f => f.lang === "Binary").length;
    const sourceFiles = totalFiles - binaryFiles;
    const totalSizeBytes = mockFiles.reduce((sum, f) => sum + f.size, 0);

    const languages: Record<string, number> = {};
    mockFiles.forEach(f => {
      languages[f.lang] = (languages[f.lang] || 0) + 1;
    });

    return {
      repository_id: id,
      total_files: totalFiles,
      source_files: sourceFiles,
      binary_files: binaryFiles,
      total_size_bytes: totalSizeBytes,
      languages,
      last_scan_at: new Date().toISOString(),
    };
  },

  getJobStatus: async (jobId: string): Promise<JobDetail> => {
    const db = getMockDB();
    const job = db.jobs[jobId];
    if (!job) {
      throw new Error("Job not found");
    }
    return job;
  },

  githubCallback: async (code: string, state: string): Promise<AuthTokenResponse> => {
    localStorage.setItem("codedna_jwt", "mock_codedna_jwt_token_123456");
    return {
      access_token: "mock_codedna_jwt_token_123456",
      token_type: "bearer",
      expires_in: 3600,
      user: {
        id: "13834d99-e025-48fe-a640-067f600bb9a2",
        github_id: "12345",
        username: "octocat",
        email: "octocat@github.com",
        name: "The Octocat",
        avatar_url: "https://avatars.githubusercontent.com/u/583231?v=4",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }
    };
  },

  getRepositoryParseResults: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      status?: string;
      language?: string;
      path_prefix?: string;
    } = {}
  ): Promise<RepositoryFileParseListResponse> => {
    const mockFiles = MOCK_FILES_BY_REPO[id] || MOCK_FILES_BY_REPO["default"];

    let list: RepositoryFileParseRead[] = mockFiles.map((f, index) => {
      const isParserError = f.path.includes("router.py") && index % 2 === 0;
      const isUnsupported = f.lang === "Markdown" || f.lang === "CSS" || f.lang === "JSON";
      const isBinary = f.lang === "Binary";

      let status = "parsed";
      let error_message: string | null = null;
      let root_node_type: string | null = "module";

      if (isParserError) {
        status = "syntax_error";
        error_message = "SyntaxError: invalid syntax at line 12";
        root_node_type = null;
      } else if (isUnsupported) {
        status = "unsupported";
        root_node_type = null;
      } else if (isBinary) {
        status = "skipped";
        root_node_type = null;
      }

      return {
        id: `${id}-parse-${index}`,
        repository_id: id,
        repository_file_id: `${id}-file-${index}`,
        path: f.path,
        language: f.lang,
        parser: isUnsupported || isBinary ? null : f.lang.toLowerCase(),
        status,
        root_node_type,
        has_error: status === "syntax_error",
        error_count: status === "syntax_error" ? 1 : 0,
        symbol_count: status === "parsed" ? 2 : 0,
        import_count: status === "parsed" ? 1 : 0,
        symbols: status === "parsed" ? [
          { name: f.path.split("/").pop()?.split(".")[0] || "symbol", kind: "module_scope", start_line: 1, end_line: 100 },
          { name: "process_data", kind: "function", start_line: 15, end_line: 45 }
        ] : [],
        imports: status === "parsed" ? [
          { statement: "import os", start_line: 1, end_line: 1 }
        ] : [],
        parsed_at: new Date().toISOString(),
        error_message,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };
    });

    if (params.status) {
      list = list.filter(f => f.status === params.status);
    }
    if (params.language) {
      list = list.filter(f => f.language?.toLowerCase() === params.language?.toLowerCase());
    }
    if (params.path_prefix) {
      list = list.filter(f => f.path.toLowerCase().includes(params.path_prefix!.toLowerCase()));
    }

    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    const start = (page - 1) * pageSize;
    const end = start + pageSize;

    return {
      parse_results: list.slice(start, end),
      page,
      page_size: pageSize,
      has_next_page: end < list.length
    };
  },

  getRepositoryKnowledge: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      source_type?: string;
      item_type?: string;
      path_prefix?: string;
    } = {}
  ): Promise<RepositoryKnowledgeItemListResponse> => {
    const items: RepositoryKnowledgeItemRead[] = [
      {
        id: `${id}-k-1`,
        repository_id: id,
        repository_file_id: `${id}-file-readme`,
        path: "README.md",
        source_type: "documentation",
        item_type: "document",
        name: "Project Overview",
        extractor: "documentation",
        data: {
          title: "CodeDNA Documentation",
          heading_count: 5,
          link_count: 3,
          code_block_count: 2
        },
        extracted_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: `${id}-k-2`,
        repository_id: id,
        repository_file_id: `${id}-file-package`,
        path: "package.json",
        source_type: "configuration",
        item_type: "package_manifest",
        name: "Node Package Config",
        extractor: "configuration",
        data: {
          name: "@codedna/web",
          version: "0.1.0",
          private: true,
          dependencies: {
            "next": "16.0.0",
            "react": "19.0.0",
            "typescript": "5.0.0"
          }
        },
        extracted_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: `${id}-k-3`,
        repository_id: id,
        repository_file_id: `${id}-file-schema`,
        path: "prisma/schema.prisma",
        source_type: "database_schema",
        item_type: "prisma_model",
        name: "UserModel",
        extractor: "schema",
        data: {
          model_name: "User",
          fields_count: 8,
          relations: ["Repository", "Session"]
        },
        extracted_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      },
      {
        id: `${id}-k-4`,
        repository_id: id,
        repository_file_id: `${id}-file-config`,
        path: "next.config.ts",
        source_type: "configuration",
        item_type: "typescript_config",
        name: "Next Configuration",
        extractor: "configuration",
        data: {
          experimental_features: ["appDir"],
          react_strict_mode: true
        },
        extracted_at: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString()
      }
    ];

    let filtered = items;
    if (params.source_type) {
      filtered = filtered.filter(item => item.source_type === params.source_type);
    }
    if (params.item_type) {
      filtered = filtered.filter(item => item.item_type === params.item_type);
    }
    if (params.path_prefix) {
      filtered = filtered.filter(item => item.path?.toLowerCase().includes(params.path_prefix!.toLowerCase()));
    }

    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    const start = (page - 1) * pageSize;
    const end = start + pageSize;

    return {
      knowledge_items: filtered.slice(start, end),
      page,
      page_size: pageSize,
      has_next_page: end < filtered.length
    };
  },

  getRepositoryChunks: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      source_type?: string;
      chunk_type?: string;
    } = {}
  ): Promise<RepositoryChunkListResponse> => {
    const mockFiles = MOCK_FILES_BY_REPO[id] || MOCK_FILES_BY_REPO["default"];

    let list: RepositoryChunkRead[] = [];
    mockFiles.forEach((f, idx) => {
      if (f.lang === "Python") {
        list.push({
          id: `${id}-chunk-func-${idx}`,
          repository_id: id,
          repository_file_id: `${id}-file-${idx}`,
          path: f.path,
          chunk_type: "function",
          source_type: "source_code",
          title: `function: ${f.path.split("/").pop()?.split(".")[0] || "func"}()`,
          language: f.lang,
          content: `def run_task(db_session, payload):\n    \"\"\"Run background job mapping\"\"\"\n    logger.info("Executing task mapping for ${f.path}")\n    try:\n        result = process_data(payload)\n        db_session.save(result)\n        return {"status": "success", "result": result}\n    except Exception as e:\n        logger.error(f"Task failed: {e}")\n        raise TaskExecutionError(str(e))`,
          start_line: 10,
          end_line: 20,
          metadata: {
            stable_symbol_id: `codna:${f.path}:run_task`,
            relationships: {
              calls: [
                { symbol: "process_data", path: f.path, stable_symbol_id: `codna:${f.path}:process_data` },
                { symbol: "logger.info" }
              ],
              called_by: [],
              imports: [
                { symbol: "logging", path: "stdlib" }
              ],
              imported_by: [],
              inherits: [],
              implements: [],
              references: [],
              exports: [{ symbol: "run_task" }]
            }
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      } else if (f.lang === "TypeScript" || f.lang === "JavaScript") {
        list.push({
          id: `${id}-chunk-class-${idx}`,
          repository_id: id,
          repository_file_id: `${id}-file-${idx}`,
          path: f.path,
          chunk_type: "class",
          source_type: "source_code",
          title: `class: ${f.path.split("/").pop()?.split(".")[0] || "Class"}`,
          language: f.lang,
          content: `export class DataExplorer {\n  private endpoint: string;\n\n  constructor(endpoint: string) {\n    this.endpoint = endpoint;\n  }\n\n  async fetchAll(repoId: string) {\n    const response = await fetch(\`\${this.endpoint}/repositories/\${repoId}/files\`)\n    return response.json();\n  }\n}`,
          start_line: 1,
          end_line: 12,
          metadata: {
            stable_symbol_id: `codna:${f.path}:DataExplorer`,
            relationships: {
              calls: [
                { symbol: "fetch", path: "window.fetch" }
              ],
              called_by: [],
              imports: [],
              imported_by: [],
              inherits: [],
              implements: [],
              references: [],
              exports: [{ symbol: "DataExplorer" }]
            }
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      } else if (f.lang === "Markdown") {
        list.push({
          id: `${id}-chunk-doc-${idx}`,
          repository_id: id,
          repository_file_id: `${id}-file-${idx}`,
          path: f.path,
          chunk_type: "documentation_section",
          source_type: "documentation",
          title: `markdown: ${f.path}`,
          language: f.lang,
          content: `# ${f.path.split("/").pop()}\n\nThis document outlines how CodeDNA works and lists the developer details.\n\n## Sub Section\n- High fidelity layouts\n- Clean styling\n- Dynamic pagination`,
          start_line: 1,
          end_line: 15,
          metadata: {
            stable_symbol_id: `codna:${f.path}:readme_main`,
            relationships: {
              calls: [],
              called_by: [],
              imports: [],
              imported_by: [],
              inherits: [],
              implements: [],
              references: [],
              exports: []
            }
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      } else {
        list.push({
          id: `${id}-chunk-other-${idx}`,
          repository_id: id,
          repository_file_id: `${id}-file-${idx}`,
          path: f.path,
          chunk_type: "configuration",
          source_type: "configuration",
          title: `config: ${f.path}`,
          language: f.lang,
          content: `{\n  "name": "codedna-workspace",\n  "version": "1.0.0",\n  "private": true\n}`,
          start_line: 1,
          end_line: 5,
          metadata: {
            stable_symbol_id: `codna:${f.path}:config`,
            relationships: {
              calls: [],
              called_by: [],
              imports: [],
              imported_by: [],
              inherits: [],
              implements: [],
              references: [],
              exports: []
            }
          },
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        });
      }
    });

    if (params.source_type) {
      list = list.filter(c => c.source_type === params.source_type);
    }
    if (params.chunk_type) {
      list = list.filter(c => c.chunk_type === params.chunk_type);
    }

    const page = params.page || 1;
    const pageSize = params.page_size || 50;
    const start = (page - 1) * pageSize;
    const end = start + pageSize;

    return {
      chunks: list.slice(start, end),
      page,
      page_size: pageSize,
      has_next_page: end < list.length
    };
  },

  getRepositoryHistory: async (id: string): Promise<import("../types/api").RepositoryHistoryListResponse> => ({
    repository_id: id,
    artifacts: [],
  }),

  getChunk: async (chunkId: string): Promise<RepositoryChunkRead> => {
    const repoId = chunkId.split("-chunk-")[0] || "codna-core";
    const chunksRes = await mockApi.getRepositoryChunks(repoId);
    const matched = chunksRes.chunks.find(c => c.id === chunkId);

    if (matched) return matched;

    return {
      id: chunkId,
      repository_id: repoId,
      repository_file_id: `${repoId}-file-default`,
      path: "src/main.py",
      chunk_type: "function",
      source_type: "source_code",
      title: "function: main()",
      language: "Python",
      content: "def main():\n    print('Hello CodeDNA')",
      start_line: 1,
      end_line: 2,
      metadata: {
        stable_symbol_id: "codna:src/main.py:main",
        relationships: {
          calls: [],
          called_by: [],
          imports: [],
          imported_by: [],
          inherits: [],
          implements: [],
          references: [],
          exports: []
        }
      },
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
  },

  searchRepository: async (
    id: string,
    query: string,
    params: {
      source_type?: string;
      chunk_type?: string;
      limit?: number;
    } = {}
  ): Promise<RepositorySearchResponse> => {
    const chunksRes = await mockApi.getRepositoryChunks(id);
    let matchedChunks = chunksRes.chunks;

    if (query) {
      const q = query.toLowerCase();
      matchedChunks = matchedChunks.filter(c =>
        c.title.toLowerCase().includes(q) ||
        c.path.toLowerCase().includes(q) ||
        c.content.toLowerCase().includes(q)
      );
    }

    if (params.source_type) {
      matchedChunks = matchedChunks.filter(c => c.source_type === params.source_type);
    }

    if (params.chunk_type) {
      matchedChunks = matchedChunks.filter(c => c.chunk_type === params.chunk_type);
    }

    const results: RepositorySearchResult[] = matchedChunks.map((chunk, idx) => {
      const lexical_score = 0.5 + (1 / (idx + 1)) * 0.4;
      const vector_score = 0.4 + (1 / (idx + 1)) * 0.4;
      return {
        chunk,
        score: (lexical_score + vector_score) / 2,
        lexical_score,
        vector_score
      };
    });

    const limit = params.limit || 20;

    return {
      repository_id: id,
      query,
      results: results.slice(0, limit),
      vector_search_used: true
    };
  },
};

// Export active client wrapper (mock or live based on flag)
export const api = USE_MOCK ? mockApi : {
  getGithubLoginUrl: async (): Promise<{ authorization_url: string }> => {
    return request<{ authorization_url: string }>("/auth/github/login");
  },

  getCurrentUser: async (): Promise<User> => {
    return request<User>("/auth/me");
  },

  getGithubRepositories: async (
    params: {
      visibility?: string;
      sort?: string;
      page?: number;
      per_page?: number;
    } = {}
  ): Promise<GitHubDiscoveryResponse> => {
    const searchParams = new URLSearchParams();
    if (params.visibility) searchParams.append("visibility", params.visibility);
    if (params.sort) searchParams.append("sort", params.sort);
    if (params.page) searchParams.append("page", String(params.page));
    if (params.per_page) searchParams.append("per_page", String(params.per_page));

    const queryString = searchParams.toString();
    return request<GitHubDiscoveryResponse>(`/github/repositories?${queryString}`);
  },

  importRepository: async (
    payload: { github_id: string } | { full_name: string }
  ): Promise<Repository> => {
    return request<Repository>("/repositories", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  retryRepositoryEmbeddings: async (id: string): Promise<Repository> => {
    return request<Repository>(`/repositories/${id}/embeddings/retry`, { method: "POST" });
  },

  getImportedRepositories: async (): Promise<Repository[]> => {
    return request<Repository[]>("/repositories");
  },

  getRepository: async (id: string): Promise<Repository> => {
    return request<Repository>(`/repositories/${id}`);
  },

  startIndexing: async (id: string): Promise<JobResponse> => {
    return request<JobResponse>(`/repositories/${id}/index`, {
      method: "POST",
    });
  },

  getRepositoryFiles: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      language?: string;
      extension?: string;
      path_prefix?: string;
    } = {}
  ): Promise<FilesResponse> => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append("page", String(params.page));
    if (params.page_size) searchParams.append("page_size", String(params.page_size));
    if (params.language) searchParams.append("language", params.language);
    if (params.extension) searchParams.append("extension", params.extension);
    if (params.path_prefix) searchParams.append("path_prefix", params.path_prefix);

    const queryString = searchParams.toString();
    return request<FilesResponse>(`/repositories/${id}/files?${queryString}`);
  },

  getRepositoryStats: async (id: string): Promise<RepositoryStats> => {
    return request<RepositoryStats>(`/repositories/${id}/stats`);
  },

  getJobStatus: async (jobId: string): Promise<JobDetail> => {
    return request<JobDetail>(`/jobs/${jobId}`);
  },

  githubCallback: async (code: string, state: string): Promise<AuthTokenResponse> => {
    return request<AuthTokenResponse>(`/auth/github/callback?code=${code}&state=${state}`);
  },

  getRepositoryParseResults: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      status?: string;
      language?: string;
      path_prefix?: string;
    } = {}
  ): Promise<RepositoryFileParseListResponse> => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append("page", String(params.page));
    if (params.page_size) searchParams.append("page_size", String(params.page_size));
    if (params.status) searchParams.append("status", params.status);
    if (params.language) searchParams.append("language", params.language);
    if (params.path_prefix) searchParams.append("path_prefix", params.path_prefix);

    return request<RepositoryFileParseListResponse>(`/repositories/${id}/parse-results?${searchParams.toString()}`);
  },

  getRepositoryKnowledge: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      source_type?: string;
      item_type?: string;
      path_prefix?: string;
    } = {}
  ): Promise<RepositoryKnowledgeItemListResponse> => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append("page", String(params.page));
    if (params.page_size) searchParams.append("page_size", String(params.page_size));
    if (params.source_type) searchParams.append("source_type", params.source_type);
    if (params.item_type) searchParams.append("item_type", params.item_type);
    if (params.path_prefix) searchParams.append("path_prefix", params.path_prefix);

    return request<RepositoryKnowledgeItemListResponse>(`/repositories/${id}/knowledge?${searchParams.toString()}`);
  },

  getRepositoryChunks: async (
    id: string,
    params: {
      page?: number;
      page_size?: number;
      source_type?: string;
      chunk_type?: string;
    } = {}
  ): Promise<RepositoryChunkListResponse> => {
    const searchParams = new URLSearchParams();
    if (params.page) searchParams.append("page", String(params.page));
    if (params.page_size) searchParams.append("page_size", String(params.page_size));
    if (params.source_type) searchParams.append("source_type", params.source_type);
    if (params.chunk_type) searchParams.append("chunk_type", params.chunk_type);

    return request<RepositoryChunkListResponse>(`/repositories/${id}/chunks?${searchParams.toString()}`);
  },

  getRepositoryHistory: async (id: string): Promise<import("../types/api").RepositoryHistoryListResponse> => {
    return request(`/repositories/${id}/history`);
  },

  getChunk: async (chunkId: string): Promise<RepositoryChunkRead> => {
    return request<RepositoryChunkRead>(`/chunks/${chunkId}`);
  },

  searchRepository: async (
    id: string,
    query: string,
    params: {
      source_type?: string;
      chunk_type?: string;
      limit?: number;
    } = {}
  ): Promise<RepositorySearchResponse> => {
    const searchParams = new URLSearchParams();
    searchParams.append("query", query);
    if (params.source_type) searchParams.append("source_type", params.source_type);
    if (params.chunk_type) searchParams.append("chunk_type", params.chunk_type);
    if (params.limit) searchParams.append("limit", String(params.limit));

    return request<RepositorySearchResponse>(`/repositories/${id}/search?${searchParams.toString()}`);
  },

  askRepositoryQuestion: async (
    id: string,
    payload: { question: string; impact_path?: string; impact_depth?: number }
  ): Promise<import("../types/api").RepositoryQuestionResponse> => {
    return request(`/repositories/${id}/questions`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};

export default api;
