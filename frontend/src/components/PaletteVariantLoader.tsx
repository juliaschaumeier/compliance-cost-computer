"use client";

import { useEffect } from "react";

const STORAGE_KEY = "ccc-palette-variant";
const VARIANTS = new Set(["palette8-current", "palette8-exact"]);

export default function PaletteVariantLoader() {
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requested = params.get("palette");
    let variant = requested ?? window.localStorage.getItem(STORAGE_KEY);

    if (requested === "reset") {
      window.localStorage.removeItem(STORAGE_KEY);
      variant = null;
    } else if (variant && VARIANTS.has(variant)) {
      window.localStorage.setItem(STORAGE_KEY, variant);
    } else {
      variant = null;
    }

    if (variant) {
      document.documentElement.dataset.paletteVariant = variant;
    } else {
      delete document.documentElement.dataset.paletteVariant;
    }
  }, []);

  return null;
}
