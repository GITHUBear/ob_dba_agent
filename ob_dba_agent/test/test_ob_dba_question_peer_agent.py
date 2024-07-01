import unittest

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.base.agentuniverse import AgentUniverse

class PlanningAgentTest(unittest.TestCase):
    """Test cases for the planning agent"""

    def setUp(self) -> None:
        AgentUniverse().start(config_path='../../config/config.toml')

    def test_planning_agent(self):
        """Test demo planning agent."""
        history = []
        first_question = None
        # 如何使用OceanBase进行TPCC测试
        while True:
            user_input = input(">> ")
            if first_question is None:
                first_question = user_input
                question_agent: Agent = AgentManager().get_instance_obj('ob_dba_questioning_agent')
                output_object: OutputObject = question_agent.run(input=first_question, chat_history=history)
                res_info = "Questioning agent result is :\n"
                for index, one_framework in enumerate(output_object.get_data('questions')):
                    res_info += f"[{index + 1}] {one_framework} \n"
                print(res_info)
                history.append({
                    'content': user_input,
                    'type': 'human',
                })
                history.append({
                    'content': res_info,
                    'type': 'ai',
                })
            else:
                peer_agent: Agent = AgentManager().get_instance_obj('ob_dba_peer_agent')
                output_object: OutputObject = peer_agent.run(input=user_input, chat_history=history)
                # res_info = f"\nPlanning agent result is :\n"
                # for index, one_framework in enumerate(output_object.get_data('framework')):
                #     res_info += f"[{index + 1}] {one_framework} \n"
                print(output_object)

if __name__ == '__main__':
    unittest.main()