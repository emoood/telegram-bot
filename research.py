import os
from dotenv import load_dotenv
from tavily import TavilyClient
from groq import Groq
load_dotenv()
from db import get_job, set_job, get_history, save_message, init_db
init_db()


llm = Groq(api_key=os.environ["GROQ_API_KEY"])
tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

MODEL = "openai/gpt-oss-120b"


def handle_message(user_id, user_message):
    history_rows = get_history(user_id)
    save_message(user_id, "user", user_message)
    job = get_job(user_id)

    if job is None and len(history_rows) == 0:
        greeting = "Welcome! What's your job or role? Once I have that, you can send me any topic and I'll research it for you."
        save_message(user_id, "assistant", greeting)
        return greeting
    
    if job is None:
        extract_prompt = f"""Extract just the job title or role from this message: "{user_message}"
Reply with only the job title, nothing else. For example if they say "I'm a software developer at google" reply "software developer"."""
        extracted = llm.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": extract_prompt}],
            max_tokens=100,
            reasoning_effort="low"
        )
        clean_job = extracted.choices[0].message.content.strip()
        set_job(user_id, clean_job)
        reply = f"Got it, saved your job as: {clean_job}. Now send me a topic for research."
        save_message(user_id, "assistant", reply)
        return reply

    #checking if something is small talk
    classify_prompt = f"""Is this message small talk or a real question/topic to research?
    Message: "{user_message}"
    Reply with only one word: "small_talk" or "topic\""""
    
    classification = llm.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": classify_prompt}],
        max_tokens=50,
        reasoning_effort="low"
    )

    classification_text = classification.choices[0].message.content

    if "small_talk" in classification_text.lower():

        small_talk_prompt = f"""The user just said: "{user_message}"
        
        Reply naturally, like a normal chat response to this message."""

        response = llm.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": small_talk_prompt}],
            max_tokens=50
        )
        reply_text = response.choices[0].message.content
        save_message(user_id, "assistant", reply_text)
        return reply_text

    
    topic = user_message
    search_query = f"{topic} for {job}"
    results = tavily.search(query=search_query, max_results=5)
    sources = "\n\n".join(
        f"{r['title']}\n{r['content']}" for r in results["results"]
    )

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

    response = llm.chat.completions.create(
        model=MODEL,
        messages=conversation,
        max_tokens=800
    )
    reply_text = response.choices[0].message.content
    save_message(user_id, "assistant", reply_text)
    return reply_text





