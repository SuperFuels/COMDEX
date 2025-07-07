import React, { useEffect, useState } from 'react';

interface DnaLog {
  proposal_id: string;
  file: string;
  reason: string;
  timestamp: string;
  backup: string;
  status: string;
}

const DnaLogViewer: React.FC = () => {
  const [logs, setLogs] = useState<DnaLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchLogs = async () => {
      try {
        const res = await fetch('/aion/dna-logs');
        const data = await res.json();
        setLogs(data.logs || []);
      } catch (err) {
        console.error('Failed to fetch DNA logs:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  return (
    <div className="mt-6 p-4 rounded-xl shadow-lg bg-white max-h-[400px] overflow-y-auto border border-gray-200">
      <h2 className="text-xl font-bold mb-4 text-blue-600">🧬 DNA Mutation Log</h2>
      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : logs.length === 0 ? (
        <p className="text-gray-500">No mutations logged yet.</p>
      ) : (
        <ul className="space-y-4">
          {logs.map((log) => (
            <li key={log.proposal_id} className="p-3 border rounded-lg bg-gray-50">
              <div className="text-sm text-gray-700">
                <span className="font-semibold">Proposal:</span> {log.proposal_id}
              </div>
              <div className="text-sm text-gray-700">
                <span className="font-semibold">File:</span> {log.file}
              </div>
              <div className="text-sm text-gray-700">
                <span className="font-semibold">Reason:</span> {log.reason}
              </div>
              <div className="text-sm text-gray-700">
                <span className="font-semibold">Timestamp:</span> {new Date(log.timestamp).toLocaleString()}
              </div>
              <div className="text-sm text-gray-700">
                <span className="font-semibold">Backup:</span> {log.backup}
              </div>
              <div className={`text-sm font-bold ${log.status === 'applied' ? 'text-green-600' : 'text-yellow-600'}`}>
                Status: {log.status}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default DnaLogViewer;