"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import {
  X, Send, Loader2, Sparkles, Search, Sliders, CheckCircle,
  BookOpen, Dna, Target, FlaskConical, AlertCircle,
} from "lucide-react"
import { api, type AnalysisRequest } from "@/lib/api"

interface StartModalProps {
  open: boolean
  onClose: () => void
  initialQuestion?: string
}

const QUESTION_TYPES = [
  { value: "mechanism", label: "机制研究", desc: "研究疾病发生发展的分子机制" },
  { value: "biomarker", label: "生物标志物", desc: "寻找诊断或预后标志物" },
  { value: "therapy", label: "治疗靶点", desc: "发现新的治疗干预靶点" },
  { value: "diagnosis", label: "诊断方法", desc: "探索新的诊断策略" },
  { value: "drug_target_identification", label: "药物靶点鉴定", desc: "鉴定可成药的分子靶点" },
]

const EXAMPLE_QUESTIONS = [
  "肝癌耐药性的新靶点发现",
  "阿尔茨海默病早期诊断标志物",
  "三阴性乳腺癌的免疫逃逸机制",
  "非小细胞肺癌EGFR-TKI耐药机制",
  "类风湿关节炎的新治疗策略",
]

export default function StartModal({ open, onClose, initialQuestion = "" }: StartModalProps) {
  const router = useRouter()

  const [step, setStep] = useState<"input" | "submitting" | "redirecting">("input")
  const [question, setQuestion] = useState(initialQuestion)
  const [keywords, setKeywords] = useState("")
  const [questionType, setQuestionType] = useState("mechanism")
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [topN, setTopN] = useState(5)
  const [error, setError] = useState("")
  const [apiHealth, setApiHealth] = useState<boolean | null>(null)

  if (!open) return null

  const handleSubmit = async () => {
    if (!question.trim()) {
      setError("请输入研究问题")
      return
    }

    setError("")
    setStep("submitting")

    try {
      // 构建请求
      const data: AnalysisRequest = {
        question: question.trim(),
        question_type: questionType,
        keywords: keywords
          .split(/[,，]/)
          .map((k) => k.trim())
          .filter(Boolean),
        top_n: topN,
      }

      // 提交分析任务
      const task = await api.submitAnalysis(data)
      setStep("redirecting")

      // 短暂延迟后跳转到分析页面
      setTimeout(() => {
        router.push(`/analysis?taskId=${task.task_id}`)
      }, 800)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "提交失败，请稍后重试"
      setError(message)
      setStep("input")
    }
  }

  const checkHealth = async () => {
    try {
      const h = await api.health()
      setApiHealth(h.status === "ok")
    } catch {
      setApiHealth(false)
    }
  }

  // 加载时检测后端状态
  if (apiHealth === null && step === "input") {
    checkHealth()
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* 遮罩 */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={step === "input" ? onClose : undefined}
      />

      {/* 弹窗主体 */}
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto
                      bg-white rounded-2xl shadow-2xl animate-scale-in">
        {/* 头部 */}
        <div className="sticky top-0 bg-gradient-to-r from-primary/5 to-teal-50
                        border-b border-primary/10 p-6 flex items-center justify-between z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold">开始研究分析</h2>
              <p className="text-sm text-gray-500">输入你的研究问题，AI 将为你完成全流程分析</p>
            </div>
          </div>
          {step === "input" && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <X className="w-5 h-5 text-gray-400" />
            </button>
          )}
        </div>

        {/* 内容区 */}
        <div className="p-6">
          {/* ---- 输入步骤 ---- */}
          {step === "input" && (
            <div className="space-y-6">
              {/* API 状态 */}
              {apiHealth !== null && (
                <div
                  className={`flex items-center gap-2 text-xs px-3 py-2 rounded-lg ${
                    apiHealth
                      ? "bg-emerald-50 text-emerald-700"
                      : "bg-amber-50 text-amber-700"
                  }`}
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      apiHealth ? "bg-emerald-500" : "bg-amber-500"
                    }`}
                  />
                  {apiHealth
                    ? "后端 API 已连接，可以开始分析"
                    : "后端 API 未连接（模拟模式下仍可使用）"}
                </div>
              )}

              {/* 研究问题输入 */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  <Search className="w-4 h-4 text-primary" />
                  研究问题 <span className="text-red-400">*</span>
                </label>
                <textarea
                  value={question}
                  onChange={(e) => {
                    setQuestion(e.target.value)
                    setError("")
                  }}
                  placeholder="描述你的研究问题，越详细越好...&#10;例如：探索非小细胞肺癌中 EGFR 突变导致的耐药机制并寻找新的治疗靶点"
                  rows={3}
                  className="w-full px-4 py-3 border border-gray-200 rounded-xl
                             focus:outline-none focus:ring-2 focus:ring-primary/30
                             focus:border-primary text-sm resize-none
                             placeholder:text-gray-400 transition-all"
                />
              </div>

              {/* 问题类型 */}
              <div>
                <label className="block text-sm font-medium mb-3 flex items-center gap-2">
                  <Target className="w-4 h-4 text-primary" />
                  研究类型
                </label>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                  {QUESTION_TYPES.map((qt) => (
                    <button
                      key={qt.value}
                      onClick={() => setQuestionType(qt.value)}
                      className={`text-left p-3 rounded-xl border-2 transition-all text-sm ${
                        questionType === qt.value
                          ? "border-primary bg-primary/5 text-primary"
                          : "border-gray-100 hover:border-gray-200 text-gray-600"
                      }`}
                    >
                      <div className="font-medium text-xs">{qt.label}</div>
                      <div className="text-[10px] opacity-60 mt-0.5">{qt.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 关键词 */}
              <div>
                <label className="block text-sm font-medium mb-2 flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-primary" />
                  关键词（可选，逗号分隔）
                </label>
                <input
                  type="text"
                  value={keywords}
                  onChange={(e) => setKeywords(e.target.value)}
                  placeholder="例如：EGFR, 耐药, 信号通路, 靶向治疗"
                  className="w-full px-4 py-2.5 border border-gray-200 rounded-xl
                             focus:outline-none focus:ring-2 focus:ring-primary/30
                             focus:border-primary text-sm
                             placeholder:text-gray-400 transition-all"
                />
              </div>

              {/* 高级选项 */}
              <div>
                <button
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-2 text-sm text-gray-400
                             hover:text-gray-600 transition-colors"
                >
                  <Sliders className="w-4 h-4" />
                  高级选项
                  <span className="text-[10px] transition-transform"
                        style={{ transform: showAdvanced ? "rotate(180deg)" : "rotate(0)" }}>
                    ▼
                  </span>
                </button>
                {showAdvanced && (
                  <div className="mt-3 p-4 bg-gray-50 rounded-xl space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-500 mb-1">
                        候选靶点数量: {topN}
                      </label>
                      <input
                        type="range"
                        min={1}
                        max={15}
                        value={topN}
                        onChange={(e) => setTopN(Number(e.target.value))}
                        className="w-full h-2 bg-gray-200 rounded-full appearance-none
                                   cursor-pointer accent-primary"
                      />
                      <div className="flex justify-between text-[10px] text-gray-400 mt-0.5">
                        <span>1</span><span>15</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* 示例问题 */}
              <div>
                <p className="text-xs text-gray-400 mb-2">试试这些例子：</p>
                <div className="flex flex-wrap gap-2">
                  {EXAMPLE_QUESTIONS.map((eq) => (
                    <button
                      key={eq}
                      onClick={() => {
                        setQuestion(eq)
                        setError("")
                      }}
                      className="text-xs px-3 py-1.5 bg-gray-50 hover:bg-primary/5
                                 border border-gray-100 hover:border-primary/20
                                 rounded-full text-gray-500 hover:text-primary
                                 transition-all"
                    >
                      {eq}
                    </button>
                  ))}
                </div>
              </div>

              {/* 错误提示 */}
              {error && (
                <div className="flex items-center gap-2 text-sm text-red-500 bg-red-50
                                px-4 py-3 rounded-xl">
                  <AlertCircle className="w-4 h-4 shrink-0" />
                  {error}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex items-center gap-3 pt-2">
                <button onClick={onClose} className="btn-secondary text-sm">
                  取消
                </button>
                <button
                  onClick={handleSubmit}
                  disabled={!question.trim()}
                  className="btn-primary flex-1 text-sm !py-3 disabled:opacity-50
                             disabled:cursor-not-allowed"
                >
                  <Send className="w-4 h-4" />
                  开始分析
                </button>
              </div>
            </div>
          )}

          {/* ---- 提交中 ---- */}
          {step === "submitting" && (
            <div className="py-12 text-center">
              <div className="w-16 h-16 rounded-full bg-primary/10 flex items-center
                              justify-center mx-auto mb-6 animate-pulse">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
              <h3 className="text-lg font-semibold mb-2">正在提交分析任务...</h3>
              <p className="text-sm text-gray-500">
                正在理解你的研究问题，启动分析流水线
              </p>
            </div>
          )}

          {/* ---- 跳转中 ---- */}
          {step === "redirecting" && (
            <div className="py-12 text-center">
              <div className="w-16 h-16 rounded-full bg-emerald-100 flex items-center
                              justify-center mx-auto mb-6 animate-bounce">
                <CheckCircle className="w-8 h-8 text-emerald-600" />
              </div>
              <h3 className="text-lg font-semibold mb-2">任务已创建</h3>
              <p className="text-sm text-gray-500">
                正在跳转到分析页面，届时将展示实时进度...
              </p>
            </div>
          )}
        </div>

        {/* 底部提示 */}
        {step === "input" && (
          <div className="px-6 pb-5">
            <div className="flex items-center justify-center gap-6 text-[10px] text-gray-300">
              <span className="flex items-center gap-1">
                <BookOpen className="w-3 h-3" /> 文献检索
              </span>
              <span className="flex items-center gap-1">
                <Dna className="w-3 h-3" /> 生信分析
              </span>
              <span className="flex items-center gap-1">
                <Target className="w-3 h-3" /> 靶点评分
              </span>
              <span className="flex items-center gap-1">
                <FlaskConical className="w-3 h-3" /> 实验方案
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
