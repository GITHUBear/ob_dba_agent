from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.action.knowledge.knowledge import Knowledge
from agentuniverse.agent.action.knowledge.store.document import Document
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from ob_dba_agent.web.logger import logger

class ClassifyIntentionResult:
    intention: str
    rewritten: str

class DocSearchResult:
    documents: str
    references: str


def classify_intention(query: str, chat_history: list[dict] = []) -> ClassifyIntentionResult:
    guard_agent: Agent = AgentManager().get_instance_obj("ob_dba_guard_agent")
    output_object: OutputObject = guard_agent.run(
        input=query, history=chat_history,
    )
    ic = ClassifyIntentionResult()
    ic.intention = output_object.get_data("type")
    ic.rewritten = output_object.get_data("rewrite")
    return ic


def chat_with_bot(query: str, chat_history: list[dict] = [], documents: str = '') -> str:
    rag_agent: Agent = AgentManager().get_instance_obj("ob_rag_agent")
    output_object: OutputObject = rag_agent.run(
        input=query, 
        document_snippets=documents,
        history=chat_history,
    )
    answer: str = output_object.get_data("output")
    return answer


def doc_search(query: str, chat_history: list[dict] = []) -> DocSearchResult:
    knowledge: Knowledge = KnowledgeManager().get_instance_obj(
        "ob_doc_knowledge"
    )
    chunks: list[Document] = knowledge.query_knowledge(query_str=query)
    length = 0
    for chunk in chunks:
        length += len(chunk.text)

    while length > 5000 and len(chunks) > 0:
        last_chunk = chunks.pop()
        length -= len(last_chunk.text)
    
    res = DocSearchResult()
    res.documents = "\n".join([chunk.text for chunk in chunks])

    visited = {}
    doc_list = []
    replace_from = "./oceanbase-doc"
    replace_to = "https://github.com/oceanbase/oceanbase-doc/blob/V4.3.1"
    for c in chunks:
        if c.metadata["doc_name"] in visited:
            continue
        visited[c.metadata["doc_name"]] = True
        doc_list.append(f"- [{c.metadata["doc_name"]}]({c.metadata["doc_url"].replace(replace_from, replace_to)})")
        
    res.references = "\n具体信息可参考以下文档:\n" + "\n".join(doc_list)
    
    return res


def doc_rag(query: str, chat_history: list[dict] = [], **kwargs) -> str:
    logger.debug("doc rag, [query]: %s [chat history]: %s", query, chat_history)
    rewritten = kwargs.get("rewritten", query)
    
    search_res: DocSearchResult = doc_search(rewritten, chat_history)
    answer = chat_with_bot(query, chat_history, search_res.documents)

    return answer + search_res.references
