"use client"

import { Suspense, useState, useCallback } from "react"
import { useSearchParams } from "next/navigation"
import Link from "next/link"
import { ArrowLeft, Maximize2, Minimize2, RefreshCw, Dna } from "lucide-react"

/**
 * 分析页面 — 嵌入 Streamlit 分析平台
 *
 * /analysis 页面作为统一入口，将 Streamlit 分析功能嵌入 Next.js 前端。
 * 保留 Demelza 风格导航，获得统一的美术体验。
 */
function AnalysisContent() {
  const searchParams = useSearchParams()
  const [fullscreen, setFullscreen] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)

  const streamlitBase = "http://localhost:8501"
  const queryString = searchParams.toString()
  const streamlitUrl = queryString
    ? `${streamlitBase}?${queryString}`
    : streamlitBase

  const handleIframeLoad = useCallback(() => {
    setLoaded(true)
    setError(false)
  }, [])

  const handleIframeError = useCallback(() => {
    setError(true)
    setLoaded(true)
  }, [])

  const retry = useCallback(() => {
    setLoaded(false)
    setError(false)
    setRetryCount((c) => c + 1)
  }, [])

  return (
    <div className="min-h-screen bg-surface flex flex-col">
      {/* 顶部导航 */}
      <nav className="glass-nav py-3 shrink-0">
        <div className="max-w-full mx-auto px-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href="/"
              className="flex items-center gap-2 text-sm text-gray-500 hover:text-primary transition-colors"
            >
              <ArrowLeft className="w-4 h-4" /> 返回首页
            </Link>

            <div className="hidden sm:flex items-center gap-2 pl-4 border-l border-white/30">
              <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
                <Dna className="w-4 h-4 text-white" />
              </div>
              <span className="text-sm font-semibold text-primary">分析平台</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={retry}
              className="btn-secondary text-xs !py-1.5 !px-3"
              title="重新加载"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${retryCount > 0 ? "animate-spin" : ""}`} />
              刷新
            </button>
            <button
              onClick={() => setFullscreen(!fullscreen)}
              className="btn-secondary text-xs !py-1.5 !px-3"
              title={fullscreen ? "退出全屏" : "全屏"}
            >
              {fullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
            </button>
          </div>
        </div>
      </nav>

      {/* 加载状态 */}
      {!loaded && !error && (
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <RefreshCw className="w-8 h-8 text-primary animate-spin" />
            </div>
            <p className="text-gray-500">正在加载分析平台...</p>
            <p className="text-xs text-gray-400 mt-2">首次加载可能需要几秒钟</p>
          </div>
        </div>
      )}

      {/* 错误状态：Streamlit 未运行 */}
      {error && (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="glass-card p-8 max-w-md text-center animate-fade-in">
            <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center mx-auto mb-4">
              <span className="text-2xl">⚠️</span>
            </div>
            <h3 className="text-lg font-semibold mb-2">无法连接到分析引擎</h3>
            <p className="text-sm text-gray-500 mb-4">Streamlit 分析服务未运行。请先启动：</p>
            <div className="bg-gray-50 rounded-lg p-3 text-left text-xs font-mono mb-4">
              cd BioResearch-Agent<br />
              streamlit run app/streamlit_app.py
            </div>
            <button onClick={retry} className="btn-primary text-sm !py-2">重试连接</button>
          </div>
        </div>
      )}

      {/* Streamlit iframe */}
      <div
        className={`flex-1 transition-all duration-300 ${
          fullscreen ? "fixed inset-0 z-50 pt-0" : ""
        } ${loaded ? "opacity-100" : "opacity-0 absolute"}`}
      >
        <iframe
          key={retryCount}
          src={streamlitUrl}
          className="w-full h-full border-0"
          title="BioResearch Analysis Platform"
          onLoad={handleIframeLoad}
          onError={handleIframeError}
          allow="clipboard-read; clipboard-write"
        />
      </div>
    </div>
  )
}

// 需要 Suspense 包裹 useSearchParams
export default function AnalysisPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-surface flex items-center justify-center">
          <div className="text-center">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <RefreshCw className="w-8 h-8 text-primary animate-spin" />
            </div>
            <p className="text-gray-500">加载中...</p>
          </div>
        </div>
      }
    >
      <AnalysisContent />
    </Suspense>
  )
}
