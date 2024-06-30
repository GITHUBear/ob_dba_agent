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

        instance: Agent = AgentManager().get_instance_obj('ob_dba_planning_agent')
        output_object: OutputObject = instance.run(input='如何使用OceanBase进行TPCC测试')
        res_info = f"\nPlanning agent execution user result is :\n"
        for index, one_framework in enumerate(output_object.get_data('user')):
            res_info += f"[{index + 1}] {one_framework} \n"
        print(res_info)
        res_info = f"\nPlanning agent execution knowledge result is :\n"
        for index, one_framework in enumerate(output_object.get_data('knowledge')):
            res_info += f"[{index + 1}] {one_framework} \n"
        print(res_info)

if __name__ == '__main__':
    unittest.main()