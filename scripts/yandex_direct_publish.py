#!/usr/bin/env python3
"""
Yandex.Direct Publisher for PowerDemon.AI
Создаёт и управляет кампаниями через Yandex.Direct API v5.

Использование:
  python3 scripts/yandex_direct_publish.py --business netashi --draft 2026-03-01_search_strollers
  python3 scripts/yandex_direct_publish.py --business netashi --test-connection
  python3 scripts/yandex_direct_publish.py --business netashi --list-campaigns

Credentials: businesses/{name}/.credentials
"""

import os
import sys
import json
import argparse
import requests
from pathlib import Path

BUSINESSES_DIR = Path(__file__).parent.parent / "businesses"
API_URL = "https://api.direct.yandex.com/json/v5/"
SANDBOX_URL = "https://api-sandbox.direct.yandex.com/json/v5/"

def load_credentials(business: str) -> dict:
    """Загрузить credentials из businesses/{name}/.credentials"""
    cred_file = BUSINESSES_DIR / business / ".credentials"
    env = {}
    if cred_file.exists():
        for line in cred_file.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return env

class YandexDirectClient:
    def __init__(self, token: str, login: str, sandbox: bool = False):
        self.token = token
        self.login = login
        self.base_url = SANDBOX_URL if sandbox else API_URL
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Client-Login": login,
            "Accept-Language": "ru",
            "Content-Type": "application/json; charset=utf-8",
        }
    
    def request(self, service: str, method: str, params: dict = None) -> dict:
        """Выполнить запрос к API"""
        url = self.base_url + service
        body = {"method": method}
        if params:
            body["params"] = params
        
        response = requests.post(url, json=body, headers=self.headers)
        result = response.json()
        
        if "error" in result:
            raise Exception(f"API Error: {result['error']['error_string']} - {result['error'].get('error_detail', '')}")
        
        return result.get("result", result)
    
    # === Кампании ===
    
    def list_campaigns(self) -> list:
        """Получить список кампаний"""
        result = self.request("campaigns", "get", {
            "SelectionCriteria": {},
            "FieldNames": ["Id", "Name", "Status", "State", "DailyBudget"]
        })
        return result.get("Campaigns", [])
    
    def create_campaign(self, name: str, daily_budget_micros: int = 30000000) -> int:
        """Создать текстово-графическую кампанию"""
        result = self.request("campaigns", "add", {
            "Campaigns": [{
                "Name": name,
                "StartDate": __import__("datetime").date.today().isoformat(),
                "DailyBudget": {
                    "Amount": daily_budget_micros,
                    "Mode": "STANDARD"
                },
                "TextCampaign": {
                    "BiddingStrategy": {
                        "Search": {
                            "BiddingStrategyType": "HIGHEST_POSITION"
                        },
                        "Network": {
                            "BiddingStrategyType": "SERVING_OFF"
                        }
                    }
                }
            }]
        })
        campaign_id = result["AddResults"][0]["Id"]
        return campaign_id
    
    # === Группы объявлений ===
    
    def create_ad_group(self, campaign_id: int, name: str, region_ids: list = None) -> int:
        """Создать группу объявлений"""
        if region_ids is None:
            region_ids = [225, 159]  # Россия + Казахстан
        
        result = self.request("adgroups", "add", {
            "AdGroups": [{
                "Name": name,
                "CampaignId": campaign_id,
                "RegionIds": region_ids
            }]
        })
        return result["AddResults"][0]["Id"]
    
    # === Ключевые слова ===
    
    def add_keywords(self, ad_group_id: int, keywords: list) -> list:
        """Добавить ключевые слова"""
        kw_items = [{"Keyword": kw, "AdGroupId": ad_group_id} for kw in keywords]
        result = self.request("keywords", "add", {"Keywords": kw_items})
        return result.get("AddResults", [])
    
    # === Объявления ===
    
    def create_ad(self, ad_group_id: int, title: str, title2: str, 
                  text: str, url: str, display_url: str = None) -> int:
        """Создать текстовое объявление"""
        ad = {
            "AdGroupId": ad_group_id,
            "TextAd": {
                "Title": title,
                "Title2": title2,
                "Text": text,
                "Href": url,
                "Mobile": "NO"
            }
        }
        if display_url:
            ad["TextAd"]["DisplayUrlPath"] = display_url
        
        result = self.request("ads", "add", {"Ads": [ad]})
        add_result = result["AddResults"][0]
        if "Id" in add_result:
            return add_result["Id"]
        else:
            raise Exception(f"Ad creation failed: {add_result.get('Errors', add_result)}")


def test_connection(client: YandexDirectClient):
    """Проверить подключение к API"""
    try:
        campaigns = client.list_campaigns()
        print(f"✅ Подключение успешно!")
        print(f"📊 Кампаний в аккаунте: {len(campaigns)}")
        for c in campaigns:
            print(f"   → {c['Name']} (ID: {c['Id']}, статус: {c.get('Status', '?')})")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False


def publish_from_draft(client: YandexDirectClient, business: str, draft_name: str, 
                       landing_url: str, dry_run: bool = False):
    """Создать кампанию из черновика"""
    draft_path = BUSINESSES_DIR / business / "drafts" / "yandex_direct" / draft_name
    campaign_file = draft_path / "campaign.md"
    
    if not campaign_file.exists():
        print(f"❌ Черновик не найден: {campaign_file}")
        return
    
    content = campaign_file.read_text()
    print(f"📄 Черновик: {draft_name}")
    print(f"🔗 Посадочная: {landing_url}")
    
    if dry_run:
        print("🏃 DRY RUN — кампания не будет создана")
        return
    
    # Здесь будет парсинг MD-файла и создание кампании
    print("⚠️ Автоматический парсинг черновиков — в разработке")
    print("   Пока используй --test-connection для проверки связи")


def main():
    parser = argparse.ArgumentParser(description="Yandex.Direct Publisher")
    parser.add_argument("--business", required=True, help="Имя бизнеса")
    parser.add_argument("--test-connection", action="store_true", help="Проверить подключение")
    parser.add_argument("--list-campaigns", action="store_true", help="Список кампаний")
    parser.add_argument("--draft", help="Имя черновика для публикации")
    parser.add_argument("--landing-url", help="URL посадочной страницы")
    parser.add_argument("--sandbox", action="store_true", help="Использовать sandbox")
    parser.add_argument("--dry-run", action="store_true", help="Только показать")
    args = parser.parse_args()
    
    creds = load_credentials(args.business)
    token = creds.get("YANDEX_DIRECT_TOKEN")
    login = creds.get("YANDEX_DIRECT_LOGIN")
    
    if not token or not login:
        print(f"❌ Нет credentials. Заполни businesses/{args.business}/.credentials:")
        print(f"   YANDEX_DIRECT_TOKEN=...")
        print(f"   YANDEX_DIRECT_LOGIN=...")
        sys.exit(1)
    
    client = YandexDirectClient(token, login, sandbox=args.sandbox)
    
    if args.test_connection or args.list_campaigns:
        test_connection(client)
    elif args.draft:
        landing = args.landing_url or creds.get("LANDING_URL", "")
        if not landing:
            print("❌ Укажи --landing-url или LANDING_URL в .credentials")
            sys.exit(1)
        publish_from_draft(client, args.business, args.draft, landing, args.dry_run)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
