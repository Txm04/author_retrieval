import React, { useState } from "react";

type Props = {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
};

export default function Collapsible({ title, defaultOpen = true, children }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="bg-white rounded-xl shadow-soft">
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-6 py-4"
      >
        <h2 className="font-semibold">{title}</h2>
        <span className="text-slate-500">{open ? "▾" : "▸"}</span>
      </button>
      {open && <div className="px-6 pb-6">{children}</div>}
    </div>
  );
}
