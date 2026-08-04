'use client'

// Studio FAQ 生成页面
// 选择笔记本和问题数量，生成 FAQ 问答列表

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { PageHeader } from '@/components/ui/page-header'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { FAQList } from '@/components/studio/FAQList'
import { StudioLayout } from '@/components/studio/StudioLayout'
import { useNotebooks } from '@/lib/hooks/use-notebooks'
import { useGenerateFAQ } from '@/lib/hooks/use-studio'
import type { FAQItem } from '@/lib/api/studio'
import { HelpCircle, Loader2 } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'

export default function StudioFAQPage() {
  const { t } = useTranslation()
  const { data: notebooks, isLoading: notebooksLoading } = useNotebooks()
  const generateFAQ = useGenerateFAQ()

  const [notebookId, setNotebookId] = useState('')
  const [numQuestions, setNumQuestions] = useState(5)
  const [faqs, setFaqs] = useState<FAQItem[]>([])

  const handleGenerate = async () => {
    if (!notebookId) return
    setFaqs([])
    const result = await generateFAQ.mutateAsync({
      notebook_id: notebookId,
      num_questions: numQuestions,
    })
    setFaqs(result.faqs)
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('studio.faq')}
          description={t('studio.faqDesc')}
          icon={HelpCircle}
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
                    <h2 className="text-xl font-semibold">{t('studio.generateFAQ')}</h2>
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
                    <Label>{t('studio.numQuestions')}</Label>
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={numQuestions}
                      onChange={(e) => setNumQuestions(Number(e.target.value))}
                    />
                  </div>

                  <Button
                    onClick={handleGenerate}
                    disabled={!notebookId || generateFAQ.isPending}
                    className="w-full"
                  >
                    {generateFAQ.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        {t('studio.generating')}
                      </>
                    ) : (
                      t('studio.generateFAQ')
                    )}
                  </Button>
                </div>
              </Card>

              <div className="min-w-0">
                {faqs.length > 0 ? (
                  <FAQList faqs={faqs} />
                ) : (
                  <Card className="rounded-[24px] border-border/70 bg-background/80 p-10 text-center text-sm text-muted-foreground shadow-none">
                    结果会在这里展开，适合快速查看笔记本中的问题与答案。
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
