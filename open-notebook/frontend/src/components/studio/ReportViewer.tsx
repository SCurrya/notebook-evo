'use client'

// 报告查看器组件
// 展示生成的 Markdown 报告，支持导出 Markdown 文件和打印 PDF

import { Button } from '@/components/ui/button'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Download, Printer, FileText } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

interface ReportViewerProps {
  report: string
  reportType: string
}

export function ReportViewer({ report, reportType }: ReportViewerProps) {
  const { t } = useTranslation()

  // 导出为 Markdown 文件
  const handleExportMarkdown = () => {
    const blob = new Blob([report], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${reportType}_${Date.now()}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  // 打印 PDF（通过浏览器打印功能）
  const handlePrintPDF = () => {
    const printWindow = window.open('', '_blank')
    if (!printWindow) return
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Report - ${reportType}</title>
          <style>
            body { font-family: sans-serif; line-height: 1.6; padding: 40px; max-width: 800px; margin: 0 auto; }
            h1, h2, h3 { color: #333; }
            code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
            pre { background: #f4f4f4; padding: 12px; border-radius: 6px; overflow-x: auto; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
          </style>
        </head>
        <body>${report.replace(/\n/g, '<br>')}</body>
      </html>
    `)
    printWindow.document.close()
    printWindow.print()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold">{t('studio.reportResult')}</h3>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={handleExportMarkdown}>
            <Download className="h-4 w-4 mr-1" />
            {t('studio.exportMarkdown')}
          </Button>
          <Button variant="outline" size="sm" onClick={handlePrintPDF}>
            <Printer className="h-4 w-4 mr-1" />
            {t('studio.printPDF')}
          </Button>
        </div>
      </div>
      <div className="rounded-lg border bg-background p-6 prose prose-sm dark:prose-invert max-w-none overflow-y-auto max-h-[60vh]">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
      </div>
    </div>
  )
}
