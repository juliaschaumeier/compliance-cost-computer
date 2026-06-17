"use client";

import { useCallback, useState } from "react";

import { logClientError } from "@/lib/errorFeedback";

type UseEaReviewSaveOptions = {
  logLabel: string;
  logContext?: Record<string, unknown>;
};

function extractTechnicalHint(error: unknown): string | null {
  const maybe = error as {
    message?: unknown;
    details?: unknown;
  };
  if (typeof maybe?.message === "string" && maybe.message.trim()) {
    return maybe.message.trim();
  }
  if (typeof maybe?.details === "string" && maybe.details.trim()) {
    return maybe.details.trim();
  }
  if (maybe?.details && typeof maybe.details === "object") {
    const details = maybe.details as Record<string, unknown>;
    if (typeof details.error === "string" && details.error.trim()) {
      return details.error.trim();
    }
    if (typeof details.detail === "string" && details.detail.trim()) {
      return details.detail.trim();
    }
  }
  return null;
}

function formatSaveErrorMessage(friendlyMessage: string, error: unknown): string {
  const base = friendlyMessage.endsWith(".")
    ? friendlyMessage
    : `${friendlyMessage}.`;
  const hint = extractTechnicalHint(error);
  if (!hint) {
    return base;
  }
  return `${base} Technischer Hinweis: ${hint}`;
}

export function useEaReviewSave({ logLabel, logContext }: UseEaReviewSaveOptions) {
  const [reviewMode, setReviewMode] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [status, setStatus] = useState<string | null>(null);

  const runSave = useCallback(
    async (
      saveFn: () => Promise<void>,
      options: { successMessage: string; errorMessage: string }
    ) => {
      setIsSaving(true);
      setStatus(null);
      try {
        await saveFn();
        setStatus(options.successMessage);
      } catch (error) {
        logClientError(logLabel, error, logContext);
        setStatus(formatSaveErrorMessage(options.errorMessage, error));
        throw error;
      } finally {
        setIsSaving(false);
      }
    },
    [logContext, logLabel]
  );

  return {
    reviewMode,
    setReviewMode,
    isSaving,
    status,
    setStatus,
    runSave,
  };
}
