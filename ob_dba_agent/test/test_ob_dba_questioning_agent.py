import unittest

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.base.agentuniverse import AgentUniverse


class QuestioningAgentTest(unittest.TestCase):
    """Test cases for the questioning agent"""

    def setUp(self) -> None:
        AgentUniverse().start(config_path='../../config/config.toml')

    def test_questioning_agent(self):
        """Test demo questioning agent."""

        instance: Agent = AgentManager().get_instance_obj('ob_dba_questioning_agent')
        complete = False
        history = []
        first_question = None
        while not complete:
            user_input = input(">> ")
            if first_question is None:
                first_question = user_input
            output_object: OutputObject = instance.run(input=first_question, chat_history=history)

            complete = output_object.get_data('complete')
            res_info = ""
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
            print(history)

if __name__ == '__main__':
    unittest.main()