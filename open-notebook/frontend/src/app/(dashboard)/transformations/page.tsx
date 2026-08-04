'use client'

import { useState } from 'react'
import { AppShell } from '@/components/layout/AppShell'
import { Button } from '@/components/ui/button'
import { PageHeader } from '@/components/ui/page-header'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DefaultPromptEditor } from './components/DefaultPromptEditor'
import { TransformationsList } from './components/TransformationsList'
import { TransformationPlayground } from './components/TransformationPlayground'
import { useTransformations } from '@/lib/hooks/use-transformations'
import { Transformation } from '@/lib/types/transformations'
import { Wand2, Play, RefreshCw } from 'lucide-react'
import { useTranslation } from '@/lib/hooks/use-translation'
import { StudioLayout } from '@/components/studio/StudioLayout'

export default function TransformationsPage() {
  const { t } = useTranslation()
  const [activeTab, setActiveTab] = useState('transformations')
  const [selectedTransformation, setSelectedTransformation] = useState<Transformation | undefined>()
  const { data: transformations, isLoading, refetch } = useTransformations()

  const handlePlayground = (transformation: Transformation) => {
    setSelectedTransformation(transformation)
    setActiveTab('playground')
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title={t('transformations.title')}
          description={t('transformations.desc')}
          icon={Wand2}
          actions={
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          }
        />

        <div className="page-container py-6 space-y-6">
          <StudioLayout>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
              <div className="space-y-3">
                <div className="space-y-2">
                  <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-background/70 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                    <span className="size-2 rounded-full bg-primary" />
                    {t('transformations.workspace')}
                  </div>
                  <h2 className="text-3xl font-semibold tracking-tight sm:text-4xl">
                    {t('transformations.title')}
                  </h2>
                  <p className="max-w-3xl text-sm leading-7 text-muted-foreground sm:text-base">
                    这里像一个研究笔记本的变换实验台，风格和 studio 保持一致，适合管理模板，也可以直接试跑内容改写。
                  </p>
                </div>
                <TabsList aria-label={t('common.accessibility.transformationViews')} className="w-full max-w-xl rounded-[18px] border border-border/70 bg-background/70 p-1">
                  <TabsTrigger value="transformations" className="flex items-center gap-2">
                    <Wand2 className="h-4 w-4" />
                    {t('transformations.title')}
                  </TabsTrigger>
                  <TabsTrigger value="playground" className="flex items-center gap-2">
                    <Play className="h-4 w-4" />
                    {t('transformations.playground')}
                  </TabsTrigger>
                </TabsList>
              </div>

              <TabsContent value="transformations" className="space-y-6">
                <DefaultPromptEditor />
                <TransformationsList 
                  transformations={transformations} 
                  isLoading={isLoading}
                  onPlayground={handlePlayground}
                />
              </TabsContent>

              <TabsContent value="playground">
                <TransformationPlayground 
                  transformations={transformations}
                  selectedTransformation={selectedTransformation}
                />
              </TabsContent>
            </Tabs>
          </StudioLayout>
        </div>
      </div>
    </AppShell>
  )
}
