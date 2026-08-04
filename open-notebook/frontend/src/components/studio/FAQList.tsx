'use client'

// FAQ 列表组件
// 使用 shadcn/ui Accordion 组件展示 FAQ 问答列表

import { HelpCircle } from 'lucide-react'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import type { FAQItem } from '@/lib/api/studio'
import { useTranslation } from '@/lib/hooks/use-translation'

interface FAQListProps {
  faqs: FAQItem[]
}

export function FAQList({ faqs }: FAQListProps) {
  const { t } = useTranslation()

  if (faqs.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground">
        <HelpCircle className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>{t('studio.noFAQs')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 mb-4">
        <HelpCircle className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-semibold">{t('studio.faqResult')}</h3>
        <span className="text-sm text-muted-foreground">({faqs.length})</span>
      </div>
      <Accordion type="single" collapsible className="w-full">
        {faqs.map((faq, index) => (
          <AccordionItem key={index} value={`item-${index}`}>
            <AccordionTrigger className="text-left hover:no-underline">
              <span className="flex items-start gap-2">
                <span className="text-primary font-bold shrink-0">Q{index + 1}.</span>
                <span>{faq.question}</span>
              </span>
            </AccordionTrigger>
            <AccordionContent>
              <div className="flex items-start gap-2 pl-7">
                <span className="text-muted-foreground font-bold shrink-0">A:</span>
                <span className="text-muted-foreground">{faq.answer}</span>
              </div>
            </AccordionContent>
          </AccordionItem>
        ))}
      </Accordion>
    </div>
  )
}
