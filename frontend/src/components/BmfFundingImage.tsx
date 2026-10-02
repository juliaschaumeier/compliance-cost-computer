"use client";

import Image from "next/image";
import { useState } from "react";

export default function BmfFundingImage() {
  const [hidden, setHidden] = useState(false);

  if (hidden) {
    return null;
  }

  return (
    <Image
      src="/csm_BMF-Logo_Gefoerdert-durch_8f2c79c04e.png"
      alt="Gefördert durch das Bundesministerium der Finanzen"
      width={750}
      height={630}
      className="mt-4 max-h-28 max-w-full object-contain"
      onError={() => setHidden(true)}
    />
  );
}
