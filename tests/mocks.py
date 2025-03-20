from typing import Optional
from telegram import User
from bot import askers


class FakeGPT:
    def __init__(self, error: Optional[Exception] = None):
        self.error = error
        self.prompt = None
        self.question = None
        self.history = None

    async def ask(self, prompt: str, question: str, history: list) -> str:
        self.prompt = prompt
        self.question = question
        self.history = history
        if self.error:
            raise self.error
        return question


class FakeDalle:
    def __init__(self, error: Optional[Exception] = None):
        self.error = error
        self.prompt = None
        self.size = None

    async def imagine(self, prompt: str, size: str) -> str:
        self.prompt = prompt
        self.size = size
        if self.error:
            raise self.error
        return "image"


class FakeFile:
    def __init__(self, file_id: str) -> None:
        self.file_id = file_id

    async def download_as_bytearray(self, buf=None, **kwargs) -> bytearray:
        return bytearray(b"file content")


class FakeBot:
    def __init__(self, username: str) -> None:
        self.user = User(
            id=42,
            first_name=username,
            is_bot=True,
            username=username,
            can_read_all_group_messages=True,
        )
        self.text = ""

    @property
    def username(self) -> str:
        return self.user.username

    @property
    def name(self) -> str:
        return f"@{self.username}"

    @property
    def can_read_all_group_messages(self) -> bool:
        return self.user.can_read_all_group_messages

    async def get_file(self, file_id, **kwargs):
        return FakeFile(file_id)

    async def send_chat_action(self, **kwargs) -> None:
        pass

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        self.text = text

    async def send_document(
        self, chat_id: int, document: object, caption: str, filename: str, **kwargs
    ) -> None:
        self.text = f"{caption}: {filename}"

    async def send_photo(self, chat_id: int, photo: str, caption: str = None, **kwargs) -> None:
        self.text = f"{caption}: {photo}"

    async def get_me(self, **kwargs) -> User:
        return self.user


class FakeApplication:
    def __init__(self, bot: FakeBot) -> None:
        self.chat_data = {1: {}}
        self.user_data = {1: {}}
        self.bot = bot


def mock_text_asker(ai: FakeGPT) -> None:
    mock_init = lambda asker, _: setattr(asker, "model", ai)
    askers.TextAsker.__init__ = mock_init
