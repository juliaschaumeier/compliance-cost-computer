import "@testing-library/jest-dom";
import type { ReactNode } from "react";
import { render, screen } from "@testing-library/react";

import AppShell from "@/components/AppShell";
import TabPanels from "@/components/TabPanels";
import { useApp } from "@/contexts/AppContext";

jest.mock("next/navigation", () => ({ usePathname: () => "/" }));
jest.mock("@/contexts/AppContext", () => ({
  AppProvider: ({ children }: { children: ReactNode }) => children,
  useApp: jest.fn(),
}));
jest.mock("@/contexts/AuthContext", () => ({ AuthProvider: ({ children }: { children: ReactNode }) => children }));
jest.mock("@/components/AuthGate", () => ({ __esModule: true, default: ({ children }: { children: ReactNode }) => children }));
jest.mock("@/components/Header", () => function MockHeader() { return <header>CCC header</header>; });
jest.mock("@/components/TabBar", () => function MockTabBar() { return <nav>Workflow tabs</nav>; });
jest.mock("@/components/UploadPanel", () => function MockUploadPanel() { return <section aria-label="File preparation">Upload</section>; });
jest.mock("@/components/RegulationsPanel", () => function MockRegulationsPanel() { return <section aria-label="Regulations">Regulations</section>; });

it("pins preparation only on Step 1 without rendering duplicate upload panels", () => {
  const mockUseApp = useApp as jest.Mock;
  mockUseApp.mockReturnValue({ state: { currentTab: 0 } });
  const content = () => <AppShell><TabPanels /><div>Canvas</div></AppShell>;
  const { rerender } = render(content());
  const upload = screen.getByRole("region", { name: "File preparation" });
  const pinned = screen.getByRole("navigation").closest(".sticky");
  expect(pinned).toContainElement(upload);
  expect(pinned).toHaveClass("max-h-dvh");
  expect(upload.parentElement).toHaveClass("min-h-0", "overflow-y-auto");
  expect(screen.getAllByRole("region", { name: "File preparation" })).toHaveLength(1);
  expect(screen.getByRole("main")).not.toContainElement(upload);

  mockUseApp.mockReturnValue({ state: { currentTab: 1 } });
  rerender(content());
  expect(screen.queryByRole("region", { name: "File preparation" })).not.toBeInTheDocument();
  expect(screen.getByRole("main")).toContainElement(screen.getByRole("region", { name: "Regulations" }));
  expect(screen.getByRole("navigation").closest(".sticky")).not.toHaveClass("max-h-dvh");

  mockUseApp.mockReturnValue({ state: { currentTab: 0 } });
  rerender(content());
  expect(screen.getAllByRole("region", { name: "File preparation" })).toHaveLength(1);
});
