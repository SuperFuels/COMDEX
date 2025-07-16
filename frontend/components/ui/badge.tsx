import { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "outline";
  className?: string;
}

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  const base = "text-xs font-medium px-2.5 py-0.5 rounded";
  const variants = {
    default: "bg-gray-800 text-white",
    outline: "border border-gray-400 text-gray-800",
  };

  return <span className={`${base} ${variants[variant]} ${className}`}>{children}</span>;
}