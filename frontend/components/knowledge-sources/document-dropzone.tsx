"use client";

import { useCallback, useRef, useState } from "react";
import { UploadCloud } from "lucide-react";

import { cn } from "@/lib/utils";

interface DocumentDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function DocumentDropzone({ onFilesSelected, disabled }: DocumentDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (event: React.DragEvent<HTMLDivElement>) => {
      event.preventDefault();
      setIsDragActive(false);
      if (disabled) return;
      const files = Array.from(event.dataTransfer.files).filter(
        (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
      );
      if (files.length > 0) onFilesSelected(files);
    },
    [disabled, onFilesSelected]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragActive(true);
      }}
      onDragLeave={() => setIsDragActive(false)}
      onDrop={handleDrop}
      onClick={() => !disabled && inputRef.current?.click()}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && !disabled) inputRef.current?.click();
      }}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
        isDragActive ? "border-primary bg-primary/5" : "border-border hover:border-primary/40 hover:bg-accent/30",
        disabled && "cursor-not-allowed opacity-50"
      )}
    >
      <div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary">
        <UploadCloud className="size-5" />
      </div>
      <p className="text-sm font-medium text-foreground">
        Drag and drop a PDF, or click to browse
      </p>
      <p className="text-xs text-muted-foreground">PDF files only</p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        disabled={disabled}
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          if (files.length > 0) onFilesSelected(files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
