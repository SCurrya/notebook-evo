﻿'use client'

import { useMemo, useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Download,
  Eye,
  Image as ImageIcon,
  Loader2,
  Sparkles,
  Trash2,
  XCircle,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { PageHeader } from '@/components/ui/page-header'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'
import Image from 'next/image'
import { imageApi } from '@/lib/api/image'
import { useCreateImageTask, useDeleteImageTask, useImageProviders, useImageTasks } from '@/lib/hooks/use-image'
import { cn } from '@/lib/utils'
import type { ImageProvider, ImageTaskStatus } from '@/lib/types/image'

const ALL_SIZES = [
  { value: '256x256', label: '256 × 256' },
  { value: '512x512', label: '512 × 512' },
  { value: '1024x1024', label: '1024 × 1024（方形）' },
  { value: '1792x1024', label: '1792 × 1024（横向）' },
  { value: '1024x1792', label: '1024 × 1792（纵向）' },
]

const QUALITY_OPTIONS = [
  { value: 'standard', label: '标准' },
  { value: 'hd', label: '高清' },
]

const STYLE_OPTIONS = [
  { value: 'vivid', label: '鲜明' },
  { value: 'natural', label: '自然' },
]

const MODEL_OPTIONS = [
  { value: 'dall-e-3', label: 'DALL·E 3' },
  { value: 'dall-e-2', label: 'DALL·E 2' },
]

const STATE_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'text-muted-foreground' },
  processing: { label: '生成中', color: 'text-blue-500' },
  completed: { label: '已完成', color: 'text-green-500' },
  failed: { label: '失败', color: 'text-red-500' },
}

function getSizesForProvider(provider: ImageProvider, model?: string) {
  if (provider === 'openai') {
    if (model === 'dall-e-2') {
      return ALL_SIZES.filter((s) => ['256x256', '512x512', '1024x1024'].includes(s.value))
    }
    return ALL_SIZES.filter((s) => ['1024x1024', '1792x1024', '1024x1792'].includes(s.value))
  }
  if (provider === 'stable_diffusion') {
    return ALL_SIZES.filter((s) => ['1024x1024', '1792x1024', '1024x1792'].includes(s.value))
  }
  return ALL_SIZES
}

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}

interface PreviewState {
  url: string
  prompt: string
  width: number
  height: number
}

