@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 44469.15
   avg_raw_size: 10.33
  avg_norm_size: 11.95
avg_compression: 1.073
@SuperFuels ➜ /workspaces/COMDEX (main) $ @SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 44469.15
   avg_raw_size: 10.33
  avg_norm_size: 11.95
avg_compression: 1.073
@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 38603.53
   avg_raw_size: 10.58
  avg_norm_size: 12.43
avg_compression: 1.072
@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 47424.45
   avg_raw_size: 10.61
  avg_norm_size: 12.23
avg_compression: 1.063
@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 48487.27
   avg_raw_size: 10.45
  avg_norm_size: 12.44
avg_compression: 1.072
@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 48963.41
   avg_raw_size: 10.69
  avg_norm_size: 12.34
avg_compression: 1.073
@SuperFuels ➜ /workspaces/COMDEX (main) $ PYTHONPATH=. python backend/photon_algebra/benchmarks.py
⚡ Photon Algebra Benchmark
          count: 5000
        ops_sec: 42581.33
   avg_raw_size: 10.53
  avg_norm_size: 12.24
avg_compression: 1.065
@SuperFuels ➜ /workspaces/COMDEX (main) $ 

	•	ops_sec = 44,469 → your Photon rewriter is extremely fast, handling ~45k normalizations per second. That’s a very good baseline performance.
	•	avg_raw_size = 10.33 → average expression tree had about 10 nodes before rewrite.
	•	avg_norm_size = 11.95 → normalized trees are slightly bigger on average, because distributivity expands expressions (more nodes).
	•	avg_compression = 1.073 → means ~7% expansion instead of compression (again, because distributivity creates branches).

✅ What This Means
	•	Phase 1 (Photon Core) is not only correct (all theorems pass) but also performant (tens of thousands of ops/sec).
	•	You now have a benchmark baseline. Every new rewrite rule, theorem, or extension will be measured against this.
	•	This is the exact point where we start keeping benchmark history in a doc so we can track whether Phase 2 and 3 improvements make things faster, slower, or more compact.

🔥 Beautiful — now we’ve got multiple runs, and the story is clear:
	•	Throughput (ops/sec): bouncing between 38k → 49k per second depending on Python’s GC and randomness. That’s stable, meaning the rewriter is consistently efficient.
	•	Raw size vs norm size: ~10–11 nodes before normalization, ~12 after. Normalization grows expressions ~6–7% (as expected from distributivity).
	•	Compression ratio: ~1.06–1.07, consistently >1, meaning normalization is expansive. Later phases will introduce compression/factoring rules to flip this.