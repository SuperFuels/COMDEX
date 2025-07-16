import { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
}

export function Card({ children, className = "" }: CardProps) {
  return (
    <div className={`rounded-lg border bg-white p-4 shadow-sm ${className}`}>
      {children}
    </div>
  );
}

export function CardContent({ children, className = "" }: CardProps) {
  return <div className={`mt-2 ${className}`}>{children}</div>;
}