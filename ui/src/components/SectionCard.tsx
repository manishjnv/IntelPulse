"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface SectionCardProps {
  title: string;
  icon?: React.ReactNode;
  iconAccent?: string;
  iconBg?: string;
  meta?: React.ReactNode;
  action?: React.ReactNode;
  accentBorder?: string;
  className?: string;
  contentClassName?: string;
  children: React.ReactNode;
}

// Normalized dashboard/list-page card. Owns the repeated
// `pb-2 pt-4 px-5` header + `px-5 pb-4` body padding so callers don't drift.
// Left-border accent, icon slot, right-rail action slot all optional.
export function SectionCard({
  title,
  icon,
  iconAccent,
  iconBg,
  meta,
  action,
  accentBorder,
  className,
  contentClassName,
  children,
}: SectionCardProps) {
  const hasActionOrMeta = action != null || meta != null;

  return (
    <Card className={cn(accentBorder, className)}>
      <CardHeader className="pb-2 pt-4 px-5">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {icon && (
              <span
                className={cn(
                  "flex items-center justify-center shrink-0",
                  iconBg ? "h-7 w-7 rounded-md" : "h-4 w-4",
                  iconAccent,
                  iconBg,
                )}
              >
                {icon}
              </span>
            )}
            <div className="min-w-0">
              <CardTitle className="text-sm font-semibold truncate">
                {title}
              </CardTitle>
              {meta && (
                <div className="text-[10px] text-muted-foreground mt-0.5">
                  {meta}
                </div>
              )}
            </div>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      </CardHeader>
      <CardContent className={cn("px-5 pb-4", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  );
}
