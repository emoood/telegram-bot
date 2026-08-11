import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from tavily import TavilyClient
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
load_dotenv()
from db import get_job, set_job, get_history, save_message, init_db
init_db()


llm = ChatGroq(model="llama-3.3-70b-versatile")
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


class State(TypedDict):
    messages: Annotated[list, add_messages]

def research_node(state: State, config):
    raw_content = state["messages"][-1].content

    #content can be a plain string or a list of content blocks
    if isinstance(raw_content, list):
        user_message = " ".join(
            block["text"] for block in raw_content if isinstance(block, dict) and "text" in block
        )
    else:
        user_message = raw_content

    user_id = config["configurable"]["thread_id"]
    save_message(user_id, "user", user_message)
    job = get_job(user_id)


    if job is None and len(state["messages"]) == 1:
        return {"messages": [{"role": "assistant", "content": "Welcome! What's your job or role? Once I have that, you can send me any topic and I'll research it for you."}]}

    if job is None:
        extract_prompt = f"""Extract just the job title or role from this message: "{user_message}"
Reply with only the job title, nothing else. For example if they say "I'm a software developer at google" reply "software developer"."""
        extracted = llm.invoke(extract_prompt, max_tokens=20)
        clean_job = extracted.content.strip()
        set_job(user_id, clean_job)
        return {"messages": [{"role": "assistant", "content": f"Got it, saved your job as: {clean_job}. Now send me a topic for research."}]}


    #checking if something is small talk
    classify_prompt = f"""Is this message small talk or a real question/topic to research?

Message: "{user_message}"

Reply with only one word: "small_talk" or "topic\""""
    
    classification = llm.invoke(classify_prompt, max_tokens=10)

    if "small_talk" in classification.content.lower():

        small_talk_prompt = f"""The user just said: "{user_message}"
        
        Reply naturally, like a normal chat response to this message."""

        response = llm.invoke(small_talk_prompt, max_tokens=50)
        return {"messages": [{"role": "assistant", "content": response.content}]}

    
    topic = user_message
    results = tavily.search(query=topic, max_results=5)
    sources = "\n\n".join(
        f"{r['title']}\n{r['content']}" for r in results["results"]
    )

    history_rows = get_history(user_id)

#     history = "\n".join(f"{role}: {content}" for role, content in history_rows)

#     prompt = f"""You are a research assistant having a conversation. The user's job is: {job}
#  Recent conversation history:
# {history}
# Based on the sources below, respond to the user's latest message: {topic}
# Match the format they asked for, if they asked for a list of things, give exactly that in a numbered list. If they asked a question, answer it directly. Don't force everything into a "report" structure with headers and multiple sections unless that's what they asked.
# If this is a followup question referring to something said earlier, use the conversation history above to understand what they mean, instead of treating it as a new topic.
# Make sure your response is made for someone in this job. Keep it concise and aim for under 200 words unless the request asked for a specific length.
# Ground your answer in the sources below and don't add generic advice that isn't supported by them.
# Sources:
# {sources}
# """
    # save_message(user_id, "assistant", response.content)
    # return {"messages": [{"role": "assistant", "content": response.content}]}



     #building history as messages
    system_message = {
        "role": "system",
        "content": f"youre a research assistant. the users job is {job}, keep that in mind but dont say it every single message. use the sources given. match whatever format they ask for (list, direct answer etc). keep it short"
    }

    conversation = [system_message]
    for role, content in history_rows:
        conversation.append({"role": role, "content": content})

    #latest question and search results
    conversation.append({
        "role": "user",
        "content": f"{topic}\n\nSources:\n{sources}"
    })

    response = llm.invoke(conversation, max_tokens=400)
    save_message(user_id, "assistant", response.content)
    return {"messages": [{"role": "assistant", "content": response.content}]}






builder = StateGraph(State)
builder.add_node("research", research_node)
builder.add_edge(START, "research")
builder.add_edge("research", END)

graph = builder.compile()

