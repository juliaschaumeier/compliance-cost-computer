import userEvent from "@testing-library/user-event";
import { render, screen, within } from "@testing-library/react";

import HeaderHelpPopover from "@/components/HeaderHelpPopover";

jest.mock("@/lib/useMounted", () => ({
  useMounted: () => true,
}));

describe("HeaderHelpPopover", () => {
  beforeEach(() => {
    Object.defineProperty(window, "innerHeight", {
      configurable: true,
      value: 520,
    });
  });

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
      screen.getByText(/Nach „Aufwand quantifizieren“ können Sie über „EA bearbeiten“/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/nach bereits berechneten Gesamtkosten werden sie automatisch neu berechnet/)
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
    expect(
      screen.getByText(/Der Button öffnet nach „Aufwand quantifizieren“/)
    ).toBeInTheDocument();
  });

  it("constrains the popover to the viewport and scrolls the help content", async () => {
    const user = userEvent.setup();

    render(<HeaderHelpPopover />);

    await user.click(screen.getByRole("button", { name: "Hilfe und Demo öffnen" }));

    const popover = screen.getByTestId("header-help-popover");
    expect(popover).toHaveClass("flex-col");
    expect(popover.getAttribute("style")).toContain(
      "max-height: calc(100vh - 24px)"
    );

    const content = screen.getByTestId("header-help-content");
    expect(content).toHaveClass("overflow-y-auto");
    const demoVideoLink = screen.getByRole("link", {
      name: "Demo-Video ansehen",
    });
    expect(demoVideoLink).toHaveAttribute("href", "/demo/index.html");
    expect(demoVideoLink).toHaveAttribute("target", "_blank");
  });
});
