import type { Metadata } from "next"
import "./globals.css"

export const metadata: Metadata = {
  title: "BioResearch Platform | 自动化生物医学靶点发现",
  description: "AI驱动的生物医学研究平台 — 从文献检索到靶点发现的全流程自动化",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="zh-CN">
      <body className="min-h-screen bg-surface">{children}</body>
    </html>
  )
}
