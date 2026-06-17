import userEvent from "@testing-library/user-event";
import { render, screen, within } from "@testing-library/react";

import HeaderHelpPopover from "@/components/HeaderHelpPopover";

jest.mock("@/lib/useMounted", () => ({
  useMounted: () => true,
}));

describe("HeaderHelpPopover", () => {
  it("shows the approved overview, workflow, and tools help text", async () => {
    const user = userEvent.setup();

    render(<HeaderHelpPopover />);

    await user.click(screen.getByRole("button", { name: "Hilfe und Demo öffnen" }));

    const popover = screen.getByRole("heading", { name: "Hilfe & Demo" })
      .parentElement?.parentElement;
    expect(popover).not.toBeNull();

    expect(
      screen.getByText(
        /Die Werte werden KI-gestützt erzeugt und sind Schätzungen/
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Textbausteine für Vorblatt und Begründung/)
    ).toBeInTheDocument();
    expect(screen.queryByText(/EA bearbeiten/)).not.toBeInTheDocument();
    expect(
      screen.getByText(/sessionweiten Funktionen in der oberen Leiste/)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Ablauf" }));

    expect(
      screen.getByText(/In sieben Schritten ermittelt die App/)
    ).toBeInTheDocument();
    expect(screen.getByText("Vorgaben identifizieren")).toBeInTheDocument();
    expect(
      screen.getByText(/Am Ende zeigt die App eine kompakte Übersicht/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Über „EA bearbeiten“ können Sie anschließend/)
    ).toBeInTheDocument();
    expect(
      screen.queryByText(/Nach „Gesamtkosten berechnen“/)
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/mit „Schrittname“ zurücksetzen tun/)
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Werkzeuge" }));

    const toolsTab = screen.getByText("Session-Menü:").closest("div");
    expect(toolsTab).not.toBeNull();
    expect(
      within(toolsTab as HTMLElement).getByText(
        /über die Auswahlliste direkt zu einer anderen Session wechseln/
      )
    ).toBeInTheDocument();
    expect(
      within(toolsTab as HTMLElement).getByText(
        /sessionweite Aktionen ausführen/
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText(/nimmt den zuletzt abgeschlossenen Schritt zurück/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Für Deep Research ist ein Gemini API Key erforderlich/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/globale Lohnsätze, Fallzahlen und Schrittkosten/)
    ).toBeInTheDocument();
  });
});
