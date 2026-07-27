"use client"

import { useState, useEffect, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import {
  ArrowLeft, Target, BookOpen, Dna, FlaskConical, FileText,
  Loader2, CheckCircle, AlertCircle, TrendingUp, ExternalLink,
  ChevronDown, ChevronRight, BarChart3, Download, Clock, Share2,
  XCircle, RefreshCw, Zap,
} from "lucide-react"
import {
  api,
  pollTaskStatus,
  type TaskStatus,
  type AnalysisResult,
  type TargetItem,
} from "@/lib/api"

// ── 工具函数 ──────────────────────────────────

function scoreBar(score: number, max = 10) {
  const pct = Math.min(Math.max(score / max, 0), 1) * 100
  const colors = ["bg-red-400", "bg-orange-400", "bg-amber-400", "bg-lime-400", "bg-emerald-400"]
  const idx = Math.min(Math.floor(pct / 20), 4)
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full ${colors[idx]} rounded-full transition-all duration-700`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs font-mono text-gray-400 w-10 text-right">{score.toFixed(1)}</span>
    </div>
  )
}

// ── 进度阶段组件 ──────────────────────────────

function ProgressPipeline({ progress, message, status }: { progress: number; message: string; status: string }) {
  const stages = [
    { label: "问题理解", range: [0, 25], icon: Zap },
    { label: "文献检索", range: [25, 45], icon: BookOpen },
    { label: "生信分析", range: [45, 60], icon: Dna },
    { label: "靶点发现", range: [60, 80], icon: Target },
    { label: "实验方案", range: [80, 95], icon: FlaskConical },
    { label: "报告生成", range: [95, 100], icon: FileText },
  ]

  return (
    <div className="space-y-3">
      {stages.map((stage, idx) => {
        const isActive = progress >= stage.range[0]
        const isComplete = progress >= stage.range[1]
        const isCurrent = progress >= stage.range[0] && progress < stage.range[1]

        return (
          <div key={stage.label} className="flex items-center gap-3">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-all ${
              isComplete
                ? "bg-emerald-100 text-emerald-600"
                : isCurrent
                ? "bg-primary/10 text-primary animate-pulse"
                : "bg-gray-50 text-gray-300"
            }`}>
              {isComplete ? (
                <CheckCircle className="w-4 h-4" />
              ) : isCurrent ? (
                <stage.icon className="w-4 h-4" />
              ) : (
                <div className="w-2 h-2 rounded-full bg-gray-300" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className={`text-sm font-medium ${
                isComplete ? "text-emerald-700" : isCurrent ? "text-primary" : "text-gray-300"
              }`}>
                {stage.label}
              </div>
              {isCurrent && (
                <div className="h-1.5 bg-gray-100 rounded-full mt-1 overflow-hidden">
                  <div
                    className="h-full bg-primary rounded-full transition-all duration-1000"
                    style={{ width: `${((progress - stage.range[0]) / (stage.range[1] - stage.range[0])) * 100}%` }}
                  />
                </div>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── 文献卡片 ──────────────────────────────────

function LiteratureCard({ item }: { item: { title: string; authors: string; journal: string; year: string; pmid: string; abstract: string; key_findings: string } }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="border border-gray-100 rounded-xl p-4 hover:border-primary/20 transition-all">
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-medium leading-snug flex-1">{item.title}</h4>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 hover:bg-gray-50 rounded shrink-0 text-gray-400"
        >
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>
      <div className="flex items-center gap-3 mt-1.5 text-xs text-gray-400">
        <span>{item.authors?.split(",")[0] || "N/A"} et al.</span>
        <span>{item.journal}, {item.year}</span>
        {item.pmid && (
          <a
            href={`https://pubmed.ncbi.nlm.nih.gov/${item.pmid}`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary/60 hover:text-primary underline underline-offset-2"
          >
            PMID: {item.pmid}
          </a>
        )}
      </div>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-gray-50 space-y-2">
          {item.key_findings && (
            <div>
              <span className="text-xs font-medium text-amber-600">关键发现：</span>
              <p className="text-xs text-gray-600 mt-1 leading-relaxed">{item.key_findings}</p>
            </div>
          )}
          {item.abstract && (
            <div>
              <span className="text-xs font-medium text-gray-600">摘要：</span>
              <p className="text-xs text-gray-500 mt-1 leading-relaxed">{item.abstract}</p>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── 靶点排名组件 ──────────────────────────────

function TargetRanking({ targets }: { targets: TargetItem[] }) {
  const [selectedTarget, setSelectedTarget] = useState<TargetItem | null>(null)

  return (
    <div className="space-y-3">
      {targets.map((t) => (
        <div
          key={t.gene}
          onClick={() => setSelectedTarget(selectedTarget?.gene === t.gene ? null : t)}
          className={`border-2 rounded-xl p-4 cursor-pointer transition-all ${
            selectedTarget?.gene === t.gene
              ? "border-primary bg-primary/[0.03]"
              : "border-gray-100 hover:border-gray-200"
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold ${
                t.ranking <= 3 ? "bg-amber-100 text-amber-700" : "bg-gray-50 text-gray-500"
              }`}>
                {t.ranking}
              </div>
              <div>
                <h4 className="font-semibold">{t.gene}</h4>
                {t.evidence_summary?.druggability_family && (
                  <span className="text-xs text-gray-400">{t.evidence_summary.druggability_family}</span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className={`text-lg font-bold ${
                t.total_score >= 7 ? "text-emerald-600" : t.total_score >= 4 ? "text-amber-600" : "text-red-500"
              }`}>
                {t.total_score.toFixed(1)}
              </div>
              <div className="text-[10px] text-gray-400">/10 总分</div>
            </div>
          </div>

          {t.scores && (
            <div className="space-y-1.5 mt-3">
              {Object.entries(t.scores).map(([key, val]) => (
                <div key={key} className="flex items-center gap-3 text-xs">
                  <span className="w-20 text-gray-500 truncate">
                    {key.replace(/_/g, " ")}
                  </span>
                  {scoreBar(val)}
                </div>
              ))}
            </div>
          )}

          {selectedTarget?.gene === t.gene && t.reasoning && (
            <div className="mt-3 pt-3 border-t border-gray-50">
              <p className="text-xs text-gray-600 leading-relaxed italic">
                {t.reasoning}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

// ── 主页面 ────────────────────────────────────

export default function AnalysisPage() {
  const searchParams = useSearchParams()
  const taskId = searchParams.get("taskId")

  const [loading, setLoading] = useState(true)
  const [status, setStatus] = useState<TaskStatus | null>(null)
  const [result, setResult] = useState<AnalysisResult | null>(null)
  const [error, setError] = useState("")
  const [manualTaskId, setManualTaskId] = useState("")
  const [currentStage, setCurrentStage] = useState<string>("")
  const [activeTab, setActiveTab] = useState<"progress" | "literature" | "targets" | "protocol">("progress")

  // 根据进度映射阶段名
  const getStageLabel = (progress: number) => {
    if (progress < 25) return "问题理解"
    if (progress < 45) return "文献检索"
    if (progress < 60) return "生信分析"
    if (progress < 80) return "靶点发现"
    if (progress < 95) return "实验方案"
    return "报告生成"
  }

  // 成果统计结束后自动切换 tab
  useEffect(() => {
    if (status?.status === "completed" && result) {
      // 自动切换到结果标签
      setTimeout(() => setActiveTab("targets"), 500)
    }
  }, [status?.status, result])

  const startPolling = useCallback((tid: string) => {
    setLoading(true)
    setError("")
    setStatus(null)
    setResult(null)
    setActiveTab("progress")

    const cancel = pollTaskStatus(
      tid,
      (s) => {
        setStatus(s)
        setCurrentStage(getStageLabel(s.progress))
      },
      (r) => {
        setResult(r)
        setLoading(false)
      },
      (e) => {
        setError(e.message)
        setLoading(false)
      },
      2000
    )

    return cancel
  }, [])

  useEffect(() => {
    if (!taskId) {
      setLoading(false)
      return
    }
    const cancel = startPolling(taskId)
    return cancel
  }, [taskId, startPolling])

  // 手动查询任务
  const handleManualQuery = () => {
    if (!manualTaskId.trim()) return
    const url = new URL(window.location.href)
    url.searchParams.set("taskId", manualTaskId.trim())
    window.history.pushState({}, "", url.toString())
    startPolling(manualTaskId.trim())
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface to-white">
      {/* 导航 */}
      <nav className="glass-nav py-4 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link
            href="/"
            className="flex items-center gap-2 text-sm text-gray-500 hover:text-primary transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            返回首页
          </Link>
          <div className="flex items-center gap-3">
            {status && status.status !== "completed" && status.status !== "failed" && (
              <span className="text-xs text-primary/70 bg-primary/5 px-3 py-1 rounded-full">
                {currentStage || status.message}
              </span>
            )}
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary" />
              <span className="font-semibold text-primary">分析中心</span>
            </div>
          </div>
        </div>
      </nav>

      {/* 无任务 ID —— 输入框 */}
      {!taskId && !loading && (
        <section className="flex items-center justify-center min-h-[70vh]">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
              <SearchIcon className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-2xl font-bold mb-3">查询分析任务</h2>
            <p className="text-gray-500 mb-6 text-sm">
              输入任务 ID 查看分析进度和结果，或返回首页开始新的分析
            </p>
            <div className="flex gap-2">
              <input
                type="text"
                value={manualTaskId}
                onChange={(e) => setManualTaskId(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleManualQuery()}
                placeholder="任务 ID..."
                className="flex-1 px-4 py-2.5 border border-gray-200 rounded-xl
                           focus:outline-none focus:ring-2 focus:ring-primary/30
                           focus:border-primary text-sm"
              />
              <button onClick={handleManualQuery} className="btn-primary text-sm">
                查询
              </button>
            </div>
            <Link href="/" className="inline-block mt-4 text-sm text-primary/60 hover:text-primary transition-colors">
              ← 返回首页开始新分析
            </Link>
          </div>
        </section>
      )}

      {/* 加载中 / 进度显示 */}
      {loading && (
        <section className="max-w-4xl mx-auto px-6 py-20">
          <div className="glass-card p-8 md:p-12">
            <div className="text-center mb-10">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center
                              justify-center mx-auto mb-4 animate-pulse">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
              <h2 className="text-2xl font-bold mb-2">分析进行中</h2>
              <p className="text-sm text-gray-500">
                {status?.message || "正在连接分析引擎..."}
              </p>
              {status && (
                <div className="mt-4">
                  <div className="flex items-center gap-3 justify-center mb-2">
                    <span className="text-sm text-gray-400">总体进度</span>
                    <span className="text-lg font-bold text-primary">{status.progress}%</span>
                  </div>
                  <div className="max-w-xs mx-auto h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-primary to-emerald-400
                                 rounded-full transition-all duration-700"
                      style={{ width: `${status.progress}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
            {status && <ProgressPipeline progress={status.progress} message={status.message} status={status.status} />}
          </div>
        </section>
      )}

      {/* 错误 */}
      {error && (
        <section className="max-w-xl mx-auto px-6 py-20">
          <div className="glass-card p-8 text-center">
            <div className="w-16 h-16 rounded-full bg-red-50 flex items-center
                            justify-center mx-auto mb-4">
              <XCircle className="w-8 h-8 text-red-400" />
            </div>
            <h2 className="text-xl font-bold mb-2">分析失败</h2>
            <p className="text-sm text-gray-500 mb-6">{error}</p>
            <div className="flex items-center justify-center gap-3">
              <Link href="/" className="btn-secondary text-sm">返回首页</Link>
              {taskId && (
                <button
                  onClick={() => startPolling(taskId)}
                  className="btn-primary text-sm flex items-center gap-2"
                >
                  <RefreshCw className="w-4 h-4" /> 重新查询
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {/* 结果展示 */}
      {result && status?.status === "completed" && (
        <section className="max-w-7xl mx-auto px-6 py-8">
          {/* 顶部概览 */}
          <div className="glass-card p-6 md:p-8 mb-6">
            <div className="flex items-start justify-between flex-wrap gap-4">
              <div>
                <h1 className="text-2xl font-bold mb-2">分析完成</h1>
                {result.summary && (
                  <p className="text-gray-500 text-sm">
                    疾病类型：{result.summary.disease_type || "N/A"} ·
                    研究目的：{result.summary.research_purpose || "N/A"} ·
                    置信度：{((result.summary.confidence || 0) * 100).toFixed(0)}%
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                {result.export_files?.html && (
                  <a
                    href={api.getExportUrl(result.task_id, "html")}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="btn-primary text-xs !py-2"
                  >
                    <Download className="w-3.5 h-3.5" /> 导出 HTML
                  </a>
                )}
                {result.export_files?.md && (
                  <a
                    href={api.getExportUrl(result.task_id, "md")}
                    className="btn-secondary text-xs !py-2"
                    download
                  >
                    <Download className="w-3.5 h-3.5" /> 导出 MD
                  </a>
                )}
              </div>
            </div>

            {/* 统计卡片 */}
            {result.summary && (
              <div className="grid grid-cols-4 gap-4 mt-6">
                {[
                  { label: "检索文献", value: result.summary.literature_count, icon: BookOpen, color: "bg-blue-50 text-blue-600" },
                  { label: "关联基因", value: result.summary.gene_count, icon: Dna, color: "bg-purple-50 text-purple-600" },
                  { label: "候选靶点", value: result.summary.target_count, icon: Target, color: "bg-amber-50 text-amber-600" },
                  { label: "置信度", value: `${((result.summary.confidence || 0) * 100).toFixed(0)}%`, icon: TrendingUp, color: "bg-emerald-50 text-emerald-600" },
                ].map((item) => (
                  <div key={item.label} className="text-center p-4 rounded-xl bg-gray-50/50">
                    <div className={`w-9 h-9 rounded-lg ${item.color} flex items-center justify-center mx-auto mb-2`}>
                      <item.icon className="w-4 h-4" />
                    </div>
                    <div className="stat-value text-xl">{item.value}</div>
                    <div className="text-[10px] text-gray-400">{item.label}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Tab 导航 */}
          <div className="flex gap-1 mb-6 bg-gray-50 p-1 rounded-xl">
            {[
              { key: "progress", label: "分析流水线", icon: Zap },
              { key: "literature", label: `文献 (${result.literature?.length || 0})`, icon: BookOpen },
              { key: "targets", label: `靶点 (${result.targets?.length || 0})`, icon: Target },
              { key: "protocol", label: "实验方案", icon: FlaskConical },
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key as typeof activeTab)}
                className={`flex-1 flex items-center justify-center gap-2 py-2.5 px-4
                            rounded-lg text-sm font-medium transition-all ${
                  activeTab === tab.key
                    ? "bg-white text-primary shadow-sm"
                    : "text-gray-400 hover:text-gray-600"
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab 内容 */}
          <div className="glass-card p-6 md:p-8">
            {/* 分析流水线 */}
            {activeTab === "progress" && (
              <div>
                <h3 className="text-lg font-semibold mb-2">分析流水线详情</h3>
                <p className="text-sm text-gray-500 mb-6">
                  以下展示了每个模块的处理过程
                </p>
                <ProgressPipeline progress={100} message="完成" status="completed" />
                {result.traceability_summary && (
                  <div className="mt-8 p-4 bg-gray-50/50 rounded-xl">
                    <h4 className="text-sm font-medium mb-2">执行摘录</h4>
                    <pre className="text-xs text-gray-500 overflow-x-auto whitespace-pre-wrap">
                      {JSON.stringify(result.traceability_summary, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* 文献结果 */}
            {activeTab === "literature" && (
              <div>
                <h3 className="text-lg font-semibold mb-2">文献检索结果</h3>
                <p className="text-sm text-gray-500 mb-6">
                  共找到 {result.literature?.length || 0} 篇相关文献
                </p>
                {result.literature && result.literature.length > 0 ? (
                  <div className="space-y-3 max-h-[600px] overflow-y-auto pr-2">
                    {result.literature.map((lit, idx) => (
                      <LiteratureCard key={lit.pmid || idx} item={lit} />
                    ))}
                  </div>
                ) : (
                  <p className="text-gray-400 text-center py-8">暂无文献数据</p>
                )}
              </div>
            )}

            {/* 靶点结果 */}
            {activeTab === "targets" && (
              <div>
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-lg font-semibold mb-1">候选靶点排名</h3>
                    <p className="text-sm text-gray-500">
                      基于6维度评分 + 多智能体推理的靶点排序
                    </p>
                  </div>
                </div>
                {result.targets && result.targets.length > 0 ? (
                  <TargetRanking targets={result.targets} />
                ) : (
                  <p className="text-gray-400 text-center py-8">暂无靶点数据</p>
                )}
              </div>
            )}

            {/* 实验方案 */}
            {activeTab === "protocol" && (
              <div>
                <h3 className="text-lg font-semibold mb-2">实验方案</h3>
                <p className="text-sm text-gray-500 mb-6">
                  自动生成的验证实验方案
                </p>
                {result.protocol && result.protocol.sections && result.protocol.sections.length > 0 ? (
                  <div className="space-y-4">
                    <div className="p-6 bg-gradient-to-r from-primary/5 to-teal-50 rounded-xl border border-primary/10">
                      <h4 className="font-semibold mb-2">{result.protocol.title || "实验方案"}</h4>
                      {result.protocol.overview && (
                        <p className="text-sm text-gray-600 leading-relaxed">
                          {typeof result.protocol.overview === "string"
                            ? result.protocol.overview
                            : JSON.stringify(result.protocol.overview)}
                        </p>
                      )}
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      {result.protocol.sections.map((section) => (
                        <div key={section} className="p-4 bg-gray-50 rounded-xl text-center">
                          <div className="text-2xl mb-1">
                            {section.includes("objective") ? "🎯" :
                             section.includes("background") ? "📚" :
                             section.includes("experiment") ? "🧪" :
                             section.includes("procedure") ? "📋" :
                             section.includes("reagent") ? "⚗️" :
                             section.includes("timeline") ? "📅" :
                             section.includes("expected") ? "📊" : "📝"}
                          </div>
                          <div className="text-xs font-medium text-gray-600">{section}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <p className="text-gray-400 text-center py-8">
                    实验方案正在生成中，请稍后查看
                  </p>
                )}
              </div>
            )}
          </div>

          {/* 底部操作 */}
          <div className="flex items-center justify-between mt-6">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <Clock className="w-3.5 h-3.5" />
              任务 ID: {result.task_id}
            </div>
            <Link href="/" className="flex items-center gap-2 text-sm text-primary/60 hover:text-primary transition-colors">
              <RefreshCw className="w-3.5 h-3.5" />
              开始新分析
            </Link>
          </div>
        </section>
      )}
    </main>
  )
}

function SearchIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="11" cy="11" r="8"/>
      <path d="m21 21-4.3-4.3"/>
    </svg>
  )
}
