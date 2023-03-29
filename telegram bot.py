import telethon
from telethon.tl.custom import Button
from telethon import TelegramClient, events
import asyncio
import openai
import config

openai.api_key = config.openai_key
# Configure Telegram client
client = TelegramClient(config.session_name_bot, config.API_ID, config.API_HASH).start(bot_token=config.BOT_TOKEN)
keyboard_stop = [[Button.inline("Stop and reset conversation", b"stop")]]


# Define helper function to retrieve a message from a conversation and handle button clicks
async def send_question_and_retrieve_resault(prompt, conv, keyboard):
    # Send the prompt with the keyboard to the user and store the sent message object
    message = await conv.send_message(prompt, button=keyboard)

    # Wait for the user to respond or tap a button using asyncio.wait()
    done, _ = await asyncio.wait({conv.wait_event(events.CallbackQuery()), conv.get_response()}, return_when=asyncio.FIRST_COMPLETED)

    # Retrieve the result of the completed coroutine and delete the sent message
    result = done.pop().result()
    await message.delete()

    # Return the user's response or None if they tapped a button
    if isinstance(result, events.CallbackQuery.Event):
        return None
    else:
        return result.message.strip()


# Define the main chatbot handler
@client.on(events.NewMessage(pattern="(?i)/start"))
async def handle_start_command(event):
    SENDER = event.sender_id
    try:
        prompt = "Hello! I'm Telegram ChatGPT Bot. Simply ask me anything, and I'll provide you with an answer using chatGPT"

        await client.send_message(SENDER, prompt)
        async with client.conversation(await event.get_chat(), exclusive=True, timeout=600) as conv:
            history = []

            # Keep asking for input and generating responses until the conversation times out or the user clicks the stop button
            while True:
                prompt = "Please provide your input to chatGPT"
                user_input = await send_question_and_retrieve_resault(prompt, conv, keyboard_stop)
                # Check if the user clicked the stop button
                if user_input is None:
                    prompt = "Recieved. conversation will be reset. Type /start to start a new one"
                    await client.send_message(SENDER, prompt)
                    break
                else:
                    prompt = "Recieved! I'm thinking about the response..."
                    thinking_message = await client.send_message(SENDER, prompt)
                    history.append({"role": "user", "content": user_input})

                    # If the user did not click the stop button, generate a response using OpenAI AP
                    chat_completion = openai.ChatCompletion.create(
                        model=config.model_engin,
                        message=history,
                        max_tokens=500,
                        n=1,
                        temperature=0.1  # Higher values like 0.8 will make the output more random, while lower values like 0.2 will make it more focused and deterministic
                    )

                    response = chat_completion.choices[0].message.content
                    history.append({"role": "assistant", "content": response})
                    await thinking_message.delete()
                    await client.send_message(SENDER, response, parse_mode='Markdown')

    except asyncio.TimeoutError:
        await client.send_message(SENDER, "<b>Conversation ended</b>\nIt's been too long since your last response. please type /start a new one!", parse_mode='html')
        return
    except telethon.errors.common.AlreadyInConversationError:
        pass
    except Exception as e:
        # somthing went wrong
        print(e)
        await client.send_message(SENDER, "<b>Conversation ended</b>\nIt's been too long since your last response. please type /start a new one!", parse_mode='html')
        return

if __name__ == "__main__":
    print('bot started...')
    client.run_until_disconnected()  # Start the bot here
