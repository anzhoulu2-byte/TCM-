"use client"

import Link from "next/link"
import { ArrowLeft, FlaskConical, FileText, Clock, Shield, Beaker, BookOpen } from "lucide-react"

export default function ProtocolPage() {
  return (
    <main className="min-h-screen bg-surface">
      <nav className="glass-nav py-4">
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
          <p className="text-gray-500 max-w-2xl mx-auto text-lg">
            自动生成验证方案、推荐试剂品牌货号、评估可行性与成本
          </p>
        </div>
      </section>

      <section className="pb-20">
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
    </main>
  )
}
