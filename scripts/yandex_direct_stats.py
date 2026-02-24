#!/usr/bin/env python3
"""
Yandex.Direct Stats Collector for PowerDemon.AI
Собирает статистику кампаний и сохраняет в reports/.

Использование:
  python3 scripts/yandex_direct_stats.py --business netashi
  python3 scripts/yandex_direct_stats.py --business netashi --days 7
  python3 scripts/yandex_direct_stats.py --business netashi --campaign-id 707523702

Cron (ежедневно в 8:00):
  0 8 * * * cd /Users/pavelrasputin/Desktop/Antygravity && python3 scripts/yandex_direct_stats.py --business netashi
"""

import sys
import json
import argparse
import requests
from pathlib import Path
from datetime import datetime, timedelta

BUSINESSES_DIR = Path(__file__).parent.parent / "businesses"
API_URL = "https://api.direct.yandex.com/json/v5/"


def load_credentials(business: str) -> dict:
    cred_file = BUSINESSES_DIR / business / ".credentials"
    env = {}
    if cred_file.exists():
        for line in cred_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_report(token: str, login: str, date_from: str, date_to: str, campaign_ids: list = None):
    """Получить статистику через Reports API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Client-Login": login,
        "Accept-Language": "ru",
        "Content-Type": "application/json; charset=utf-8",
        "returnMoneyInMicros": "false",
        "skipReportHeader": "true",
        "skipReportSummary": "true",
    }

    selection = {"DateFrom": date_from, "DateTo": date_to}
    if campaign_ids:
        selection["Filter"] = [{"Field": "CampaignId", "Operator": "IN", "Values": [str(x) for x in campaign_ids]}]

    body = {
        "params": {
            "SelectionCriteria": selection,
            "FieldNames": ["Date", "CampaignName", "AdGroupName", "Impressions", "Clicks", "Ctr", "Cost", "AvgCpc"],
            "OrderBy": [{"Field": "Date"}],
            "ReportName": f"PowerDemon_{date_from}_{date_to}",
            "ReportType": "CUSTOM_REPORT",
            "DateRangeType": "CUSTOM_DATE",
            "Format": "TSV",
            "IncludeVAT": "YES",
        }
    }

    response = requests.post(API_URL + "reports", json=body, headers=headers)

    if response.status_code == 200:
        return response.text
    elif response.status_code == 201:
        # Отчёт формируется, нужно подождать
        import time
        for _ in range(10):
            time.sleep(5)
            response = requests.post(API_URL + "reports", json=body, headers=headers)
            if response.status_code == 200:
                return response.text
        raise Exception("Отчёт не сформировался за 50 секунд")
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")


def parse_tsv(tsv_data: str) -> list:
    """Парсим TSV в список словарей"""
    lines = tsv_data.strip().split("\n")
    if not lines:
        return []

    headers = lines[0].split("\t")
    rows = []
    for line in lines[1:]:
        values = line.split("\t")
        row = dict(zip(headers, values))
        rows.append(row)
    return rows


def generate_report_md(rows: list, date_from: str, date_to: str, business: str) -> str:
    """Сформировать MD-отчёт"""
    report = f"# Отчёт Яндекс.Директ: {business}\n"
    report += f"**Период:** {date_from} — {date_to}\n"
    report += f"**Дата формирования:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"

    if not rows:
        report += "> Нет данных за указанный период. Кампания, возможно, ещё на модерации.\n"
        return report

    # Сводка
    total_impressions = sum(int(r.get("Impressions", 0)) for r in rows)
    total_clicks = sum(int(r.get("Clicks", 0)) for r in rows)
    total_cost = sum(float(r.get("Cost", 0)) for r in rows)
    avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0

    report += "## Сводка\n\n"
    report += "| Показы | Клики | CTR | Расход |\n"
    report += "|--------|-------|-----|--------|\n"
    report += f"| {total_impressions} | {total_clicks} | {avg_ctr:.1f}% | {total_cost:.0f}₽ |\n\n"

    # По группам
    groups = {}
    for r in rows:
        gname = r.get("AdGroupName", "—")
        if gname not in groups:
            groups[gname] = {"impressions": 0, "clicks": 0, "cost": 0}
        groups[gname]["impressions"] += int(r.get("Impressions", 0))
        groups[gname]["clicks"] += int(r.get("Clicks", 0))
        groups[gname]["cost"] += float(r.get("Cost", 0))

    report += "## По группам\n\n"
    report += "| Группа | Показы | Клики | CTR | Расход |\n"
    report += "|--------|--------|-------|-----|--------|\n"
    for gname, data in sorted(groups.items(), key=lambda x: x[1]["clicks"], reverse=True):
        ctr = (data["clicks"] / data["impressions"] * 100) if data["impressions"] > 0 else 0
        flag = "⚠️" if ctr < 3 else "✅" if ctr > 7 else ""
        report += f"| {gname} | {data['impressions']} | {data['clicks']} | {ctr:.1f}% {flag} | {data['cost']:.0f}₽ |\n"

    report += "\n"

    # По дням
    days = {}
    for r in rows:
        d = r.get("Date", "—")
        if d not in days:
            days[d] = {"impressions": 0, "clicks": 0, "cost": 0}
        days[d]["impressions"] += int(r.get("Impressions", 0))
        days[d]["clicks"] += int(r.get("Clicks", 0))
        days[d]["cost"] += float(r.get("Cost", 0))

    report += "## По дням\n\n"
    report += "| Дата | Показы | Клики | Расход |\n"
    report += "|------|--------|-------|--------|\n"
    for d in sorted(days.keys()):
        data = days[d]
        report += f"| {d} | {data['impressions']} | {data['clicks']} | {data['cost']:.0f}₽ |\n"

    report += "\n---\n*Сгенерировано автоматически скриптом yandex_direct_stats.py*\n"
    return report
import csv


def append_to_csv(rows: list, csv_path: Path):
    """Добавить строки в кумулятивный CSV (создаёт если не существует)"""
    file_exists = csv_path.exists()
    
    fieldnames = ["Дата", "Кампания", "Группа", "Показы", "Клики", "CTR", "Расход", "Ср. цена клика"]
    
    # Прочитать существующие даты, чтобы не дублировать
    existing_dates = set()
    if file_exists:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                existing_dates.add(row.get("Дата", ""))
    
    new_rows = []
    for r in rows:
        date = r.get("Date", "")
        if date not in existing_dates:
            new_rows.append({
                "Дата": date,
                "Кампания": r.get("CampaignName", ""),
                "Группа": r.get("AdGroupName", ""),
                "Показы": r.get("Impressions", "0"),
                "Клики": r.get("Clicks", "0"),
                "CTR": r.get("Ctr", "0"),
                "Расход": r.get("Cost", "0"),
                "Ср. цена клика": r.get("AvgCpc", "0"),
            })
    
    if not new_rows:
        print(f"   CSV: нет новых данных для добавления")
        return
    
    with open(csv_path, "a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        if not file_exists:
            writer.writeheader()
        writer.writerows(new_rows)
    
    print(f"   CSV: +{len(new_rows)} строк → {csv_path.name}")


def main():
    parser = argparse.ArgumentParser(description="Сбор статистики Яндекс.Директ")
    parser.add_argument("--business", required=True)
    parser.add_argument("--days", type=int, default=1, help="За сколько дней (по умолчанию 1 = вчера)")
    parser.add_argument("--campaign-id", type=int, help="ID конкретной кампании")
    args = parser.parse_args()

    creds = load_credentials(args.business)
    token = creds.get("YANDEX_DIRECT_TOKEN")
    login = creds.get("YANDEX_DIRECT_LOGIN")

    if not token or not login:
        print(f"❌ Нет credentials в businesses/{args.business}/.credentials")
        sys.exit(1)

    # По умолчанию: вчерашний день
    date_to = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    date_from = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")

    campaign_ids = [args.campaign_id] if args.campaign_id else None

    print(f"📊 Собираем статистику {args.business} за {date_from} — {date_to}...")

    try:
        tsv_data = get_report(token, login, date_from, date_to, campaign_ids)
        rows = parse_tsv(tsv_data)
        print(f"   Строк данных: {len(rows)}")

        # Папка отчётов
        reports_dir = BUSINESSES_DIR / args.business / "projects" / "yandex-direct" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        # 1. MD-отчёт (один файл на запрос)
        report_md = generate_report_md(rows, date_from, date_to, args.business)
        md_filename = f"report_{date_from}.md"
        md_path = reports_dir / md_filename
        md_path.write_text(report_md)
        print(f"✅ MD-отчёт: {md_filename}")

        # 2. Кумулятивный CSV (один файл, дополняется каждый день)
        csv_path = reports_dir / "stats.csv"
        append_to_csv(rows, csv_path)
        print(f"✅ CSV: stats.csv")

        # Вывести сводку в консоль
        print("\n" + report_md)

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

