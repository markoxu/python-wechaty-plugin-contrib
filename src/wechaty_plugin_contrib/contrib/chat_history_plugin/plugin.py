"""Chat history plugin"""
import os
from typing import Optional, List
from dataclasses import dataclass, field
from wechaty_puppet import MessageType, FileBox  # type: ignore
from wechaty import Wechaty, Message, get_logger  # type: ignore
from wechaty.plugin import WechatyPlugin, WechatyPluginOptions  # type: ignore
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine  # type: ignore
from sqlalchemy.orm import sessionmaker, declarative_base  # type: ignore
from sqlalchemy import (  # type: ignore
    Column,
    Integer,
    VARCHAR,
    Text
)

logger = get_logger('ChatHistoryPlugin')

SUPPORTED_MESSAGE_FILE_TYPES: List[MessageType] = [
    MessageType.MESSAGE_TYPE_ATTACHMENT,
    MessageType.MESSAGE_TYPE_IMAGE,
    MessageType.MESSAGE_TYPE_EMOTICON,
    MessageType.MESSAGE_TYPE_VIDEO,
    MessageType.MESSAGE_TYPE_AUDIO
]

Base = declarative_base()  # type: ignore


class ChatHistory(Base):  # type: ignore
    """ChatHistory"""
    __tablename__ = 'ChatHistory'

    id = Column(Integer, primary_key=True, autoincrement=True)
    msg_id = Column(Integer, default=None)
    filename = Column(Text, default=None)
    text = Column(Text, default=None)
    timestamp = Column(Integer, default=None)
    type = Column(Integer, default=None)
    from_id = Column(VARCHAR(50), default=None)
    room_id = Column(VARCHAR(50), default=None)
    to_id = Column(VARCHAR(50), default=None)
    mention_ids = Column(Text, default=None)


@dataclass
class ChatHistoryPluginOptions(WechatyPluginOptions):
    """
    chat history plugin options
    """
    chat_history_path: str = field(default_factory=str)
    chat_history_database: str = field(default_factory=str)


class ChatHistoryPlugin(WechatyPlugin):
    """chat history plugin"""

    def __init__(self, options: Optional[ChatHistoryPluginOptions] = None):
        super().__init__(options)
        if options is None:
            options = ChatHistoryPluginOptions()
        if not options.chat_history_path:
            self.chat_history_path = os.path.join(os.getcwd(), 'chathistory')
        if not os.path.exists(self.chat_history_path):
            os.makedirs(self.chat_history_path)
        self.chat_history_database = options.chat_history_database \
            or 'sqlite+aiosqlite:///chathistory.db'

    @property
    def name(self) -> str:
        return 'chat-history'

    async def init_plugin(self, wechaty: Wechaty):
        """init plugin"""
        async_engine = create_async_engine(self.chat_history_database)
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def on_message(self, msg: Message):
        """listen message event"""
        async_engine = create_async_engine(self.chat_history_database)
        async_session = sessionmaker(async_engine,
                                     expire_on_commit=False,
                                     class_=AsyncSession)
        async with async_session() as session:
            async with session.begin():
                file_box: FileBox = None
                if msg.type() in SUPPORTED_MESSAGE_FILE_TYPES:
                    file_box = await msg.to_file_box()
                payload = msg.payload
                chathistroy = ChatHistory(
                    msg_id=msg.message_id,
                    filename=file_box.name if file_box else None,
                    text=payload.text if payload.text else None,
                    timestamp=payload.timestamp,
                    type=payload.type,
                    from_id=payload.from_id,
                    room_id=payload.room_id if payload.room_id else None,
                    to_id=payload.to_id if payload.to_id else None,
                    mention_ids=','.join(
                        payload.mention_ids) if payload.mention_ids else None
                )
                session.add(chathistroy)
            await session.commit()
        await async_engine.dispose()

        if msg.type() in SUPPORTED_MESSAGE_FILE_TYPES:
            file_box = await msg.to_file_box()
            if file_box is not None:
                await file_box.to_file(os.path.join(self.chat_history_path, file_box.name))
