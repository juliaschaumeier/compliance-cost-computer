import { render, screen, waitFor } from "@testing-library/react";

import GraphCanvas from "@/components/GraphCanvas";
import { useApp } from "@/contexts/AppContext";
import { apiClient } from "@/lib/api";

jest.mock("@/contexts/AppContext", () => ({
  useApp: jest.fn(),
}));

jest.mock("@/lib/api", () => ({
  apiClient: {
    fetchTiles: jest.fn(),
    upsertTile: jest.fn(),
  },
}));

jest.mock("@xyflow/react", () => {
  const React = jest.requireActual<typeof import("react")>("react");
  const updateNodeInternals = jest.fn();

  return {
    __esModule: true,
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
      <div>{children}</div>
    ),
    ReactFlow: ({
      children,
      onInit,
      onViewportChange,
    }: {
      children: React.ReactNode;
      onInit?: (instance: { getViewport: () => { x: number; y: number; zoom: number } }) => void;
      onViewportChange?: (viewport: { x: number; y: number; zoom: number }) => void;
    }) => {
      React.useEffect(() => {
        onInit?.({
          getViewport: () => ({ x: 0, y: 0, zoom: 1 }),
          fitView: () => undefined,
        });
        onViewportChange?.({ x: 120, y: -40, zoom: 1.5 });
      }, [onInit, onViewportChange]);
      return <div>{children}</div>;
    },
    useUpdateNodeInternals: () => updateNodeInternals,
    Background: () => null,
    Controls: () => null,
    Handle: ({ children }: { children?: React.ReactNode }) => <div>{children}</div>,
    Position: { Left: "left", Right: "right" },
  };
});

const mockUseApp = useApp as jest.Mock;
const mockFetchTiles = apiClient.fetchTiles as jest.Mock;
const mockUpsertTile = apiClient.upsertTile as jest.Mock;

describe("GraphCanvas", () => {
  beforeEach(() => {
    mockUseApp.mockReturnValue({
      state: {
        summaryReady: true,
        appSessionId: "ABC123",
      },
    });
    mockFetchTiles.mockReset();
    mockUpsertTile.mockReset();
    mockFetchTiles.mockResolvedValue({
      tiles: [
        {
          id: "law_tile",
          title: "Law",
          text: "Current vs proposed law",
          meta_information: {},
          column: 0,
          row: 0,
          deletable: false,
          link_from_tile: [],
        },
        {
          id: "regulation_1",
          title: "Regulation",
          text: "A derived regulation",
          meta_information: {},
          column: 1,
          row: 0,
          deletable: false,
          link_from_tile: ["law_tile"],
        },
      ],
    });
    mockUpsertTile.mockResolvedValue(undefined);
  });

  it("keeps swimlane transform in sync with programmatic viewport changes", async () => {
    const { container } = render(<GraphCanvas />);

    await waitFor(() => expect(mockFetchTiles).toHaveBeenCalled());

    const laneLayer = Array.from(container.querySelectorAll("div")).find(
      (element) => (element as HTMLDivElement).style.transformOrigin === "0 0"
    ) as HTMLDivElement | undefined;

    expect(laneLayer).toBeDefined();
    await waitFor(() =>
      expect(laneLayer?.style.transform).toBe(
        "translate(120px, -40px) scale(1.5)"
      )
    );
  });

  it("shows swimlane tile counts for non-law lanes", async () => {
    render(<GraphCanvas />);

    await waitFor(() => expect(mockFetchTiles).toHaveBeenCalled());

    const matches = await screen.findAllByText(/1 Vorgaben/i);
    expect(matches.length).toBeGreaterThan(0);
  });
});
