"use client"

import { useState } from "react"
import Link from "next/link"
import {
  ArrowLeft, FlaskConical, FileText, Clock, Shield, Beaker, BookOpen,
  ArrowRight, Sparkles, CheckCircle, AlertTriangle, DollarSign, Calendar,
} from "lucide-react"

export default function ProtocolPage() {
  const [activeTab, setActiveTab] = useState<"structure" | "feasibility">("structure")

  const protocolSections = [
    { icon: FileText, label: "研究目标", desc: "明确研究假说和验证目标" },
    { icon: Beaker, label: "实验设计", desc: "分组、样本量、对照设计" },
    { icon: FlaskConical, label: "具体步骤", desc: "材料、操作、检测方法" },
    { icon: BookOpen, label: "试剂耗材", desc: "品牌、货号、价格估算" },
    { icon: Calendar, label: "时间表", desc: "分阶段计划与里程碑" },
    { icon: TrendingUp, label: "预期结果", desc: "统计分析和结果解读" },
    { icon: Shield, label: "备选方案", desc: "风险预案和替代方法" },
  ]

  return (
    <main className="min-h-screen bg-gradient-to-b from-surface to-white">
      <nav className="glass-nav py-4 sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2 text-sm text-gray-500 hover:text-primary transition-colors">
            <ArrowLeft className="w-4 h-4" /> 返回首页
          </Link>
          <div className="flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-primary" />
            <span className="font-semibold text-primary">实验方案生成</span>
          </div>
        </div>
      </nav>

      <section className="relative py-20 overflow-hidden">
        <div className="hero-blob w-[400px] h-[400px] bg-emerald-300/20 top-[-100px] right-[-100px]" />
        <div className="max-w-4xl mx-auto px-6 text-center relative">
          <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-6">
            <FlaskConical className="w-8 h-8 text-primary" />
          </div>
          <h1 className="text-3xl md:text-5xl font-bold mb-4">实验方案生成</h1>
          <p className="text-gray-500 max-w-2xl mx-auto text-lg mb-8">
            自动生成验证方案、推荐试剂品牌货号、评估可行性与成本
          </p>
          <Link href="/?start=true" className="btn-primary inline-flex text-sm">
            <Sparkles className="w-4 h-4" />
            生成实验方案
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* 方案结构 */}
      <section className="pb-12">
        <div className="max-w-5xl mx-auto px-6">
          {/* Tab */}
          <div className="flex gap-1 mb-8 bg-gray-50 p-1 rounded-xl">
            <button
              onClick={() => setActiveTab("structure")}
              className={`flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all ${
                activeTab === "structure" ? "bg-white text-primary shadow-sm" : "text-gray-400"
              }`}
            >
              方案结构
            </button>
            <button
              onClick={() => setActiveTab("feasibility")}
              className={`flex-1 py-3 px-4 rounded-lg text-sm font-medium transition-all ${
                activeTab === "feasibility" ? "bg-white text-primary shadow-sm" : "text-gray-400"
              }`}
            >
              可行性评估
            </button>
          </div>

          {activeTab === "structure" && (
            <div className="glass-card p-8">
              <h3 className="text-xl font-bold mb-6">七部分专业方案结构</h3>
              <div className="space-y-4">
                {protocolSections.map((section, idx) => (
                  <div key={section.label} className="flex items-start gap-4 p-4 bg-gray-50/50 rounded-xl hover:bg-primary/[0.02] transition-colors">
                    <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center shrink-0">
                      <section.icon className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-bold text-primary/40">#{idx + 1}</span>
                        <h4 className="font-semibold">{section.label}</h4>
                      </div>
                      <p className="text-sm text-gray-500">{section.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === "feasibility" && (
            <div className="glass-card p-8">
              <h3 className="text-xl font-bold mb-6">五维可行性评估体系</h3>
              <div className="space-y-5">
                {[
                  { icon: Clock, label: "时间成本", value: 4, max: 5, desc: "预计完成周期 6-8 周，时间可控", color: "bg-emerald-500" },
                  { icon: DollarSign, label: "资金成本", value: 3, max: 5, desc: "中等预算，主要试剂和耗材费用在正常范围", color: "bg-amber-500" },
                  { icon: FlaskConical, label: "技术难度", value: 3, max: 5, desc: "标准分子生物学技术，不需要特殊设备", color: "bg-amber-500" },
                  { icon: CheckCircle, label: "成功率", value: 4, max: 5, desc: "基于文献报道，类似实验成功率较高", color: "bg-emerald-500" },
                  { icon: AlertTriangle, label: "伦理风险", value: 5, max: 5, desc: "仅涉及细胞实验，无动物或人体实验", color: "bg-emerald-500" },
                ].map((item) => (
                  <div key={item.label} className="flex items-start gap-4">
                    <div className="w-10 h-10 rounded-xl bg-gray-50 flex items-center justify-center shrink-0">
                      <item.icon className="w-5 h-5 text-primary" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-medium text-sm">{item.label}</span>
                        <span className="text-xs text-gray-400">{item.value}/{item.max}</span>
                      </div>
                      <div className="h-2 bg-gray-100 rounded-full overflow-hidden mb-2">
                        <div
                          className={`h-full ${item.color} rounded-full transition-all duration-700`}
                          style={{ width: `${(item.value / item.max) * 100}%` }}
                        />
                      </div>
                      <p className="text-xs text-gray-400">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="mt-8 p-4 bg-emerald-50 rounded-xl text-center">
                <div className="flex items-center justify-center gap-2 mb-1">
                  <CheckCircle className="w-5 h-5 text-emerald-600" />
                  <span className="font-semibold text-emerald-700">综合可行性：良好</span>
                </div>
                <p className="text-xs text-emerald-600/70">该方案在现有资源和条件下具备较高的可执行性</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* 特性 */}
      <section className="pb-20 bg-white/50">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: FileText, title: "7 部分结构方案", desc: "研究目标 → 实验设计 → 具体步骤 → 试剂耗材 → 时间表 → 预期结果 → 备选方案", color: "from-emerald-400/20" },
              { icon: Beaker, title: "三种实验类型", desc: "细胞实验 (in vitro)、动物实验 (in vivo)、分子生物学实验 — 自动适配", color: "from-teal-400/20" },
              { icon: BookOpen, title: "资源智能推荐", desc: "推荐最适细胞系、抗体品牌货号、检测方法和统计分析方法", color: "from-green-400/20" },
              { icon: Shield, title: "5 维可行性评估", desc: "时间成本、资金成本、技术难度、成功率、伦理风险 — 综合打分", color: "from-emerald-300/20" },
              { icon: Clock, title: "详细时间线", desc: "自动生成分阶段时间表，包含里程碑日期和关键交付物", color: "from-teal-300/20" },
              { icon: FlaskConical, title: "Word 文档导出", desc: "专业格式的 .docx 文档，含表格和格式化参考文献", color: "from-green-300/20" },
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
              <h3 className="text-2xl font-bold mb-3">生成你的实验方案</h3>
              <p className="text-gray-500 mb-6 text-sm">输入靶点基因，AI 为你设计完整的验证方案</p>
              <Link href="/" className="btn-primary inline-flex text-sm">
                生成方案 <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}

function TrendingUp({ className }: { className?: string }) {
  return (
    <svg className={className} width="24" height="24" viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"/>
      <polyline points="17 6 23 6 23 12"/>
    </svg>
  )
}
