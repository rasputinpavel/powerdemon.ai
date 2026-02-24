#!/bin/bash
# PowerDemon.AI — Cron-задачи для автоматического сбора аналитики
#
# УСТАНОВКА:
# 1. Открой crontab:
#    crontab -e
#
# 2. Добавь строки ниже:
#
# ━━━ Ежедневный сбор статистики Яндекс.Директ (8:00 по Москве) ━━━
# 0 8 * * * cd /Users/pavelrasputin/Desktop/Antygravity && python3 scripts/yandex_direct_stats.py --business netashi >> /tmp/powerdemon_cron.log 2>&1
#
# ━━━ Ежедневный сбор Яндекс.Метрики (8:05 по Москве) ━━━
# 5 8 * * * cd /Users/pavelrasputin/Desktop/Antygravity && python3 scripts/yandex_metrica_stats.py --business netashi >> /tmp/powerdemon_cron.log 2>&1
#
# ━━━ Еженедельный полный отчёт (понедельник 9:00) ━━━
# 0 9 * * 1 cd /Users/pavelrasputin/Desktop/Antygravity && python3 scripts/yandex_direct_stats.py --business netashi --days 7 >> /tmp/powerdemon_cron.log 2>&1
# 5 9 * * 1 cd /Users/pavelrasputin/Desktop/Antygravity && python3 scripts/yandex_metrica_stats.py --business netashi --days 7 >> /tmp/powerdemon_cron.log 2>&1
#
# ━━━ Авто-коммит отчётов в git (каждый день 23:00) ━━━
# 0 23 * * * cd /Users/pavelrasputin/Desktop/Antygravity && git add -A && git commit -m "📊 Auto: daily analytics" && git push >> /tmp/powerdemon_cron.log 2>&1
#
# ПРОВЕРКА:
# crontab -l          — посмотреть текущие задачи
# tail -f /tmp/powerdemon_cron.log  — смотреть логи
#
# ВАЖНО: на macOS нужно дать разрешение на cron в:
# Системные настройки → Конфиденциальность → Полный доступ к диску → cron
