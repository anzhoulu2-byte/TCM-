"use client"

import { useState, useEffect, useRef } from "react"
import Link from "next/link"
import {
  Search, BookOpen, Dna, Target, FlaskConical,
  ChevronRight, BarChart3, TrendingUp, Users, FileText,
  Menu, X, Sparkles, ArrowRight, Globe, Shield,
} from "lucide-react"
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Area, AreaChart,
} from "recharts"
import StartModal from "@/components/StartModal"

// ── 工具函数 ──────────────────────────────────

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}

// ── 数据 ──────────────────────────────────────

const FEATURES = [
  {
    icon: BookOpen,
    title: "文献智能检索",
    desc: "自动搜索 PubMed 文献，提取关键信息，生成结构化文献综述",
    href: "/features/literature",
    color: "from-emerald-400/20 to-emerald-600/10",
  },
  {
    icon: Dna,
    title: "生信分析引擎",
    desc: "差异表达分析、通路富集、生存分析 — 全自动生信流水线",
    href: "/features/bioinformatics",
    color: "from-teal-400/20 to-teal-600/10",
  },
  {
    icon: Target,
    title: "智能靶点发现",
    desc: "多维度评分 + 多智能体推理 + 人工反馈，精确锁定候选靶点",
    href: "/features/target-discovery",
    color: "from-green-400/20 to-green-600/10",
  },
  {
    icon: FlaskConical,
    title: "实验方案生成",
    desc: "自动化生成验证方案、推荐试剂、评估可行性与成本",
    href: "/features/protocol",
    color: "from-emerald-300/20 to-emerald-500/10",
  },
]

const STATS = [
  { label: "已分析文献", value: "58,234", icon: FileText, change: "+12.5%" },
  { label: "候选靶点", value: "1,847", icon: Target, change: "+8.3%" },
  { label: "研究项目", value: "356", icon: TrendingUp, change: "+23.1%" },
  { label: "活跃用户", value: "2,891", icon: Users, change: "+15.7%" },
]

const chartData = [
  { month: "1月", literature: 4200, targets: 120, analysis: 85 },
  { month: "2月", literature: 4800, targets: 145, analysis: 92 },
  { month: "3月", literature: 5600, targets: 168, analysis: 108 },
  { month: "4月", literature: 6200, targets: 195, analysis: 124 },
  { month: "5月", literature: 7800, targets: 224, analysis: 145 },
  { month: "6月", literature: 9200, targets: 268, analysis: 168 },
]

const NAV_ITEMS = [
  { label: "功能特性", href: "#features" },
  { label: "数据统计", href: "#stats" },
  { label: "工作流程", href: "#workflow" },
]

// ── 导航栏 ────────────────────────────────────

