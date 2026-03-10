import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { NodeProps } from "@xyflow/react";

import { TileNode, type TileNodeData } from "@/components/TileNode";

jest.mock("@xyflow/react", () => {
  const React = jest.requireActual<typeof import("react")>("react");
  return {
    __esModule: true,
    ReactFlow: ({ children }: { children: React.ReactNode }) => (
      <div>{children}</div>
    ),
    Background: () => null,
    Controls: () => null,
    Handle: ({ children }: { children?: React.ReactNode }) => (
      <div>{children}</div>
    ),
    Position: { Left: "left", Right: "right" },
    ReactFlowProvider: ({ children }: { children: React.ReactNode }) => (
      <div>{children}</div>
    ),
  };
});

function buildTileNodeProps(
  id: string,
  overrides: Partial<TileNodeData> = {}
): NodeProps<TileNodeData> {
  return {
    id,
    data: {
      title: "Regelung",
      text: "Kurztext",
      deletable: false,
      onBodyRef: jest.fn(),
      onNodeRef: jest.fn(),
      onDelete: jest.fn(),
      onToggleExpand: jest.fn(),
      isExpanded: false,
      textHasOverflow: false,
      isFocused: false,
      isNeighbor: false,
      ...overrides,
    },
  } as unknown as NodeProps<TileNodeData>;
}

describe("TileNode", () => {
  it("renders a status marker when change status is provided", () => {
    render(
      <TileNode
        {...buildTileNodeProps("regulation_3", {
          changeStatus: "eingefuehrt",
        })}
      />
    );

    expect(screen.getByText("Neu")).toBeInTheDocument();
  });

  it("does not bubble the expand click to parent handlers", async () => {
    const user = userEvent.setup();
    const onParentClick = jest.fn();
    const longText = "A".repeat(200);

    render(
      <div onClick={onParentClick}>
        <TileNode
          {...buildTileNodeProps("regulation_1", {
            text: longText,
            textHasOverflow: true,
          })}
        />
      </div>
    );

    const expandButton = screen.getByTitle("Text ausklappen");
    await user.click(expandButton);

    expect(onParentClick).not.toHaveBeenCalled();
  });

  it("keeps ref callbacks stable on rerender", () => {
    const onNodeRef = jest.fn();
    const onBodyRef = jest.fn();
    const { rerender } = render(
      <TileNode
        {...buildTileNodeProps("regulation_2", {
          onBodyRef,
          onNodeRef,
        })}
      />
    );

    onNodeRef.mockClear();
    onBodyRef.mockClear();

    rerender(
      <TileNode
        {...buildTileNodeProps("regulation_2", {
          onBodyRef,
          onNodeRef,
        })}
      />
    );

    const nodeNullCall = onNodeRef.mock.calls.find(([, el]) => el === null);
    const bodyNullCall = onBodyRef.mock.calls.find(([, el]) => el === null);
    expect(nodeNullCall).toBeUndefined();
    expect(bodyNullCall).toBeUndefined();
  });

  it("renders header metrics around the delete action", () => {
    render(
      <TileNode
        {...buildTileNodeProps("step_4", {
          deletable: true,
          headerMetricLeft: "Δ 120 €",
          headerMetricRight: "Δ Fälle/Jahr +5",
        })}
      />
    );

    expect(screen.getByText("Δ 120 €")).toBeInTheDocument();
    expect(screen.getByText("Δ Fälle/Jahr +5")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "×" })).toBeInTheDocument();
  });
});
