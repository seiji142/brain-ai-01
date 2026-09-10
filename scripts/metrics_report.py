#!/usr/bin/env python3
"""
Script de métricas para monitoreo semanal del sistema de provenance.
Genera reportes de tendencias, anomalías y recomendaciones.

Uso:
    python scripts/metrics_report.py                    # Reporte semanal
    python scripts/metrics_report.py --period 7d        # Últimos 7 días
    python scripts/metrics_report.py --period 30d       # Últimos 30 días
    python scripts/metrics_report.py --json             # Salida JSON
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from pathlib import Path

AUDIT_LOG = Path(__file__).parent.parent / "logs" / "audit.jsonl"


def parse_timestamp(ts: str) -> datetime:
    """Parsea timestamp ISO 8601."""
    return datetime.fromisoformat(ts)


def load_events(period: str = "7d") -> list[dict]:
    """Carga eventos del audit log filtrados por período."""
    if not AUDIT_LOG.exists():
        return []

    days = int(period.replace("d", ""))
    cutoff = datetime.now().astimezone() - timedelta(days=days)

    events = []
    with open(AUDIT_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                ts = parse_timestamp(event["ts"])
                if ts >= cutoff:
                    events.append(event)
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
    return events


def compute_metrics(events: list[dict]) -> dict:
    """Calcula métricas principales."""
    metrics = {
        "total_events": len(events),
        "by_event": Counter(),
        "by_action": Counter(),
        "by_session": Counter(),
        "violations_by_action": Counter(),
        "violations_by_reason": Counter(),
        "handles_issued": 0,
        "handles_validated": 0,
        "handles_rejected": 0,
        "leaks_detected": 0,
        "action_allowed": 0,
        "action_denied": 0,
        "action_allowed_with_violations": 0,
        "resolve_requests": 0,
        "resolve_success": 0,
        "resolve_failures": 0,
        "timeline": defaultdict(lambda: {"allowed": 0, "denied": 0, "violations": 0}),
    }

    for event in events:
        event_type = event.get("event", "unknown")
        metrics["by_event"][event_type] += 1

        if event_type == "handle_issued":
            metrics["handles_issued"] += 1
        elif event_type == "handle_validated":
            metrics["handles_validated"] += 1
        elif event_type == "handle_rejected":
            metrics["handles_rejected"] += 1
        elif event_type == "leak_detected":
            metrics["leaks_detected"] += 1
        elif event_type == "action_allowed":
            metrics["action_allowed"] += 1
            action = event.get("action", "unknown")
            metrics["by_action"][action] += 1
            if event.get("had_violations"):
                metrics["action_allowed_with_violations"] += 1
            # Timeline
            ts = parse_timestamp(event["ts"]).strftime("%Y-%m-%d")
            metrics["timeline"][ts]["allowed"] += 1
        elif event_type == "action_denied":
            metrics["action_denied"] += 1
            action = event.get("action", "unknown")
            metrics["by_action"][action] += 1
            # Timeline
            ts = parse_timestamp(event["ts"]).strftime("%Y-%m-%d")
            metrics["timeline"][ts]["denied"] += 1
        elif event_type == "policy_violation":
            action = event.get("action", "unknown")
            mode = event.get("mode", "unknown")
            violations = event.get("violations", [])
            metrics["violations_by_action"][f"{action} ({mode})"] += 1
            for v in violations:
                reason = v.split(":")[0] if ":" in v else v
                metrics["violations_by_reason"][reason] += 1
            # Timeline
            ts = parse_timestamp(event["ts"]).strftime("%Y-%m-%d")
            metrics["timeline"][ts]["violations"] += 1
        elif event_type == "resolve_request":
            metrics["resolve_requests"] += 1
        elif event_type == "resolve_result":
            status = event.get("status", "unknown")
            if status in ("resolved", "resolved_no_store"):
                metrics["resolve_success"] += 1
            else:
                metrics["resolve_failures"] += 1
        elif event_type == "session":
            session = event.get("session", "unknown")
            metrics["by_session"][session] += 1

    return metrics


def detect_anomalies(metrics: dict) -> list[str]:
    """Detecta anomalías en las métricas."""
    anomalies = []

    # Alto ratio de violaciones
    if metrics["action_allowed"] > 0:
        violation_rate = metrics["action_allowed_with_violations"] / metrics["action_allowed"]
        if violation_rate > 0.3:
            anomalies.append(
                f"⚠️  Alto ratio de violaciones permitidas: {violation_rate:.1%} "
                f"({metrics['action_allowed_with_violations']}/{metrics['action_allowed']})"
            )

    # Fugas de secretos
    if metrics["leaks_detected"] > 0:
        anomalies.append(
            f"🚨 Fugas de secretos detectadas: {metrics['leaks_detected']}"
        )

    # Handles rechazados
    if metrics["handles_rejected"] > 0:
        anomalies.append(
            f"⚠️  Handles rechazados: {metrics['handles_rejected']} "
            "(posible session mismatch o expiración)"
        )

    # Resolver failures
    if metrics["resolve_failures"] > 0:
        anomalies.append(
            f"⚠️  Resoluciones fallidas: {metrics['resolve_failures']} "
            "(referencias no encontradas)"
        )

    # Alta concentración en una sesión
    if metrics["by_session"]:
        top_session, count = metrics["by_session"].most_common(1)[0]
        if count > metrics["total_events"] * 0.8:
            anomalies.append(
                f"⚠️  Concentración de actividad en sesión {top_session[:15]}...: {count} eventos"
            )

    return anomalies


def generate_recommendations(metrics: dict, anomalies: list[str]) -> list[str]:
    """Genera recomendaciones basadas en métricas."""
    recommendations = []

    # Deploy listo para enforce?
    deploy_violations = sum(
        v for k, v in metrics["violations_by_action"].items()
        if k.startswith("deploy")
    )
    if deploy_violations == 0 and metrics["handles_validated"] >= 2:
        recommendations.append(
            "✅ deploy: Candidato para promote a enforce (0 violaciones, "
            f"{metrics['handles_validated']} handles validados)"
        )
    elif deploy_violations > 0:
        recommendations.append(
            f"❌ deploy: No promover aún ({deploy_violations} violaciones)"
        )

    # write_file listo para enforce?
    write_violations = sum(
        v for k, v in metrics["violations_by_action"].items()
        if k.startswith("write_file")
    )
    if write_violations == 0:
        recommendations.append(
            "✅ write_file: Candidato para promote a enforce (0 violaciones)"
        )
    else:
        recommendations.append(
            f"❌ write_file: No promover aún ({write_violations} violaciones)"
        )

    # http_request listo?
    http_violations = sum(
        v for k, v in metrics["violations_by_action"].items()
        if k.startswith("http_request")
    )
    if http_violations == 0 and metrics["handles_validated"] == 0:
        recommendations.append(
            "ℹ️  http_request: Sin tests aún, necesita validación"
        )

    # Alta tasa de denies por no_policy
    no_policy_denies = sum(
        v for k, v in metrics["violations_by_reason"].items()
        if "no_policy" in k.lower()
    )
    if no_policy_denies > 0:
        recommendations.append(
            f"⚠️  {no_policy_denies} denegaciones por 'no_policy': "
            "considerar agregar políticas para acciones no registradas"
        )

    return recommendations


def print_report(metrics: dict, anomalies: list[str], recommendations: list[str]):
    """Imprime el reporte formateado."""
    print("=" * 60)
    print("📊 REPORTE DE MÉTRICAS - SISTEMA DE PROVENANCE")
    print("=" * 60)
    print(f"📅 Período: Últimos 7 días")
    print(f"🕐 Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Resumen general
    print("📈 RESUMEN GENERAL")
    print("-" * 40)
    print(f"  Total de eventos:          {metrics['total_events']}")
    print(f"  Acciones permitidas:       {metrics['action_allowed']}")
    print(f"  Acciones denegadas:        {metrics['action_denied']}")
    print(f"  Violaciones (en warn):     {metrics['action_allowed_with_violations']}")
    print(f"  Handles emitidos:          {metrics['handles_issued']}")
    print(f"  Handles validados:         {metrics['handles_validated']}")
    print(f"  Handles rechazados:        {metrics['handles_rejected']}")
    print(f"  Fugas detectadas:          {metrics['leaks_detected']}")
    print()

    # Métricas de resolución
    print("🔍 RESOLUCIÓN DE REFERENCIAS")
    print("-" * 40)
    print(f"  Requests totales:          {metrics['resolve_requests']}")
    print(f"  Exitosas:                  {metrics['resolve_success']}")
    print(f"  Fallidas:                  {metrics['resolve_failures']}")
    if metrics["resolve_requests"] > 0:
        success_rate = metrics["resolve_success"] / metrics["resolve_requests"]
        print(f"  Ratio de éxito:            {success_rate:.1%}")
    print()

    # Top acciones
    if metrics["by_action"]:
        print("🎯 ACCIONES MÁS USADAS")
        print("-" * 40)
        for action, count in metrics["by_action"].most_common(10):
            print(f"  {action:25s} {count:5d}")
        print()

    # Violaciones por acción
    if metrics["violations_by_action"]:
        print("⚠️  VIOLACIONES POR ACCIÓN")
        print("-" * 40)
        for action, count in metrics["violations_by_action"].most_common(10):
            print(f"  {action:35s} {count:5d}")
        print()

    # Timeline
    if metrics["timeline"]:
        print("📅 TIMELINE DIARIO")
        print("-" * 40)
        for day in sorted(metrics["timeline"].keys()):
            data = metrics["timeline"][day]
            print(
                f"  {day}  "
                f"✅ {data['allowed']:3d}  "
                f"❌ {data['denied']:3d}  "
                f"⚠️  {data['violations']:3d}"
            )
        print()

    # Anomalías
    if anomalies:
        print("🚨 ANOMALÍAS DETECTADAS")
        print("-" * 40)
        for anomaly in anomalies:
            print(f"  {anomaly}")
        print()

    # Recomendaciones
    if recommendations:
        print("💡 RECOMENDACIONES")
        print("-" * 40)
        for rec in recommendations:
            print(f"  {rec}")
        print()

    print("=" * 60)


def main():
    """Punto de entrada principal."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Reporte de métricas del sistema de provenance"
    )
    parser.add_argument(
        "--period",
        default="7d",
        help="Período de análisis (ej: 7d, 30d, 90d)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Salida en formato JSON"
    )
    args = parser.parse_args()

    # Cargar y analizar
    events = load_events(args.period)
    metrics = compute_metrics(events)
    anomalies = detect_anomalies(metrics)
    recommendations = generate_recommendations(metrics, anomalies)

    if args.json:
        output = {
            "metrics": metrics,
            "anomalies": anomalies,
            "recommendations": recommendations,
            "generated_at": datetime.now().isoformat(),
        }
        # Convertir Counters y defaultdicts a dicts
        output["metrics"]["by_event"] = dict(output["metrics"]["by_event"])
        output["metrics"]["by_action"] = dict(output["metrics"]["by_action"])
        output["metrics"]["by_session"] = dict(output["metrics"]["by_session"])
        output["metrics"]["violations_by_action"] = dict(output["metrics"]["violations_by_action"])
        output["metrics"]["violations_by_reason"] = dict(output["metrics"]["violations_by_reason"])
        output["metrics"]["timeline"] = dict(output["metrics"]["timeline"])
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print_report(metrics, anomalies, recommendations)


if __name__ == "__main__":
    main()