function Navbar({ onStartClick }: { onStartClick: () => void }) {
  const [scrolled, setScrolled] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20)
    window.addEventListener("scroll", onScroll)
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <nav
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        scrolled
          ? "glass-nav py-3"
          : "bg-transparent py-5"
      )}
    >
      <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
        {/* Logo */}
        <a href="#" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-lg bg-primary flex items-center justify-center
                          group-hover:scale-105 transition-transform">
            <Dna className="w-5 h-5 text-white" />
          </div>
          <span className="text-lg font-semibold text-primary">
            BioResearch<span className="text-primary/60">Platform</span>
          </span>
        </a>

        {/* Desktop Nav */}
        <div className="hidden md:flex items-center gap-8">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="text-sm text-foreground/70 hover:text-primary transition-colors
                         relative after:absolute after:bottom-[-4px] after:left-0 after:h-[2px]
                         after:w-0 after:bg-primary after:transition-all hover:after:w-full"
            >
              {item.label}
            </a>
          ))}
          <button onClick={onStartClick} className="btn-primary text-sm !py-2.5 !px-5">
            开始使用
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>

        {/* Mobile Toggle */}
        <button
          onClick={() => setMobileOpen(!mobileOpen)}
          className="md:hidden p-2 text-foreground/70"
        >
          {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {mobileOpen && (
        <div className="md:hidden glass-card mx-4 mt-3 p-4 animate-fade-in">
          {NAV_ITEMS.map((item) => (
            <a
              key={item.label}
              href={item.href}
              className="block py-3 px-4 text-foreground/70 hover:text-primary
                         hover:bg-primary/5 rounded-lg transition-colors"
              onClick={() => setMobileOpen(false)}
            >
              {item.label}
            </a>
          ))}
          <button onClick={onStartClick} className="btn-primary w-full mt-3 text-sm">
            开始使用 <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </nav>
  )
}

// ── Hero 区域 ─────────────────────────────────

function Hero({ onStartClick, onSearchSubmit }: { onStartClick: (q?: string) => void; onSearchSubmit: (q: string) => void }) {
  const [query, setQuery] = useState("")

  const handleSubmit = () => {
    if (query.trim()) {
      onSearchSubmit(query.trim())
    } else {
      onStartClick()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSubmit()
  }

  return (
    <section className="relative min-h-[85vh] flex items-center justify-center overflow-hidden pt-24 pb-16">
      {/* 背景装饰 */}
      <div className="hero-blob w-[600px] h-[600px] bg-emerald-300/30 top-[-200px] right-[-200px]" />
      <div className="hero-blob w-[400px] h-[400px] bg-teal-300/20 bottom-[-100px] left-[-100px]" />
      <div className="hero-blob w-[300px] h-[300px] bg-green-200/20 top-[40%] left-[60%]" />

      <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
        {/* 标签 */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 bg-primary/10 text-primary
                        text-sm font-medium rounded-full mb-6 animate-fade-in">
          <Sparkles className="w-4 h-4" />
          AI 驱动的生物医学研究平台
        </div>

        {/* 标题 */}
        <h1 className="text-4xl md:text-6xl lg:text-7xl font-bold leading-tight mb-6 animate-slide-up">
          从研究问题到
          <span className="text-primary block mt-2">
            靶点发现
          </span>
          <span className="bg-gradient-to-r from-primary to-emerald-400 bg-clip-text text-transparent">
            ，一键完成
          </span>
        </h1>

        {/* 副标题 */}
        <p className="text-lg md:text-xl text-foreground/60 max-w-2xl mx-auto mb-10 animate-slide-up">
          整合文献检索、生物信息学分析、多智能体推理和实验方案生成，
          <br className="hidden md:block" />
          将数周的研究工作缩短到几分钟
        </p>

        {/* 搜索框 */}
        <div className="max-w-2xl mx-auto animate-slide-up">
          <div className="glass-card !p-2 flex items-center gap-2">
            <div className="flex-1 flex items-center gap-3 px-4">
              <Search className="w-5 h-5 text-primary/50 shrink-0" />
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="输入研究问题，例如：肝癌耐药性的新靶点..."
                className="w-full bg-transparent border-none outline-none text-foreground
                           placeholder:text-foreground/30 py-2 text-sm"
              />
            </div>
            <button onClick={handleSubmit} className="btn-primary text-sm !py-3 !px-6 shrink-0">
              开始分析
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
          <p className="text-xs text-foreground/40 mt-3">
            支持中英文 · 例如：&ldquo;Breast cancer resistance mechanisms&rdquo; 或 &ldquo;阿尔茨海默病生物标志物&rdquo;
          </p>
        </div>

        {/* 数据徽标 */}
        <div className="flex items-center justify-center gap-6 md:gap-10 mt-12 flex-wrap animate-fade-in">
          {[
            { icon: Globe, text: "PubMed 实时检索" },
            { icon: Shield, text: "多维度评分" },
            { icon: BarChart3, text: "可视化报告" },
          ].map((item) => (
            <div key={item.text} className="flex items-center gap-2 text-xs text-foreground/50">
              <item.icon className="w-4 h-4 text-primary/40" />
              {item.text}
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// ── 功能模块卡片 ──────────────────────────────

function FeatureCards() {
  return (
    <section id="features" className="py-20 md:py-28">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="section-label">核心功能</span>
          <h2 className="text-3xl md:text-4xl font-bold mt-4 mb-4">
            全流程自动化分析
          </h2>
          <p className="text-foreground/60 max-w-xl mx-auto">
            从文献检索到实验方案，每一个步骤都由 AI 驱动
          </p>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {FEATURES.map((feature, idx) => (
            <Link
              key={feature.title}
              href={feature.href}
              className="module-card group animate-fade-in block"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              {/* 装饰色块 */}
              <div
                className={cn(
                  "absolute inset-0 rounded-2xl bg-gradient-to-br opacity-0",
                  "group-hover:opacity-100 transition-opacity duration-500",
                  feature.color
                )}
              />

              <div className="relative z-10">
                <div className="module-icon mb-5">
                  <feature.icon className="w-6 h-6" />
                </div>

                <h3 className="text-lg font-semibold mb-3 group-hover:text-primary transition-colors">
                  {feature.title}
                </h3>

                <p className="text-sm text-foreground/60 leading-relaxed mb-5">
                  {feature.desc}
                </p>

                <div
                  className={cn(
                    "inline-flex items-center gap-1 text-sm font-medium",
                    "text-primary/60 group-hover:text-primary transition-colors"
                  )}
                >
                  了解更多 <ChevronRight className="w-4 h-4" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}

// ── 数据统计与图表 ─────────────────────────────

function StatsSection() {
  return (
    <section id="stats" className="py-20 md:py-28 bg-gradient-to-b from-transparent to-white/40">
      <div className="max-w-7xl mx-auto px-6">
        {/* 统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 md:gap-6 mb-20">
          {STATS.map((stat, idx) => (
            <div
              key={stat.label}
              className="glass-card p-6 text-center animate-fade-in"
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              <stat.icon className="w-6 h-6 text-primary/40 mx-auto mb-3" />
              <div className="stat-value text-3xl md:text-4xl">{stat.value}</div>
              <div className="stat-label">{stat.label}</div>
              <div className="text-xs text-emerald-600 font-medium mt-1">
                {stat.change}
              </div>
            </div>
          ))}
        </div>

        {/* 图表 */}
        <div className="glass-card p-6 md:p-8">
          <div className="flex items-center justify-between mb-8">
            <div>
              <h3 className="text-xl font-semibold">平台增长趋势</h3>
              <p className="text-sm text-foreground/60 mt-1">
                近 6 个月数据
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-primary" />
                <span>文献检索</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-emerald-400" />
                <span>靶点发现</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded bg-amber-400" />
                <span>分析项目</span>
              </div>
            </div>
          </div>

          <div className="h-[300px] md:h-[350px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorLit" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#2D6A4F" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#2D6A4F" stopOpacity={0} />
                  </linearGradient>
                  <linearGradient id="colorTgt" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#52B788" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#52B788" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#E8E3DC" />
                <XAxis dataKey="month" stroke="#9CA3AF" fontSize={12} />
                <YAxis stroke="#9CA3AF" fontSize={12} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(255,255,255,0.9)",
                    backdropFilter: "blur(10px)",
                    border: "1px solid rgba(255,255,255,0.3)",
                    borderRadius: "12px",
                    boxShadow: "0 8px 32px rgba(31,38,135,0.07)",
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="literature"
                  stroke="#2D6A4F"
                  fill="url(#colorLit)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="targets"
                  stroke="#52B788"
                  fill="url(#colorTgt)"
                  strokeWidth={2}
                />
                <Area
                  type="monotone"
                  dataKey="analysis"
                  stroke="#F59E0B"
                  fill="none"
                  strokeWidth={2}
                  strokeDasharray="5 5"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </section>
  )
}

// ── 工作流程 ──────────────────────────────────

function Workflow() {
  const steps = [
    { num: "01", title: "输入研究问题", desc: "自然语言描述你的研究目标，AI 自动理解意图" },
    { num: "02", title: "文献检索与阅读", desc: "自动搜索 PubMed，LLM 深度阅读并提取关键发现" },
    { num: "03", title: "多维度靶点评分", desc: "6 维度评分 + 多智能体协作推理，精确评估" },
    { num: "04", title: "方案与报告生成", desc: "生成实验方案 + 完整研究报告，一键导出" },
  ]

  return (
    <section id="workflow" className="py-20 md:py-28">
      <div className="max-w-7xl mx-auto px-6">
        <div className="text-center mb-16">
          <span className="section-label">工作流程</span>
          <h2 className="text-3xl md:text-4xl font-bold mt-4 mb-4">
            四步完成研究
          </h2>
          <p className="text-foreground/60 max-w-xl mx-auto">
            从想法到结果，全程自动化
          </p>
        </div>

        <div className="relative">
          {/* 连接线 */}
          <div className="hidden lg:block absolute top-1/2 left-[15%] right-[15%] h-[2px] 
                          bg-gradient-to-r from-primary/20 via-primary/40 to-primary/20 -translate-y-1/2" />

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-8">
            {steps.map((step, idx) => (
              <div
                key={step.num}
                className="relative text-center animate-fade-in"
                style={{ animationDelay: `${idx * 150}ms` }}
              >
                <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center
                                mx-auto mb-6 group-hover:scale-110 transition-transform relative z-10">
                  <span className="text-2xl font-bold text-primary">{step.num}</span>
                </div>
                <h3 className="text-lg font-semibold mb-2">{step.title}</h3>
                <p className="text-sm text-foreground/60">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// ── CTA 区域 ──────────────────────────────────

function CTA({ onStartClick }: { onStartClick: () => void }) {
  return (
    <section className="py-20 md:py-28">
      <div className="max-w-4xl mx-auto px-6">
        <div className="glass-card p-12 md:p-16 text-center relative overflow-hidden">
          <div className="hero-blob w-[300px] h-[300px] bg-emerald-300/20 top-[-100px] right-[-100px]" />
          <div className="hero-blob w-[200px] h-[200px] bg-teal-300/15 bottom-[-50px] left-[-50px]" />

          <div className="relative z-10">
            <h2 className="text-3xl md:text-4xl font-bold mb-4">
              准备好开始你的研究了吗？
            </h2>
            <p className="text-foreground/60 max-w-lg mx-auto mb-8">
              无需编程基础，输入研究问题即可获得完整的靶点分析报告
            </p>
            <button onClick={onStartClick} className="btn-primary text-base !px-8 !py-4">
              免费开始使用
              <ArrowRight className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}

// ── 页脚 ──────────────────────────────────────

function Footer() {
  return (
    <footer className="border-t border-white/30 bg-white/40 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-6 py-12">
        <div className="grid md:grid-cols-4 gap-8 mb-10">
          <div className="md:col-span-2">
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                <Dna className="w-4 h-4 text-white" />
              </div>
              <span className="font-semibold text-primary">
                BioResearch<span className="text-primary/60">Platform</span>
              </span>
            </div>
            <p className="text-sm text-foreground/60 max-w-sm">
              AI 驱动的生物医学研究平台 — 让科研更高效、更精准。
            </p>
          </div>
          <div>
            <h4 className="text-sm font-semibold mb-4">功能</h4>
            <div className="space-y-2 text-sm text-foreground/60">
              <p>文献检索</p>
              <p>生信分析</p>
              <p>靶点发现</p>
              <p>方案生成</p>
            </div>
          </div>
          <div>
            <h4 className="text-sm font-semibold mb-4">支持</h4>
            <div className="space-y-2 text-sm text-foreground/60">
              <p>使用文档</p>
              <p>API 参考</p>
              <p>联系我们</p>
            </div>
          </div>
        </div>
        <div className="border-t border-white/30 pt-6 text-center text-xs text-foreground/40">
          © 2026 BioResearch Platform. All rights reserved.
        </div>
      </div>
    </footer>
  )
}

// ── 页面 ──────────────────────────────────────

export default function Home() {
  const [modalOpen, setModalOpen] = useState(false)
  const [modalQuestion, setModalQuestion] = useState("")
  const heroRef = useRef<HTMLDivElement>(null)

  const scrollToHero = () => {
    heroRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  const openModal = (question = "") => {
    setModalQuestion(question)
    setModalOpen(true)
  }

  return (
    <main>
      <StartModal
        open={modalOpen}
        onClose={() => { setModalOpen(false); setModalQuestion("") }}
        initialQuestion={modalQuestion}
      />
      <Navbar onStartClick={scrollToHero} />
      <div ref={heroRef}><Hero
        onStartClick={openModal}
        onSearchSubmit={(q) => openModal(q)}
      /></div>
      <FeatureCards />
      <StatsSection />
      <Workflow />
      <CTA onStartClick={() => openModal()} />
      <Footer />
    </main>
  )
}
