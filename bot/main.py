"""Bot entry point — registers all handlers and starts polling."""
from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from bot.config import TELEGRAM_TOKEN, ALLOWED_USER_ID
from bot.database.models import init_db

from bot.handlers import menu, varieties, events, cuttings, templates, analytics, backup
from bot.handlers.events import (
    EV_VARIETY, EV_TYPE, EV_DATE, EV_PRODUCT, EV_PRODUCT_NEW_NAME, EV_WEIGHT, EV_NOTE, EV_PHOTO,
)
from bot.handlers.varieties import (
    VAR_WAITING_NAME, VAR_WAITING_RENAME_PICK, VAR_WAITING_NEW_NAME,
    VAR_WAITING_NOTE_PICK, VAR_WAITING_NOTE_TEXT,
)
from bot.handlers.cuttings import (
    CUT_VARIETY, CUT_DATE, CUT_COUNT, CUT_STORAGE, CUT_PICK, CUT_EDIT_FIELD, CUT_EDIT_VALUE,
)
from bot.handlers.templates import (
    TPL_NEW_NAME, TPL_NEW_TYPE, TPL_NEW_PRODUCT, TPL_NEW_PRODUCT_NEW, TPL_NEW_NOTE,
    TPL_APPLY_PICK, TPL_APPLY_SEL, TPL_APPLY_DATE, TPL_APPLY_NOTE,
    TPL_APPLY_PROD, TPL_APPLY_PROD_NEW, TPL_DELETE_PICK,
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

_ONLY_ME = filters.User(user_id=ALLOWED_USER_ID)
_TEXT = filters.TEXT & ~filters.COMMAND & _ONLY_ME
_PHOTO = filters.PHOTO & _ONLY_ME


def _register_handlers(app: Application) -> None:
    app.add_handler(MessageHandler(~_ONLY_ME, _silent_reject), group=-1)

    # ── Top-level commands ────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",  menu.cmd_start,    filters=_ONLY_ME))
    app.add_handler(CommandHandler("menu",   menu.cmd_menu,     filters=_ONLY_ME))
    app.add_handler(CommandHandler("backup", backup.cmd_backup, filters=_ONLY_ME))

    # ── Variety management conversation ──────────────────────────────────────
    var_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(varieties.cb_variety_add_start,   pattern="^var_menu:add$"),
            CallbackQueryHandler(varieties.cb_variety_rename_start, pattern="^var_menu:rename$"),
            CallbackQueryHandler(varieties.cb_variety_note_start,   pattern="^var_menu:note$"),
        ],
        states={
            VAR_WAITING_NAME: [
                MessageHandler(_TEXT, varieties.receive_variety_name),
                CallbackQueryHandler(varieties.cb_variety_exists_choice, pattern="^var_exist:"),
            ],
            VAR_WAITING_RENAME_PICK: [
                CallbackQueryHandler(varieties.cb_variety_rename_pick, pattern="^var_rename:"),
            ],
            VAR_WAITING_NEW_NAME: [
                MessageHandler(_TEXT, varieties.receive_new_variety_name),
            ],
            VAR_WAITING_NOTE_PICK: [
                CallbackQueryHandler(varieties.cb_variety_note_pick, pattern="^var_note:"),
            ],
            VAR_WAITING_NOTE_TEXT: [
                MessageHandler(_TEXT, varieties.receive_variety_note),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", varieties.cmd_cancel, filters=_ONLY_ME),
            CallbackQueryHandler(menu.cb_cancel, pattern="^menu:cancel$"),
        ],
        per_message=False,
    )
    app.add_handler(var_conv)

    # ── Event logging conversation ────────────────────────────────────────────
    ev_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(events.start_event, pattern="^menu:event$"),
        ],
        states={
            EV_VARIETY: [
                CallbackQueryHandler(events.cb_ev_variety, pattern="^ev_var:"),
                MessageHandler(_TEXT, events.text_ev_variety),
            ],
            EV_TYPE: [
                CallbackQueryHandler(events.cb_ev_type, pattern="^etype:"),
            ],
            EV_DATE: [
                CallbackQueryHandler(events.cb_ev_date, pattern="^ev_date:"),
                MessageHandler(_TEXT, events.text_ev_date),
            ],
            EV_PRODUCT: [
                CallbackQueryHandler(events.cb_ev_product, pattern="^ev_prod:"),
                MessageHandler(_TEXT, events.text_ev_product),
            ],
            EV_PRODUCT_NEW_NAME: [
                MessageHandler(_TEXT, events.receive_new_product_name),
            ],
            EV_WEIGHT: [
                MessageHandler(_TEXT, events.text_ev_weight),
            ],
            EV_NOTE: [
                CallbackQueryHandler(events.cb_ev_skip_note, pattern="^ev_skip_note$"),
                MessageHandler(_TEXT, events.text_ev_note),
            ],
            EV_PHOTO: [
                CallbackQueryHandler(events.cb_ev_skip_photo, pattern="^ev_skip_photo$"),
                MessageHandler(_PHOTO, events.receive_photo),
                MessageHandler(_TEXT, events.cb_ev_skip_photo),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", events.cmd_cancel, filters=_ONLY_ME),
            CallbackQueryHandler(menu.cb_cancel, pattern="^menu:cancel$"),
        ],
        per_message=False,
    )
    app.add_handler(ev_conv)

    # ── Cuttings conversation ─────────────────────────────────────────────────
    cut_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(cuttings.cb_cut_new_start, pattern="^cut:new$"),
            CallbackQueryHandler(cuttings.cb_cut_list,      pattern="^cut:list$"),
            CallbackQueryHandler(cuttings.cb_cut_edit,      pattern="^cut_edit:"),
        ],
        states={
            CUT_VARIETY: [
                CallbackQueryHandler(cuttings.cb_cut_variety, pattern="^cut_var:"),
            ],
            CUT_DATE: [
                CallbackQueryHandler(cuttings.cb_cut_date, pattern="^cut_date:"),
                MessageHandler(_TEXT, cuttings.text_cut_date),
            ],
            CUT_COUNT: [
                MessageHandler(_TEXT, cuttings.text_cut_count),
            ],
            CUT_STORAGE: [
                CallbackQueryHandler(cuttings.cb_cut_skip_storage, pattern="^cut_skip_storage$"),
                MessageHandler(_TEXT, cuttings.text_cut_storage),
            ],
            CUT_PICK: [
                CallbackQueryHandler(cuttings.cb_cut_list_variety, pattern="^cut_list_var:"),
            ],
            CUT_EDIT_FIELD: [
                CallbackQueryHandler(cuttings.cb_cut_edit_field, pattern="^cut_ef:"),
            ],
            CUT_EDIT_VALUE: [
                MessageHandler(_TEXT, cuttings.text_cut_edit_value),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cuttings.cmd_cancel, filters=_ONLY_ME),
            CallbackQueryHandler(menu.cb_cancel, pattern="^menu:cancel$"),
        ],
        per_message=False,
    )
    app.add_handler(cut_conv)

    # ── Templates conversation ────────────────────────────────────────────────
    tpl_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(templates.cb_tpl_new_start,    pattern="^tpl:new$"),
            CallbackQueryHandler(templates.cb_tpl_apply_start,  pattern="^tpl:apply$"),
            CallbackQueryHandler(templates.cb_tpl_delete_start, pattern="^tpl:delete$"),
        ],
        states={
            TPL_NEW_NAME: [
                MessageHandler(_TEXT, templates.text_tpl_new_name),
            ],
            TPL_NEW_TYPE: [
                CallbackQueryHandler(templates.cb_tpl_new_type, pattern="^etype:"),
            ],
            TPL_NEW_PRODUCT: [
                CallbackQueryHandler(templates.cb_tpl_new_product, pattern="^tpl_prod:"),
            ],
            TPL_NEW_PRODUCT_NEW: [
                MessageHandler(_TEXT, templates.receive_tpl_new_product),
            ],
            TPL_NEW_NOTE: [
                CallbackQueryHandler(templates.cb_tpl_skip_note, pattern="^tpl_skip_note$"),
                MessageHandler(_TEXT, templates.text_tpl_note),
            ],
            TPL_APPLY_PICK: [
                CallbackQueryHandler(templates.cb_tpl_apply_pick, pattern="^tpl_pick:"),
            ],
            TPL_APPLY_SEL: [
                CallbackQueryHandler(templates.cb_tpl_sel, pattern="^tpl_sel:"),
            ],
            TPL_APPLY_DATE: [
                CallbackQueryHandler(templates.cb_tpl_apply_date, pattern="^tpl_date:"),
                MessageHandler(_TEXT, templates.text_tpl_apply_date),
            ],
            TPL_APPLY_PROD: [
                CallbackQueryHandler(templates.cb_tpl_use_default_prod, pattern="^tpl_use_default_prod$"),
                CallbackQueryHandler(templates.cb_tpl_change_prod,      pattern="^tpl_change_prod$"),
                CallbackQueryHandler(templates.cb_tpl_ap_prod,          pattern="^tpl_ap_prod:"),
            ],
            TPL_APPLY_PROD_NEW: [
                MessageHandler(_TEXT, templates.receive_tpl_ap_prod_new),
            ],
            TPL_APPLY_NOTE: [
                CallbackQueryHandler(templates.cb_tpl_use_default_note, pattern="^tpl_use_default_note$"),
                CallbackQueryHandler(templates.cb_tpl_skip_note_apply,  pattern="^tpl_skip_note$"),
                MessageHandler(_TEXT, templates.text_tpl_apply_note),
            ],
            TPL_DELETE_PICK: [
                CallbackQueryHandler(templates.cb_tpl_delete_confirm, pattern="^tpl_del_pick:"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", templates.cmd_cancel, filters=_ONLY_ME),
            CallbackQueryHandler(menu.cb_cancel, pattern="^menu:cancel$"),
        ],
        per_message=False,
    )
    app.add_handler(tpl_conv)

    # ── Standalone callback handlers ──────────────────────────────────────────

    app.add_handler(CallbackQueryHandler(menu.cb_main_menu,             pattern="^menu:main$"))
    app.add_handler(CallbackQueryHandler(menu.cb_cancel,                pattern="^menu:cancel$"))
    app.add_handler(CallbackQueryHandler(backup.cmd_backup,             pattern="^menu:backup$"))

    app.add_handler(CallbackQueryHandler(varieties.show_varieties_menu, pattern="^menu:varieties$"))
    app.add_handler(CallbackQueryHandler(varieties.cb_varieties_list,   pattern="^var_menu:list$"))

    app.add_handler(CallbackQueryHandler(cuttings.show_cuttings_menu,   pattern="^menu:cuttings$"))
    app.add_handler(CallbackQueryHandler(cuttings.cb_cut_stats,         pattern="^cut:stats$"))
    app.add_handler(CallbackQueryHandler(cuttings.cb_cut_view,          pattern="^cut_view:"))
    app.add_handler(CallbackQueryHandler(cuttings.cb_cut_delete,        pattern="^cut_del:"))

    app.add_handler(CallbackQueryHandler(templates.show_templates_menu, pattern="^menu:templates$"))

    app.add_handler(CallbackQueryHandler(analytics.show_analytics_menu, pattern="^menu:analytics$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_calendar,      pattern="^an:calendar$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_cal_year,      pattern="^an_cal_year:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_cal_month,     pattern="^an_cal_month:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_bush_history,  pattern="^an:bush_history$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_hist_var,      pattern="^an_hist_var:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_phenology,     pattern="^an:phenology$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_phen_year,     pattern="^an_phen_year:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_harvest,       pattern="^an:harvest$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_harv_year,     pattern="^an_harv_year:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_harv_variety,  pattern="^an_harv_variety$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_harv_var,      pattern="^an_harv_var:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_treatments,    pattern="^an:treatments$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_treat_year,    pattern="^an_treat_year:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_products,      pattern="^an:products$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_prod_year,     pattern="^an_prod_year:"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_cuttings,      pattern="^an:cuttings$"))
    app.add_handler(CallbackQueryHandler(analytics.cb_an_cut_year,      pattern="^an_cut_year:"))


async def _silent_reject(update: Update, ctx) -> None:
    pass


async def _post_init(app: Application) -> None:
    await init_db()
    logger.info("Database initialised.")


def main() -> None:
    app = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .post_init(_post_init)
        .build()
    )
    _register_handlers(app)
    logger.info("Starting bot...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
