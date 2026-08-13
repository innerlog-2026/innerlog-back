"""
before/after 결과 비교표 출력.

    python -m loadtest.compare sync_baseline async_optimized
"""
import argparse
import json
import os

RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def _load(label: str) -> dict:
    with open(os.path.join(RESULTS_DIR, f"{label}.json")) as f:
        return json.load(f)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("before")
    parser.add_argument("after")
    args = parser.parse_args()

    before = _load(args.before)
    after = _load(args.after)
    b_by_c = {lv["concurrency"]: lv for lv in before["levels"]}
    a_by_c = {lv["concurrency"]: lv for lv in after["levels"]}
    concs = sorted(set(b_by_c) | set(a_by_c))

    print(f"\n{'':>5} | {'RPS (before→after)':^26} | {'p95ms (before→after)':^28} | {'fail':^13}")
    print(f"{'conc':>5} | {args.before[:12]:>12} {args.after[:12]:>12} | "
          f"{args.before[:12]:>13} {args.after[:12]:>13} | {'b':>5} {'a':>5}")
    print("-" * 92)
    for c in concs:
        b = b_by_c.get(c)
        a = a_by_c.get(c)
        b_rps = f"{b['rps']:.1f}" if b else "-"
        a_rps = f"{a['rps']:.1f}" if a else "-"
        b_p95 = f"{b['p95_ms']:.0f}" if b else "-"
        a_p95 = f"{a['p95_ms']:.0f}" if a else "-"
        b_fail = b["fail"] if b else "-"
        a_fail = a["fail"] if a else "-"
        gain = ""
        if b and a and b["rps"] > 0:
            gain = f"  ({a['rps'] / b['rps']:.1f}x)"
        print(f"{c:>5} | {b_rps:>12} {a_rps:>12} | {b_p95:>13} {a_p95:>13} | "
              f"{b_fail:>5} {a_fail:>5}{gain}")


if __name__ == "__main__":
    main()
