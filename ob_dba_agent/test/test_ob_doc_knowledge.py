import unittest
from agentuniverse.base.agentuniverse import AgentUniverse
from agentuniverse.agent.action.knowledge.knowledge_manager import KnowledgeManager
from agentuniverse.agent.action.knowledge.knowledge import Knowledge

class ObDocKnowledgeTest(unittest.TestCase):
    def setUp(self) -> None:
        AgentUniverse().start(config_path='../../config/config.toml')

    def test_ob_doc_knowledge_query(self):
        # knowledge.query_knowledge(**query_input)
        knowledge: Knowledge = KnowledgeManager().get_instance_obj("ob_doc_knowledge")
        docs = knowledge.query_knowledge(query_str="OceanBase是什么")
        print(docs)

if __name__ == '__main__':
    unittest.main()