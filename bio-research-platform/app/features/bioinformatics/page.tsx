"use client"

import { useState } from "react"
import Link from "next/link"
import {
  ArrowLeft, Dna, BarChart3, PieChart, TrendingUp, Network, Brain,
  ArrowRight, Sparkles, FlaskConical,
} from "lucide-react"

export default function BioinformaticsPage() {
  const [activeCard, setActiveCard] = useState<string | null>(null)

  const analyses = [
    {
      id: "de",
      icon: BarChart3,
      title: "差异表达分析",
      desc: "t-test / Wilcoxon 自适应选择，BH / Bonferroni 多重校正，log2FC 与 p-value 联合筛选",
      detail: "自动加载用户上传的基因表达矩阵（CSV/TSV格式），根据分组信息自动选择参数检验或非参数检验方法。多重校正支持 Bonferroni 和 BH 两种方案。输出包含 log2FC、p-value、padj 三列。结果自动保存为 CSV 文件。",
      emoji: "📊",
    },
    {
      id: "go",
      icon: PieChart,
      title: "GO 富集分析",
      desc: "支持 BP / CC / MF 三大子本体，自动识别显著富集的生物学过程",
      detail: "对差异表达基因列表执行 GO 富集分析。覆盖 Biological Process、Cellular Component、Molecular Function 三大子本体。使用超几何检验计算 p-value，经 BH 校正后输出显著富集项。自动生成气泡图可视化。",
      emoji: "🎯",
    },
    {
      id: "kegg",
      icon: Network,
      title: "KEGG 通路富集",
      desc: "基于 KEGG 数据库的通路富集分析，揭示关键信号通路",
      detail: "将差异基因映射到 KEGG 信号通路，识别显著富集的代谢和调控通路。支持人类和小鼠两种基因 ID 格式（Entrez/Symbol）。输出富集通路列表和可视化结果。",
      emoji: "🧬",
    },
    {
      id: "survival",
      icon: TrendingUp,
      title: "生存分析",
      desc: "Kaplan-Meier 生存曲线 + Log-rank 检验 + Cox 比例风险回归",
      detail: "加载临床生存数据（总生存/无进展生存），按基因表达中位数分组。自动绘制 KM 生存曲线和风险表。执行 Log-rank 检验和 Cox 比例风险回归分析。输出生存曲线图、p-value 和 HR 值。",
      emoji: "📈",
    },
    {
      id: "viz",
      icon: Brain,
      title: "自动化可视化",
      desc: "火山图、表达热图、富集气泡图、KM 曲线 — 出版级 300 DPI",
      detail: "所有图表使用专业配色方案，满足 SCI 期刊发表要求。支持火山图（标注 Top 基因）、聚类热图（自动层次聚类）、富集气泡图、KM 生存曲线。导出格式支持 PNG（300 DPI）/ SVG / PDF。",
      emoji: "🎨",
    },
    {
      id: "pipeline",
      icon: Dna,
      title: "一键全流程编排",
      desc: "串联全部生信分析步骤，自动保存结果到 CSV / JSON / PNG",
      detail: "只需提供表达矩阵和分组文件，系统自动执行完整分析流水线：差异表达 → GO 富集 → KEGG 通络 → 可视化。所有中间结果和最终图表按目录结构组织保存，便于后续检查和复用。",
      emoji: "⚡",
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
            <Dna className="w-5 h-5 text-primary" />
            <span className="font-semibold text-primary">生信分析引擎</span>
          </div>
        </div>
      </nav>

      <section className="relative py-20 overflow-hidden">
        <div className="hero-blob w-[400px] h-[400px] bg-teal-300/20 top-[-100px] right-[-100px]" />
        <div className="max-w-4xl mx-auto px-6 text-center relative">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <Dna className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl md:text-5xl font-bold mb-4">生信分析引擎</h1>
          <p className="text-gray-500 max-w-2xl mx-auto text-lg mb-8">
            全自动生物信息学分析流水线，从差异表达到通路富集，一键完成
          </p>
          <Link href="/?start=true" className="btn-primary inline-flex text-sm">
            <Sparkles className="w-4 h-4" />
            上传数据开始分析
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* 交互式分析卡片 */}
      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-10">分析能力概览</h2>
          <div className="grid md:grid-cols-2 gap-4">
            {analyses.map((item) => (
              <div key={item.id}>
                <button
                  onClick={() => setActiveCard(activeCard === item.id ? null : item.id)}
                  className={`w-full glass-card p-6 text-left hover:shadow-glass-hover transition-all ${
                    activeCard === item.id ? "border-primary/30 bg-primary/[0.02]" : ""
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br from-teal-400/20 to-transparent flex items-center justify-center shrink-0`}>
                      <item.icon className="w-6 h-6 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold mb-1">{item.title}</h3>
                      <p className="text-sm text-gray-500 leading-relaxed">{item.desc}</p>
                    </div>
                    <span className="text-2xl shrink-0">{item.emoji}</span>
                  </div>
                  {activeCard === item.id && (
                    <div className="mt-4 pt-4 border-t border-gray-100 animate-fade-in">
                      <p className="text-sm text-gray-600 leading-relaxed">{item.detail}</p>
                    </div>
                  )}
                </button>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* 工作流示意图 */}
      <section className="pb-20 bg-white/50">
        <div className="max-w-4xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-10">分析流水线</h2>
          <div className="glass-card p-8">
            <div className="flex items-center justify-center gap-4 flex-wrap">
              {[
                { icon: Dna, label: "表达矩阵" },
                { icon: BarChart3, label: "差异分析" },
                { icon: PieChart, label: "GO 富集" },
                { icon: Network, label: "KEGG" },
                { icon: TrendingUp, label: "生存分析" },
                { icon: FlaskConical, label: "聚类热图" },
              ].map((item, idx) => (
                <div key={item.label} className="flex items-center gap-4">
                  <div className="flex flex-col items-center gap-2">
                    <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center">
                      <item.icon className="w-6 h-6 text-primary" />
                    </div>
                    <span className="text-xs text-gray-500">{item.label}</span>
                  </div>
                  {idx < 5 && <ArrowRight className="w-4 h-4 text-primary/30" />}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-20">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="glass-card p-10 relative overflow-hidden">
            <div className="hero-blob w-[200px] h-[200px] bg-teal-300/15 top-[-50px] right-[-50px]" />
            <div className="relative z-10">
              <h3 className="text-2xl font-bold mb-3">开始生信分析</h3>
              <p className="text-gray-500 mb-6 text-sm">上传表达数据，AI 自动完成全流程分析</p>
              <Link href="/" className="btn-primary inline-flex text-sm">
                开始使用 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
