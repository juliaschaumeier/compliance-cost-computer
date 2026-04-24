import { formatActionErrorMessage, logClientError } from "@/lib/errorFeedback";
import { AUTOMATED_NORM_ADDRESSEES, NormAddressee } from "@/types";

const NORM_ADDRESSEE_LABELS: Record<NormAddressee, string> = {
  administration: "Verwaltung",
  business: "Wirtschaft",
  citizens: "Buerger",
};

export type PerAddresseeRunOutcome<TResult> = {
  allSucceeded: boolean;
  successes: Array<{ normAddressee: NormAddressee; result: TResult }>;
  failures: Array<{ normAddressee: NormAddressee; error: unknown }>;
  statusMessage: string | null;
};

export type PerAddresseeRunOptions<TResult> = {
  /** Log scope used in logClientError, prefix only; NA is appended as [admin]. */
  logScope: string;
  /** Optional extra context passed to logClientError for each failure. */
  logContext?: Record<string, unknown>;
  /** Short label for the operation, e.g. "Prozesse buendeln". */
  operationLabel: string;
  /** Function that triggers the backend call for one norm addressee. */
  run: (normAddressee: NormAddressee) => Promise<TResult>;
};

/**
 * Fuehrt eine Backend-Operation pro Normadressat in paralleler
 * Promise.allSettled-Semantik aus. Partial failures werden nicht mehr als
 * Gesamt-Crash dargestellt: erfolgreiche Adressaten zaehlen als Erfolg,
 * fehlgeschlagene werden pro NA geloggt und in die statusMessage
 * eingearbeitet.
 */
export async function runPerAddressee<TResult>(
  options: PerAddresseeRunOptions<TResult>
): Promise<PerAddresseeRunOutcome<TResult>> {
  const { logScope, logContext, operationLabel, run } = options;
  const addressees = AUTOMATED_NORM_ADDRESSEES;
  const settled = await Promise.allSettled(addressees.map(run));

  const successes: PerAddresseeRunOutcome<TResult>["successes"] = [];
  const failures: PerAddresseeRunOutcome<TResult>["failures"] = [];

  settled.forEach((outcome, idx) => {
    const normAddressee = addressees[idx];
    if (outcome.status === "fulfilled") {
      successes.push({ normAddressee, result: outcome.value });
    } else {
      failures.push({ normAddressee, error: outcome.reason });
      logClientError(`${logScope}[${normAddressee}]`, outcome.reason, logContext);
    }
  });

  let statusMessage: string | null = null;
  if (failures.length === addressees.length) {
    const details = failures
      .map(
        ({ normAddressee, error }) =>
          `${NORM_ADDRESSEE_LABELS[normAddressee]}: ${formatActionErrorMessage(
            "Fehler",
            error
          )}`
      )
      .join(" · ");
    statusMessage = `${operationLabel} fehlgeschlagen fuer alle Normadressaten. ${details}`;
  } else if (failures.length > 0) {
    const okLabels = successes
      .map((s) => NORM_ADDRESSEE_LABELS[s.normAddressee])
      .join(", ");
    const failDetails = failures
      .map(
        ({ normAddressee, error }) =>
          `${NORM_ADDRESSEE_LABELS[normAddressee]}: ${formatActionErrorMessage(
            "Fehler",
            error
          )}`
      )
      .join(" · ");
    statusMessage = `${operationLabel} teilweise erfolgreich (OK: ${okLabels}). Fehler: ${failDetails}`;
  }

  return {
    allSucceeded: failures.length === 0,
    successes,
    failures,
    statusMessage,
  };
}
