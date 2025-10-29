import MemorySidebar from "../components/MemorySidebar";

export default function IDE() {
  const userId = "default"; // later can be dynamic
  return (
    <div className="flex h-screen">
      <div className="flex-1">{/* editor + canvas */}</div>
      <MemorySidebar userId={userId} />
    </div>
  );
}