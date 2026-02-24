#!/usr/bin/env python3
"""
Yandex.Metrica Stats Collector for PowerDemon.AI
Собирает данные о поведении на сайте и сохраняет в reports/.

Использование:
  python3 scripts/yandex_metrica_stats.py --business netashi
  python3 scripts/yandex_metrica_stats.py --business netashi --days 7

Credentials: businesses/{name}/.credentials
  YANDEX_METRICA_COUNTER=12345678
  YANDEX_DIRECT_TOKEN=...  (тот же OAuth-токен)
"""

import sys
import csv
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta

BUSINESSES_DIR = Path(__file__).parent.parent / "businesses"
METRICA_API = "https://api-metrika.yandex.net/stat/v1/data"


def load_credentials(business: str) -> dict:
    cred_file = BUSINESSES_DIR / business / ".credentials"
    env = {}
    if cred_file.exists():
        for line in cred_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_metrica_data(token: str, counter_id: str, date_from: str, date_to: str,
                     metrics: str, dimensions: str = "ym:s:date", group: str = "day"):
    """Запрос к API Яндекс.Метрики"""
    headers = {"Authorization": f"OAuth {token}"}
    params = {
        "ids": counter_id,
        "date1": date_from,
        "date2": date_to,
        "metrics": metrics,
        "dimensions": dimensions,
        "group": group,
        "limit": 100,
    }
    response = requests.get(METRICA_API, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Metrica API Error {response.status_code}: {response.text}")
    return response.json()


def get_traffic_summary(token: str, counter_id: str, date_from: str, date_to: str) -> list:
    """Трафик по дням: визиты, пользователи, просмотры, отказы, время"""
    metrics = "ym:s:visits,ym:s:users,ym:s:pageviews,ym:s:bounceRate,ym:s:avgVisitDurationSeconds"
    data = get_metrica_data(token, counter_id, date_from, date_to, metrics)

    rows = []
    for item in data.get("data", []):
        date = item["dimensions"][0]["name"]
        m = item["metrics"]
        rows.append({
            "date": date,
            "visits": int(m[0]),
            "users": int(m[1]),
            "pageviews": int(m[2]),
            "bounce_rate": round(m[3], 1),
            "avg_duration": round(m[4], 0),
        })
    return rows


def get_traffic_sources(token: str, counter_id: str, date_from: str, date_to: str) -> list:
    """Источники трафика"""
    metrics = "ym:s:visits,ym:s:users,ym:s:bounceRate"
    dimensions = "ym:s:lastTrafficSource"
    data = get_metrica_data(token, counter_id, date_from, date_to, metrics, dimensions)

    rows = []
    for item in data.get("data", []):
        source = item["dimensions"][0]["name"]
        m = item["metrics"]
        rows.append({
            "source": source,
            "visits": int(m[0]),
            "users": int(m[1]),
            "bounce_rate": round(m[2], 1),
        })
    return rows


def get_search_queries(token: str, counter_id: str, date_from: str, date_to: str) -> list:
    """Поисковые запросы (по каким запросам приходят)"""
    metrics = "ym:s:visits"
    dimensions = "ym:s:lastSearchPhrase"
    data = get_metrica_data(token, counter_id, date_from, date_to, metrics, dimensions)

    rows = []
    for item in data.get("data", []):
        query = item["dimensions"][0]["name"]
        if query and query != "(not set)":
            rows.append({
                "query": query,
                "visits": int(item["metrics"][0]),
            })
    return sorted(rows, key=lambda x: x["visits"], reverse=True)


def generate_report_md(traffic: list, sources: list, queries: list,
                       date_from: str, date_to: str, business: str) -> str:
    """Сформировать MD-отчёт по Метрике"""
    report = f"# Отчёт Яндекс.Метрика: {business}\n"
    report += f"**Период:** {date_from} — {date_to}\n"
    report += f"**Дата формирования:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    if not traffic:
        report += "> Нет данных за указанный период.\n"
        return report

    # Сводка
    total_visits = sum(r["visits"] for r in traffic)
    total_users = sum(r["users"] for r in traffic)
    total_views = sum(r["pageviews"] for r in traffic)
    avg_bounce = sum(r["bounce_rate"] for r in traffic) / len(traffic) if traffic else 0
    avg_duration = sum(r["avg_duration"] for r in traffic) / len(traffic) if traffic else 0

    report += "## Сводка\n\n"
    report += "| Визиты | Пользователи | Просмотры | Отказы | Ср. время |\n"
    report += "|--------|-------------|-----------|--------|----------|\n"
    bounce_flag = "⚠️" if avg_bounce > 50 else "✅"
    report += f"| {total_visits} | {total_users} | {total_views} | {avg_bounce:.0f}% {bounce_flag} | {avg_duration:.0f} сек |\n\n"

    # По дням
    report += "## По дням\n\n"
    report += "| Дата | Визиты | Пользователи | Просмотры | Отказы |\n"
    report += "|------|--------|-------------|-----------|--------|\n"
    for r in traffic:
        report += f"| {r['date']} | {r['visits']} | {r['users']} | {r['pageviews']} | {r['bounce_rate']}% |\n"

    # Источники
    if sources:
        report += "\n## Источники трафика\n\n"
        report += "| Источник | Визиты | Пользователи | Отказы |\n"
        report += "|----------|--------|-------------|--------|\n"
        for r in sorted(sources, key=lambda x: x["visits"], reverse=True):
            report += f"| {r['source']} | {r['visits']} | {r['users']} | {r['bounce_rate']}% |\n"

    # Поисковые запросы
    if queries:
        report += "\n## Поисковые запросы (топ)\n\n"
        report += "| Запрос | Визиты |\n"
        report += "|--------|--------|\n"
        for r in queries[:20]:
            report += f"| {r['query']} | {r['visits']} |\n"

    report += "\n---\n*Сгенерировано автоматически скриптом yandex_metrica_stats.py*\n"
    return report


def append_to_csv(traffic: list, csv_path: Path):
    """Добавить данные в кумулятивный CSV"""
    file_exists = csv_path.exists()
    fieldnames = ["Дата", "Визиты", "Пользователи", "Просмотры", "Отказы %", "Ср. время (сек)"]

    existing_dates = set()
    if file_exists:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                existing_dates.add(row.get("Дата", ""))

    new_rows = []
    for r in traffic:
        if r["date"] not in existing_dates:
            new_rows.append({
                "Дата": r["date"],
                "Визиты": r["visits"],
                "Пользователи": r["users"],
                "Просмотры": r["pageviews"],
                "Отказы %": r["bounce_rate"],
                "Ср. время (сек)": r["avg_duration"],
            })

    if not new_rows:
        print("   CSV: нет новых данных")
        return

    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)
    print(f"   CSV: +{len(new_rows)} строк → {csv_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Сбор статистики Яндекс.Метрики")
    parser.add_argument("--business", required=True)
    parser.add_argument("--days", type=int, default=1, help="За сколько дней (по умолчанию 1)")
    args = parser.parse_args()

    creds = load_credentials(args.business)
    token = creds.get("YANDEX_DIRECT_TOKEN")  # Тот же OAuth-токен
    counter_id = creds.get("YANDEX_METRICA_COUNTER")

    if not token:
        print(f"❌ Нет YANDEX_DIRECT_TOKEN в businesses/{args.business}/.credentials")
        sys.exit(1)
    if not counter_id:
        print(f"❌ Нет YANDEX_METRICA_COUNTER в businesses/{args.business}/.credentials")
        print(f"   Добавь: YANDEX_METRICA_COUNTER=12345678")
        print(f"   ID счётчика можно найти на metrika.yandex.ru")
        sys.exit(1)

    date_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    print(f"📊 Метрика {args.business} за {date_from} — {date_to}...")

    try:
        traffic = get_traffic_summary(token, counter_id, date_from, date_to)
        sources = get_traffic_sources(token, counter_id, date_from, date_to)
        queries = get_search_queries(token, counter_id, date_from, date_to)
        print(f"   Дней с данными: {len(traffic)}")

        # Папка отчётов (общая для сайта, не для проекта)
        reports_dir = BUSINESSES_DIR / args.business / "projects" / "yandex-direct" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # MD-отчёт
        report_md = generate_report_md(traffic, sources, queries, date_from, date_to, args.business)
        md_path = reports_dir / f"metrica_{date_from}.md"
        md_path.write_text(report_md)
        print(f"✅ MD-отчёт: {md_path.name}")

        # Кумулятивный CSV
        csv_path = reports_dir / "metrica.csv"
        append_to_csv(traffic, csv_path)
        print(f"✅ CSV: metrica.csv")

        print("\n" + report_md)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
