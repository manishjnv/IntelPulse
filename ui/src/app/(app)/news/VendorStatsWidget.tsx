"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/Skeleton";
import { Factory } from "lucide-react";
import * as api from "@/lib/api";

export default function VendorStatsWidget() {
  const [data, setData] = useState<Array<{ vendor: string; count: number; critical: number; high: number; kev_count: number }> | null>(null);
  useEffect(() => { api.getVendorStats().then(setData).catch(() => {}); }, []);
  if (data === null) return (
    <Card className="card-3d mb-3">
      <CardHeader className="pb-2 pt-3 px-4">
        <Skeleton className="h-3 w-40" />
      </CardHeader>
      <CardContent className="px-4 pb-3">
        <div className="space-y-1.5">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="flex items-center gap-2">
              <Skeleton className="h-3 w-[140px]" />
              <Skeleton className="flex-1 h-3 rounded-full" />
              <Skeleton className="h-3 w-6" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
  if (data.length === 0) return null;
  const max = data[0]?.count || 1;
  return (
    <Card className="card-3d mb-3">
      <CardHeader className="pb-2 pt-3 px-4">
        <CardTitle className="text-xs font-semibold flex items-center gap-1.5"><Factory className="h-3.5 w-3.5 text-orange-400" />Top Vendors by Vulnerabilities</CardTitle>
      </CardHeader>
      <CardContent className="px-4 pb-3">
        <div className="space-y-1.5">
          {data.slice(0, 10).map((v) => (
            <div key={v.vendor} className="flex items-center gap-2 text-[11px]">
              <span className="w-[140px] truncate text-muted-foreground font-medium" title={v.vendor}>{v.vendor}</span>
              <div className="flex-1 h-3 bg-muted/20 rounded-full overflow-hidden relative">
                <div className="h-full rounded-full bg-gradient-to-r from-orange-500/60 to-red-500/60" style={{ width: `${(v.count / max) * 100}%` }} />
              </div>
              <span className="w-6 text-right font-mono text-muted-foreground">{v.count}</span>
              {v.kev_count > 0 && <span title={`${v.kev_count} KEV`} className="text-[8px] px-1 rounded bg-red-500/20 text-red-300">{v.kev_count} KEV</span>}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
