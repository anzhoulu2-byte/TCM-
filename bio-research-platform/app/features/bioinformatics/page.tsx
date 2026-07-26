"use client"

import Link from "next/link"
import { ArrowLeft, Dna, BarChart3, PieChart, TrendingUp, Network, Brain } from "lucide-react"

export default function BioinformaticsPage() {
  return (
    <main className="min-h-screen bg-surface">
      <nav className="glass-nav py-4">
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
          <p className="text-gray-500 max-w-2xl mx-auto text-lg">
            全自动生物信息学分析流水线，从差异表达到通路富集，一键完成
          </p>
        </div>
      </section>

      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: BarChart3, title: "差异表达分析", desc: "t-test / Wilcoxon 自适应选择，BH / Bonferroni 多重校正，log2FC 计算", color: "from-emerald-400/20" },
              { icon: PieChart, title: "GO 富集分析", desc: "支持 BP / CC / MF 三大子本体，自动识别显著富集的生物学过程", color: "from-teal-400/20" },
              { icon: Network, title: "KEGG 通路富集", desc: "基于 KEGG 数据库的通路富集分析，揭示关键信号通路", color: "from-green-400/20" },
              { icon: TrendingUp, title: "生存分析", desc: "Kaplan-Meier 生存曲线 + Log-rank 检验 + Cox 比例风险回归", color: "from-emerald-300/20" },
              { icon: Brain, title: "自动化可视化", desc: "火山图、表达热图、富集气泡图、KM 曲线 — 出版级 300 DPI", color: "from-teal-300/20" },
              { icon: Dna, title: "一键全流程编排", desc: "串联全部生信分析步骤，自动保存结果到 CSV / JSON / PNG", color: "from-green-300/20" },
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
