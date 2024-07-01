from agentuniverse.agent.agent import Agent
from agentuniverse.agent.input_object import InputObject


class ObDBAPeerAgent(Agent):
    """Peer Agent class."""

    def input_keys(self) -> list[str]:
        """Return the input keys of the Agent."""
        return ['input']

    def output_keys(self) -> list[str]:
        """Return the output keys of the Agent."""
        return ['executing_output', 'expressing_output']

    def parse_input(self, input_object: InputObject, agent_input: dict) -> dict:
        """Agent parameter parsing.

        Args:
            input_object(InputObject): input parameters passed by the user.
            agent_input(dict): agent input preparsed by the agent.
        Returns:
            dict: agent input parsed from `input_object` by the user.
        """
        agent_input['input'] = input_object.get_data('input')
        return agent_input

    def parse_result(self, planner_result: dict) -> dict:
        """Planner result parser.

        Args:
            planner_result(dict): Planner result
        Returns:
            dict: Agent result object.
        """
        return {
            "executing_output": planner_result.get('result')[0].get('executing_result').get_data('executing_result'),
            "expressing_output": planner_result.get('result')[0].get('expressing_result').get_data('output'),
        }
