import getpass
import os

if "API_KEY" not in os.environ:
    os.environ["API_KEY"] = getpass.getpass("API_KEY: ")

from langchain_openai import ChatOpenAI


def get_model(**kwargs) -> ChatOpenAI:
    model = ChatOpenAI(
        model="qwen-plus",
        temperature=0.3,
        max_tokens=2000,
        api_key=os.environ["API_KEY"],
        **kwargs,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    return model


if __name__ == "__main__":
    from langchain_core.messages import HumanMessage

    #
    # content='你好！我可以帮助你执行许多基于语言的任务，例如回答问题、提供定义、解释和建议、生成文本、总结文档、分析情绪、开发算法、编写代码等等。如果你有具体的问题或需要帮助的地方，随时告诉我！'
    # response_metadata={'token_usage': {'completion_tokens': 50, 'prompt_tokens': 14, 'total_tokens': 64}, 'model_name': 'qwen-plus', 'system_fingerprint': None, 'finish_reason': 'stop', 'logprobs': None}
    # id='run-fc815a32-818e-41ae-aec5-a27195a33f3d-0'
    #
    model = get_model()
    print(model.invoke([HumanMessage(content="你好，请问你能做什么?")]))
