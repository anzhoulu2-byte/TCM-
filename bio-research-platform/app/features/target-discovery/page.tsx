"use client"

import Link from "next/link"
import { ArrowLeft, Target, Shield, Layers, Sliders, Brain, GitBranch } from "lucide-react"

export default function TargetDiscoveryPage() {
  return (
    <main className="min-h-screen bg-surface">
      <nav className="glass-nav py-4">
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
          <p className="text-gray-500 max-w-2xl mx-auto text-lg">
            多维度评分 + 多智能体推理 + 人工反馈，精确锁定候选靶点
          </p>
        </div>
      </section>

      <section className="pb-20">
        <div className="max-w-5xl mx-auto px-6">
          <div className="grid md:grid-cols-2 gap-6">
            {[
              { icon: Layers, title: "6 维度靶点评分", desc: "文献支持度、表达差异、功能重要性、可药性、新颖性、安全性 — 全方位评估", color: "from-emerald-400/20" },
              { icon: Brain, title: "多智能体推理", desc: "4 个 AI Agent 协作：文献分析 + 组学整合 + 网络分析 + 批判评估", color: "from-teal-400/20" },
              { icon: Sliders, title: "可配置权重", desc: "每个评分维度的权重可调，支持动态更新和自动归一化", color: "from-green-400/20" },
              { icon: Shield, title: "人工反馈融合", desc: "贝叶斯方法融合人工评分与算法评分，让排序更符合专家判断", color: "from-emerald-300/20" },
              { icon: GitBranch, title: "ML 排序模型", desc: "可选 LightGBM / XGBoost 排序模型，含交叉验证评估", color: "from-teal-300/20" },
              { icon: Target, title: "完整证据链", desc: "每个评分附带来源引用，结果全程可追溯、可复现", color: "from-green-300/20" },
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
