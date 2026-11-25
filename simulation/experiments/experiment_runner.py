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
import xml.etree.ElementTree as ET
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
    result['parking_success_rate'] = (
        result['total_parking_success'] / len(rows)
    )

    result['return_trip_success_rate'] = (
        result['total_completed_return_trip'] / len(rows)
    )

    result['total_parking_failures'] = (
        len(rows) - result['total_parking_success']
    )

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
        groups.setdefault(
            (record['experiment'], record['policy']), []
        ).append(record)

    vehicle_keys = [f'avg_{m}' for m in METRICS] + [
        'total_co2_g',
        'total_parking_reassignments',
        'total_parking_success',
        'total_completed_return_trip',
        'total_teleported',
        'parking_success_rate',
        'return_trip_success_rate',
        'total_parking_failures',
    ]

    network_suffixes = [
        'vehicle_count',
        'completed_trips',
        'unfinished_trips',
        'completion_rate',
        'avg_duration_s',
        'avg_active_duration_s',
        'avg_distance_m',
        'total_completed_distance_m',
        'avg_waiting_time_s',
        'avg_time_loss_s',
        'avg_depart_delay_s',
        'emissions_count',
        'avg_co2_g',
        'total_co2_g',
    ]

    network_keys = [
        f'{prefix}_{suffix}'
        for prefix in ('network', 'background', 'parking')
        for suffix in network_suffixes
    ]

    network_keys += [
        'network_loaded',
        'network_inserted',
        'network_running',
        'network_waiting',
        'network_teleports',
        'network_collisions',
        'network_emergency_stops',
        'simulation_duration_s',
        'execution_duration_s',
    ]

    report_rows = []

    for (experiment, policy), group in sorted(groups.items()):
        valid = [
            r for r in group
            if r.get('status') == 'complete'
        ]

        network_valid = [
            r for r in valid
            if r.get('network_metrics_available') is True
        ]

        row = {
            'experiment': experiment,
            'policy': policy,
            'trials_attempted': len(group),
            'trials_complete': len(valid),
            'trials_incomplete': len(group) - len(valid),
            'trials_with_network_metrics': len(network_valid),
        }

        def aggregate(keys, source):
            for key in keys:
                values = [
                    as_float(r.get(key))
                    for r in source
                ]

                values = [
                    v for v in values
                    if v is not None
                ]

                row[f'mean_{key}'] = (
                    mean(values) if values else None
                )

                row[f'std_{key}'] = (
                    stdev(values)
                    if len(values) > 1
                    else (0.0 if values else None)
                )

                row[f'n_{key}'] = len(values)

        aggregate(vehicle_keys, valid)

        if network_valid:
            aggregate(network_keys, network_valid)

        report_rows.append(row)

    write_csv(
        report_dir / 'policy_comparison.csv',
        report_rows
    )

    print(f'\nTrial report: {report_dir / "trial_summary.csv"}')
    print(f'Policy report: {report_dir / "policy_comparison.csv"}')

    print('\nPolicy summary (complete trials only):')

    for row in report_rows:
        print(
            f"{row['experiment']} / {row['policy']}: "
            f"{row['trials_complete']}/"
            f"{row['trials_attempted']} complete; "
            f"avg driving={row['mean_avg_distance_m']}, "
            f"avg walking={row['mean_avg_walking_distance_m']}, "
            f"avg CO2={row['mean_avg_co2_g']}"
        )

        if row['trials_with_network_metrics'] > 0:
            print(
                f"  Network: "
                f"avg waiting="
                f"{row['mean_network_avg_waiting_time_s']}, "
                f"total CO2="
                f"{row['mean_network_total_co2_g']} g, "
                f"background avg time loss="
                f"{row['mean_background_avg_time_loss_s']} s"
            )


def snapshot_runs(policy_dir):
    return {p.resolve() for p in policy_dir.glob('run_*') if p.is_dir()}

