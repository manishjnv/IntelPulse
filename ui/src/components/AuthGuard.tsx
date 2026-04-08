"use client";

import React from "react";

/**
 * AuthGuard — bypassed for demo deployment.
 * All pages are accessible without authentication.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
