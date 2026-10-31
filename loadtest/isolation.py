"""
장애 격리 부하 드라이버 (closed-loop).

스피치 분석 요청(배경 부하)을 동시에 N건 걸어 둔 상태에서 다른 API(프로브)를
고정 동시성으로 호출해, 배경 부하가 프로브의 지연·실패율에 주는 영향을 측정함.

레벨(배경 동시성 N)마다:
  1) 배경 워커 N개가 POST /speech-practices/questions/{question_id}/submissions 를 반복함.
  2) ramp 초 뒤 프로브 워커 P개가 duration 초 동안 프로브 경로(기본 GET /applications)를 반복함.
  3) 프로브가 끝나면 배경 워커는 새 요청을 보내지 않고 진행 중인 요청만 마친 뒤 종료함.

결과는 loadtest/results/<label>.json 에 저장함.

실행:
    source venv/bin/activate
    python -m loadtest.isolation run --label isolation_async --levels 0,5,10,15,20,30
    python -m loadtest.isolation compare isolation_sync isolation_async
"""
import argparse
import asyncio
import io
import json
import os
import time
import wave

import httpx

from loadtest.loadgen import _percentile

HERE = os.path.dirname(__file__)
SEED_PATH = os.path.join(HERE, "seed_data.json")
RESULTS_DIR = os.path.join(HERE, "results")

SUBMISSION_PATH = "/speech-practices/questions/{question_id}/submissions"


