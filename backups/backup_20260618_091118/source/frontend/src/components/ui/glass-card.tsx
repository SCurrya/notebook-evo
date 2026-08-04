import * as React from "react"
import { cn } from "@/lib/utils"

/**
 * 玻璃卡片组件 - 玻璃拟态风格的卡片
 * 适用于浮层、工具栏、信息面板
 */
function GlassCard({
  className,
  strong = false,
  ...props
}: React.ComponentProps<"div"> & { strong?: boolean }) {
  return (
    <div
      className={cn(
        "rounded-xl p-6",
        strong ? "glass-strong" : "glass",
        className
      )}
      {...props}
    />
  )
}

/**
 * 渐变边框卡片
 */
function GradientBorderCard({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  return (
    <div
      className={cn(
        "relative rounded-xl p-[1px] gradient-primary",
        className
      )}
      {...props}
    >
      <div className="rounded-[calc(theme(borderRadius.xl)-1px)] bg-card h-full w-full">
        {children}
      </div>
    </div>
  )
}

export { GlassCard, GradientBorderCard }
