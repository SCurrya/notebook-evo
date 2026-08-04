'use client'

import { useRouter, useParams, usePathname, useSearchParams } from 'next/navigation'
import { useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { ArrowLeft } from 'lucide-react'
import { useSourceChat } from '@/lib/hooks/useSourceChat'
import { ChatPanel } from '@/components/source/ChatPanel'
import { useNavigation } from '@/lib/hooks/use-navigation'
import { SourceDetailContent } from '@/components/source/SourceDetailContent'

interface PageClientProps {
  sourceId?: string
}

function decodeRouteId(value: string | string[] | undefined): string {
  const raw = Array.isArray(value) ? value[0] : value
  if (!raw || raw === '_placeholder') return ''
  return decodeURIComponent(raw)
}

function getSourceIdFromPath(pathname: string | null): string {
  const marker = '/sources/'
  if (!pathname?.startsWith(marker)) return ''
  const raw = pathname.slice(marker.length).split('/')[0]
  return decodeRouteId(raw)
}

export default function PageClient({ sourceId: sourceIdProp }: PageClientProps) {
  const router = useRouter()
  const params = useParams()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const sourceId =
    decodeRouteId(searchParams.get('sourceId') || undefined) ||
    getSourceIdFromPath(pathname) ||
    decodeRouteId(params?.id as string | string[] | undefined) ||
    decodeRouteId(sourceIdProp)
  const navigation = useNavigation()

  // Initialize source chat
  const chat = useSourceChat(sourceId)

  const handleBack = useCallback(() => {
    const returnPath = navigation.getReturnPath()
    router.push(returnPath)
    navigation.clearReturnTo()
  }, [navigation, router])

  return (
    <div className="flex flex-col h-screen">
      {/* Back button */}
      <div className="pt-6 pb-4 px-6">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleBack}
          className="mb-4"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          {navigation.getReturnLabel()}
        </Button>
      </div>

      {/* Main content: Source detail + Chat */}
      <div className="flex-1 grid gap-6 lg:grid-cols-[2fr_1fr] overflow-hidden px-6">
        {/* Left column - Source detail */}
        <div className="overflow-y-auto px-4 pb-6">
          <SourceDetailContent
            sourceId={sourceId}
            showChatButton={false}
            onClose={handleBack}
          />
        </div>

        {/* Right column - Chat */}
        <div className="overflow-y-auto px-4 pb-6">
          <ChatPanel
            messages={chat.messages}
            isStreaming={chat.isStreaming}
            contextIndicators={chat.contextIndicators}
            onSendMessage={(message, model) => chat.sendMessage(message, model)}
            modelOverride={chat.currentSession?.model_override}
            onModelChange={(model) => {
              if (chat.currentSessionId) {
                chat.updateSession(chat.currentSessionId, { model_override: model })
              }
            }}
            sessions={chat.sessions}
            currentSessionId={chat.currentSessionId}
            onCreateSession={(title) => chat.createSession({ title })}
            onSelectSession={chat.switchSession}
            onUpdateSession={(sessionId, title) => chat.updateSession(sessionId, { title })}
            onDeleteSession={chat.deleteSession}
            loadingSessions={chat.loadingSessions}
          />
        </div>
      </div>
    </div>
  )
}