def _silent_wav(seconds: float = 1.0, rate: int = 16000) -> bytes:
    """업로드용 무음 wav(16kHz, mono, 16bit) 바이트를 생성함."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * int(seconds * rate))
    return buf.getvalue()


class _Stats:
    def __init__(self):
        self.latencies: list[float] = []
        self.errors: dict[str, int] = {}

    def ok(self, dt: float) -> None:
        self.latencies.append(dt)

    def fail(self, key: str) -> None:
        self.errors[key] = self.errors.get(key, 0) + 1

    def summary(self, window: float) -> dict:
        ok = len(self.latencies)
        fail = sum(self.errors.values())
        total = ok + fail
        s = sorted(self.latencies)
        return {
            "total_requests": total,
            "ok": ok,
            "fail": fail,
            "fail_rate": round(fail / total, 4) if total else 0.0,
            "rps": round(ok / window, 2) if window > 0 else 0.0,
            "p50_ms": round(_percentile(s, 0.50) * 1000, 1),
            "p95_ms": round(_percentile(s, 0.95) * 1000, 1),
            "p99_ms": round(_percentile(s, 0.99) * 1000, 1),
            "max_ms": round((s[-1] * 1000) if s else 0.0, 1),
            "errors": self.errors,
        }


async def _timed(stats: _Stats, send) -> None:
    t0 = time.perf_counter()
    try:
        resp = await send()
        dt = time.perf_counter() - t0
        if resp.status_code < 400:
            stats.ok(dt)
        else:
            stats.fail(f"http_{resp.status_code}")
    except Exception as exc:
        stats.fail(type(exc).__name__)


async def _background_worker(client, base_url, headers, question_ids, counter, wav, stop_at, timeout, stats):
    while time.perf_counter() < stop_at:
        question_id = question_ids[counter[0] % len(question_ids)]
        counter[0] += 1
        url = base_url + SUBMISSION_PATH.format(question_id=question_id)
        await _timed(
            stats,
            lambda: client.post(
                url,
                headers=headers,
                files={"file": ("answer.wav", wav, "audio/wav")},
                data={"input_type": "UPLOAD"},
                timeout=timeout,
            ),
        )


async def _probe_worker(client, url, headers, stop_at, timeout, stats):
    while time.perf_counter() < stop_at:
        await _timed(stats, lambda: client.get(url, headers=headers, timeout=timeout))


async def run_level(seed: dict, args, background: int, wav: bytes) -> dict:
    base_url = seed["base_url"].rstrip("/")
    headers = {"Authorization": f"Bearer {seed['access_token']}"}
    probe_url = base_url + args.probe_path

    bg_stats = _Stats()
    probe_stats = _Stats()
    counter = [0]

    size = background + args.probe_concurrency + 10
    limits = httpx.Limits(max_connections=size, max_keepalive_connections=size)
    async with httpx.AsyncClient(limits=limits) as client:
        start = time.perf_counter()
        probe_start = start + args.ramp
        probe_stop = probe_start + args.duration

        bg_tasks = [
            asyncio.create_task(
                _background_worker(
                    client, base_url, headers, seed["question_ids"], counter, wav,
                    probe_stop, args.bg_timeout, bg_stats,
                )
            )
            for _ in range(background)
        ]

        await asyncio.sleep(max(0.0, probe_start - time.perf_counter()))
        probe_tasks = [
            asyncio.create_task(
                _probe_worker(client, probe_url, headers, probe_stop, args.probe_timeout, probe_stats)
            )
            for _ in range(args.probe_concurrency)
        ]
        await asyncio.gather(*probe_tasks)
        probe_window = time.perf_counter() - probe_start

        await asyncio.gather(*bg_tasks)
        level_wall = time.perf_counter() - start

    return {
        "background_concurrency": background,
        "level_wall_s": round(level_wall, 2),
        "probe": probe_stats.summary(probe_window),
        "background": bg_stats.summary(level_wall),
    }


async def run(args) -> None:
    with open(SEED_PATH) as f:
        seed = json.load(f)

    levels = [int(x) for x in args.levels.split(",") if x.strip()]
    wav = _silent_wav()
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print(f"\n== probe: GET {seed['base_url']}{args.probe_path} x{args.probe_concurrency} "
          f"/ background: POST {SUBMISSION_PATH} ==")
    print(f"{'bg':>4} | {'probe rps':>9} {'p50ms':>8} {'p95ms':>8} {'fail':>6} {'fail%':>6} | "
          f"{'bg ok':>6} {'bg fail':>7}  errors")
    print("-" * 96)

    results = []
    for n in levels:
        res = await run_level(seed, args, n, wav)
        results.append(res)
        p, b = res["probe"], res["background"]
        errs = {**{f"probe:{k}": v for k, v in p["errors"].items()},
                **{f"bg:{k}": v for k, v in b["errors"].items()}}
        err_str = ",".join(f"{k}={v}" for k, v in errs.items()) or "-"
        print(f"{n:>4} | {p['rps']:>9.2f} {p['p50_ms']:>8.1f} {p['p95_ms']:>8.1f} {p['fail']:>6} "
              f"{p['fail_rate'] * 100:>5.1f}% | {b['ok']:>6} {b['fail']:>7}  {err_str}")
        await asyncio.sleep(args.rest)

    out = {
        "label": args.label,
        "probe_path": args.probe_path,
        "probe_concurrency": args.probe_concurrency,
        "duration_s": args.duration,
        "ramp_s": args.ramp,
        "levels": results,
    }
    out_path = os.path.join(RESULTS_DIR, f"{args.label}.json")
    with open(out_path, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\nsaved → {out_path}")


def compare(args) -> None:
    def load(label):
        with open(os.path.join(RESULTS_DIR, f"{label}.json")) as f:
            return {lv["background_concurrency"]: lv for lv in json.load(f)["levels"]}

    before, after = load(args.before), load(args.after)
    print(f"\n{'':>4} | {'probe p95ms':^19} | {'probe fail%':^15} | {'probe rps':^13} | {'bg ok/fail':^17}")
    print(f"{'bg':>4} | {'before':>9} {'after':>9} | {'before':>7} {'after':>7} | "
          f"{'before':>6} {'after':>6} | {'before':>8} {'after':>8}")
    print("-" * 84)
    for n in sorted(set(before) | set(after)):
        b, a = before.get(n), after.get(n)

        def cell(lv, key, fmt):
            return format(lv["probe"][key], fmt) if lv else "-"

        def bg(lv):
            return f"{lv['background']['ok']}/{lv['background']['fail']}" if lv else "-"

        b_fail = f"{b['probe']['fail_rate'] * 100:.1f}" if b else "-"
        a_fail = f"{a['probe']['fail_rate'] * 100:.1f}" if a else "-"
        print(f"{n:>4} | {cell(b, 'p95_ms', '.0f'):>9} {cell(a, 'p95_ms', '.0f'):>9} | "
              f"{b_fail:>7} {a_fail:>7} | {cell(b, 'rps', '.1f'):>6} {cell(a, 'rps', '.1f'):>6} | "
              f"{bg(b):>8} {bg(a):>8}")


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--label", required=True, help="결과 파일 이름 (예: isolation_sync)")
    r.add_argument("--levels", default="0,5,10,15,20,30", help="쉼표로 구분한 배경(스피치 분석) 동시성")
    r.add_argument("--probe-path", default="/applications", help="프로브 대상 GET 경로")
    r.add_argument("--probe-concurrency", type=int, default=10, help="프로브 동시성")
    r.add_argument("--duration", type=float, default=90.0, help="레벨당 프로브 측정 시간(초)")
    r.add_argument("--ramp", type=float, default=5.0, help="배경 부하 시작 후 프로브 시작까지 대기(초)")
    r.add_argument("--rest", type=float, default=3.0, help="레벨 간 휴식(초)")
    r.add_argument("--probe-timeout", type=float, default=60.0, help="프로브 요청 타임아웃(초)")
    r.add_argument("--bg-timeout", type=float, default=240.0, help="스피치 분석 요청 타임아웃(초)")

    c = sub.add_parser("compare")
    c.add_argument("before")
    c.add_argument("after")

    args = parser.parse_args()
    if args.cmd == "run":
        asyncio.run(run(args))
    else:
        compare(args)


if __name__ == "__main__":
    main()
