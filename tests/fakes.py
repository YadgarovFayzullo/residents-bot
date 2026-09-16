"""Telegram obyektlarining soxta (mock) versiyalari — handlerlarni to'g'ridan-to'g'ri sinash uchun."""
from __future__ import annotations
from types import SimpleNamespace

OUT: list[tuple[str, str]] = []   # (kimga, matn)


class FakeUser:
    def __init__(self, uid=1001, username="aliuz", first_name="Ali"):
        self.id = uid
        self.username = username
        self.first_name = first_name


class FakeChat:
    def __init__(self, cid=1001, ctype="private"):
        self.id = cid
        self.type = ctype


class FakeMessage:
    def __init__(self, text=None, user=None, photo=None, document=None,
                 contact=None, caption=None, chat=None):
        self.text = text
        self.caption = caption
        self.from_user = user or FakeUser()
        self.chat = chat or FakeChat(self.from_user.id)
        self.photo = photo
        self.document = document
        self.contact = contact
        self.message_id = 500
        self.replies: list[dict] = []

    async def answer(self, text, reply_markup=None, **kw):
        self.replies.append({"text": text, "markup": reply_markup})
        OUT.append((f"user:{self.chat.id}", text))
        return FakeMessage(text=text, user=self.from_user)

    async def edit_text(self, text, reply_markup=None, **kw):
        OUT.append((f"edit:{self.chat.id}", text))
        self.text = text

    async def edit_caption(self, caption, reply_markup=None, **kw):
        OUT.append((f"edit:{self.chat.id}", caption))
        self.caption = caption

    async def edit_reply_markup(self, reply_markup=None, **kw):
        pass

    async def send_copy(self, chat_id, **kw):
        OUT.append((f"user:{chat_id}", self.text or "<media>"))


class FakeCallback:
    def __init__(self, data, user=None, message=None):
        self.data = data
        self.from_user = user or FakeUser()
        self.message = message or FakeMessage(user=self.from_user)
        self.alerts: list[str] = []

    async def answer(self, text=None, show_alert=False, **kw):
        if text:
            self.alerts.append(text)
            OUT.append((f"alert:{self.from_user.id}", text))


class FakePhoto:
    def __init__(self, file_id="PHOTO_123"):
        self.file_id = file_id


class FakeDocument:
    def __init__(self, file_id="DOC_123", mime_type="application/pdf"):
        self.file_id = file_id
        self.mime_type = mime_type


class FakeContact:
    def __init__(self, phone="+998901234567", user_id=1001):
        self.phone_number = phone
        self.user_id = user_id


class FakeState:
    """FSMContext o'rnini bosuvchi oddiy holat saqlagich."""
    def __init__(self):
        self._state = None
        self._data: dict = {}

    async def set_state(self, state):
        self._state = state

    async def get_state(self):
        return self._state

    async def clear(self):
        self._state = None
        self._data = {}

    async def update_data(self, **kw):
        self._data.update(kw)
        return self._data

    async def get_data(self):
        return dict(self._data)


class FakeBot:
    """Adminlarga va foydalanuvchilarga yuborilgan xabarlarni yozib boradi."""
    def __init__(self, invite_ok=True):
        self.sent: list[tuple[int, str]] = []
        self.edits: list[tuple[int, int, str]] = []
        self.deleted: list[tuple[int, int]] = []
        self.invite_ok = invite_ok
        self.invites: list[str] = []
        self.invite_calls: list[dict] = []

    async def send_message(self, chat_id, text, reply_markup=None, **kw):
        self.sent.append((chat_id, text))
        OUT.append((f"bot->{chat_id}", text))
        return self._sent_msg()

    async def delete_message(self, chat_id, message_id, **kw):
        self.deleted.append((chat_id, message_id))
        OUT.append((f"del->{chat_id}", str(message_id)))

    async def edit_message_text(self, text, chat_id=None, message_id=None, **kw):
        self.edits.append((chat_id, message_id, text))
        OUT.append((f"edit->{chat_id}", text))
        return SimpleNamespace(message_id=message_id)

    async def send_photo(self, chat_id, file_id, caption=None, reply_markup=None, **kw):
        self.sent.append((chat_id, f"[PHOTO] {caption}"))
        OUT.append((f"bot->{chat_id}", f"[PHOTO] {caption}"))
        return self._sent_msg()

    async def send_document(self, chat_id, file_id, caption=None, reply_markup=None, **kw):
        self.sent.append((chat_id, f"[DOC] {caption}"))
        OUT.append((f"bot->{chat_id}", f"[DOC] {caption}"))
        return self._sent_msg()

    def _sent_msg(self):
        """Telegram javobi — arxiv havolasi uchun message_id kerak."""
        self._msg_no = getattr(self, "_msg_no", 900) + 1
        return SimpleNamespace(message_id=self._msg_no)

    async def create_chat_invite_link(self, chat_id, name=None, member_limit=None,
                                      expire_date=None, **kw):
        if not self.invite_ok:
            raise RuntimeError("bot guruhda admin emas")
        link = f"https://t.me/+FAKE{len(self.invites)}"
        self.invites.append(link)
        self.invite_calls.append({"chat_id": chat_id, "name": name,
                                  "member_limit": member_limit,
                                  "expire_date": expire_date})

        class L:
            invite_link = link
        return L()


class FakeSheets:
    """Sheets o'rniga — yozuvlarni xotirada saqlaydi."""
    def __init__(self, enabled=True, mode="webhook"):
        self.enabled = enabled
        self.mode = mode if enabled else "off"
        self.rows: dict[int, dict] = {}
        self.calls = 0
        self.last_error = None

    async def upsert(self, user):
        self.calls += 1
        self.rows[user["user_id"]] = dict(user)
        return len(self.rows) + 1

    async def check(self):
        return self.enabled, "soxta jadval"


class _Obj:
    """Atributlarni erkin o'rnatish uchun oddiy konteyner."""
    def __init__(self, **kw):
        self.__dict__.update(kw)


class FakeChatMemberUpdated:
    """my_chat_member update'i."""
    def __init__(self, chat_id=-100500, title="Yopiq guruh", ctype="supergroup",
                 status="administrator", can_invite=True):
        self.chat = _Obj(id=chat_id, type=ctype, title=title)
        self.new_chat_member = _Obj(status=status, can_invite_users=can_invite)
