---
description: Запуск рекламной кампании в Google Ads — ключевые слова, объявления, настройки
---

# Запуск рекламной кампании в Google Ads

## Вход

- Прочитай `context.md` в папке бизнеса (продукт, ICP, география)
- Прочитай `brief.md` текущего проекта (цель, бюджет, KPI)
- Если есть `knowledge/icp_*.md` — используй для таргетинга

## Шаг 1: Определить параметры кампании

Уточни у оператора:
1. **Тип кампании:** Search / Display / Performance Max
2. **География:** страны и регионы
3. **Язык аудитории:** 
4. **Бюджет:** дневной и общий
5. **Посадочная страница:** URL
6. **Цель:** конверсии / трафик / awareness

## Шаг 2: Keyword Research

Через веб-поиск и анализ ниши:
1. **Seed keywords** — базовые запросы (5-10)
2. **Long-tail keywords** — длинные запросы с высоким intent (15-25)
3. **Группировка** по ad groups (3-7 групп)
4. **Negative keywords** — минус-слова (10-20)
5. **Match types** — рекомендации по типам соответствия

```markdown
### Ad Group: {название}
Keywords:
- [phrase] "{запрос 1}"
- [exact] [{запрос 2}]

Negative Keywords:
- {слово 1}
```

## Шаг 3: Написать объявления (RSA)

Для каждой Ad Group:
- **Headlines** (15 штук, до 30 символов каждый)
  - 3-5 с ключевым словом
  - 3-5 с УТП/выгодой
  - 3-5 с CTA
- **Descriptions** (4 штуки, до 90 символов)
- **Sitelinks** (4-6 штук)
- **Callouts** (4-6 штук)
- **Structured Snippets**

## Шаг 4: Рекомендации по настройкам

```markdown
## Campaign Settings
- Bidding strategy: {рекомендация}
- Bid adjustments: {devices, demographics, locations}
- Ad schedule: {расписание}
- Ad rotation: Optimize
- Audience signals: {рекомендации}
```

## Шаг 5: Чек-лист запуска

```markdown
## Launch Checklist
- [ ] Landing page: загрузка < 3 сек, mobile-friendly
- [ ] Google Tag / GA4 настроены с целями
- [ ] Conversion tracking установлен
- [ ] Кампания загружена и на review
- [ ] Daily budget установлен
- [ ] Billing подтверждён
- [ ] Уведомления настроены
```

## Шаг 6: Сохранить результат

Файл: `businesses/{business_name}/projects/{project}/assets/google_ads_campaign_{YYYY-MM-DD}.md`

Обнови `log.md` текущего проекта.
