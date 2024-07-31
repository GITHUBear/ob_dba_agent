from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.action.knowledge.knowledge import Knowledge
from agentuniverse.agent.action.knowledge.store.document import Document
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from ob_dba_agent.web.logger import logger
import json
from typing import Callable

db_store = "../../DB"

import os

supported: list[str] = []
for name in os.listdir(db_store):
    supported.append((name.replace(".db", "")))


class ClassifyIntentionResult:
    intention: str
    rewritten: str


class DocSearchResult:
    documents: str
    references: str


def classify_intention(
    query: str, chat_history: list[dict] = []
) -> ClassifyIntentionResult:
    guard_agent: Agent = AgentManager().get_instance_obj("ob_dba_guard_agent")
    output_object: OutputObject = guard_agent.run(
        input=query,
        history=chat_history,
    )
    ic = ClassifyIntentionResult()
    ic.intention = output_object.get_data("type")
    ic.rewritten = output_object.get_data("rewrite")
    return ic


def chat_with_bot(
    query: str, chat_history: list[dict] = [], documents: str = ""
) -> str:
    rag_agent: Agent = AgentManager().get_instance_obj("ob_rag_agent")
    output_object: OutputObject = rag_agent.run(
        input=query,
        document_snippets=documents,
        history=chat_history,
    )
    answer: str = output_object.get_data("output")
    logger.debug(f"chat_with_bot: {answer}")
    return answer


replace_bases = {
    "./oceanbase-doc": "https://github.com/oceanbase/oceanbase-doc/blob/V",
    "./ocp-doc": "https://github.com/oceanbase/ocp-doc/blob/V",
    "./obd-doc": "https://github.com/oceanbase/ocp-doc/blob/V",
    "./miniob": "https://github.com/oceanbase/ocp-doc/blob/"
}

comp_doc_bases = {
    "oceanbase": "./oceanbase-doc",
    "ocp": "./ocp-doc",
    "obd": "./obd-doc",
    "miniob": "./miniob",
}


def get_url_replacer(components: list[str]) -> Callable[[str], str]:
    pairs = []
    for comp in components:
        name, version = comp.split("-")
        if name not in comp_doc_bases:
            continue
        replace_from = comp_doc_bases[name]
        replace_to = replace_bases[replace_from] + version
        pairs.append((replace_from, replace_to))

    def replace_url(doc_url: str) -> str:
        new_url = doc_url
        for replace_from, replace_to in pairs:
            new_url = new_url.replace(replace_from, replace_to)
        return new_url

    return replace_url


def doc_search(query: str, chat_history: list[dict] = [], **kwargs) -> DocSearchResult:
    db_names = kwargs.get("supported_components", ["oceanbase-4.3.1"])
    if len(db_names) > 1:    
        analyzing_agent: Agent = AgentManager().get_instance_obj(
            "ob_component_analyzing_agent"
        )
        analyzing_output: OutputObject = analyzing_agent.run(input=query, **kwargs)
        for key in analyzing_output.to_dict().keys():
            logger.debug(f"key: {key}, value: {analyzing_output.get_data(key)}")

        output_json_str: str = analyzing_output.get_data("output", "{{}}")
        # The output of LLM is probably ```json{...}```
        output_json_str = output_json_str.replace("```json", "").replace("```", "")
        output_json: dict = json.loads(output_json_str)
        db_names: list[str] = output_json.get("components", [])
        oceanbase_version = output_json.get("oceanbase", "4.3.1")

        if not any("oceanbase" in db_name for db_name in db_names):
            db_names.append(f"oceanbase-{oceanbase_version}")

    logger.debug(f"db_names: {db_names}")

    length_limit = kwargs.get("length_limit", 5000)
    knowledge: Knowledge = KnowledgeManager().get_instance_obj("ob_doc_knowledge")
    chunks: list[Document] = knowledge.query_knowledge(
        query_str=query, db_names=db_names
    )
    length = 0
    for chunk in chunks:
        length += len(chunk.text)

    while length > length_limit and len(chunks) > 0:
        last_chunk = chunks.pop()
        length -= len(last_chunk.text)

    res = DocSearchResult()
    res.documents = "\n".join([chunk.text for chunk in chunks])

    visited = {}
    doc_list = []
    replacer = get_url_replacer(db_names)
    for c in chunks:
        if c.metadata["doc_name"] in visited:
            continue
        visited[c.metadata["doc_name"]] = True
        doc_list.append(
            f"- [{c.metadata['doc_name']}]({replacer(c.metadata['doc_url'])})"
        )

    if len(doc_list) > 0:
        res.references = "\n\n具体信息可参考以下文档:\n" + "\n".join(doc_list)
    else:
        res.references = ""

    return res


def doc_rag(query: str, chat_history: list[dict] = [], **kwargs) -> str:
    components = kwargs.get("components", supported)
    logger.debug("doc rag, [query]: %s [chat history]: %s", query, chat_history)
    rewritten = kwargs.get("rewritten", query)

    search_res: DocSearchResult = doc_search(
        rewritten, chat_history, supported_components=components, **kwargs
    )
    logger.debug(f"search_res.documents: {search_res.documents}")
    answer = chat_with_bot(query, chat_history, search_res.documents)

    return answer + search_res.references


if __name__ == "__main__":
    from agentuniverse.base.agentuniverse import AgentUniverse

    AgentUniverse().start()
    print(doc_rag("OCP所在的机器重启了，如何恢复OCP的所有服务？"))
    # print(doc_rag("oceanbase社区版本V4.2.1， OCP进程死掉，无法重启"))
    # print(doc_rag("当某个普通租户的memstore使用达到闯值后，选择合并或者转储的依据是什么？"))