def summarize_network_metrics(run_dir):
    run_dir = Path(run_dir)

    tripinfo_file = run_dir / "tripinfo.xml"
    statistics_file = run_dir / "statistics.xml"

    if not tripinfo_file.exists():
        raise FileNotFoundError(tripinfo_file)

    if not statistics_file.exists():
        raise FileNotFoundError(statistics_file)

    trips = ET.parse(tripinfo_file).getroot().findall("tripinfo")
    statistics = ET.parse(statistics_file).getroot()

    def summarize_group(group, prefix):
        completed = [
            trip for trip in group
            if float(trip.attrib["arrival"]) >= 0
        ]

        def average(values):
            return sum(values) / len(values) if values else None

        durations = [
            float(trip.attrib["duration"])
            for trip in completed
        ]

        active_durations = [
            float(trip.attrib["duration"])
            - float(trip.attrib["stopTime"])
            for trip in completed
        ]

        distances = [
            float(trip.attrib["routeLength"])
            for trip in completed
        ]

        waiting_times = [
            float(trip.attrib["waitingTime"])
            for trip in completed
        ]

        time_losses = [
            float(trip.attrib["timeLoss"])
            for trip in completed
        ]

        departure_delays = [
            float(trip.attrib["departDelay"])
            for trip in completed
        ]

        co2_values = []

        for trip in group:
            emissions = trip.find("emissions")

            if emissions is not None:
                co2_values.append(
                    float(emissions.attrib["CO2_abs"]) / 1000
                )

        return {
            f"{prefix}_vehicle_count": len(group),
            f"{prefix}_completed_trips": len(completed),
            f"{prefix}_unfinished_trips": (
                len(group) - len(completed)
            ),
            f"{prefix}_completion_rate": (
                len(completed) / len(group)
                if group else None
            ),
            f"{prefix}_avg_duration_s": average(durations),
            f"{prefix}_avg_active_duration_s": average(
                active_durations
            ),
            f"{prefix}_avg_distance_m": average(distances),
            f"{prefix}_total_completed_distance_m": sum(distances),
            f"{prefix}_avg_waiting_time_s": average(waiting_times),
            f"{prefix}_avg_time_loss_s": average(time_losses),
            f"{prefix}_avg_depart_delay_s": average(
                departure_delays
            ),
            f"{prefix}_emissions_count": len(co2_values),
            f"{prefix}_avg_co2_g": average(co2_values),
            f"{prefix}_total_co2_g": (
                sum(co2_values) if co2_values else None
            ),
        }

    background_trips = [
        trip for trip in trips
        if trip.attrib["id"].startswith("background_vehicle_")
    ]

    parking_trips = [
        trip for trip in trips
        if trip.attrib["id"].startswith("parking_vehicle_")
    ]

    results = {}

    results.update(summarize_group(trips, "network"))

    results.update(
        summarize_group(background_trips, "background")
    )

    results.update(
        summarize_group(parking_trips, "parking")
    )

    vehicles = statistics.find("vehicles")
    teleports = statistics.find("teleports")
    safety = statistics.find("safety")
    performance = statistics.find("performance")

    results.update({
        "network_loaded": int(vehicles.attrib["loaded"]),
        "network_inserted": int(vehicles.attrib["inserted"]),
        "network_running": int(vehicles.attrib["running"]),
        "network_waiting": int(vehicles.attrib["waiting"]),
        "network_teleports": int(teleports.attrib["total"]),
        "network_collisions": int(safety.attrib["collisions"]),
        "network_emergency_stops": int(
            safety.attrib["emergencyStops"]
        ),
        "simulation_duration_s": float(
            performance.attrib["duration"]
        ),
        "execution_duration_s": float(
            performance.attrib["clockDuration"]
        ),
    })

    return results


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
                            record.update(
                                summarize_vehicle_csv(metrics_path)
                            )

                            network_metrics = summarize_network_metrics(
                                metrics_path.parent
                            )

                            record.update(network_metrics)

                            record['network_metrics_available'] = True

                            record['network_complete'] = (
                                record['network_loaded']
                                == record['network_completed_trips']
                                and record['network_running'] == 0
                                and record['network_waiting'] == 0
                                and record['network_teleports'] == 0
                                and record['network_emissions_count']
                                == record['network_vehicle_count']
                            )

                            record['status'] = (
                                'complete'
                                if proc.returncode == 0
                                and record['network_complete']
                                and record['vehicle_count'] == 40
                                and record['parking_vehicle_count'] == 40
                                else 'incomplete'
                            )

                        except (
                            ValueError,
                            OSError,
                            ET.ParseError,
                            KeyError,
                        ) as error:
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
