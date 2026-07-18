import {
  User,
  Repository,
  GitHubDiscoveryResponse,
  FilesResponse,
  RepositoryStats,
  JobResponse,
  JobDetail,
  RepositoryStatus,
  JobStatus
} from "../types/api";

const API_BASE_URL = typeof window !== "undefined" ? (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001") : "http://localhost:8001";

// For mockup, we default to mock mode to make the app fully interactive immediately.
const USE_MOCK = true;

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
      sha256: "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
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
};

export default api;
