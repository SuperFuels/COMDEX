# File: backend/modules/codexcore_virtual/instruction_profiler.py

import time
from collections import defaultdict

class InstructionProfiler:
    def __init__(self):
        self.execution_counts = defaultdict(int)
        self.execution_times = defaultdict(list)
        self.active = False

    def start(self):
        self.active = True
        self.start_time = time.time()

    def stop(self):
        self.active = False
        self.total_time = time.time() - self.start_time

    def record(self, instruction: str, exec_time: float):
        if not self.active:
            return
        self.execution_counts[instruction] += 1
        self.execution_times[instruction].append(exec_time)

    def get_summary(self):
        summary = {}
        for instr, times in self.execution_times.items():
            total_time = sum(times)
            avg_time = total_time / len(times)
            summary[instr] = {
                "count": self.execution_counts[instr],
                "total_time": total_time,
                "average_time": avg_time,
            }
        return summary

    def print_report(self):
        print("\n🔍 Instruction Profiling Report")
        for instr, stats in self.get_summary().items():
            print(f"{instr}: executed {stats['count']} times, total {stats['total_time']:.6f}s, avg {stats['average_time']:.6f}s")