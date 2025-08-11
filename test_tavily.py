from dotenv import load_dotenv
import os
from tavily import TavilyClient

# load environment variables from .env file
_ = load_dotenv()

client = TavilyClient(api_key=os.environ.get("TAVILY_API_KEY"))


print(os.environ.get("TAVILY_API_KEY"))
# run search
result = client.search("What is in Nvidia's new Blackwell GPU?",
                       include_answer=True)

# print the answer
print(result["answer"])
