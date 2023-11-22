class DictError(Exception):
    """Ошибка отсутствия ключевых слов в словаре."""

    def __init__(self, text):
        """Инициализация."""
        self.txt = text


class APIAccessError(Exception):
    """Ошибка доступа к API openai."""

    def __init__(self, text):
        """Инициализация."""
        self.txt = text


class SendMessageError(Exception):
    """Исключение отправки сообщения в Telegram."""

    def __init__(self, text):
        """Инициализация."""
        self.txt = text