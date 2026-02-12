import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { TileNode } from "@/components/TileNode";

jest.mock("@xyflow/react", () => {
  const React = require("react");
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

describe("TileNode", () => {
  it("does not bubble the expand click to parent handlers", async () => {
    const user = userEvent.setup();
    const onParentClick = jest.fn();
    const longText = "A".repeat(200);

    render(
      <div onClick={onParentClick}>
        <TileNode
          {...({
            id: "regulation_1",
            data: {
              title: "Regelung",
              text: longText,
              deletable: false,
              onBodyRef: jest.fn(),
              onNodeRef: jest.fn(),
              onDelete: jest.fn(),
              onToggleExpand: jest.fn(),
              isExpanded: false,
              textHasOverflow: true,
              isFocused: false,
              isNeighbor: false,
            },
          } as any)}
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
        {...({
          id: "regulation_2",
          data: {
            title: "Regelung",
            text: "Kurztext",
            deletable: false,
            onBodyRef,
            onNodeRef,
            onDelete: jest.fn(),
            onToggleExpand: jest.fn(),
            isExpanded: false,
            textHasOverflow: false,
            isFocused: false,
            isNeighbor: false,
          },
        } as any)}
      />
    );

    onNodeRef.mockClear();
    onBodyRef.mockClear();

    rerender(
      <TileNode
        {...({
          id: "regulation_2",
          data: {
            title: "Regelung",
            text: "Kurztext",
            deletable: false,
            onBodyRef,
            onNodeRef,
            onDelete: jest.fn(),
            onToggleExpand: jest.fn(),
            isExpanded: false,
            textHasOverflow: false,
            isFocused: false,
            isNeighbor: false,
          },
        } as any)}
      />
    );

    const nodeNullCall = onNodeRef.mock.calls.find(([, el]) => el === null);
    const bodyNullCall = onBodyRef.mock.calls.find(([, el]) => el === null);
    expect(nodeNullCall).toBeUndefined();
    expect(bodyNullCall).toBeUndefined();
  });
});
