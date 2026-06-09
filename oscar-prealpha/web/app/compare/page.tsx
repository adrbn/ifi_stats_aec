"use client";
import { useEffect, useState } from "react";

const V2_URL = "https://ifi-stats-aec.streamlit.app/?embed=true";
const V3_URL = "/cours/synthese";

export default function ComparePage() {
  const [v, setV] = useState<"v2" | "v3">("v2");
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === "1") setV("v2");
      else if (e.key === "2") setV("v3");
    };
    addEventListener("keydown", h);
    return () => removeEventListener("keydown", h);
  }, []);
  return (
    <div className="flex h-screen flex-col">
      <div className="flex h-14 items-center justify-between border-b border-neutral-200 bg-white px-4">
        <span className="text-sm font-bold tracking-[0.14em]">OSCAR · comparateur</span>
        <div className="relative inline-flex rounded-lg bg-neutral-100 p-1">
          <span
            className="absolute top-1 h-[calc(100%-8px)] w-[calc(50%-4px)] rounded-md bg-white shadow transition-transform duration-200"
            style={{ transform: v === "v3" ? "translateX(100%)" : "translateX(0)" }}
          />
          <button onClick={() => setV("v2")} className={`relative z-10 px-4 py-1.5 text-sm font-semibold ${v === "v2" ? "text-neutral-900" : "text-neutral-500"}`}>v2 · Streamlit</button>
          <button onClick={() => setV("v3")} className={`relative z-10 px-4 py-1.5 text-sm font-semibold ${v === "v3" ? "text-neutral-900" : "text-neutral-500"}`}>v3 · Nouvelle UI</button>
        </div>
        <span className="text-xs text-neutral-500">{v === "v2" ? "en ligne · production" : "natif · Vercel"}</span>
      </div>
      <div className="relative flex-1">
        <iframe src={V2_URL} title="v2" className={`absolute inset-0 h-full w-full border-0 ${v === "v2" ? "" : "invisible"}`} />
        <iframe src={V3_URL} title="v3" className={`absolute inset-0 h-full w-full border-0 ${v === "v3" ? "" : "invisible"}`} />
      </div>
    </div>
  );
}
