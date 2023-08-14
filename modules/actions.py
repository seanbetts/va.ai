# modules/actions.py

import chainlit as cl

from llama_index import TrafilaturaWebReader

from modules.chatbot import handle_file_upload
from .utils import extract_first_200_words, num_tokens_from_string, get_token_limit, is_over_token_limit, dataframe_to_json_metadata

import io
from wordcloud import WordCloud, STOPWORDS
import matplotlib.pyplot as plt
import pyperclip
import requests
import PyPDF2
from io import BytesIO

###--CREATE WORDCLOUD--###
@cl.action_callback("Create Wordcloud")
async def on_action(action):
    # Send message to user
    msg = cl.Message(content="Generating Wordcloud...")
    await msg.send()

    # Generate the wordcloud
    wordcloud = WordCloud(colormap='cool', background_color="rgba(0, 0, 0, 0)", mode="RGBA", stopwords=STOPWORDS, width=1980, height=1080, scale=1).generate(action.value)

    # Plot and save the word cloud
    fig = plt.figure(figsize=(19.80, 10.80))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis("off")
    plt.tight_layout()

    # Saving the figure to a bytes buffer
    buf = io.BytesIO()
    fig.savefig(buf, format="png")

    # Convert the buffered image to bytes for sending
    image_bytes = buf.getvalue()

    # Save image to user session
    cl.user_session.set("image", image_bytes)

    # Sending an image with the file name
    elements = [
        cl.Image(name="Wordcloud", display="inline", size="large", content=image_bytes),
        cl.File(name="Wordcloud.png", content=image_bytes, display="inline")
    ]

    actions = [
        cl.Action(name="Save To Knowledgebase", value=f"{image_bytes}", description="Save To Knowledgebase!"),
        cl.Action(name="Upload File", value="temp", description="Upload File!"),
    ]

    # Remove previous message
    await msg.remove()

    # Send final message to user
    await cl.Message(content="Here's your wordcloud:", elements=elements, actions=actions).send()

    # Clear the current wordcloud figure
    plt.clf()

    # Remove the action button from the chatbot user interface
    # await action.remove()

###--GET WEBSITE CONTENT--###
@cl.action_callback("Get Website Content")
async def on_action(action):
    # Send message to user
    msg = cl.Message(content="Getting website content...")
    await msg.send()

    if ".pdf" in action.value:
        response = requests.get(action.value)
        response.raise_for_status()

        # Convert the response content to a BytesIO object
        pdf_content = BytesIO(response.content)

        # Read the PDF with PyPDF2
        pdf_reader = PyPDF2.PdfReader(pdf_content)

        text = []
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text.append(page.extract_text())
        pdf_text = "\n".join(text)
        extracted_text = extract_first_200_words(pdf_text)

        elements = [
            # cl.Pdf(name="PDF", display="inline", content=uploaded_file.content),
            cl.Text(name="Here are the first 200 words from the document:", content=extracted_text, display="inline")
        ]

        actions = [
            cl.Action(name="Summarise", value=f"{pdf_text}", description="Summarise!"),
            cl.Action(name="Bulletpoint Summary", value=f"{pdf_text}", description="Bulletpoint Summary!"),
            cl.Action(name="Create Wordcloud", value=f"{pdf_text}", description="Create Wordcloud!"),
            cl.Action(name="Copy", value=f"{pdf_text}", description="Copy Text!"),
            cl.Action(name="Save To Knowledgebase", value=f"{pdf_text}", description="Save To Knowledgebase!"),
            cl.Action(name="Upload File", value="temp", description="Upload File!"),
        ]

        model = cl.user_session.get("action_model")
        tokens = num_tokens_from_string(pdf_text, model)
        token_limit = get_token_limit(model)
        is_over = is_over_token_limit(tokens, token_limit)

        # Remove previous message
        await msg.remove()

        # Send final message to user
        await cl.Message(
            content=f"The PDF contains {format(len(pdf_text), ',')} characters which is c.{format(tokens, ',')} tokens.\nYou're currently using the {model} model which has a token limit of {format(token_limit, ',')}.\n{is_over[1]}", elements=elements, actions=actions
        ).send()

    else:
        documents = TrafilaturaWebReader().load_data([action.value])
        model = cl.user_session.get("action_model")
        tokens = num_tokens_from_string(documents[0].text, model)
        token_limit = get_token_limit(model)
        is_over = is_over_token_limit(tokens, token_limit)
        extracted_text = extract_first_200_words(documents[0].text)

        elements = [
            cl.Text(name="Here are the first 200 words from the webpage:", content=extracted_text, display="inline")
        ]

        actions = [
            cl.Action(name="Summarise", value=f"{documents[0].text}", description="Summarise!"),
            cl.Action(name="Bulletpoint Summary", value=f"{documents[0].text}", description="Bulletpoint Summary!"),
            cl.Action(name="Create Wordcloud", value=f"{documents[0].text}", description="Create Wordcloud!"),
            cl.Action(name="Copy", value=f"{documents[0].text}", description="Copy Text!"),
            cl.Action(name="Save To Knowledgebase", value=f"{documents[0].text}", description="Save To Knowledgebase!"),
            cl.Action(name="Upload File", value="temp", description="Upload File!"),
        ]

        # Remove previous message
        await msg.remove()

        # Send final message to user
        await cl.Message(content=f"The webpage contains {format(len(documents[0].text), ',')} characters which is c.{format(tokens, ',')} tokens.\nYou're currently using the {model} model which has a token limit of {format(token_limit, ',')}.\n{is_over[1]}", elements=elements, actions=actions).send()

    # Optionally remove the action button from the chatbot user interface
    await action.remove()

