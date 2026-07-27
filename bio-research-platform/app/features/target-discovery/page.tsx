"use client"

import { useState } from "react"
import Link from "next/link"
import {
  ArrowLeft, Target, Shield, Layers, Sliders, Brain, GitBranch,
  ArrowRight, Sparkles, Award, TrendingUp, CheckCircle,
} from "lucide-react"

export default function TargetDiscoveryPage() {
  const [activeDimension, setActiveDimension] = useState<string | null>(null)

  const dimensions = [
    {
      id: "literature",
      icon: Brain,
      label: "文献支持度",
      weight: "25%",
      desc: "基于 PubMed 文献数量、质量、时效性评估",
      detail: "统计目标基因在 PubMed 中的出版物总数，计算与疾病关键词的共出现频率。评估文献质量（影响因子/引用次数）。区分直接证据（机制研究）vs 间接证据（相关研究）。权重最高——科学文献是靶点评估的核心基础。",
    },
    {
      id: "expression",
      icon: TrendingUp,
      label: "表达差异",
      weight: "20%",
      desc: "疾病组 vs 对照组表达差异显著性评估",
      detail: "基于差异表达分析结果：log2FC > 2 得高分（表达变化显著），p-value < 0.01 加分（统计显著）。考虑组织特异性表达模式——靶组织 vs 正常组织的表达差异优先。",
    },
    {
      id: "function",
      icon: Layers,
      label: "功能重要性",
      weight: "15%",
      desc: "GO 富集、KEGG 通路中的关键位置评估",
      detail: "评估基因在疾病相关通路中的位置——通路核心节点加分，末端效应器减分。GO 富集分析中的显著项数量越多越好。是否是已知的疾病相关通路的驱动基因。",
    },
    {
      id: "druggability",
      icon: Shield,
      label: "可药性",
      weight: "20%",
      desc: "蛋白家族类别、结构特征、已知药物评估",
      detail: "评估蛋白是否属于「可成药家族」（激酶 > 受体 > 酶 > 转录因子 > 结构蛋白）。是否有已知的晶体结构或可结合的活性口袋。是否有已有药物或临床候选物。",
    },
    {
      id: "novelty",
      icon: Award,
      label: "新颖性",
      weight: "10%",
      desc: "研究热度和竞争程度评估",
      detail: "通过出版物趋势分析判断研究热度——上升趋势加分（新兴靶点），已饱和领域减分。临床试验数量、专利数量反向加权——太多已有研究说明创新空间小。",
    },
    {
      id: "safety",
      icon: CheckCircle,
      label: "安全性",
      weight: "10%",
      desc: "组织特异性、已知副作用评估",
      detail: "靶组织特异性表达越高越安全（减少脱靶效应）。检索已知副作用数据。分析蛋白-蛋白互作网络中的冗余性——有冗余意味着敲除/抑制后有补偿机制。",
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
            <Target className="w-5 h-5 text-primary" />
            <span className="font-semibold text-primary">智能靶点发现</span>
          </div>
        </div>
      </nav>

      <section className="relative py-20 overflow-hidden">
        <div className="hero-blob w-[400px] h-[400px] bg-green-300/20 top-[-100px] right-[-100px]" />
        <div className="max-w-4xl mx-auto px-6 text-center relative">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <Target className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl md:text-5xl font-bold mb-4">智能靶点发现</h1>
          <p className="text-gray-500 max-w-2xl mx-auto text-lg mb-8">
            6 维度评分 + 多智能体推理 + 人工反馈，精确锁定候选靶点
          </p>
          <Link href="/?start=true" className="btn-primary inline-flex text-sm">
            <Sparkles className="w-4 h-4" />
            开始发现靶点
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* 六维度详情 */}
      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-10">六维度靶点评估体系</h2>

          <div className="grid md:grid-cols-3 gap-4 mb-8">
            {dimensions.map((d) => (
              <button
                key={d.id}
                onClick={() => setActiveDimension(activeDimension === d.id ? null : d.id)}
                className={`glass-card p-5 text-left hover:shadow-glass-hover transition-all ${
                  activeDimension === d.id ? "ring-2 ring-primary/30 bg-primary/[0.02]" : ""
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                    <d.icon className="w-5 h-5 text-primary" />
                  </div>
                  <span className="text-xs font-bold px-2 py-1 bg-primary/10 text-primary rounded-full">
                    {d.weight}
                  </span>
                </div>
                <h3 className="font-semibold text-sm mb-1">{d.label}</h3>
                <p className="text-xs text-gray-400">{d.desc}</p>
              </button>
            ))}
          </div>

          {/* 展开详情 */}
          {activeDimension && (
            <div className="glass-card p-6 animate-fade-in">
              {dimensions.filter((d) => d.id === activeDimension).map((d) => (
                <div key={d.id} className="flex gap-4">
                  <div className="w-10 h-10 rounded-xl bg-green-50 flex items-center justify-center shrink-0">
                    <d.icon className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <h4 className="font-semibold mb-1">
                      {d.label}
                      <span className="ml-2 text-xs font-normal px-2 py-0.5 bg-amber-50 text-amber-600 rounded-full">
                        权重 {d.weight}
                      </span>
                    </h4>
                    <p className="text-sm text-gray-600 leading-relaxed">{d.detail}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* 多智能体推理 */}
      <section className="pb-20 bg-white/50">
        <div className="max-w-5xl mx-auto px-6">
          <h2 className="text-2xl font-bold text-center mb-3">多智能体协作推理</h2>
          <p className="text-center text-gray-500 mb-10 text-sm">4 个专业 Agent 协同工作，模拟科研团队讨论</p>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { role: "📚", label: "文献分析 Agent", desc: "系统回顾 PubMed 文献，提取靶点相关的支持证据，包括机制、模型、临床数据。" },
              { role: "🧬", label: "组学整合 Agent", desc: "整合表达谱、蛋白质组、网络等数据，验证靶点在不同数据层的信号一致性。" },
              { role: "🔗", label: "网络分析 Agent", desc: "分析靶点在蛋白互作网络中的拓扑位置，识别上下游调控关系和功能模块。" },
              { role: "⚖️", label: "批判评估 Agent", desc: "独立审查前三个 Agent 的分析，识别潜在偏见、验证薄弱点和替代假说。" },
            ].map((a) => (
              <div key={a.label} className="glass-card p-5 flex gap-4">
                <div className="text-3xl shrink-0">{a.role}</div>
                <div>
                  <h4 className="font-semibold text-sm mb-1">{a.label}</h4>
                  <p className="text-xs text-gray-500 leading-relaxed">{a.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="pb-20">
        <div className="max-w-3xl mx-auto px-6 text-center">
          <div className="glass-card p-10 relative overflow-hidden">
            <div className="hero-blob w-[200px] h-[200px] bg-green-300/15 top-[-50px] right-[-50px]" />
            <div className="relative z-10">
              <h3 className="text-2xl font-bold mb-3">开始靶点发现之旅</h3>
              <p className="text-gray-500 mb-6 text-sm">输入疾病名称，AI 为你排序最佳候选靶点</p>
              <Link href="/" className="btn-primary inline-flex text-sm">
                发现靶点 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}
