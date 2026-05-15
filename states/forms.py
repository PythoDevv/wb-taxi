from aiogram.fsm.state import State, StatesGroup


class PromoStates(StatesGroup):
    asking_promo = State()       # "Ha, bor" tanlangan, kod kiritish kutilmoqda
    entering_promo = State()     # Foydalanuvchi kodni yozmoqda


class DriverStates(StatesGroup):
    full_name = State()
    phone = State()
    warning_ack = State()        # Ogohlantirish xabarini tasdiqlash
    passport_front = State()
    passport_back = State()
    license_front = State()
    license_back = State()
    texpassport_front = State()
    texpassport_back = State()
    selfie = State()
    license_card = State()
    car_photos = State()         # 4 ta rasm ketma-ket
    plate_number = State()


class BrandStates(StatesGroup):
    warning_ack = State()
    full_name = State()
    phone = State()
    car_model = State()
    car_year = State()
    car_color = State()
    plate_number = State()


class AdminStates(StatesGroup):
    adding_admin = State()
    removing_admin = State()
    adding_notification_chat = State()
    removing_notification_chat = State()
    waiting_broadcast_post = State()
    exporting_promocode = State()
    searching_user = State()
    searching_application_message = State()
