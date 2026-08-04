'use client'

// Studio 报告生成页面
// 选择笔记本和报告类型，生成学术/商业/简短摘要报告

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { ReportViewer } from '@/components/studio/ReportViewer'
import { StudioLayout } from '@/components/studio/StudioLayout'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useGenerateReport } from '@/lib/hooks/use-studio'
import type { ReportType } from '@/lib/api/studio'
import { FileBarChart, Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function StudioReportPage() {
  const { t } = useTranslation()
  const { data: notebooks, isLoading: notebooksLoading } = useNotebooks()
  const generateReport = useGenerateReport()

  const [notebookId, setNotebookId] = useState('')
  const [reportType, setReportType] = useState<ReportType>('academic')
  const [report, setReport] = useState('')

  const handleGenerate = async () => {
    if (!notebookId) return
    setReport('')
    const result = await generateReport.mutateAsync({
      notebook_id: notebookId,
      report_type: reportType,
    })
    setReport(result.report)
  }

  const reportTypes: { value: ReportType; label: string }[] = [
    { value: 'academic', label: t('studio.reportTypeAcademic') },
    { value: 'business', label: t('studio.reportTypeBusiness') },
    { value: 'brief', label: t('studio.reportTypeBrief') },
  ]

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('studio.report')}
          description={t('studio.reportDesc')}
          icon={FileBarChart}
        />

        <div className="page-container py-6 space-y-6">
          <StudioLayout>
            <div className="grid gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
              <Card className="rounded-[24px] border-border/70 bg-background/80 p-6 shadow-none">
                <div className="space-y-5">
                  <div className="space-y-2">
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                      生成参数
                    </p>
                    <h2 className="text-xl font-semibold">{t('studio.generateReport')}</h2>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('studio.selectNotebook')}</Label>
                    <Select value={notebookId} onValueChange={setNotebookId}>
                      <SelectTrigger className="w-full">
                        <SelectValue placeholder={t('studio.selectNotebookPlaceholder')} />
                      </SelectTrigger>
                      <SelectContent>
                        {notebooksLoading ? (
                          <SelectItem value="_loading" disabled>
                            {t('common.loading')}
                          </SelectItem>
                        ) : (
                          notebooks?.map((nb) => (
                            <SelectItem key={nb.id} value={nb.id}>
                              {nb.name}
                            </SelectItem>
                          ))
                        )}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>{t('studio.reportType')}</Label>
                    <Select
                      value={reportType}
                      onValueChange={(v) => setReportType(v as ReportType)}
                    >
                      <SelectTrigger className="w-full">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {reportTypes.map((rt) => (
                          <SelectItem key={rt.value} value={rt.value}>
                            {rt.label}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <Button
                    onClick={handleGenerate}
                    disabled={!notebookId || generateReport.isPending}
                    className="w-full"
                  >
                    {generateReport.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('studio.generating')}
                      </>
                    ) : (
                      t('studio.generateReport')
                    )}
                  </Button>
                </div>
              </Card>

              <div className="min-w-0">
                {report ? (
                  <ReportViewer report={report} reportType={reportType} />
                ) : (
                  <Card className="rounded-[24px] border-border/70 bg-background/80 p-10 text-center text-sm text-muted-foreground shadow-none">
                    先选择一个笔记本并生成报告，结果会显示在这里。
                  </Card>
                )}
              </div>
            </div>
          </StudioLayout>
        </div>
      </div>
    </AppShell>
  )
}
