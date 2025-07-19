import { ReactNode } from "react";

interface BadgeProps {
  children: ReactNode;
  variant?: "default" | "outline" | "secondary" | "destructive";
  className?: string;
}

export function Badge({ children, variant = "default", className = "" }: BadgeProps) {
  const base = "text-xs font-medium px-2.5 py-0.5 rounded";
  const variants = {
    default: "bg-gray-800 text-white",
    outline: "border border-gray-400 text-gray-800",
    secondary: "bg-blue-700 text-white",
    destructive: "bg-red-600 text-white",
  };

  return <span className={`${base} ${variants[variant]} ${className}`}>{children}</span>;
}