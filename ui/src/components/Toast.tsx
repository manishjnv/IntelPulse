"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { X, CheckCircle, AlertTriangle, Info, XCircle } from "lucide-react";

export type ToastVariant = "success" | "error" | "warning" | "info";

interface ToastAction {
  label: string;
  onClick: () => void;
}

interface Toast {
  id: number;
  message: string;
  variant: ToastVariant;
  action?: ToastAction;
}

interface ToastContextValue {
  toast: (message: string, variant?: ToastVariant, action?: ToastAction) => void;
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} });

export function useToast() {
  return useContext(ToastContext);
}

const MAX_TOASTS = 5;

const VARIANT_STYLES: Record<ToastVariant, { bg: string; icon: React.ElementType; duration: number }> = {
  success: { bg: "bg-emerald-900/90 border-emerald-500/40 text-emerald-100", icon: CheckCircle, duration: 4000 },
  error: { bg: "bg-red-900/90 border-red-500/40 text-red-100", icon: XCircle, duration: 7000 },
  warning: { bg: "bg-amber-900/90 border-amber-500/40 text-amber-100", icon: AlertTriangle, duration: 5000 },
  info: { bg: "bg-blue-900/90 border-blue-500/40 text-blue-100", icon: Info, duration: 4000 },
};

let nextId = 0;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((message: string, variant: ToastVariant = "info", action?: ToastAction) => {
    const id = ++nextId;
    const duration = VARIANT_STYLES[variant].duration;
    setToasts((prev) => {
      const next = [...prev, { id, message, variant, action }];
      return next.length > MAX_TOASTS ? next.slice(-MAX_TOASTS) : next;
    });
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, duration);
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  return (
    <ToastContext.Provider value={{ toast: addToast }}>
      {children}
      {/* Toast container - fixed bottom-right */}
      <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 max-w-sm" role="region" aria-label="Notifications" aria-live="polite">
        {toasts.map((t) => {
          const cfg = VARIANT_STYLES[t.variant];
          const Icon = cfg.icon;
          return (
            <div
              key={t.id}
              role="alert"
              className={`flex items-start gap-2 px-3 py-2.5 rounded-lg border shadow-lg backdrop-blur-sm text-sm animate-in slide-in-from-right-5 fade-in duration-200 ${cfg.bg}`}
            >
              <Icon className="h-4 w-4 mt-0.5 shrink-0" />
              <span className="flex-1">{t.message}</span>
              {t.action && (
                <button
                  onClick={() => { t.action!.onClick(); dismiss(t.id); }}
                  className="shrink-0 text-xs font-medium underline underline-offset-2 opacity-80 hover:opacity-100"
                >
                  {t.action.label}
                </button>
              )}
              <button
                onClick={() => dismiss(t.id)}
                className="shrink-0 opacity-60 hover:opacity-100"
                aria-label="Dismiss notification"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
