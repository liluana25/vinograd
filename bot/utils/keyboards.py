"""Reusable inline keyboard builders."""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

EVENT_TYPES: dict[str, str] = {
    "planting":       "🌱 Посадка",
    "treatment":      "💊 Обработка",
    "fertilizing":    "🌿 Подкормка",
    "watering":       "💧 Полив",
    "pruning":        "✂️ Обрезка",
    "pinching":       "🤏 Чеканка",
    "suckering":      "🌾 Пасынкование",
    "shoot_norm":     "🌿 Норм. побегами",
    "cluster_norm":   "🍇 Норм. гроздями",
    "disease":        "🐛 Болезни/вредители",
    "flowering":      "🌸 Цветение",
    "ripening":       "🟡 Созревание",
    "harvest":        "🍇 Сбор урожая",
}

EVENT_TYPE_LABELS = EVENT_TYPES  # alias


def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Записать событие", callback_data="menu:event"),
            InlineKeyboardButton("🌿 Мои сорта",        callback_data="menu:varieties"),
        ],
        [
            InlineKeyboardButton("✂️ Черенки",          callback_data="menu:cuttings"),
            InlineKeyboardButton("📊 Аналитика",        callback_data="menu:analytics"),
        ],
        [
            InlineKeyboardButton("🗂 Шаблоны",          callback_data="menu:templates"),
            InlineKeyboardButton("💾 Бэкап",            callback_data="menu:backup"),
        ],
    ])


def event_type_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    items = list(EVENT_TYPES.items())
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(items[i][1], callback_data=f"etype:{items[i][0]}")]
        if i + 1 < len(items):
            row.append(InlineKeyboardButton(items[i + 1][1], callback_data=f"etype:{items[i + 1][0]}"))
        buttons.append(row)
    buttons.append([InlineKeyboardButton("« Отмена", callback_data="menu:cancel")])
    return InlineKeyboardMarkup(buttons)


def varieties_keyboard(varieties: list[dict], callback_prefix: str = "var") -> InlineKeyboardMarkup:
    buttons = []
    for v in varieties:
        buttons.append([InlineKeyboardButton(v["name"], callback_data=f"{callback_prefix}:{v['id']}")])
    buttons.append([InlineKeyboardButton("« Главное меню", callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)


def varieties_multiselect_keyboard(
    varieties: list[dict],
    selected: set[int],
    callback_prefix: str = "tpl_sel",
) -> InlineKeyboardMarkup:
    buttons = []
    for i in range(0, len(varieties), 2):
        row = []
        for v in varieties[i:i + 2]:
            mark = "✅" if v["id"] in selected else "◻️"
            row.append(InlineKeyboardButton(
                f"{mark} {v['name']}", callback_data=f"{callback_prefix}:{v['id']}"
            ))
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton("Выбрать все", callback_data=f"{callback_prefix}:all"),
        InlineKeyboardButton("Снять все",   callback_data=f"{callback_prefix}:none"),
    ])
    buttons.append([
        InlineKeyboardButton("✅ Применить", callback_data=f"{callback_prefix}:confirm"),
        InlineKeyboardButton("« Отмена",    callback_data="menu:cancel"),
    ])
    return InlineKeyboardMarkup(buttons)


def products_keyboard(products: list[dict], callback_prefix: str = "prod") -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        buttons.append([InlineKeyboardButton(p["name"], callback_data=f"{callback_prefix}:{p['id']}")])
    buttons.append([InlineKeyboardButton("➕ Добавить новый", callback_data=f"{callback_prefix}:new")])
    buttons.append([InlineKeyboardButton("« Отмена", callback_data="menu:cancel")])
    return InlineKeyboardMarkup(buttons)


def confirm_keyboard(yes_data: str, no_data: str = "menu:cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да", callback_data=yes_data),
        InlineKeyboardButton("❌ Нет", callback_data=no_data),
    ]])


def skip_cancel_keyboard(skip_data: str = "skip", cancel_data: str = "menu:cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("Пропустить →", callback_data=skip_data),
        InlineKeyboardButton("« Отмена",     callback_data=cancel_data),
    ]])


def back_keyboard(back_data: str = "menu:main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("« Назад", callback_data=back_data)]])


def analytics_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Календарь событий",      callback_data="an:calendar")],
        [InlineKeyboardButton("🌿 История куста",           callback_data="an:bush_history")],
        [InlineKeyboardButton("🌸 Фенология (цветение/созревание)", callback_data="an:phenology")],
        [InlineKeyboardButton("🍇 Урожай по сортам",        callback_data="an:harvest")],
        [InlineKeyboardButton("💊 Обработки по кустам",     callback_data="an:treatments")],
        [InlineKeyboardButton("🧪 Препараты и сроки",       callback_data="an:products")],
        [InlineKeyboardButton("✂️ Статистика черенков",     callback_data="an:cuttings")],
        [InlineKeyboardButton("« Главное меню",             callback_data="menu:main")],
    ])


def cuttings_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✂️ Новая партия черенков",  callback_data="cut:new")],
        [InlineKeyboardButton("📋 Мои партии",             callback_data="cut:list")],
        [InlineKeyboardButton("📊 Статистика за сезон",    callback_data="cut:stats")],
        [InlineKeyboardButton("« Главное меню",            callback_data="menu:main")],
    ])


def varieties_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 Список сортов",          callback_data="var_menu:list")],
        [InlineKeyboardButton("➕ Добавить сорт",           callback_data="var_menu:add")],
        [InlineKeyboardButton("✏️ Переименовать сорт",     callback_data="var_menu:rename")],
        [InlineKeyboardButton("📝 Заметка о сорте",        callback_data="var_menu:note")],
        [InlineKeyboardButton("« Главное меню",            callback_data="menu:main")],
    ])


def templates_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("▶️ Применить шаблон",       callback_data="tpl:apply")],
        [InlineKeyboardButton("➕ Создать шаблон",          callback_data="tpl:new")],
        [InlineKeyboardButton("🗑 Удалить шаблон",          callback_data="tpl:delete")],
        [InlineKeyboardButton("« Главное меню",            callback_data="menu:main")],
    ])


def years_keyboard(years: list[int], callback_prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for y in sorted(years, reverse=True):
        row.append(InlineKeyboardButton(str(y), callback_data=f"{callback_prefix}:{y}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("« Назад", callback_data="menu:analytics")])
    return InlineKeyboardMarkup(buttons)


def months_keyboard(year: int, callback_prefix: str) -> InlineKeyboardMarkup:
    MONTH_NAMES = ["Янв","Фев","Мар","Апр","Май","Июн","Июл","Авг","Сен","Окт","Ноя","Дек"]
    buttons = []
    row = []
    for i, m in enumerate(MONTH_NAMES, start=1):
        row.append(InlineKeyboardButton(m, callback_data=f"{callback_prefix}:{year}:{i}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("« Назад", callback_data="an:calendar")])
    return InlineKeyboardMarkup(buttons)
