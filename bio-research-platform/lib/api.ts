"use client"

// ── 类型定义 ────────────────────────────────────

export interface AnalysisRequest {
  question: string
  question_type?: string
  keywords?: string[]
  log2fc?: number
  padj?: number
  top_n?: number
}

export interface TaskStatus {
  task_id: string
  status: "pending" | "running" | "completed" | "failed"
  progress: number
  message: string
  created_at: string
  updated_at: string
}

export interface IntentResult {
  disease_type: string
  research_purpose: string
  confidence: number
  research_area: string
  keywords: string[]
}

export interface LiteratureItem {
  title: string
  authors: string
  journal: string
  year: string
  pmid: string
  abstract: string
  key_findings: string
}

export interface GeneItem {
  gene_symbol: string
  gene_name: string
  score: number
  description: string
}

export interface TargetItem {
  ranking: number
  gene: string
  total_score: number
  scores: Record<string, number>
  reasoning: string
  evidence_summary: {
    literature_support: number
    expression_log2fc: number
    druggability_family: string
  }
}

export interface ProtocolInfo {
  title: string
  protocol_id?: string
  sections: string[]
  overview: string
}

export interface AnalysisResult {
  task_id: string
  status: string
  summary?: {
    disease_type: string
    research_purpose: string
    confidence: number
    literature_count: number
    gene_count: number
    target_count: number
  }
  intent?: IntentResult
  literature?: LiteratureItem[]
  genes?: GeneItem[]
  targets?: TargetItem[]
  protocol?: ProtocolInfo
  export_files?: Record<string, string>
  traceability_summary?: Record<string, unknown>
  error?: string
}

// ── API 配置 ────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8510"

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  })

  if (res.status === 425) {
    throw new ApiError("分析进行中", res.status)
  }

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new ApiError(
      (body as { detail?: string }).detail || `请求失败 (${res.status})`,
      res.status
    )
  }

  return res.json()
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

// ── API 方法 ────────────────────────────────────

export const api = {
  /** 健康检查 */
  health: () => apiFetch<{ status: string; app: string; version: string }>("/api/health"),

  /** 提交分析任务 */
  submitAnalysis: (data: AnalysisRequest) =>
    apiFetch<TaskStatus>("/api/analyze", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  /** 查询任务状态 */
  getStatus: (taskId: string) => apiFetch<TaskStatus>(`/api/status/${taskId}`),

  /** 获取分析结果 */
  getResults: (taskId: string) => apiFetch<AnalysisResult>(`/api/results/${taskId}`),

  /** 导出报告 */
  getExportUrl: (taskId: string, format: string) =>
    `${API_BASE}/api/export/${taskId}/${format}`,

  /** 获取任务列表 */
  listTasks: (limit?: number) =>
    apiFetch<{ tasks: Array<{ task_id: string; status: string; progress: number; question: string }>; total: number }>(
      `/api/tasks${limit ? `?limit=${limit}` : ""}`
    ),
}

// ── 轮询工具 ────────────────────────────────────

export function pollTaskStatus(
  taskId: string,
  onUpdate: (status: TaskStatus) => void,
  onComplete: (result: AnalysisResult) => void,
  onError: (error: Error) => void,
  intervalMs = 2000
) {
  const interval = setInterval(async () => {
    try {
      const status = await api.getStatus(taskId)
      onUpdate(status)

      if (status.status === "completed") {
        clearInterval(interval)
        try {
          const result = await api.getResults(taskId)
          onComplete(result)
        } catch (e) {
          onError(e instanceof Error ? e : new Error("获取结果失败"))
        }
      }

      if (status.status === "failed") {
        clearInterval(interval)
        onError(new Error(status.message || "分析失败"))
      }
    } catch (e) {
      clearInterval(interval)
      onError(e instanceof Error ? e : new Error("轮询失败"))
    }
  }, intervalMs)

  // 返回取消函数
  return () => clearInterval(interval)
}
