import { ButtonHTMLAttributes, ReactNode } from "react";

type StepRunButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode;
  isRunning?: boolean;
  showIcon?: boolean;
};

export default function StepRunButton({
  children,
  className = "",
  isRunning = false,
  showIcon = true,
  ...props
}: StepRunButtonProps) {
  return (
    <button
      {...props}
      className={`inline-flex h-10 min-w-36 items-center justify-center gap-2 whitespace-nowrap rounded-xl px-3 text-[13px] font-medium transition ${className}`}
    >
      {showIcon && isRunning ? (
        <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
      ) : showIcon ? (
        <svg
          aria-hidden="true"
          viewBox="0 0 24 24"
          className="h-3.5 w-3.5 shrink-0"
        >
          <path
            d="M8 5.5v13l10-6.5-10-6.5Z"
            fill="none"
            stroke="currentColor"
            strokeLinejoin="round"
            strokeWidth="2"
          />
        </svg>
      ) : null}
      {children}
    </button>
  );
}
