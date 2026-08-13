"""
설치 없이 venv에서 도는 async 부하 드라이버 (closed-loop).

여러 동시성 레벨(--levels)을 순서대로 밟으며 각 레벨에서 N개의 워커가
"요청 → 응답 받으면 즉시 다음 요청"을 duration초 동안 반복한다.
각 레벨마다 throughput(RPS), 성공/실패, p50/p95/p99/max 지연을 집계한다.

결과는 loadtest/results/<label>.json 에 저장 → before/after 비교(compare.py)에 사용.

실행:
    source venv/bin/activate
    python -m loadtest.loadgen --label sync_baseline --duration 20 --levels 5,10,15,20,30,50,100
"""
import argparse
import asyncio
import json
import os
import time

import httpx

HERE = os.path.dirname(__file__)
SEED_PATH = os.path.join(HERE, "seed_data.json")
RESULTS_DIR = os.path.join(HERE, "results")


def _percentile(sorted_vals: list[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    k = (len(sorted_vals) - 1) * pct
    lo = int(k)
    hi = min(lo + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


async def _worker(client, url, headers, app_ids, deadline, latencies, errors, idx_counter):
    while time.perf_counter() < deadline:
        app_id = app_ids[idx_counter[0] % len(app_ids)]
        idx_counter[0] += 1
        target = url.format(application_id=app_id)
        t0 = time.perf_counter()
        try:
            resp = await client.post(target, headers=headers)
            dt = time.perf_counter() - t0
            if resp.status_code < 400:
                latencies.append(dt)
            else:
                errors[f"http_{resp.status_code}"] = errors.get(f"http_{resp.status_code}", 0) + 1
        except Exception as exc:  # 연결/타임아웃 등
            errors[type(exc).__name__] = errors.get(type(exc).__name__, 0) + 1


async def run_level(seed: dict, path_template: str, concurrency: int, duration: float,
                    req_timeout: float) -> dict:
    base_url = seed["base_url"].rstrip("/")
    url = base_url + path_template
    headers = {"Authorization": f"Bearer {seed['access_token']}"}
    app_ids = seed["application_ids"]

    latencies: list[float] = []
    errors: dict[str, int] = {}
    idx_counter = [0]

    limits = httpx.Limits(max_connections=concurrency + 50, max_keepalive_connections=concurrency + 50)
    timeout = httpx.Timeout(req_timeout)
    async with httpx.AsyncClient(limits=limits, timeout=timeout) as client:
        start = time.perf_counter()
        deadline = start + duration
        tasks = [
            asyncio.create_task(
                _worker(client, url, headers, app_ids, deadline, latencies, errors, idx_counter)
            )
            for _ in range(concurrency)
        ]
        await asyncio.gather(*tasks)
        wall = time.perf_counter() - start

    ok = len(latencies)
    fail = sum(errors.values())
    total = ok + fail
    s = sorted(latencies)
    result = {
        "concurrency": concurrency,
        "duration_s": round(wall, 2),
        "total_requests": total,
        "ok": ok,
        "fail": fail,
        "rps": round(ok / wall, 2) if wall > 0 else 0.0,
        "p50_ms": round(_percentile(s, 0.50) * 1000, 1),
        "p95_ms": round(_percentile(s, 0.95) * 1000, 1),
        "p99_ms": round(_percentile(s, 0.99) * 1000, 1),
        "max_ms": round((s[-1] * 1000) if s else 0.0, 1),
        "errors": errors,
    }
    return result


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", required=True, help="결과 파일 이름 (예: sync_baseline)")
    parser.add_argument("--path", default="/speech-practices/{application_id}/questions",
                        help="부하 대상 경로 템플릿")
    parser.add_argument("--duration", type=float, default=20.0, help="레벨당 지속 시간(초)")
    parser.add_argument("--levels", default="5,10,15,20,30,50,100",
                        help="쉼표로 구분한 동시성 레벨")
    parser.add_argument("--req-timeout", type=float, default=60.0, help="개별 요청 타임아웃(초)")
    parser.add_argument("--warmup", type=float, default=3.0, help="레벨 간 휴식(초)")
    args = parser.parse_args()

    with open(SEED_PATH) as f:
        seed = json.load(f)

    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"\n== load target: {seed['base_url']}{args.path} ==")
    print(f"{'conc':>5} {'rps':>8} {'p50ms':>9} {'p95ms':>9} {'p99ms':>9} {'ok':>7} {'fail':>6}  errors")
    print("-" * 78)

    results = []
    for c in levels:
        res = await run_level(seed, args.path, c, args.duration, args.req_timeout)
        results.append(res)
        err_str = ",".join(f"{k}={v}" for k, v in res["errors"].items()) or "-"
        print(f"{res['concurrency']:>5} {res['rps']:>8.2f} {res['p50_ms']:>9.1f} "
              f"{res['p95_ms']:>9.1f} {res['p99_ms']:>9.1f} {res['ok']:>7} {res['fail']:>6}  {err_str}")
        await asyncio.sleep(args.warmup)

    out = {
        "label": args.label,
        "path": args.path,
        "duration_s": args.duration,
        "levels": results,
    }
    out_path = os.path.join(RESULTS_DIR, f"{args.label}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nsaved → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
