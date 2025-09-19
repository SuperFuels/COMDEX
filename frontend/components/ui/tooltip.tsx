'use client';

import React, { createContext, useContext, useState } from 'react';
import { cn } from '@/lib/utils';

type TooltipCtx = {
  open: boolean;
  setOpen: (v: boolean) => void;
};

const Ctx = createContext<TooltipCtx | null>(null);

/** Lightweight tooltip shim (no Radix dependency). API-compatible enough for
 *  `<Tooltip><TooltipTrigger asChild>…</TooltipTrigger><TooltipContent>…</TooltipContent></Tooltip>`
 */
export function Tooltip({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <span
      className="relative inline-flex"
      onMouseLeave={() => setOpen(false)}
      onBlur={() => setOpen(false)}
    >
      <Ctx.Provider value={{ open, setOpen }}>{children}</Ctx.Provider>
    </span>
  );
}

export function TooltipTrigger({
  asChild = false,
  children,
  ...rest
}: {
  asChild?: boolean;
  children: React.ReactNode;
} & React.HTMLAttributes<HTMLElement>) {
  const ctx = useContext(Ctx);
  const handlers = {
    onMouseEnter: () => ctx?.setOpen(true),
    onFocus: () => ctx?.setOpen(true),
    onMouseLeave: () => ctx?.setOpen(false),
    onBlur: () => ctx?.setOpen(false),
  };

  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, {
      ...handlers,
      ...(children.props || {}),
    });
  }

  return (
    <span {...rest} {...handlers}>
      {children}
    </span>
  );
}

export function TooltipContent({
  className,
  children,
  side = 'top',
}: {
  className?: string;
  children: React.ReactNode;
  /** 'top' | 'bottom' | 'left' | 'right' (basic positioning) */
  side?: 'top' | 'bottom' | 'left' | 'right';
}) {
  const ctx = useContext(Ctx);
  if (!ctx?.open) return null;

  const base = 'absolute z-50 rounded border border-zinc-700 bg-zinc-900 px-2 py-1 text-xs shadow-xl';
  const pos =
    side === 'top'
      ? 'left-1/2 -translate-x-1/2 -translate-y-2 bottom-full'
      : side === 'bottom'
      ? 'left-1/2 -translate-x-1/2 top-full mt-2'
      : side === 'left'
      ? 'right-full mr-2 top-1/2 -translate-y-1/2'
      : 'left-full ml-2 top-1/2 -translate-y-1/2';

  return <div className={cn(base, pos, className)}>{children}</div>;
}

/** No-op provider to match prior Radix-based imports */
export function TooltipProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}