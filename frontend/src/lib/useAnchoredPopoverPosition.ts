import { RefObject, useCallback, useEffect, useState } from "react";

type HorizontalAlign = "left" | "right";

type PopoverPosition = {
  top: number;
  left: number;
};

type UseAnchoredPopoverPositionOptions = {
  open: boolean;
  triggerRef: RefObject<HTMLElement | null>;
  width: number;
  offset?: number;
  padding?: number;
  align?: HorizontalAlign;
  fallbackPosition?: PopoverPosition;
};

export function useAnchoredPopoverPosition({
  open,
  triggerRef,
  width,
  offset = 8,
  padding = 12,
  align = "right",
  fallbackPosition,
}: UseAnchoredPopoverPositionOptions): {
  position: PopoverPosition;
  updatePosition: () => void;
} {
  const fallbackTop = fallbackPosition?.top;
  const fallbackLeft = fallbackPosition?.left;
  const [position, setPosition] = useState<PopoverPosition>(
    fallbackPosition ?? { top: 0, left: padding }
  );

  const setPositionIfChanged = useCallback((next: PopoverPosition) => {
    setPosition((current) =>
      current.top === next.top && current.left === next.left ? current : next
    );
  }, []);

  const updatePosition = useCallback(() => {
    const rect = triggerRef.current?.getBoundingClientRect();
    const fallback =
      fallbackTop !== undefined && fallbackLeft !== undefined
        ? { top: fallbackTop, left: fallbackLeft }
        : null;
    if (!rect || (rect.width === 0 && rect.height === 0 && fallback)) {
      setPositionIfChanged(fallback ?? { top: offset, left: padding });
      return;
    }

    const preferredLeft = align === "right" ? rect.right - width : rect.left;
    const maxLeft = Math.max(padding, window.innerWidth - width - padding);
    const left = Math.min(Math.max(padding, preferredLeft), maxLeft);
    setPositionIfChanged({
      top: rect.bottom + offset,
      left,
    });
  }, [
    align,
    fallbackLeft,
    fallbackTop,
    offset,
    padding,
    setPositionIfChanged,
    triggerRef,
    width,
  ]);

  useEffect(() => {
    if (!open) {
      return;
    }
    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [open, updatePosition]);

  return { position, updatePosition };
}
