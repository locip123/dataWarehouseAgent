import httpx
from langchain.messages import AnyMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph

from app.conf.app_config import app_config


llm = ChatOpenAI(
    model=app_config.llm.model_name,
    api_key=app_config.llm.api_key,
    base_url=app_config.llm.base_url,
    use_responses_api=True,
    streaming=True,
    http_client=httpx.Client(trust_env=False),
    http_async_client=httpx.AsyncClient(trust_env=False),
)


def call_llm(state: MessagesState) -> dict[str, list[AnyMessage]]:
    return {"messages": [llm.invoke(state["messages"])]}


workflow = StateGraph(MessagesState)
workflow.add_node("call_llm", call_llm)
workflow.add_edge(START, "call_llm")
workflow.add_edge("call_llm", END)

llm_caller = workflow.compile()
