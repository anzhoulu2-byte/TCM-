"use client"

import { useState } from "react"
import { X, Eye, EyeOff, Check, ArrowRight, Dna, Key, Settings, FlaskConical } from "lucide-react"

interface StartModalProps {
  open: boolean
  onClose: () => void
}

// ── 预设配置 ──────────────────────────────────

const PRESETS = [
  {
    id: "strict",
    name: "🏆 严格发现模式",
    desc: "高置信度，适合验证已知靶点",
    config: { log2fc: 2.0, padj: 0.01, dbs: ["GO_BP", "KEGG"], minGenes: 5, output: 5 },
  },
  {
    id: "exploratory",
    name: "🔬 探索性模式",
    desc: "广覆盖，适合新领域探索",
    config: { log2fc: 0.5, padj: 0.1, dbs: ["GO_BP", "GO_CC", "GO_MF", "KEGG", "Reactome"], minGenes: 2, output: 20 },
  },
  {
    id: "drug",
    name: "💊 药物靶点模式",
    desc: "侧重可药性评估",
    config: { log2fc: 1.0, padj: 0.05, dbs: ["GO_BP", "KEGG", "Reactome"], minGenes: 3, output: 10 },
  },
  {
    id: "basic",
    name: "🧬 基础研究模式",
    desc: "侧重功能机制解析",
    config: { log2fc: 1.0, padj: 0.05, dbs: ["GO_BP", "GO_CC", "GO_MF", "KEGG"], minGenes: 3, output: 15 },
  },
]

