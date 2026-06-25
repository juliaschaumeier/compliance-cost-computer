"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { useAnchoredPopoverPosition } from "@/lib/useAnchoredPopoverPosition";
import { useMounted } from "@/lib/useMounted";

type HelpTab = "overview" | "flow" | "tools";

const tabs: Array<{ id: HelpTab; label: string }> = [
  { id: "overview", label: "Überblick" },
  { id: "flow", label: "Ablauf" },
  { id: "tools", label: "Werkzeuge" },
];

function TabContent({ activeTab }: { activeTab: HelpTab }) {
  if (activeTab === "flow") {
    return (
      <div className="space-y-3 text-sm leading-6 text-slate-600">
        <p>
          In sieben Schritten ermittelt die App, wie sich der jährliche
          Erfüllungsaufwand durch die Gesetzesänderung verändert.
        </p>
        <ol className="grid grid-cols-1 gap-1">
          {[
            "Gesetz auswählen",
            "Vorgaben identifizieren",
            "Prozesse bündeln",
            "Fallgruppen entwickeln",
            "Prozessschritte bestimmen",
            "Aufwand quantifizieren",
            "Gesamtkosten berechnen",
          ].map((label, index) => (
            <li key={label} className="flex gap-2">
              <span className="font-mono text-xs font-semibold text-slate-400">
                {index + 1}
              </span>
              <span>{label}</span>
            </li>
          ))}
        </ol>
        <p>
          Am Ende zeigt die App eine kompakte Übersicht der Gesamtkosten sowie
          der Aufwände je Normadressat. Für Bürgerinnen und Bürger werden
          Zeitaufwand und Sachkosten ausgewiesen.
        </p>
        <p>
          Über „EA bearbeiten“ können Sie anschließend die berechneten Werte
          prüfen und anpassen: globale Lohnsätze, Fallzahlen und Schrittkosten
          wie Zeitaufwand und Sachkosten. Dort sehen Sie auch Begründungen und
          Konfidenzangaben. Gespeicherte Änderungen berechnen die Gesamtkosten
          automatisch neu.
        </p>
        <p>
          Deep Research kann im Session-Menü für Fallzahlen aktiviert werden.
          Wenn es aktiv ist, werden die Fallzahlen beim Schritt „Aufwand
          quantifizieren“ vertieft recherchiert. Nach Abschluss kann der
          Deep-Research-Bericht im Session-Menü heruntergeladen werden.
        </p>
        <p>
          Wenn Sie den zuletzt abgeschlossenen Schritt zurücknehmen möchten,
          können Sie das im Session-Menü mit „Schrittname“ zurücksetzen tun.
        </p>
      </div>
    );
  }

  if (activeTab === "tools") {
    return (
      <div className="space-y-3 text-sm leading-6 text-slate-600">
        <p>
          <strong className="font-semibold text-slate-900">Session-Menü:</strong>{" "}
          Im Session-Menü können Sie eine neue Session starten, über die
          Auswahlliste direkt zu einer anderen Session wechseln und
          sessionweite Aktionen ausführen.
        </p>
        <div className="ml-1 space-y-2 border-l border-slate-200 pl-3 text-[13px] leading-5 text-slate-600">
          <p>
            <strong className="font-semibold text-slate-900">
              Deep Research:
            </strong>{" "}
            recherchiert Fallzahlen vertieft und wird beim Schritt „Aufwand
            quantifizieren“ berücksichtigt. Der erzeugte Bericht steht nach Abschluss
            als Download bereit.
          </p>
          <p>
            <strong className="font-semibold text-slate-900">Zurücksetzen:</strong>{" "}
            nimmt den zuletzt abgeschlossenen Schritt zurück. Zurückgesetzte
            Schritte müssen erneut berechnet werden.
          </p>
          <p>
            <strong className="font-semibold text-slate-900">Exporte:</strong>{" "}
            laden Textbausteine für Vorblatt und Begründung herunter.
            Deep-Research-Berichte stehen separat bereit, wenn Deep Research für
            die Session durchgeführt wurde.
          </p>
        </div>
        <p>
          <strong className="font-semibold text-slate-900">Modellwahl:</strong>{" "}
          LLM zeigt das aktuell ausgewählte Modell. Über den Dialog können Sie
          das Modell für zukünftige Prompts ändern und die benötigten
          API-Schlüssel hinterlegen. Für Deep Research ist ein Gemini API Key
          erforderlich.
        </p>
        <p>
          <strong className="font-semibold text-slate-900">
            Normadressaten-Ansicht:
          </strong>{" "}
          Die Ansicht wechselt zwischen Bürgerinnen und Bürgern, Wirtschaft und
          Verwaltung. Sie ändert nur, welche Werte und Kacheln angezeigt werden;
          die Berechnungsschritte laufen für alle Normadressaten.
        </p>
        <p>
          <strong className="font-semibold text-slate-900">EA bearbeiten:</strong>{" "}
          Der Button öffnet nach „Gesamtkosten berechnen“ die berechneten Werte
          zum Erfüllungsaufwand. Dort können Sie globale Lohnsätze, Fallzahlen
          und Schrittkosten wie Zeitaufwand und Sachaufwand prüfen und
          bearbeiten. Soweit vorhanden, zeigt der Dialog auch die vom Modell
          mitgelieferte Einschätzung zu Sicherheit und Begründung.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3 text-sm leading-6 text-slate-600">
      <p>
        Der Compliance-Cost Computer unterstützt dabei, den jährlichen
        Erfüllungsaufwand einer Gesetzesänderung abzuschätzen. Die App führt
        durch einen siebenstufigen Arbeitsablauf: vom Gesetzestext über
        Vorgaben, Prozesse, Fallgruppen und Prozessschritte bis zur Berechnung
        von Aufwand und Gesamtkosten.
      </p>
      <p className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 font-semibold text-slate-700">
        Die Werte werden KI-gestützt erzeugt und sind Schätzungen. Bitte
        fachlich prüfen.
      </p>
      <p>
        Die App trennt zwischen sessionweiten Funktionen in der oberen Leiste
        und dem aktuellen Arbeitsschritt darunter. Dort wählen Sie auch die
        Normadressaten-Ansicht. Sie bestimmt, welche Kacheln und Werte angezeigt
        werden; die Berechnungsschritte laufen trotzdem für alle Normadressaten
        zusammen.
      </p>
      <p className="font-semibold text-slate-900">
        Nach Abschluss können die Ergebnisse als Textbausteine für Vorblatt und
        Begründung exportiert werden.
      </p>
    </div>
  );
}

export default function HeaderHelpPopover() {
  const [open, setOpen] = useState(false);
  const [activeTab, setActiveTab] = useState<HelpTab>("overview");
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const popoverRef = useRef<HTMLDivElement | null>(null);
  const isMounted = useMounted();
  const { position: menuPos } = useAnchoredPopoverPosition({
    open,
    triggerRef,
    width: 420,
    align: "right",
    offset: 12,
    padding: 12,
  });

  useEffect(() => {
    if (!open) {
      return;
    }
    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target as Node;
      if (
        popoverRef.current?.contains(target) ||
        triggerRef.current?.contains(target)
      ) {
        return;
      }
      setOpen(false);
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const popover = (
    <div
      ref={popoverRef}
      data-testid="header-help-popover"
      className="fixed z-[70] flex w-[420px] flex-col rounded-2xl border border-slate-200 bg-white p-4 text-slate-800 shadow-2xl"
      style={{
        top: menuPos.top,
        left: menuPos.left,
        maxHeight: `calc(100vh - ${menuPos.top + 12}px)`,
      }}
    >
      <div className="flex shrink-0 items-start justify-between gap-4">
        <div>
          <h2 className="text-lg font-semibold text-slate-950">Hilfe &amp; Demo</h2>
          <p className="mt-1 text-xs text-slate-500">
            Kurze Orientierung zur Bedienung.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(false)}
          className="flex h-7 w-7 items-center justify-center rounded-full text-sm font-semibold text-slate-400 transition hover:bg-slate-100 hover:text-slate-700"
          aria-label="Hilfe schließen"
        >
          ×
        </button>
      </div>
      <div className="mt-4 flex shrink-0 gap-2">
        {tabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              className={`rounded-xl border px-3 py-1.5 text-xs font-semibold transition ${
                isActive
                  ? "border-slate-700 bg-slate-800 text-white"
                  : "border-slate-200 bg-slate-50 text-slate-600 hover:bg-white"
              }`}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      <div
        data-testid="header-help-content"
        className="mt-4 min-h-0 flex-1 overflow-y-auto pr-1"
      >
        <TabContent activeTab={activeTab} />
      </div>
      <div className="mt-4 shrink-0 border-t border-slate-100 pt-4">
        <button
          type="button"
          className="w-full rounded-xl bg-slate-800 px-3 py-2 text-sm font-semibold text-white"
        >
          Demo-Session laden
        </button>
      </div>
    </div>
  );

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-8 w-8 items-center justify-center rounded-xl border border-white/30 bg-white/10 text-base font-bold text-white shadow-sm transition hover:bg-white/20"
        aria-label="Hilfe und Demo öffnen"
        title="Hilfe und Demo"
        aria-expanded={open}
      >
        ?
      </button>
      {open && isMounted ? createPortal(popover, document.body) : null}
    </>
  );
}
