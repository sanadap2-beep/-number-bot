"""دعم فني تفاعلي عبر نظام تذاكر داخل البوت."""
from html import escape

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import desc, select

from database.models import (
    SupportTicket,
    SupportTicketStatus,
    User,
)
from keyboards.main_menu import back_to_main_kb
from keyboards.support import (
    admin_ticket_kb,
    support_cancel_kb,
    support_menu_kb,
    support_ticket_view_kb,
    support_tickets_kb,
)
from services.notification_service import NotificationService
from services.settings_service import SettingsService
from states.states import SupportTicketStates

router = Router(name="support")

_STATUS_LABELS = {
    SupportTicketStatus.OPEN: "🟢 مفتوحة",
    SupportTicketStatus.IN_PROGRESS: "🔄 قيد المتابعة",
    SupportTicketStatus.RESOLVED: "✅ محلولة",
    SupportTicketStatus.CLOSED: "⚪ مغلقة",
}


def _status_label(status) -> str:
    return _STATUS_LABELS.get(
        status, getattr(status, "value", str(status))
    )


@router.message(F.text == "🛠 الدعم الفني")
async def support_handler(message: Message):
    await _send_support(message)


@router.callback_query(F.data == "menu:support")
async def support_handler_cb(callback: CallbackQuery):
    await callback.answer()
    await _send_support(callback.message)


async def _send_support(message: Message):
    support_username = await SettingsService.get(
        "support_username", "@support"
    )
    await message.answer(
        "🛠 <b>الدعم الفني</b>\n\n"
        "يمكنك فتح تذكرة وسيقوم الفريق بمتابعتها من داخل البوت، "
        "أو التواصل المباشر مع الدعم:\n"
        f"{escape(support_username or '@support')}\n\n"
        "⏰ أوقات الاستجابة: خلال 24 ساعة",
        reply_markup=support_menu_kb(),
    )


@router.callback_query(F.data == "support:new")
async def support_new(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_text(
        "📝 <b>فتح تذكرة دعم</b>\n\n"
        "اكتب مشكلتك أو استفسارك بالتفصيل في رسالة واحدة "
        "(حتى 2000 حرف):",
        reply_markup=support_cancel_kb(),
    )
    await state.set_state(SupportTicketStates.waiting_message)


@router.message(SupportTicketStates.waiting_message)
async def support_message_received(
    message: Message,
    state: FSMContext,
    session,
    db_user: User,
    bot,
):
    ticket_message = (message.text or "").strip()
    if len(ticket_message) < 5:
        await message.answer("⚠️ اكتب تفاصيل أكثر عن المشكلة.")
        return
    if len(ticket_message) > 2000:
        await message.answer("⚠️ الحد الأقصى للتذكرة 2000 حرف.")
        return

    subject = ticket_message.splitlines()[0][:128]
    ticket = SupportTicket(
        user_id=db_user.id,
        subject=subject or "طلب دعم",
        message=ticket_message,
        status=SupportTicketStatus.OPEN,
    )
    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)

    admin_text = (
        "🎫 <b>تذكرة دعم جديدة</b>\n\n"
        f"🆔 التذكرة: <b>#{ticket.id}</b>\n"
        f"👤 المستخدم: <code>{db_user.telegram_id}</code> "
        f"(@{escape(db_user.username or '-')})\n"
        f"📝 العنوان: <b>{escape(subject)}</b>\n\n"
        f"{escape(ticket_message)}"
    )
    await NotificationService(bot).notify_admin(
        admin_text,
        reply_markup=admin_ticket_kb(ticket.id, "open"),
    )

    await message.answer(
        "✅ <b>تم فتح تذكرة الدعم</b>\n\n"
        f"رقم التذكرة: <code>#{ticket.id}</code>\n"
        "سيصلك الرد هنا عند متابعته من فريق الدعم.",
        reply_markup=back_to_main_kb(),
    )
    await state.clear()


@router.callback_query(F.data == "support:list")
async def support_list(
    callback: CallbackQuery,
    session,
    db_user: User,
):
    result = await session.execute(
        select(SupportTicket)
        .where(SupportTicket.user_id == db_user.id)
        .order_by(desc(SupportTicket.created_at))
        .limit(20)
    )
    tickets = list(result.scalars().all())
    await callback.answer()
    if not tickets:
        await callback.message.edit_text(
            "📋 لا توجد لديك تذاكر دعم بعد.",
            reply_markup=support_menu_kb(),
        )
        return

    lines = ["📋 <b>تذاكري</b>\n"]
    for ticket in tickets:
        lines.append(
            f"#{ticket.id} · {_status_label(ticket.status)} · "
            f"{escape(ticket.subject[:60])}"
        )
    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=support_tickets_kb(tickets),
    )


@router.callback_query(F.data.startswith("support:ticket:"))
async def support_ticket_view(
    callback: CallbackQuery,
    session,
    db_user: User,
):
    ticket_id = int(callback.data.split(":")[2])
    result = await session.execute(
        select(SupportTicket).where(
            SupportTicket.id == ticket_id,
            SupportTicket.user_id == db_user.id,
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        await callback.answer("⚠️ التذكرة غير موجودة.", show_alert=True)
        return

    text = (
        f"🎫 <b>التذكرة #{ticket.id}</b>\n\n"
        f"📊 الحالة: {_status_label(ticket.status)}\n"
        f"📝 العنوان: <b>{escape(ticket.subject)}</b>\n"
        f"📅 التاريخ: {ticket.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"<b>رسالتك:</b>\n{escape(ticket.message)}"
    )
    if ticket.admin_reply:
        text += f"\n\n<b>رد الدعم:</b>\n{escape(ticket.admin_reply)}"

    await callback.message.edit_text(
        text,
        reply_markup=support_ticket_view_kb(),
    )
    await callback.answer()
