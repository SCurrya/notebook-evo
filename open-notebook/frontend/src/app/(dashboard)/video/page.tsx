'use client'

import { useState } from 'react'
import {
  AlertTriangle,
  CheckCircle2,
  Clapperboard,
  GraduationCap,
  Loader2,
  Megaphone,
  Newspaper,
  Smartphone,
  Sparkles,
  Video,
  XCircle,
} from 'lucide-react'

import { AppShell } from '@/components/layout/AppShell'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { PageHeader } from '@/components/ui/page-header'
import { Textarea } from '@/components/ui/textarea'
import {
  useCreateVideoTask,
  useDeleteVideoTask,
  useLaunchMpt,
  useVideoServiceHealth,
  useVideoTasks,
  useVideoTemplates,
} from '@/lib/hooks/use-video'
import type {
  VideoAspect,
  VideoConcatMode,
  VideoSource,
  VideoTemplate,
} from '@/lib/types/video'

const ASPECT_OPTIONS: { value: VideoAspect; label: string }[] = [
  { value: '16:9', label: '16:9 横屏（YouTube）' },
  { value: '9:16', label: '9:16 竖屏（抖音/Shorts）' },
  { value: '1:1', label: '1:1 方形（Instagram）' },
]

const SOURCE_OPTIONS: { value: VideoSource; label: string }[] = [
  { value: 'pexels', label: 'Pexels（免费视频素材）' },
  { value: 'pixabay', label: 'Pixabay（免费视频素材）' },
  { value: 'local', label: '仅本地素材' },
]

const CONCAT_OPTIONS: { value: VideoConcatMode; label: string }[] = [
  { value: 'sequential', label: '顺序拼接' },
  { value: 'random', label: '随机拼接' },
  { value: 'sequential_desc', label: '倒序拼接' },
]

// 模板视觉元数据：每个模板的渐变色、图标和标签
const TEMPLATE_META: Record<
  string,
  {
    gradient: string
    icon: typeof Megaphone
    tag: string
  }
> = {
  marketing: {
    gradient: 'from-rose-500 via-orange-500 to-amber-400',
    icon: Megaphone,
    tag: '快节奏',
  },
  tutorial: {
    gradient: 'from-sky-500 via-blue-500 to-indigo-500',
    icon: GraduationCap,
    tag: '循序渐进',
  },
  story: {
    gradient: 'from-violet-500 via-purple-500 to-fuchsia-500',
    icon: Sparkles,
    tag: '叙事型',
  },
  news: {
    gradient: 'from-slate-600 via-slate-700 to-zinc-700',
    icon: Newspaper,
    tag: '正式风格',
  },
  short: {
    gradient: 'from-emerald-500 via-teal-500 to-cyan-500',
    icon: Smartphone,
    tag: '15-30秒',
  },
}

const STATE_LABELS: Record<string, { label: string; color: string }> = {
  pending: { label: '等待中', color: 'text-muted-foreground' },
  processing: { label: '处理中', color: 'text-blue-500' },
  downloading_materials: { label: '下载素材中', color: 'text-blue-500' },
  generating_script: { label: '生成脚本中', color: 'text-blue-500' },
  generating_audio: { label: '生成音频中', color: 'text-blue-500' },
  generating_subtitle: { label: '生成字幕中', color: 'text-blue-500' },
  generating_video: { label: '生成视频中', color: 'text-blue-500' },
  completed: { label: '已完成', color: 'text-green-500' },
  failed: { label: '失败', color: 'text-red-500' },
  unknown: { label: '未知', color: 'text-muted-foreground' },
}

