import { render, screen } from "@testing-library/react";

import Header from "@/components/Header";

jest.mock("@/components/SessionMenu", () => ({
  __esModule: true,
  default: () => <div data-testid="session-menu" />,
}));

jest.mock("@/components/ModelSelector", () => ({
  __esModule: true,
  default: () => <div data-testid="model-selector" />,
}));

jest.mock("@/components/HeaderHelpPopover", () => ({
  __esModule: true,
  default: () => <button type="button">Hilfe und Demo</button>,
}));

describe("Header", () => {
  it("renders app context and global session tools", () => {
    render(<Header />);

    expect(
      screen.getByRole("heading", { name: "Compliance-Cost Computer" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Errechnet den jährlichen Erfüllungsaufwand einer Gesetzesänderung."
      )
    ).toBeInTheDocument();
    expect(screen.getByTestId("session-menu")).toBeInTheDocument();
    expect(screen.getByTestId("model-selector")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Hilfe und Demo" })
    ).toBeInTheDocument();
  });
});
