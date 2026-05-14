#!/usr/bin/env python3
import sys, json
from backend.photon_algebra.rewriter import normalize

def main():
    data = json.load(sys.stdin)
    print(json.dumps(normalize(data), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()