export default function VideoPage() {
  const [subject, setSubject] = useState('')
  const [script, setScript] = useState('')
  const [aspect, setAspect] = useState<VideoAspect>('16:9')
  const [source, setSource] = useState<VideoSource>('pexels')
  const [concatMode, setConcatMode] = useState<VideoConcatMode>('sequential')
  const [language, setLanguage] = useState('zh-CN')
  const [paragraphs, setParagraphs] = useState(3)
  const [voiceName, setVoiceName] = useState('zh-CN-XiaoxiaoNeural-Female')
  const [bgmType, setBgmType] = useState('random')
  const [maxClipDuration, setMaxClipDuration] = useState(5)
  const [subtitleFontSize, setSubtitleFontSize] = useState(60)
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)

  const healthQuery = useVideoServiceHealth()
  const templatesQuery = useVideoTemplates()
  const tasksQuery = useVideoTasks(1, 20)
  const createTask = useCreateVideoTask()
  const deleteTask = useDeleteVideoTask()
  const launchMpt = useLaunchMpt()

  const serviceAvailable = healthQuery.data?.available ?? false

  const handleLaunchMpt = async () => {
    const result = await launchMpt.mutateAsync()
    if (result.success) {
      // 5-15s 后服务就绪；轮询 health
      setTimeout(() => healthQuery.refetch(), 4000)
      setTimeout(() => healthQuery.refetch(), 10000)
    }
  }

  // 应用模板：将模板预设值填充到表单字段
  const applyTemplate = (template: VideoTemplate) => {
    setSelectedTemplate(template.key)
    setParagraphs(template.paragraph_number)
    setVoiceName(template.voice_name)
    setBgmType(template.bgm_type)
    setAspect(template.video_aspect)
    setConcatMode(template.video_concat_mode)
    setMaxClipDuration(template.max_clip_duration)
    setSubtitleFontSize(template.subtitle_font_size)
  }

  const handleSubmit = async () => {
    if (!subject.trim()) return
    await createTask.mutateAsync({
      video_subject: subject,
      video_script: script.trim() || undefined,
      language,
      video_aspect: aspect,
      paragraph_number: paragraphs,
      voice: {
        voice_name: voiceName,
        voice_rate: 1.0,
        voice_volume: 1.0,
      },
      subtitle: {
        enabled: true,
        font_name: 'STHeitiMedium.ttc',
        font_size: subtitleFontSize,
        text_color: '#FFFFFF',
        stroke_color: '#000000',
        stroke_width: 1.5,
        position: 'bottom',
        custom_position: 70.0,
      },
      video_source: source,
      max_clip_duration: maxClipDuration,
      video_concat_mode: concatMode,
      bgm_type: bgmType,
    })
    setSubject('')
    setScript('')
  }

  return (
    <AppShell>
      <div className="flex-1 overflow-y-auto animate-fade-in">
        <PageHeader
          title="视频生成"
          description="通过 AI 脚本、语音合成和素材拼接，根据主题自动生成短视频。"
          icon={Video}
        />

        <div className="page-container py-6 space-y-6">
          {/* Service health */}
          {!serviceAvailable && (
            <Alert className="research-panel bg-amber-50/75 text-amber-900 border-amber-200 dark:bg-amber-950/25 dark:text-amber-200 dark:border-amber-900">
              <AlertTriangle className="h-4 w-4" />
              <AlertTitle>MoneyPrinterTurbo 服务未启动</AlertTitle>
              <AlertDescription className="space-y-3">
                <p>需要先启动 MoneyPrinterTurbo 服务才能生成视频。可点击下方按钮一键启动，或手动执行：</p>
                <code className="block px-3 py-1.5 rounded bg-amber-100 dark:bg-amber-900/50 text-xs">
                  cd e:\notebook\MoneyPrinterTurbo; python main.py
                </code>
                <p className="text-xs">默认 URL: <span className="font-mono">http://localhost:8080</span></p>
                <Button
                  type="button"
                  size="sm"
                  variant="default"
                  onClick={handleLaunchMpt}
                  disabled={launchMpt.isPending}
                  className="bg-amber-600 hover:bg-amber-700 text-white"
                >
                  {launchMpt.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      启动中…
                    </>
                  ) : (
                    '一键启动服务'
                  )}
                </Button>
                {launchMpt.isSuccess && (
                  <p className="text-xs">
                    {launchMpt.data?.success ? '✅ ' : '❌ '}
                    {launchMpt.data?.message}
                  </p>
                )}
                {launchMpt.isError && (
                  <p className="text-xs text-red-600">
                    启动请求失败: {(launchMpt.error as Error)?.message ?? '未知错误'}
                  </p>
                )}
              </AlertDescription>
            </Alert>
          )}

          {/* Template selection */}
            <Card className="research-panel rounded-[24px]">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Clapperboard className="h-5 w-5 text-primary" />
                选择一个模板
              </CardTitle>
              <CardDescription>
                选择预设模板自动填充推荐参数，再按需微调。
              </CardDescription>
            </CardHeader>
            <CardContent>
              {templatesQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  正在加载模板...
                </div>
              ) : templatesQuery.data?.length ? (
                <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-5">
                  {templatesQuery.data.map((template) => {
                    const meta = TEMPLATE_META[template.key] ?? {
                      gradient: 'from-slate-500 to-slate-700',
                      icon: Video,
                      tag: '',
                    }
                    const Icon = meta.icon
                    const isSelected = selectedTemplate === template.key
                    return (
                      <button
                        key={template.key}
                        type="button"
                        onClick={() => applyTemplate(template)}
                        disabled={!serviceAvailable || createTask.isPending}
                      className={[
                          'group relative overflow-hidden rounded-[22px] border bg-background/80 text-left transition-all duration-200',
                          'hover:-translate-y-0.5 hover:shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                          'disabled:cursor-not-allowed disabled:opacity-50',
                          isSelected
                            ? 'border-primary ring-2 ring-primary shadow-md'
                            : 'border-border hover:border-primary/50',
                        ].join(' ')}
                      >
                        {/* 渐变色块头部 */}
                        <div
                          className={`relative flex h-20 items-center justify-center bg-gradient-to-br ${meta.gradient}`}
                        >
                          <Icon className="h-8 w-8 text-white drop-shadow-sm" />
                          {isSelected && (
                            <span className="absolute right-2 top-2 flex h-5 w-5 items-center justify-center rounded-full bg-white/90">
                              <CheckCircle2 className="h-4 w-4 text-primary" />
                            </span>
                          )}
                          {meta.tag && (
                            <span className="absolute bottom-2 right-2 rounded-full bg-black/25 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm">
                              {meta.tag}
                            </span>
                          )}
                        </div>
                        {/* 模板信息 */}
                        <div className="space-y-1 p-3">
                          <div className="flex items-center justify-between gap-1">
                            <span className="text-sm font-semibold leading-tight">
                              {template.name}
                            </span>
                            <span className="shrink-0 text-[10px] font-mono text-muted-foreground">
                              {template.video_aspect}
                            </span>
                          </div>
                          <p className="text-xs text-muted-foreground leading-snug line-clamp-2">
                            {template.description}
                          </p>
                          <div className="flex flex-wrap gap-1 pt-1">
                            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                              {template.paragraph_number} 段
                            </span>
                            <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                              {template.max_clip_duration}秒/片段
                            </span>
                          </div>
                        </div>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  暂无可用模板。
                </div>
              )}
            </CardContent>
          </Card>

          {/* Generation form */}
          <Card className="research-panel rounded-[24px]">
            <CardHeader>
              <CardTitle>新建视频任务</CardTitle>
              <CardDescription>
                输入主题，AI 将自动生成脚本、配音、字幕，并拼接素材生成视频。
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="subject">主题（必填）</Label>
                <Input
                  id="subject"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  placeholder="例如：远程办公的 5 个效率技巧"
                  disabled={!serviceAvailable || createTask.isPending}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="script">自定义脚本（可选）</Label>
                <Textarea
                  id="script"
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  placeholder="提供自己的脚本可跳过 AI 脚本生成..."
                  rows={4}
                  disabled={!serviceAvailable || createTask.isPending}
                />
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="space-y-2">
                  <Label>画面比例</Label>
                  <Select
                    value={aspect}
                    onValueChange={(v) => setAspect(v as VideoAspect)}
                    disabled={!serviceAvailable || createTask.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {ASPECT_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>素材来源</Label>
                  <Select
                    value={source}
                    onValueChange={(v) => setSource(v as VideoSource)}
                    disabled={!serviceAvailable || createTask.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {SOURCE_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>语言</Label>
                  <Select
                    value={language}
                    onValueChange={setLanguage}
                    disabled={!serviceAvailable || createTask.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="zh-CN">中文（简体）</SelectItem>
                      <SelectItem value="en-US">英语（美式）</SelectItem>
                      <SelectItem value="en-GB">英语（英式）</SelectItem>
                      <SelectItem value="ja-JP">日语</SelectItem>
                      <SelectItem value="ko-KR">韩语</SelectItem>
                      <SelectItem value="es-ES">西班牙语</SelectItem>
                      <SelectItem value="fr-FR">法语</SelectItem>
                      <SelectItem value="de-DE">德语</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="paragraphs">段落数</Label>
                  <Input
                    id="paragraphs"
                    type="number"
                    min={1}
                    max={20}
                    value={paragraphs}
                    onChange={(e) =>
                      setParagraphs(Number(e.target.value) || 3)
                    }
                    disabled={!serviceAvailable || createTask.isPending}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="voice">语音名称</Label>
                  <Input
                    id="voice"
                    value={voiceName}
                    onChange={(e) => setVoiceName(e.target.value)}
                    placeholder="zh-CN-XiaoxiaoNeural-Female"
                    disabled={!serviceAvailable || createTask.isPending}
                  />
                </div>

                <div className="space-y-2">
                  <Label>拼接方式</Label>
                  <Select
                    value={concatMode}
                    onValueChange={(v) =>
                      setConcatMode(v as VideoConcatMode)
                    }
                    disabled={!serviceAvailable || createTask.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONCAT_OPTIONS.map((opt) => (
                        <SelectItem key={opt.value} value={opt.value}>
                          {opt.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="bgm">背景音乐</Label>
                  <Select
                    value={bgmType}
                    onValueChange={setBgmType}
                    disabled={!serviceAvailable || createTask.isPending}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="random">随机</SelectItem>
                      <SelectItem value="none">无</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                <div className="space-y-2">
                  <Label htmlFor="maxClipDuration">单片段最大时长（秒）</Label>
                  <Input
                    id="maxClipDuration"
                    type="number"
                    min={1}
                    max={60}
                    value={maxClipDuration}
                    onChange={(e) =>
                      setMaxClipDuration(Number(e.target.value) || 5)
                    }
                    disabled={!serviceAvailable || createTask.isPending}
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="subtitleFontSize">字幕字号</Label>
                  <Input
                    id="subtitleFontSize"
                    type="number"
                    min={10}
                    max={200}
                    value={subtitleFontSize}
                    onChange={(e) =>
                      setSubtitleFontSize(Number(e.target.value) || 60)
                    }
                    disabled={!serviceAvailable || createTask.isPending}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <Button
                  onClick={handleSubmit}
                  disabled={
                    !serviceAvailable ||
                    createTask.isPending ||
                    !subject.trim()
                  }
                >
                  {createTask.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      正在提交...
                    </>
                  ) : (
                    <>
                      <Video className="h-4 w-4 mr-2" />
                      生成视频
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Task list */}
          <Card>
            <CardHeader>
              <CardTitle>视频任务</CardTitle>
              <CardDescription>
                查看视频生成任务的进度。
              </CardDescription>
            </CardHeader>
            <CardContent>
              {tasksQuery.isLoading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <Loader2 className="h-5 w-5 mr-2 animate-spin" />
                  正在加载任务...
                </div>
              ) : tasksQuery.data?.items?.length ? (
                <div className="space-y-3">
                  {tasksQuery.data.items.map((task) => {
                    const stateInfo =
                      STATE_LABELS[task.state] ?? STATE_LABELS.unknown
                    const isActive = !['completed', 'failed'].includes(
                      task.state
                    )
                    return (
                      <div
                        key={task.id}
                        className="flex items-center justify-between rounded-lg border p-4"
                      >
                        <div className="space-y-1 min-w-0 flex-1">
                          <div className="flex items-center gap-2">
                            {task.state === 'completed' ? (
                              <CheckCircle2 className="h-4 w-4 text-green-500 shrink-0" />
                            ) : task.state === 'failed' ? (
                              <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                            ) : (
                              <Loader2 className="h-4 w-4 text-blue-500 animate-spin shrink-0" />
                            )}
                            <span className="font-medium truncate">
                              {task.id}
                            </span>
                            <span className={`text-xs ${stateInfo.color}`}>
                              {stateInfo.label}
                              {isActive && task.progress > 0
                                ? ` (${task.progress}%)`
                                : ''}
                            </span>
                          </div>
                          {task.message && (
                            <p className="text-xs text-muted-foreground truncate">
                              {task.message}
                            </p>
                          )}
                          {task.error && (
                            <p className="text-xs text-red-500 truncate">
                              {task.error}
                            </p>
                          )}
                          {task.video_url && task.state === 'completed' && (
                            <a
                              href={task.video_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-xs text-blue-500 hover:underline"
                            >
                              下载视频 →
                            </a>
                          )}
                        </div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteTask.mutate(task.id)}
                          disabled={deleteTask.isPending}
                        >
                          删除
                        </Button>
                      </div>
                    )
                  })}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  暂无视频任务，请在上方创建。
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </AppShell>
  )
}
