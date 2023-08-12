import os
import openai
import asyncio

from llama_index.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.callbacks.base import CallbackManager
from llama_index import (
    LLMPredictor,
    ServiceContext,
    StorageContext,
    load_index_from_storage,
)
from langchain.chat_models import ChatOpenAI
from langchain import PromptTemplate, LLMChain

import chainlit as cl
from chainlit.input_widget import Select, Switch, Slider
from modules import actions
from modules.chatbot import handle_url_message

openai.api_key = os.environ.get("OPENAI_API_KEY") or exit("OPENAI_API_KEY not set!")

template = """Question: {question}

Answer: Let's think step by step."""


@cl.on_chat_start
async def start():
    settings = await cl.ChatSettings(
        [
            Select(
                id="Model",
                label="OpenAI - Model",
                values=["gpt-3.5-turbo", "gpt-3.5-turbo-16k", "gpt-4", "gpt-4-32k"],
                initial_index=0,
            ),
            Slider(
                id="Temperature",
                label="OpenAI - Temperature",
                initial=1.0,
                min=0,
                max=2,
                step=0.1,
            ),
            Switch(id="Streaming", label="OpenAI - Stream Tokens", initial=True),
        ]
    ).send()

    # Instantiate the chain for that user session
    model = ChatOpenAI(model=settings["Model"], temperature=settings["Temperature"], streaming=settings["Streaming"])
    prompt = PromptTemplate(template=template, input_variables=["question"])
    llm_chain = LLMChain(prompt=prompt, llm=model, verbose=True)

    # Store the chain in the user session
    cl.user_session.set("llm_chain", llm_chain)

    await cl.Avatar(
        name="seanbetts@icloud.com",
        url="https://github.com/seanbetts/va.ai/blob/main/assets/seanbetts.png?raw=true",
    ).send()
    
    await cl.Avatar(
        name="va.ai",
        url="https://github.com/seanbetts/va.ai/blob/f100e27c5a31dfacdb7296b7afcad8ea3a33ebee/assets/chatAvatar.png?raw=true",
    ).send()

    actions = [
        cl.Action(name="Upload File", value="temp", description="Upload File!"),
    ]

    await asyncio.sleep(2)
    await cl.Message(
        content=f"**Hi!**\n\nYou are currently using the following settings:\n\n**Model:** {settings['Model']}\n**Temperature:** {settings['Temperature']}\n**Streaming:** {settings['Streaming']}\n\nYou can update this in the settings below ↓", actions=actions).send()

@cl.on_message
async def main(message):
    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get("llm_chain")
    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True

    if "http" in message or "www" in message:
        await handle_url_message(message)

    else: 
         # Call the chain asynchronously
        res = await llm_chain.acall(message, callbacks=[cb])
        answer = res["text"]

        actions = [
            cl.Action(name="Upload File", value="temp", description="Upload File!"),
        ]

        # Do any post processing here

        # "res" is a Dict. For this chain, we get the response by reading the "text" key.
        # This varies from chain to chain, you should check which key to read.
        await cl.Message(content=answer, actions=actions).send()

@cl.on_settings_update
async def setup_agent(settings):
    # Instantiate the chain for that user session
    model = ChatOpenAI(model=settings["Model"], temperature=settings["Temperature"], streaming=settings["Streaming"])
    prompt = PromptTemplate(template=template, input_variables=["question"])
    llm_chain = LLMChain(prompt=prompt, llm=model, verbose=True)

    # Store the chain in the user session
    cl.user_session.set("llm_chain", llm_chain)

    actions = [
        cl.Action(name="Upload File", value="temp", description="Upload File!"),
    ]

    await cl.Message(
        content=f"You are now using the following settings:\n**Model:** {settings['Model']}\n**Temperature:** {settings['Temperature']}\n**Streaming:** {settings['Streaming']}", actions=actions).send()