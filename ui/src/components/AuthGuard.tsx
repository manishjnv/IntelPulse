"use client";

import React, { Suspense } from "react";

/**
 * AuthGuard — bypassed for demo deployment.
 * Wraps children in Suspense boundary for useSearchParams compatibility.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  return <Suspense>{children}</Suspense>;
}
