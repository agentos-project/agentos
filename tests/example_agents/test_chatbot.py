from example_agents.chatbot.main import ChatBot
from example_agents.chatbot.env import MultiChatEnv


def test_chatbot(capsys):
    env_generator = MultiChatEnv()
    client_env = env_generator()
    client_env.reset()
    chat_bot = ChatBot(env_generator)
    # Say something in the room for the agent to hear
    response_txt, _, _, _ = client_env.step("one")
    # Agent hears "one" on this advance, but can't respond yet
    chat_bot.advance()
    response_txt, _, _, _ = client_env.step("")
    assert response_txt == "", "chatbot should have no strings in memory"
    # Agent responds with a random selection from memory (which is only "one")
    chat_bot.advance()
    response_txt, _, _, _ = client_env.step("")
    assert response_txt == "one", "chatbot should repeat strings from memory"
    # TODO(andyk): also test CommandLineListener