export default function ImagePage() {
  const [selectedProvider, setSelectedProvider] = useState<ImageProvider>('placeholder')
  const [prompt, setPrompt] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [size, setSize] = useState('1024x1024')
  const [quality, setQuality] = useState('standard')
  const [style, setStyle] = useState('vivid')
  const [n, setN] = useState(1)
  const [model, setModel] = useState('dall-e-3')
  const [preview, setPreview] = useState<PreviewState | null>(null)

  const providersQuery = useImageProviders()
  const tasksQuery = useImageTasks(1, 20)
  const createTask = useCreateImageTask()
  const deleteTask = useDeleteImageTask()

  const providers = providersQuery.data ?? []
  const selectedProviderInfo = providers.find((p) => p.id === selectedProvider)
  const providerAvailable = selectedProviderInfo?.available ?? false
  const availableSizes = useMemo(() => getSizesForProvider(selectedProvider, model), [selectedProvider, model])

  const handleSelectProvider = (p: ImageProvider) => {
    setSelectedProvider(p)
    if (p === 'openai') setModel('dall-e-3')
    const newSizes = getSizesForProvider(p, p === 'openai' ? 'dall-e-3' : undefined)
    if (!newSizes.some((s) => s.value === size)) {
      setSize(newSizes[0]?.value ?? '1024x1024')
    }
  }

  const handleModelChange = (m: string) => {
    setModel(m)
    const newSizes = getSizesForProvider('openai', m)
    if (!newSizes.some((s) => s.value === size)) {
      setSize(newSizes[0]?.value ?? '1024x1024')
    }
  }

  const handleSubmit = async () => {
    if (!prompt.trim() || !providerAvailable) return
    await createTask.mutateAsync({
      prompt: prompt.trim(),
      negative_prompt: selectedProvider === 'stable_diffusion' ? negativePrompt.trim() || undefined : undefined,
      size,
      quality,
      style,
      n,
      provider: selectedProvider,
      model: selectedProvider === 'openai' ? model : undefined,
    })
    setPrompt('')
    setNegativePrompt('')
  }

  const isDalle3 = selectedProvider === 'openai' && model === 'dall-e-3'
  const showNegativePrompt = selectedProvider === 'stable_diffusion'
  const showModelSelect = selectedProvider === 'openai'
  const showQualityStyle = isDalle3

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title="图片生成"
          description="使用 OpenAI、Stable Diffusion 或占位服务，根据文本提示生成图片。"
          icon={ImageIcon}
        />

        <div className="page-container py-6 space-y-6">
          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle>生成服务</CardTitle>
              <CardDescription>选择一个图片生成服务。未配置的服务会显示，但不能直接使用。</CardDescription>
            </CardHeader>
            <CardContent>
              {providersQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  正在加载服务列表...
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                  {providers.map((p) => (
                    <div
                      key={p.id}
                      onClick={() => handleSelectProvider(p.id as ImageProvider)}
                      className={cn('relative cursor-pointer rounded-2xl border p-4 transition-all duration-normal', selectedProvider === p.id ? 'border-primary bg-accent/60 ring-2 ring-primary/15' : 'hover:border-muted-foreground/50 hover:bg-accent/30')}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="space-y-1">
                          <span className="font-medium">{p.name}</span>
                          <p className="text-xs text-muted-foreground">{p.description}</p>
                        </div>
                        {p.available ? <Badge className="bg-green-500 text-white">可用</Badge> : <Badge variant="secondary">未配置</Badge>}
                      </div>
                      {p.models.length > 0 && (
                        <div className="mt-3 flex flex-wrap gap-1">
                          {p.models.map((m) => <Badge key={m} variant="outline" className="text-xs rounded-full">{m}</Badge>)}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle>新建图片任务</CardTitle>
              <CardDescription>输入提示词并配置生成参数。</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {!providerAvailable && selectedProvider !== 'placeholder' && (
                <Alert className="bg-amber-50 text-amber-900 border-amber-200 dark:bg-amber-950/40 dark:text-amber-200 dark:border-amber-900">
                  <AlertTriangle className="h-4 w-4" />
                  <AlertTitle>服务未配置</AlertTitle>
                  <AlertDescription>
                    请设置 <code className="mx-1 px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/50 text-xs">{selectedProvider === 'openai' ? 'OPENAI_API_KEY' : 'STABILITY_API_KEY'}</code>
                    环境变量后再使用，或切换到占位符服务做离线演示。
                  </AlertDescription>
                </Alert>
              )}

              <div className="space-y-2">
                <Label htmlFor="prompt">提示词 <span className="text-destructive">*</span></Label>
                <Textarea id="prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="例如：日落时分的宁静山景，橙紫交织的天空..." rows={3} disabled={!providerAvailable || createTask.isPending} />
              </div>

              {showNegativePrompt && (
                <div className="space-y-2">
                  <Label htmlFor="negative-prompt">反向提示词</Label>
                  <Textarea id="negative-prompt" value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} placeholder="需要排除的元素：模糊、低质量、扭曲..." rows={2} disabled={!providerAvailable || createTask.isPending} />
                </div>
              )}

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                {showModelSelect && (
                  <div className="space-y-2">
                    <Label>模型</Label>
                    <Select value={model} onValueChange={handleModelChange} disabled={!providerAvailable || createTask.isPending}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {MODEL_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="space-y-2">
                  <Label>尺寸</Label>
                  <Select value={size} onValueChange={setSize} disabled={!providerAvailable || createTask.isPending}>
                    <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {availableSizes.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>

                {showQualityStyle && (
                  <div className="space-y-2">
                    <Label>质量</Label>
                    <Select value={quality} onValueChange={setQuality} disabled={!providerAvailable || createTask.isPending}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {QUALITY_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                {showQualityStyle && (
                  <div className="space-y-2">
                    <Label>风格</Label>
                    <Select value={style} onValueChange={setStyle} disabled={!providerAvailable || createTask.isPending}>
                      <SelectTrigger className="w-full"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {STYLE_OPTIONS.map((opt) => <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>)}
                      </SelectContent>
                    </Select>
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="n">数量（1-4）</Label>
                  <Input id="n" type="number" min={1} max={4} value={n} onChange={(e) => setN(Math.max(1, Math.min(4, Number(e.target.value) || 1)))} disabled={!providerAvailable || createTask.isPending} />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button variant="gradient" onClick={handleSubmit} disabled={!providerAvailable || createTask.isPending || !prompt.trim()} className="rounded-xl">
                  {createTask.isPending ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" />正在生成...</>) : (<><Sparkles className="h-4 w-4 mr-2" />生成图片</>)}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card className="rounded-2xl">
            <CardHeader>
              <CardTitle>图片任务</CardTitle>
              <CardDescription>生成的图片保存在本地。点击缩略图预览，或下载保存。</CardDescription>
            </CardHeader>
            <CardContent>
              {tasksQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground"><Loader2 className="h-5 w-5 mr-2 animate-spin" />正在加载任务...</div>
              ) : tasksQuery.data?.items?.length ? (
                <div className="space-y-4">
                  {tasksQuery.data.items.map((task) => <TaskCard key={task.id} task={task} onPreview={setPreview} onDelete={(id) => deleteTask.mutate(id)} deleting={deleteTask.isPending} />)}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">暂无图片任务，请在上方创建。</div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Dialog open={!!preview} onOpenChange={(open) => !open && setPreview(null)}>
        <DialogContent className="sm:max-w-3xl rounded-2xl">
          <DialogHeader>
            <DialogTitle>图片预览</DialogTitle>
            <DialogDescription>{preview ? `${preview.width} × ${preview.height}px` : ''}</DialogDescription>
          </DialogHeader>
          {preview && (
            <div className="space-y-4">
              <div className="flex items-center justify-center rounded-2xl overflow-hidden bg-muted/30">
              <Image src={preview.url} alt={preview.prompt} width={preview.width} height={preview.height} className="max-w-full max-h-[60vh] h-auto w-auto object-contain" unoptimized />
              </div>
              <p className="text-sm text-muted-foreground">{preview.prompt}</p>
              <div className="flex justify-end">
                <a href={preview.url} download className="inline-flex">
                  <Button variant="outline" className="rounded-xl"><Download className="h-4 w-4 mr-2" />下载</Button>
                </a>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </AppShell>
  )
}

interface TaskCardProps {
  task: ImageTaskStatus
  onPreview: (state: PreviewState) => void
  onDelete: (taskId: string) => void
  deleting: boolean
}

function TaskCard({ task, onPreview, onDelete, deleting }: TaskCardProps) {
  const stateInfo = STATE_LABELS[task.state] ?? { label: task.state, color: 'text-muted-foreground' }
  const isActive = !['completed', 'failed'].includes(task.state)

  return (
    <div className="rounded-2xl border bg-card/80 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 min-w-0 flex-1">
          <div className="flex items-center gap-2 flex-wrap">
            {task.state === 'completed' ? <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" /> : task.state === 'failed' ? <XCircle className="h-4 w-4 text-red-500 shrink-0" /> : <Loader2 className="h-4 w-4 text-blue-500 animate-spin shrink-0" />}
            <Badge variant="outline" className="text-xs rounded-full">{task.provider}</Badge>
            {task.model && <Badge variant="outline" className="text-xs rounded-full">{task.model}</Badge>}
            <span className={cn('text-xs', stateInfo.color)}>{stateInfo.label}{isActive && task.progress > 0 ? ` (${task.progress}%)` : ''}</span>
          </div>
          <p className="text-sm font-medium truncate">{task.prompt}</p>
          <p className="text-xs text-muted-foreground">{formatTime(task.created_at)}{task.size ? ` · ${task.size}` : ''}{task.n > 1 ? ` · ${task.n} 张` : ''}</p>
          {task.message && task.state !== 'completed' && <p className="text-xs text-muted-foreground truncate">{task.message}</p>}
          {task.error && <p className="text-xs text-red-500">{task.error}</p>}
        </div>
        <Button variant="ghost" size="icon-sm" onClick={() => onDelete(task.id)} disabled={deleting} className="rounded-full">
          <Trash2 className="h-4 w-4" />
        </Button>
      </div>

      {task.images.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
          {task.images.map((img) => (
            <div key={img.index} className="group relative aspect-square rounded-2xl overflow-hidden border bg-muted/30">
              <Image src={`data:image/jpeg;base64,${img.thumbnail_base64}`} alt={task.prompt} width={img.width} height={img.height} className="h-full w-full object-cover transition-transform duration-normal group-hover:scale-105" unoptimized />
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/35 transition-colors flex items-center justify-center gap-2 opacity-0 group-hover:opacity-100">
                <Button size="icon-sm" variant="secondary" className="rounded-full" onClick={() => onPreview({ url: imageApi.getDownloadUrl(task.id, img.index), prompt: task.prompt, width: img.width, height: img.height })}>
                  <Eye className="h-4 w-4" />
                </Button>
                <a href={imageApi.getDownloadUrl(task.id, img.index)} download className="inline-flex">
                  <Button size="icon-sm" variant="secondary" className="rounded-full">
                    <Download className="h-4 w-4" />
                  </Button>
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
