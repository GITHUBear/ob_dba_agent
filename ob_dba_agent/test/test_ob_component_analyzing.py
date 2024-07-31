import unittest

from agentuniverse.agent.agent import Agent
from agentuniverse.agent.agent_manager import AgentManager
from agentuniverse.agent.output_object import OutputObject
from agentuniverse.base.agentuniverse import AgentUniverse

import json


class AgentTest(unittest.TestCase):

    def setUp(self) -> None:
        AgentUniverse().start(config_path="../../config/config.toml")

    def test_component_analyzing_agent(self):

        instance: Agent = AgentManager().get_instance_obj(
            "ob_component_analyzing_agent"
        )
        output_object: OutputObject = instance.run(
            input="OCP所在的机器重启了，如何恢复OCP的所有服务？"
        )
        print("output", output_object.to_dict().keys())
        for key in output_object.to_dict().keys():
            print(key, output_object.get_data(key))
        output = json.loads(output_object.get_data("output"))
        print(output)
        print(output.get("components"))


if __name__ == "__main__":
    unittest.main()