###--COPY--###
@cl.action_callback("Copy")
async def on_action(action):
    pyperclip.copy(action.value)

    await cl.Message(content=f"Text copied to clipboard").send()

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()

###--UPLOAD FILE--###
@cl.action_callback("Upload File")
async def on_action(action):
    model = cl.user_session.get("action_model")
    await handle_file_upload(model)

    # Optionally remove the action button from the chatbot user interface
    await action.remove()

###--WRITE SUMMARY--###
@cl.action_callback("Summarise")
async def on_action(action):

    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get("llm_chain")
    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True

    # Call the chain asynchronously
    res = await llm_chain.acall(f"Write me a summary of this text:\n{action.value}", callbacks=[cb])
    answer = res["text"]

    actions = [
        cl.Action(name="Copy", value=answer, description="Copy Text!"),
        cl.Action(name="Save To Knowledgebase", value=answer, description="Save To Knowledgebase!"),
        cl.Action(name="Upload File", value="temp", description="Upload File!"),
    ]

    await cl.Message(content=f"**Here is your summary:**\n\n{answer}", actions=actions).send()

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()

###--WRITE BULLETPOINT SUMMARY--###
@cl.action_callback("Bulletpoint Summary")
async def on_action(action):

    # Retrieve the chain from the user session
    llm_chain = cl.user_session.get("llm_chain")
    cb = cl.AsyncLangchainCallbackHandler(
        stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
    )
    cb.answer_reached = True

    # Call the chain asynchronously
    res = await llm_chain.acall(f"Write me a bulletpoint summary of this text:\n{action.value}", callbacks=[cb])
    answer = res["text"]

    actions = [
        cl.Action(name="Copy", value=answer, description="Copy Text!"),
        cl.Action(name="Save To Knowledgebase", value=answer, description="Save To Knowledgebase!"),
        cl.Action(name="Upload File", value="temp", description="Upload File!"),
    ]

    await cl.Message(content=f"**Here is your bulletpoint summary:**\n\n{answer}", actions=actions).send()

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()

###--SAVE TO KNOWLEDGEBASE--###
@cl.action_callback("Save To Knowledgebase")
async def on_action(action):

    ## Add LLM query etc. here ##

    await cl.Message("**Knowledge Saved!**").send()

    # Optionally remove the action button from the chatbot user interface
    # await action.remove()

###--GET INSIGHTS--###
@cl.action_callback("Get Insights")
async def on_action(action):

    # Retrieve the dataframe from the user session
    df = cl.user_session.get("df")

    # Extract data to JSON and create metadata from the dataframe
    res = dataframe_to_json_metadata(df)

    # Construct the prompt
    prompt = f"""
    Based on the provided data, please analyze and provide insights regarding patterns, anomalies, and key findings. Structure your response as a bulletpoint list as follows:
    '''
    **Data Description:**
    Describe the data in a paragraph
    **Patterns:**
    -
    -
    **Anomalies:**
    -
    -
    ** Key Findings:**
    -
    -
    '''

    Metadata:
    - Number of rows: {res['metadata']['num_rows']}
    - Number of columns: {res['metadata']['num_columns']}
    - Column names: {', '.join(res['metadata']['column_names'])}
    - Data types: {', '.join([f"{k}: {v}" for k, v in res['metadata']['data_types'].items()])}

    Data:
    {res['data']}
    """

    model = cl.user_session.get("action_model")
    tokens = num_tokens_from_string(prompt, model)
    token_limit = get_token_limit(model)

    # Check if prompt is over token limit
    if tokens > token_limit:
        await cl.Message(content=f"The data is c.{format(tokens, ',')} tokens, which is {format(tokens - token_limit, ',')} too many tokens for {model}. Please select a model that allows more tokens and try again.").send()

    else:
        # Retrieve the chain from the user session
        llm_chain = cl.user_session.get("llm_chain")

        # Set up message streaming
        cb = cl.AsyncLangchainCallbackHandler(
            stream_final_answer=True, answer_prefix_tokens=["FINAL", "ANSWER"]
        )
        cb.answer_reached = True

        # Call the chain asynchronously
        response = await llm_chain.acall(prompt, callbacks=[cb])
        answer = response["text"]

        actions = [
            cl.Action(name="Copy", value=answer, description="Copy Text!"),
            cl.Action(name="Save To Knowledgebase", value=answer, description="Save To Knowledgebase!"),
            cl.Action(name="Upload File", value="temp", description="Upload File!"),
        ]

        await cl.Message(content=answer, actions=actions).send()

        # Optionally remove the action button from the chatbot user interface
        # await action.remove()