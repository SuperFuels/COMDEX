import React from "react";

interface ReplayBranchSelectorProps {
  availableBranches: string[];
  selectedBranch: string;
  onSelect: (branchId: string) => void;
  onRetry: () => void;
}

export const ReplayBranchSelector: React.FC<ReplayBranchSelectorProps> = ({
  availableBranches,
  selectedBranch,
  onSelect,
  onRetry,
}) => {
  return (
    <div className="absolute top-4 right-4 z-50 bg-black/70 text-white p-3 rounded-lg">
      <label className="block mb-1">⏪ Replay Branch</label>
      <select
        className="w-full text-black"
        value={selectedBranch}
        onChange={(e) => onSelect(e.target.value)}
      >
        {availableBranches.map((b) => (
          <option key={b} value={b}>
            {b}
          </option>
        ))}
      </select>

      <button
        className="mt-2 bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded"
        onClick={onRetry}
      >
        🔁 Retry from Branch
      </button>
    </div>
  );
};