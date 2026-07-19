export type RepositoryStatus =
  | "registered"
  | "cloning"
  | "indexing"
  | "ready"
  | "failed"
  | "archived";

export type JobStatus = "queued" | "running" | "completed" | "failed";

export interface User {
  id: string;
  github_id: string;
  username: string;
  email: string | null;
  name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Repository {
  id: string;
  github_id: string;
  name: string;
  full_name: string;
  default_branch: string;
  clone_url: string;
  visibility: "public" | "private" | string;
  status: RepositoryStatus;
  created_at: string;
  updated_at: string;
  last_cloned_at?: string;
  last_indexed_at?: string;
}

export interface GitHubRepository {
  github_id: string;
  name: string;
  full_name: string;
  default_branch: string;
  clone_url: string;
  visibility: "public" | "private" | string;
  private: boolean;
}

export interface GitHubDiscoveryResponse {
  repositories: GitHubRepository[];
  page: number;
  per_page: number;
  has_next_page: boolean;
}

export interface RepositoryFile {
  id: string;
  repository_id: string;
  path: string;
  filename: string;
  extension: string | null;
  language: string | null;
  size_bytes: number;
  sha256: string;
  is_binary: boolean;
  discovered_at: string;
  created_at: string;
  updated_at: string;
}

export interface FilesResponse {
  files: RepositoryFile[];
  page: number;
  page_size: number;
  has_next_page: boolean;
}

export interface RepositoryStats {
  repository_id: string;
  total_files: number;
  source_files: number;
  binary_files: number;
  total_size_bytes: number;
  languages: Record<string, number>;
  last_scan_at: string;
}

export interface JobResponse {
  repository_id: string;
  job_id: string;
  status: JobStatus;
  error_message?: string | null;
}

export interface JobDetail {
  id: string;
  repository_id: string;
  status: JobStatus;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthTokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface RepositoryFileParseRead {
  id: string;
  repository_id: string;
  repository_file_id: string;
  path: string;
  language: string | null;
  parser: string | null;
  status: string;
  root_node_type: string | null;
  has_error: boolean;
  error_count: number;
  symbol_count: number;
  import_count: number;
  symbols: any[];
  imports: any[];
  parsed_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface RepositoryFileParseListResponse {
  parse_results: RepositoryFileParseRead[];
  page: number;
  page_size: number;
  has_next_page: boolean;
}

export interface RepositoryKnowledgeItemRead {
  id: string;
  repository_id: string;
  repository_file_id: string | null;
  path: string | null;
  source_type: string;
  item_type: string;
  name: string | null;
  extractor: string;
  data: Record<string, any>;
  extracted_at: string;
  created_at: string;
  updated_at: string;
}

export interface RepositoryKnowledgeItemListResponse {
  knowledge_items: RepositoryKnowledgeItemRead[];
  page: number;
  page_size: number;
  has_next_page: boolean;
}

export interface RepositoryChunkRead {
  id: string;
  repository_id: string;
  repository_file_id: string | null;
  path: string;
  chunk_type: string;
  source_type: string;
  title: string;
  language: string | null;
  content: string;
  start_line: number | null;
  end_line: number | null;
  metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export interface RepositoryChunkListResponse {
  chunks: RepositoryChunkRead[];
  page: number;
  page_size: number;
  has_next_page: boolean;
}

export interface RepositorySearchResult {
  chunk: RepositoryChunkRead;
  score: number;
  lexical_score: number;
  vector_score: number | null;
}

export interface RepositorySearchResponse {
  repository_id: string;
  query: string;
  results: RepositorySearchResult[];
  vector_search_used: boolean;
}

