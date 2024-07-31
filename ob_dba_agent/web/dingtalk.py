from fastapi import FastAPI, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import requests
import os
import threading
import traceback
import datetime
from typing import Union, List
from typing_extensions import Annotated
from agentuniverse.agent.agent_manager import AgentManager
from ob_dba_agent.web.doc_rag import doc_rag, classify_intention, chat_with_bot
from ob_dba_agent.web.logger import logger
from ob_dba_agent.web.database import SessionLocal
from ob_dba_agent.web.schemas import DingtalkMsg


dingtalk_app = FastAPI()


def handle_dingtalk_msg(query: str, query_dbs: list[str] = ["oceanbase-4.3.1"]) -> str:
    ic = classify_intention(query)
    if ic.intention == "闲聊":
        return chat_with_bot(query)
    else:
        return doc_rag(ic.rewritten, components=query_dbs)


class TextMsg(BaseModel):
    content: str


class RichTextMsg(BaseModel):
    text: Union[str, None] = None
    downloadCode: Union[str, None] = None
    type: Union[str, None] = None


class ContentMsg(BaseModel):
    richText: Union[List[RichTextMsg], None] = None
    downloadCode: Union[str, None] = None


class QueryRequest(BaseModel):
    conversationId: str
    msgId: str
    senderNick: str
    text: Union[TextMsg, None] = None
    content: Union[ContentMsg, None] = None
    msgtype: str
    sessionWebhookExpiredTime: int
    sessionWebhook: str

    conversationTitle: Union[str, None] = None
    senderPlatform: Union[str, None] = None
    atUsers: Union[list[dict], None] = None
    chatbotUserId: Union[str, None] = None
    isAdmin: Union[bool, None] = None
    conversationType: Union[str, None] = None
    createAt: Union[int, None] = None
    senderId: Union[str, None] = None
    isInAtList: Union[bool, None] = None
    robotCode: Union[str, None] = None


DINGTALK_TOKEN = os.getenv("DINGTALK_TOKEN")


def send_msg(
    url: str, session: str, content: str, title: str = None
) -> requests.Response:
    if title is None:
        return requests.post(
            url,
            json={
                "msgtype": "text",
                "text": {"content": content},
            },
            params={"session": session},
        )
    return requests.post(
        url,
        json={
            "msgtype": "markdown",
            "markdown": {
                "title": title,
                "text": content,
            },
        },
        params={"session": session},
    )


@dingtalk_app.post("/miniob")
async def miniob(
    request: QueryRequest, token: Annotated[Union[str, None], Header()] = None
):
    if token is None or token != DINGTALK_TOKEN:
        return JSONResponse(content={"msg": "Unauthorized"}, status_code=401)
    if request.msgtype != "text":
        return JSONResponse(content={"msg": "Invalid request"}, status_code=400)
    if request.msgtype == "text" and request.text is None:
        return JSONResponse(content={"msg": "Invalid request"}, status_code=400)

    query_content = request.text.content
    webhook_splits = request.sessionWebhook.split("?")
    webhook_url, session = webhook_splits[0], webhook_splits[1].split("=")[1]

    def query_and_reply():
        answer = handle_dingtalk_msg(query_content, ["miniob-main"])
        logger.debug(f"[DingTalk] Answer for {query_content} is:\n{answer}")
        send_msg(
            webhook_url,
            session,
            f"@{request.senderNick}，你的提问是: {query_content}\n\n回答如下:\n\n{answer}",
            title="xvx! 回答已生成!",
        )

    threading.Thread(target=query_and_reply).start()

    return {
        "text": {"content": f"x!x @{request.senderNick} 正在查询，请稍候..."},
        "msgtype": "text",
    }


@dingtalk_app.post("/query")
async def query(
    request: QueryRequest, token: Annotated[Union[str, None], Header()] = None
):
    if token is None or token != DINGTALK_TOKEN:
        return JSONResponse(content={"msg": "Unauthorized"}, status_code=401)
    logger.info(request)

    if request.msgtype == "text" and request.text is None:
        return JSONResponse(content={"msg": "Invalid request"}, status_code=400)
    elif request.msgtype in ["picture", "richText"] and (
        request.content is None
        or (request.content.richText is None and request.content.downloadCode is None)
    ):
        return JSONResponse(content={"msg": "Invalid request"}, status_code=400)

    query_content = ""
    if request.msgtype == "text":
        query_content = request.text.content
    elif request.msgtype == "richText":
        query_content = "\n".join(
            list(
                map(
                    lambda x: x.text,
                    filter(lambda x: x.text is not None, request.content.richText),
                )
            )
        )
    elif request.msgtype == "picture":
        pass

    webhook_splits = request.sessionWebhook.split("?")
    webhook_url, session = webhook_splits[0], webhook_splits[1].split("=")[1]

    def query_and_reply():
        with SessionLocal() as db:
            try:
                msg = DingtalkMsg(
                    conversation_id=request.conversationId,
                    text=query_content,
                    sender_nick=request.senderNick,
                    msg_id=request.msgId,
                    conversation_title=request.conversationTitle,
                    created_at=datetime.datetime.now(),
                )
                start = datetime.datetime.now()

                answer = handle_dingtalk_msg(query_content)
                logger.debug(f"[DingTalk] Answer for {query_content} is:\n{answer}")
                msg.answer = answer
                send_msg(
                    webhook_url,
                    session,
                    f"@{request.senderNick}，你的提问是: {query_content}\n\n回答如下:\n\n{answer}",
                    title="xvx! 回答已生成!",
                )
                msg.status = "done"
            except Exception:
                logger.error(traceback.format_exc())
                send_msg(webhook_url, session, f"x_x 查询失败")
                msg.status = "failed"
            finally:
                end = datetime.datetime.now()
                delta = end - start
                msg.cost_seconds = delta.seconds
                db.add(msg)
                db.commit()

    threading.Thread(target=query_and_reply, args=()).start()

    return {
        "text": {"content": f"x!x @{request.senderNick} 正在查询答案..."},
        "msgtype": "text",
    }


if __name__ == "__main__":
    from agentuniverse.base.agentuniverse import AgentUniverse

    AgentUniverse().start()
    print(handle_dingtalk_msg("今天天气怎么样"))
    print(handle_dingtalk_msg("OceanBase 的分布式架构是如何的?"))
