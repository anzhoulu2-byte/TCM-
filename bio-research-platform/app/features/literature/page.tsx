"use client"

import Link from "next/link"
import { ArrowLeft, BookOpen, Search, FileText, Globe, Database, Zap, ChevronRight } from "lucide-react"

export default function LiteraturePage() {
  return (
    <main className="min-h-screen bg-surface">
      {/* 导航 */}
      <nav className="glass-nav py-4">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm text-gray-500 hover:text-primary transition-colors">
            <ArrowLeft className="w-4 h-4" /> 返回首页
          </Link>
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary" />
            <span className="font-semibold text-primary">文献智能检索</span>
          </div>
        </div>
      </nav>

      {/* Hero */}
      <section className="relative py-20 overflow-hidden">
        <div className="hero-blob w-[400px] h-[400px] bg-emerald-300/20 top-[-100px] right-[-100px]" />
        <div className="max-w-4xl mx-auto px-6 text-center relative">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <BookOpen className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl md:text-5xl font-bold mb-4">文献智能检索</h1>
          <p className="text-gray-500 max-w-2xl mx-auto text-lg">
            自动搜索 PubMed，LLM 深度阅读并提取关键信息，生成结构化文献综述
          </p>
        </div>
      </section>

      {/* 功能详情 */}
      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: Search, title: "智能布尔查询", desc: "根据研究问题自动构建 PubMed 布尔检索式，支持 AND/OR/NOT 逻辑组合", color: "from-emerald-400/20" },
              { icon: Database, title: "多源数据整合", desc: "整合 PubMed、Open Targets 等多数据库，一次搜索覆盖文献和基因数据", color: "from-teal-400/20" },
              { icon: FileText, title: "LLM 深度阅读", desc: "获取文献摘要后，AI 自动提取研究目的、方法、发现、局限性等结构化信息", color: "from-green-400/20" },
              { icon: Globe, title: "实时更新追踪", desc: "按相关度或发表时间排序，确保获取最新研究进展", color: "from-emerald-300/20" },
              { icon: Zap, title: "批量并行检索", desc: "异步并发请求，速率限制自动管理，50 篇文献检索仅需数秒", color: "from-teal-300/20" },
              { icon: ChevronRight, title: "迭代深度搜索", desc: "根据初步结果自动优化查询，实现多轮递进式文献挖掘", color: "from-green-300/20" },
            ].map((item) => (
              <div key={item.title} className="glass-card p-6 hover:shadow-glass-hover transition-shadow">
                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${item.color} to-transparent flex items-center justify-center mb-4`}>
                  <item.icon className="w-6 h-6 text-primary" />
                </div>
                <h3 className="font-semibold mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </main>
  )
}
