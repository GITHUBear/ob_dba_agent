from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.agent.action.knowledge.knowledge import Knowledge
from agentuniverse.agent.action.knowledge.store.document import Document
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager


def doc_rag(query: str, chat_history: list[dict] = [], **kwargs) -> str:
    print("rag agent", query, chat_history)
    rewritten = kwargs.get("rewritten", query)
    knowledge: Knowledge = KnowledgeManager().get_instance_obj(
        "ob_doc_knowledge"
    )
    chunks: list[Document] = knowledge.query_knowledge(query_str=rewritten)
    length = 0
    for chunk in chunks:
        length += len(chunk.text)

    while length > 5000 and len(chunks) > 0:
        last_chunk = chunks.pop()
        length -= len(last_chunk.text)
        
    documents = "\n".join([chunk.text for chunk in chunks])

    rag_agent: Agent = AgentManager().get_instance_obj("ob_rag_agent")
    output_object: OutputObject = rag_agent.run(
        input=query, 
        document_snippets=documents,
        history=chat_history,
    )
    answer: str = output_object.get_data("output")
    # print("expressing_result:", expressing_result)
    visited = {}
    doc_list = []
    replace_from = "./oceanbase-doc"
    replace_to = "https://github.com/oceanbase/oceanbase-doc/blob/V4.3.1"
    for c in chunks:
        print(c.metadata)
        if c.metadata["doc_name"] in visited:
            continue
        visited[c.metadata["doc_name"]] = True
        doc_list.append(f"- [{c.metadata["doc_name"]}]({c.metadata["doc_url"].replace(replace_from, replace_to)})")
        
    references = "\n具体信息可参考以下文档:\n" + "\n".join(doc_list)
    return answer + references
