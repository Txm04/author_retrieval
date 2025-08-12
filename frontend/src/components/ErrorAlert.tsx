import React from "react";

type Props = { message: string };

export default function ErrorAlert({ message }: Props) {
  return (
    <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg p-3">
      <strong className="font-medium">Fehler:</strong> {message}
    </div>
  );
}