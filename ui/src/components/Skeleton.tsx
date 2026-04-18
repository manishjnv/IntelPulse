"use client";

import React from "react";
import { cn } from "@/lib/utils";

// Base primitive — compose `className` for size/shape. Keep it a single `<div>`
// so it inherits parent layout (flex / grid) without extra wrappers.
export function Skeleton({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("animate-pulse rounded-md bg-muted/50", className)}
      {...props}
    />
  );
}

// Convenience composites used by the dashboard's per-card loading states.
// Sized to roughly match the real widget so the layout doesn't jump on data
// arrival.

export function SkeletonStatCard() {
  return (
    <div className="rounded-xl border bg-gradient-to-br from-primary/5 to-transparent border-primary/20 p-4 card-3d space-y-2">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-16" />
      <Skeleton className="h-3 w-24" />
    </div>
  );
}

export function SkeletonRankedList({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="space-y-1">
          <div className="flex items-center justify-between">
            <Skeleton className="h-3 w-[60%]" />
            <Skeleton className="h-3 w-10" />
          </div>
          <Skeleton className="h-1 w-full" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonDonut({ height = 180 }: { height?: number }) {
  return (
    <div className="flex flex-col items-center" style={{ height }}>
      <Skeleton className="h-[144px] w-[144px] rounded-full" />
      <div className="mt-3 w-full space-y-1.5">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between">
            <Skeleton className="h-3 w-[60%]" />
            <Skeleton className="h-3 w-10" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonTableRow({ cols = 7 }: { cols?: number }) {
  return (
    <tr className="border-b border-border/30">
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-2.5 px-2">
          <Skeleton className="h-4 w-full" />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonCardGrid({
  count = 4,
  height = 64,
}: {
  count?: number;
  height?: number;
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <Skeleton key={i} className={`rounded-lg`} style={{ height }} />
      ))}
    </div>
  );
}
