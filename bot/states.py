from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    """Состояния пользователя для FSM"""
    waiting_for_question = State()
    asking_about_tariff = State()
    asking_about_model = State()