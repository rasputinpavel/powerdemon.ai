#!/usr/bin/env python3
"""
Instagram Publisher for PowerDemon.AI
Публикует контент из drafts/ в Instagram без участия оператора.

Использование:
  python3 scripts/instagram_publish.py --business netashi --draft 2026-02-24_carousel_catalog
  python3 scripts/instagram_publish.py --business netashi --all-approved

Конфигурация: scripts/.env (НЕ коммитить в git!)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# === Конфигурация ===

BUSINESSES_DIR = Path(__file__).parent.parent / "businesses"

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

def get_draft_path(business: str, draft: str) -> Path:
    return BUSINESSES_DIR / business / "drafts" / "instagram" / draft

def read_caption(draft_path: Path) -> str:
    """Прочитать текст подписи"""
    caption_file = draft_path / "caption.md"
    if not caption_file.exists():
        raise FileNotFoundError(f"Нет caption.md в {draft_path}")
    
    text = caption_file.read_text()
    # Убираем заголовок markdown
    lines = text.split("\n")
    content_lines = []
    skip_header = True
    for line in lines:
        if skip_header and (line.startswith("#") or line.strip() == "" or line.startswith("## Подпись")):
            if line.startswith("## Подпись"):
                skip_header = False
            continue
        skip_header = False
        content_lines.append(line)
    
    return "\n".join(content_lines).strip()

def get_images(draft_path: Path) -> list:
    """Найти все изображения в черновике"""
    extensions = {".png", ".jpg", ".jpeg", ".webp"}
    images = []
    for f in sorted(draft_path.iterdir()):
        if f.suffix.lower() in extensions:
            images.append(f)
    return images

def read_meta(draft_path: Path) -> dict:
    """Прочитать мета-данные поста"""
    meta_file = draft_path / "meta.md"
    meta = {"format": "photo"}
    if meta_file.exists():
        text = meta_file.read_text()
        if "Карусель" in text or "карусель" in text:
            meta["format"] = "album"
        elif "Reels" in text or "reels" in text:
            meta["format"] = "reels"
    return meta

def publish_photo(client, image_path: Path, caption: str):
    """Опубликовать одно фото"""
    return client.photo_upload(str(image_path), caption)

def publish_album(client, image_paths: list, caption: str):
    """Опубликовать карусель"""
    paths = [str(p) for p in image_paths]
    return client.album_upload(paths, caption)

def publish_reels(client, video_path: Path, caption: str):
    """Опубликовать Reels"""
    return client.clip_upload(str(video_path), caption)

def update_queue(business: str, draft_name: str, status: str = "📤 Опубликован"):
    """Обновить статус в _queue.md"""
    queue_file = BUSINESSES_DIR / business / "drafts" / "_queue.md"
    if queue_file.exists():
        content = queue_file.read_text()
        # Найти строку с этим черновиком и обновить статус
        lines = content.split("\n")
        updated_lines = []
        for line in lines:
            if draft_name in line and "⏳" in line:
                line = line.replace("⏳ На одобрении", status)
            elif draft_name in line and "✅" in line:
                line = line.replace("✅ Одобрен", status)
            updated_lines.append(line)
        queue_file.write_text("\n".join(updated_lines))

def main():
    parser = argparse.ArgumentParser(description="Публикация Instagram-контента из drafts/")
    parser.add_argument("--business", required=True, help="Имя бизнеса (папка)")
    parser.add_argument("--draft", help="Имя конкретного черновика")
    parser.add_argument("--all-approved", action="store_true", help="Опубликовать все одобренные")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, что будет опубликовано")
    args = parser.parse_args()
    
    creds = load_credentials(args.business)
    ig_username = creds.get("INSTAGRAM_USERNAME")
    ig_password = creds.get("INSTAGRAM_PASSWORD")
    
    if not ig_username or not ig_password:
        print(f"❌ Нет credentials. Создай businesses/{args.business}/.credentials:")
        print(f"   INSTAGRAM_USERNAME=your_account")
        print(f"   INSTAGRAM_PASSWORD=your_password")
        sys.exit(1)
    
    # Определить черновики для публикации
    drafts_to_publish = []
    if args.draft:
        drafts_to_publish.append(args.draft)
    elif args.all_approved:
        queue_file = BUSINESSES_DIR / args.business / "drafts" / "_queue.md"
        if queue_file.exists():
            for line in queue_file.read_text().split("\n"):
                if "✅ Одобрен" in line and "Instagram" in line:
                    # Извлечь имя черновика из строки
                    parts = line.split("|")
                    if len(parts) >= 5:
                        draft_desc = parts[4].strip()
                        # Ищем папку по описанию
                        drafts_dir = BUSINESSES_DIR / args.business / "drafts" / "instagram"
                        if drafts_dir.exists():
                            for d in drafts_dir.iterdir():
                                if d.is_dir() and not d.name.startswith("_"):
                                    drafts_to_publish.append(d.name)
    
    if not drafts_to_publish:
        print("📭 Нет черновиков для публикации")
        sys.exit(0)
    
    # Подключиться к Instagram
    if not args.dry_run:
        try:
            from instagrapi import Client
            client = Client()
            client.login(ig_username, ig_password)
            print(f"✅ Залогинились как @{ig_username}")
        except Exception as e:
            print(f"❌ Ошибка входа: {e}")
            sys.exit(1)
    
    # Публиковать каждый черновик
    for draft_name in drafts_to_publish:
        draft_path = get_draft_path(args.business, draft_name)
        if not draft_path.exists():
            print(f"⚠️ Черновик не найден: {draft_path}")
            continue
        
        caption = read_caption(draft_path)
        images = get_images(draft_path)
        meta = read_meta(draft_path)
        
        print(f"\n{'='*50}")
        print(f"📱 Черновик: {draft_name}")
        print(f"📝 Формат: {meta['format']}")
        print(f"🖼 Изображений: {len(images)}")
        print(f"📝 Подпись: {caption[:100]}...")
        
        if args.dry_run:
            print("🏃 DRY RUN — пропускаем публикацию")
            continue
        
        try:
            if meta["format"] == "album" and len(images) > 1:
                result = publish_album(client, images, caption)
            elif meta["format"] == "reels":
                videos = [f for f in draft_path.iterdir() if f.suffix in {".mp4", ".mov"}]
                if videos:
                    result = publish_reels(client, videos[0], caption)
                else:
                    print("⚠️ Нет видео для Reels, публикуем как фото")
                    result = publish_photo(client, images[0], caption)
            else:
                result = publish_photo(client, images[0], caption)
            
            print(f"✅ Опубликовано! ID: {result.pk}")
            update_queue(args.business, draft_name)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            update_queue(args.business, draft_name, "❌ Ошибка")

if __name__ == "__main__":
    main()
