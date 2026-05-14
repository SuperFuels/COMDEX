// frontend/components/sci/SciFileCabinet.tsx
import React, { useState } from "react";

export type SciFile = {
  id: string;
  name: string;
};

export type SciFolder = {
  id: string;
  name: string;
  files: SciFile[];
};

export interface SciFileCabinetProps {
  folders: SciFolder[];
  activeFileId: string | null;
  onCreateFolder: () => void;               // "New Container"
  onCreateFile: (folderId: string) => void; // "New Capsule" in a folder
  onSelectFile: (fileId: string) => void;
  onRenameFile: (fileId: string, name: string) => void;
}

const SciFileCabinet: React.FC<SciFileCabinetProps> = ({
  folders,
  activeFileId,
  onCreateFolder,
  onCreateFile,
  onSelectFile,
  onRenameFile,
}) => {
  const [editingFileId, setEditingFileId] = useState<string | null>(null);
  const [draftName, setDraftName] = useState("");

  // Choose a default folder to drop a new capsule into
  const getDefaultFolderId = (): string | null => {
    if (!folders.length) return null;

    if (activeFileId) {
      const owningFolder = folders.find((folder) =>
        folder.files.some((f) => f.id === activeFileId),
      );
      if (owningFolder) return owningFolder.id;
    }

    return folders[0].id;
  };

  const handleNewContainerClick = () => {
    onCreateFolder();
  };

  const handleNewCapsuleClick = () => {
    const folderId = getDefaultFolderId();
    if (folderId) {
      onCreateFile(folderId);
    }
  };

  return (
    <div className="flex h-full flex-col border-r border-border bg-background/95">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 text-xs font-medium text-foreground/80">
        <span>Workspace</span>
        <div className="flex gap-1">
          <button
            className="rounded border border-border px-2 py-0.5 text-[11px] hover:bg-muted/60"
            onClick={handleNewContainerClick}
          >
            + Container
          </button>
          <button
            className="rounded border border-border px-2 py-0.5 text-[11px] hover:bg-muted/60"
            onClick={handleNewCapsuleClick}
          >
            + Capsule
          </button>
        </div>
      </div>

      {/* Folder / file tree */}
      <div className="flex-1 overflow-auto px-2 pb-2 text-xs">
        {folders.map((folder) => (
          <div key={folder.id} className="mb-2">
            <div className="mb-1 flex items-center justify-between text-[11px] font-semibold text-foreground/70">
              <span>📁 {folder.name}</span>
              <button
                className="rounded px-1 text-[10px] text-foreground/60 hover:bg-muted/60"
                onClick={() => onCreateFile(folder.id)}
              >
                + capsule
              </button>
            </div>
            <ul className="space-y-0.5 pl-4">
              {folder.files.map((f) => {
                const isActive = f.id === activeFileId;
                const isEditing = f.id === editingFileId;
                return (
                  <li key={f.id}>
                    <button
                      className={`flex w-full items-center justify-between rounded px-1.5 py-0.5 text-left ${
                        isActive
                          ? "bg-primary text-primary-foreground"
                          : "text-foreground/80 hover:bg-muted/60"
                      }`}
                      onClick={() => {
                        if (!isEditing) onSelectFile(f.id);
                      }}
                      onDoubleClick={() => {
                        setEditingFileId(f.id);
                        setDraftName(f.name);
                      }}
                    >
                      {isEditing ? (
                        <input
                          autoFocus
                          className="w-full bg-transparent text-[11px] outline-none"
                          value={draftName}
                          onChange={(e) => setDraftName(e.target.value)}
                          onBlur={() => {
                            onRenameFile(
                              f.id,
                              draftName.trim() || "Untitled.ptn",
                            );
                            setEditingFileId(null);
                          }}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") {
                              e.currentTarget.blur();
                            } else if (e.key === "Escape") {
                              setEditingFileId(null);
                            }
                          }}
                        />
                      ) : (
                        <span className="truncate">{f.name}</span>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        ))}

        {folders.length === 0 && (
          <p className="mt-6 text-[11px] text-slate-500">
            No containers yet. Click <strong>+ Container</strong> to create your
            first container, then add Photon capsules inside it.
          </p>
        )}
      </div>
    </div>
  );
};

export default SciFileCabinet;