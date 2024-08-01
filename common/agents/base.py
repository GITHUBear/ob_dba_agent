import datetime
import hashlib
import logging

from common.models import get_model
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain.output_parsers.json import parse_json_markdown


class AgentBase:
    def __init__(self, **kwargs):
        self.__prompt: str = kwargs.pop("prompt", "")
        if not self.__prompt or not isinstance(self.__prompt, str):
            raise ValueError("Prompt must be a non-empty string")
        default_name = f"Agent-{hashlib.md5(self.__prompt.encode()).hexdigest()}"
        self.__name: str = kwargs.pop("name", default_name)
        self.logger = logging.getLogger(self.__name)

        log_level = logging.getLevelNamesMapping().get(kwargs.pop("log_level", "DEBUG"))
        self.logger.setLevel(log_level)

        self.model = get_model(**kwargs)

    def __invoke(self, query: str, history: list[BaseMessage] = [], **kwargs) -> str:
        today = str(datetime.datetime.now().date())
        system_msg = SystemMessage(
            self.__prompt.format(
                today=today,
                **kwargs,
            ),
        )
        messages = [system_msg] + history + [HumanMessage(query)]
        self.logger.debug(f"messages: {messages}")
        return self.model.invoke(messages)

    def invoke(self, query: str, history: list[BaseMessage] = [], **kwargs) -> str:
        msg: BaseMessage = self.__invoke(query, history, **kwargs)
        self.logger.debug(f"invoke msg: {msg}")
        return msg.content

    def invoke_json(
        self, query: str, history: list[BaseMessage] = [], **kwargs
    ) -> dict[str, any]:
        msg: BaseMessage = self.__invoke(query, history, **kwargs)
        self.logger.debug(f"invoke_json msg: {msg}")
        return parse_json_markdown(msg.content)
