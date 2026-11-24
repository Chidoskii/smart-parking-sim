#!/usr/bin/env python3
"""Run SUMO parking experiments and aggregate run-level results.

Run from the project root. Uses only Python standard library.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib import request, error
from datetime import datetime, timezone
from statistics import mean, stdev

POLICIES = ('baseline', 'availability', 'smart', 'smart_v2')
METRICS = ('time_to_parking', 'parking_search_time', 'waiting_time', 'time_loss', 'distance_m', 'walking_distance_m', 'co2_g')
COUNTS = ('parking_reassignments', 'parking_success', 'completed_return_trip', 'teleported')

def initialize_parking_scenario(parking_file):
    """Load the matching occupancy scenario into the backend."""

    scenario = parking_file.parent.name

    if scenario not in ("normal_occupancy", "high_occupancy"):
        raise ValueError(
            f"Unknown occupancy scenario directory: {scenario}"
        )

    url = "http://localhost:5000/api/occupancy/scenario"

    payload = json.dumps({
        "scenario": scenario
    }).encode("utf-8")

    req = request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as response:
            result = json.load(response)
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            f"Unable to initialize backend scenario '{scenario}': {exc}"
        ) from exc

    if not result.get("success") or result.get("scenario") != scenario:
        raise RuntimeError(
            f"Backend rejected occupancy scenario '{scenario}': {result}"
        )

    print(
        f"Backend initialized: {scenario} | "
        f"capacity={result['totalCapacity']} | "
        f"occupied={result['totalOccupied']} | "
        f"available={result['totalAvailable']}",
        flush=True,
    )


def as_float(value):
    if value is None or str(value).strip().lower() in ('', 'nan', 'none', 'null'):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (ValueError, TypeError):
        return None


def as_count(value):
    if isinstance(value, bool):
        return int(value)
    if str(value).strip().lower() in ('true', 'yes'):
        return 1
    if str(value).strip().lower() in ('false', 'no', ''):
        return 0
    return int(as_float(value) or 0)


def summarize_vehicle_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        columns = set(reader.fieldnames or [])
        required = set(METRICS) | set(COUNTS)
        missing = required - columns
        if missing:
            raise ValueError(f'Missing columns in {path}: {sorted(missing)}')
        rows = list(reader)
    if not rows:
        raise ValueError(f'Empty vehicle metrics: {path}')
    result = {'vehicle_count': len(rows)}
    for metric in METRICS:
        values = [v for row in rows if (v := as_float(row[metric])) is not None]
        result[f'avg_{metric}'] = mean(values) if values else None
        result[f'n_{metric}'] = len(values)
    result['total_co2_g'] = sum(as_float(row['co2_g']) or 0 for row in rows)
    for metric in COUNTS:
        result[f'total_{metric}'] = sum(as_count(row[metric]) for row in rows)
    result['complete'] = (
        result['total_parking_success'] == len(rows)
        and result['total_completed_return_trip'] == len(rows)
        and result['total_teleported'] == 0
    )
    return result


def write_csv(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open('w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def build_report(records, report_dir):
    write_csv(report_dir / 'trial_summary.csv', records)
    groups = {}
    for record in records:
        groups.setdefault((record['experiment'], record['policy']), []).append(record)
    report_rows = []
    for (experiment, policy), group in sorted(groups.items()):
        valid = [r for r in group if r.get('status') == 'complete']
        row = {'experiment': experiment, 'policy': policy,
               'trials_attempted': len(group), 'trials_complete': len(valid),
               'trials_incomplete': len(group) - len(valid)}
        for key in [f'avg_{m}' for m in METRICS] + ['total_co2_g', 'total_parking_reassignments', 'total_parking_success', 'total_completed_return_trip', 'total_teleported']:
            values = [as_float(r.get(key)) for r in valid]
            values = [v for v in values if v is not None]
            row[f'mean_{key}'] = mean(values) if values else None
            row[f'std_{key}'] = stdev(values) if len(values) > 1 else (0.0 if values else None)
        report_rows.append(row)
    write_csv(report_dir / 'policy_comparison.csv', report_rows)
    print(f'\nTrial report: {report_dir / "trial_summary.csv"}')
    print(f'Policy report: {report_dir / "policy_comparison.csv"}')
    print('\nPolicy summary (complete trials only):')
    for row in report_rows:
        print(f"{row['experiment']} / {row['policy']}: {row['trials_complete']}/{row['trials_attempted']} complete; "
              f"avg driving={row['mean_avg_distance_m']}, avg walking={row['mean_avg_walking_distance_m']}, "
              f"avg CO2={row['mean_avg_co2_g']}")


def snapshot_runs(policy_dir):
    return {p.resolve() for p in policy_dir.glob('run_*') if p.is_dir()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', default='simulation/experiments/experiment_config.json')
    parser.add_argument('--report-dir', default='simulation/results/experiment_reports')
    parser.add_argument('--report-only', action='store_true', help='Aggregate trial manifest without launching SUMO')
    parser.add_argument('--stop-on-error', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    os.chdir(root)
    config_path = root / args.config
    report_dir = root / args.report_dir
    manifest = report_dir / 'trial_manifest.json'
    report_dir.mkdir(parents=True, exist_ok=True)
    records = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else []
    if not args.report_only:
        config = json.loads(config_path.read_text(encoding='utf-8'))
        bridge = root / config.get('bridge', 'simulation/src/sumo_backend_bridge.py')
        if not bridge.is_file():
            parser.error(f'Bridge not found: {bridge}')
        for experiment in config['experiments']:
            label = experiment['name']
            parking = root / experiment['parking_file']
            if not parking.is_file():
                parser.error(f'Parking file not found: {parking}')
            for trial in experiment['trials']:
                seed = trial['seed']
                route = root / trial['route_file']
                if not route.is_file():
                    parser.error(f'Route file not found: {route}')
                for policy in config.get('policies', POLICIES):
                    if policy not in POLICIES:
                        parser.error(f'Unknown policy: {policy}')
                    if any(r.get('experiment') == label and r.get('seed') == seed and r.get('policy') == policy and r.get('status') == 'complete' for r in records):
                        print(f'SKIP completed: {label}, seed={seed}, policy={policy}')
                        continue
                    # Initialize the backend with the correct parking occupancy.
                    # This also resets simulated occupancy from the previous trial.
                    initialize_parking_scenario(parking)

                    policy_dir = root / 'simulation/results' / policy
                    before = snapshot_runs(policy_dir)

                    cmd = [sys.executable, str(bridge), '--scenario', policy,
                        '--route-file', str(route), '--parking-file', str(parking)]
                    print(f'\nRUN: {label}, seed={seed}, policy={policy}', flush=True)
                    started = datetime.now(timezone.utc).isoformat()
                    log_path = report_dir / 'logs' / f'{re.sub(r"[^a-zA-Z0-9_-]", "_", label)}_seed{seed}_{policy}_{datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")}.log'
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                    with log_path.open('w', encoding='utf-8') as log:
                        proc = subprocess.run(cmd, cwd=root, stdout=log, stderr=subprocess.STDOUT, check=False)
                    after = snapshot_runs(policy_dir)
                    created = sorted(after - before)
                    record = {'experiment': label, 'seed': seed, 'policy': policy,
                              'route_file': str(route.relative_to(root)),
                              'parking_file': str(parking.relative_to(root)),
                              'started_utc': started, 'return_code': proc.returncode,
                              'log_file': str(log_path.relative_to(root))}
                    if len(created) == 1 and (created[0] / 'vehicle_metrics.csv').is_file():
                        metrics_path = created[0] / 'vehicle_metrics.csv'
                        record['metrics_file'] = str(metrics_path.relative_to(root))
                        try:
                            record.update(summarize_vehicle_csv(metrics_path))
                            record['status'] = 'complete' if proc.returncode == 0 and record['complete'] else 'incomplete'
                        except (ValueError, OSError) as error:
                            record['status'] = 'error'
                            record['error'] = str(error)
                    else:
                        record['status'] = 'error'
                        record['error'] = f'Expected exactly one new run directory with metrics; found {len(created)}'
                    records.append(record)
                    manifest.write_text(json.dumps(records, indent=2, allow_nan=False), encoding='utf-8')
                    print(f"RESULT: {record['status']} | log: {log_path}", flush=True)
                    if record['status'] != 'complete' and args.stop_on_error:
                        build_report(records, report_dir)
                        return 1
    build_report(records, report_dir)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
