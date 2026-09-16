"""FSM holatlari."""
from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    full_name = State()
    phone = State()
    username = State()
    receipt = State()
    stage2 = State()
    stage3 = State()
    stage4 = State()


class AdminForm(StatesGroup):
    reject_reason = State()
    broadcast = State()