export default function StartModal({ open, onClose }: StartModalProps) {
  const [step, setStep] = useState<"api" | "params" | "review">("api")
  const [showKeys, setShowKeys] = useState(false)
  const [selectedPreset, setSelectedPreset] = useState("strict")

  // API Key 状态
  const [apiKeys, setApiKeys] = useState({ deepseek: "", openai: "", email: "" })

  // 参数状态
  const [params, setParams] = useState({
    log2fc: 2.0, padj: 0.01,
    databases: ["GO_BP", "KEGG"],
    minGenes: 5, outputCount: 5,
    sortBy: "comprehensive_score",
    focusGenes: "",
    excludeMito: false, excludeRibo: false,
  })

  if (!open) return null

  const applyPreset = (id: string) => {
    const p = PRESETS.find((x) => x.id === id)
    if (!p) return
    setSelectedPreset(id)
    setParams((prev) => ({ ...prev, ...p.config }))
  }

  const handleStart = () => {
    // 跳转到 Streamlit 应用，携带参数
    const query = new URLSearchParams({
      deepseek: apiKeys.deepseek,
      openai: apiKeys.openai,
      email: apiKeys.email,
      log2fc: String(params.log2fc),
      padj: String(params.padj),
      databases: params.databases.join(","),
      minGenes: String(params.minGenes),
      outputCount: String(params.outputCount),
      sortBy: params.sortBy,
      preset: selectedPreset,
    })
    window.location.href = `/analysis?${query.toString()}`
  }

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
      {/* 遮罩 */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />

      {/* 弹窗 */}
      <div className="relative w-full max-w-2xl max-h-[90vh] overflow-y-auto glass-card !p-0 animate-fade-in">
        {/* 头部 */}
        <div className="flex items-center justify-between p-6 border-b border-white/20">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Dna className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">配置分析</h2>
              <p className="text-xs text-gray-500">配置完成后将跳转到分析平台</p>
            </div>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-black/5 rounded-lg transition-colors">
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* 步骤指示器 */}
        <div className="flex items-center gap-2 px-6 pt-4 pb-2">
          {(["api", "params", "review"] as const).map((s, i) => (
            <div key={s} className="flex items-center gap-2 flex-1">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium
                  ${step === s ? "bg-primary text-white" : step === "api" && i > 0 || step === "params" && i > 1 ? "bg-primary/20 text-primary" : "bg-gray-100 text-gray-400"}`}
              >
                {i === 0 ? <Key className="w-3.5 h-3.5" /> : i === 1 ? <Settings className="w-3.5 h-3.5" /> : <Check className="w-3.5 h-3.5" />}
              </div>
              <span className={`text-xs ${step === s ? "text-primary font-medium" : "text-gray-400"}`}>
                {s === "api" ? "API 密钥" : s === "params" ? "分析参数" : "确认"}
              </span>
              {i < 2 && <div className="flex-1 h-px bg-gray-200" />}
            </div>
          ))}
        </div>

        <div className="p-6">
          {/* 步骤 1: API 密钥 */}
          {step === "api" && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-medium text-base">🔑 配置 API 密钥</h3>
              <p className="text-sm text-gray-500">密钥仅保存在本地浏览器，不会上传到服务器</p>

              <div className="space-y-3">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">
                    DeepSeek API Key <span className="text-red-400">*</span>
                  </label>
                  <div className="relative">
                    <input
                      type={showKeys ? "text" : "password"}
                      value={apiKeys.deepseek}
                      onChange={(e) => setApiKeys((p) => ({ ...p, deepseek: e.target.value }))}
                      placeholder="sk-..."
                      className="input-glass pr-10"
                    />
                    <button
                      onClick={() => setShowKeys(!showKeys)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                    >
                      {showKeys ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">OpenAI API Key（可选）</label>
                  <input
                    type="password"
                    value={apiKeys.openai}
                    onChange={(e) => setApiKeys((p) => ({ ...p, openai: e.target.value }))}
                    placeholder="sk-..."
                    className="input-glass"
                  />
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">PubMed 邮箱</label>
                  <input
                    type="email"
                    value={apiKeys.email}
                    onChange={(e) => setApiKeys((p) => ({ ...p, email: e.target.value }))}
                    placeholder="your@email.com"
                    className="input-glass"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button onClick={() => setStep("params")} className="btn-primary text-sm !py-2.5">
                  下一步 <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* 步骤 2: 分析参数 */}
          {step === "params" && (
            <div className="space-y-5 animate-fade-in">
              <h3 className="font-medium text-base">⚙️ 分析参数配置</h3>

              {/* 预设方案 */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">预设方案</label>
                <div className="grid grid-cols-2 gap-2">
                  {PRESETS.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => applyPreset(p.id)}
                      className={`p-3 rounded-xl text-left text-sm border transition-all
                        ${selectedPreset === p.id
                          ? "border-primary bg-primary/5 ring-1 ring-primary/30"
                          : "border-gray-200 hover:border-primary/30 bg-white/50"}`}
                    >
                      <div className="font-medium text-gray-800">{p.name}</div>
                      <div className="text-xs text-gray-500 mt-0.5">{p.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* 差异表达 */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">📊 差异表达筛选</label>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>log2FC 阈值</span>
                      <span className="font-medium text-primary">{params.log2fc}</span>
                    </div>
                    <input
                      type="range" min="0.5" max="3" step="0.1"
                      value={params.log2fc}
                      onChange={(e) => setParams((p) => ({ ...p, log2fc: parseFloat(e.target.value) }))}
                      className="w-full accent-primary"
                    />
                  </div>
                  <div>
                    <div className="flex justify-between text-xs text-gray-500 mb-1">
                      <span>padj 阈值</span>
                      <span className="font-medium text-primary">{params.padj}</span>
                    </div>
                    <input
                      type="range" min="0.001" max="0.1" step="0.001"
                      value={params.padj}
                      onChange={(e) => setParams((p) => ({ ...p, padj: parseFloat(e.target.value) }))}
                      className="w-full accent-primary"
                    />
                  </div>
                </div>
              </div>

              {/* 富集数据库 */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-2 block">🔬 富集数据库</label>
                <div className="flex flex-wrap gap-2">
                  {[
                    { id: "GO_BP", label: "GO_BP" },
                    { id: "GO_CC", label: "GO_CC" },
                    { id: "GO_MF", label: "GO_MF" },
                    { id: "KEGG", label: "KEGG" },
                    { id: "Reactome", label: "Reactome" },
                  ].map((db) => (
                    <button
                      key={db.id}
                      onClick={() =>
                        setParams((p) => ({
                          ...p,
                          databases: p.databases.includes(db.id)
                            ? p.databases.filter((d) => d !== db.id)
                            : [...p.databases, db.id],
                        }))
                      }
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all
                        ${params.databases.includes(db.id)
                          ? "bg-primary text-white border-primary"
                          : "bg-white text-gray-600 border-gray-200 hover:border-primary/30"}`}
                    >
                      {db.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 输出配置 */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">输出 Top N</label>
                  <select
                    value={params.outputCount}
                    onChange={(e) => setParams((p) => ({ ...p, outputCount: parseInt(e.target.value) }))}
                    className="input-glass !py-2"
                  >
                    {[5, 10, 15, 20].map((n) => (
                      <option key={n} value={n}>Top {n}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="text-sm font-medium text-gray-700 mb-1 block">排序依据</label>
                  <select
                    value={params.sortBy}
                    onChange={(e) => setParams((p) => ({ ...p, sortBy: e.target.value }))}
                    className="input-glass !py-2"
                  >
                    <option value="comprehensive_score">综合评分</option>
                    <option value="fold_change">差异倍数</option>
                    <option value="literature_support">文献支持度</option>
                    <option value="druggability">可药性</option>
                  </select>
                </div>
              </div>

              {/* 基因筛选 */}
              <div>
                <label className="text-sm font-medium text-gray-700 mb-1 block">重点关注基因（可选）</label>
                <input
                  value={params.focusGenes}
                  onChange={(e) => setParams((p) => ({ ...p, focusGenes: e.target.value }))}
                  placeholder="TP53, MYC, EGFR (逗号分隔)"
                  className="input-glass !py-2"
                />
                <div className="flex gap-3 mt-2">
                  <label className="flex items-center gap-1.5 text-xs text-gray-500">
                    <input
                      type="checkbox" checked={params.excludeMito}
                      onChange={(e) => setParams((p) => ({ ...p, excludeMito: e.target.checked }))}
                      className="accent-primary"
                    /> 排除线粒体基因
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-gray-500">
                    <input
                      type="checkbox" checked={params.excludeRibo}
                      onChange={(e) => setParams((p) => ({ ...p, excludeRibo: e.target.checked }))}
                      className="accent-primary"
                    /> 排除核糖体蛋白
                  </label>
                </div>
              </div>

              <div className="flex justify-between pt-2">
                <button onClick={() => setStep("api")} className="text-sm text-gray-500 hover:text-gray-700">
                  ← 返回
                </button>
                <button onClick={() => setStep("review")} className="btn-primary text-sm !py-2.5">
                  下一步 <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* 步骤 3: 确认 */}
          {step === "review" && (
            <div className="space-y-4 animate-fade-in">
              <h3 className="font-medium text-base">✅ 确认配置</h3>

              <div className="bg-white/50 rounded-xl p-4 space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">DeepSeek Key</span>
                  <span className="font-mono">{apiKeys.deepseek ? `${apiKeys.deepseek.slice(0, 8)}...` : "未配置"}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">筛选严格度</span>
                  <span>{params.log2fc >= 2 ? "严格" : params.log2fc >= 1 ? "标准" : "宽松"} (log2FC&gt;{params.log2fc})</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">富集数据库</span>
                  <span>{params.databases.join(", ")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">输出数量</span>
                  <span>Top {params.outputCount}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">排序依据</span>
                  <span>{params.sortBy === "comprehensive_score" ? "综合评分" : params.sortBy}</span>
                </div>
              </div>

              <div className="flex justify-between pt-2">
                <button onClick={() => setStep("params")} className="text-sm text-gray-500 hover:text-gray-700">
                  ← 返回修改
                </button>
                <button onClick={handleStart} className="btn-primary text-sm !py-2.5">
                  开始分析 <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
