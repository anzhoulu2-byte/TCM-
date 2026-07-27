"use client"

import { useState } from "react"
import Link from "next/link"
import {
  ArrowLeft, BookOpen, Search, Globe, FileText, Sparkles,
  ChevronRight, ArrowRight, Database, ExternalLink, Brain, Bot,
} from "lucide-react"

type Step = "query" | "search" | "extract" | "synthesize" | "output"

export default function LiteraturePage() {
  const [activeStep, setActiveStep] = useState<Step>("query")

  const steps: { key: Step; icon: typeof Search; title: string; desc: string; detail: string }[] = [
    {
      key: "query",
      icon: Search,
      title: "智能查询生成",
      desc: "AI 自动将你的研究问题转化为最优检索策略",
      detail: "系统使用大语言模型理解你的研究意图，自动生成包含 MeSH 术语、同义词和布尔逻辑的 PubMed 查询语句。支持中英文问题，自动翻译并扩充检索词。",
    },
    {
      key: "search",
      icon: Globe,
      title: "PubMed 实时检索",
      desc: "通过 NCBI E-utilities API 实时检索最新文献",
      detail: "自动调用 PubMed 官方 API，支持按相关度排序。每次检索最多获取 50 篇文献，支持分页获取更多。严格遵循 NCBI 使用策略——每秒不超过 3 次请求。",
    },
    {
      key: "extract",
      icon: Brain,
      title: "LLM 摘要抽取",
      desc: "DeepSeek/OpenAI 模型提取关键信息并结构化",
      detail: "将每篇文献的摘要发送给大模型，自动提取：研究背景、方法、关键发现、基因/蛋白信息、统计显著性。生成标准化的 JSON 结构化数据，便于后续分析。",
    },
    {
      key: "synthesize",
      icon: Bot,
      title: "多智能体综合",
      desc: "综合分析、交叉验证、去重合并，生成文献综述",
      detail: "4 个 AI Agent 协同工作——文献分析师负责整理、因果推理师负责验证、矛盾检测师负责发现不一致、综述编辑师负责合并输出。每个步骤附带来源引用。",
    },
    {
      key: "output",
      icon: FileText,
      title: "结构化输出",
      desc: "生成 JSON + Markdown + HTML 多格式报告",
      detail: "输出包含：文献摘要表、基因-疾病关联网络、关键发现列表、研究缺口分析。所有结论附带 PMID 链接。一键导出 Markdown、HTML 或 Word 文档。",
    },
  ]

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface to-white">
      <nav className="glass-nav py-4 sticky top-0 z-50">
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

      <section className="relative py-20 overflow-hidden">
        <div className="hero-blob w-[400px] h-[400px] bg-emerald-300/20 top-[-100px] right-[-100px]" />
        <div className="max-w-4xl mx-auto px-6 text-center relative">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <BookOpen className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl md:text-5xl font-bold mb-4">文献智能检索</h1>
          <p className="text-gray-500 max-w-2xl mx-auto text-lg mb-8">
            从 PubMed 检索到情报摘要，AI 全程为你阅读、提取与综合
          </p>
          <Link href="/?start=true" className="btn-primary inline-flex text-sm">
            <Sparkles className="w-4 h-4" />
            立即体验
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* 五步流程 */}
      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-10">五步检索流水线</h2>

          <div className="grid md:grid-cols-5 gap-2 mb-10">
            {steps.map((s) => (
              <button
                key={s.key}
                onClick={() => setActiveStep(s.key)}
                className={`p-4 rounded-xl text-center transition-all ${
                  activeStep === s.key
                    ? "bg-primary text-white shadow-lg scale-105"
                    : "bg-gray-50 text-gray-500 hover:bg-gray-100"
                }`}
              >
                <s.icon className={`w-6 h-6 mx-auto mb-2 ${
                  activeStep === s.key ? "text-white" : "text-gray-400"
                }`} />
                <div className="text-xs font-medium">{s.title}</div>
              </button>
            ))}
          </div>

          {/* 步骤详情 */}
          <div className="glass-card p-8 animate-fade-in">
            {steps.filter((s) => s.key === activeStep).map((step) => (
              <div key={step.key} className="flex gap-6 items-start">
                <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                  <step.icon className="w-7 h-7 text-primary" />
                </div>
                <div>
                  <h3 className="text-xl font-semibold mb-2">{step.title}</h3>
                  <p className="text-gray-600 leading-relaxed text-sm">{step.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 特性卡片 */}
      <section className="pb-20 bg-white/50">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: Database, title: "多数据库支持", desc: "PubMed / PMC / NCBI Gene 自动联动，支持 3000 万+ 文献索引", color: "from-emerald-400/20" },
              { icon: Brain, title: "深度学习理解", desc: "基于 LLM 的上下文理解，准确提取实验条件、统计数据和科学发现", color: "from-teal-400/20" },
              { icon: Bot, title: "多智能体协作", desc: "多角度交叉验证关键发现，自动检测文献间的矛盾与共识", color: "from-green-400/20" },
              { icon: FileText, title: "多格式报告输出", desc: "JSON（结构化） / Markdown（可读） / HTML（交互式） / Word（正式）", color: "from-emerald-300/20" },
              { icon: ExternalLink, title: "全程可追溯", desc: "每条分析结论附带 PMID 链接，支持一键跳转原文验证", color: "from-teal-300/20" },
              { icon: Globe, title: "中英双语支持", desc: "输入中文问题自动翻译检索，中文摘要 + 英文原文双输出", color: "from-green-300/20" },
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

      {/* CTA */}
      <section className="pb-20">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="glass-card p-10 relative overflow-hidden">
            <div className="hero-blob w-[200px] h-[200px] bg-emerald-300/15 top-[-50px] right-[-50px]" />
            <div className="relative z-10">
              <h3 className="text-2xl font-bold mb-3">准备好探索文献了吗？</h3>
              <p className="text-gray-500 mb-6 text-sm">输入你的研究主题，AI 为你完成文献检索与综述</p>
              <Link href="/" className="btn-primary inline-flex text-sm">
                开始检索 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
