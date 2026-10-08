from openai import OpenAI

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

from openai import OpenAI, RateLimitError
import os
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

try:
    response = client.chat.completions.create(
        model="gpt-5.5",
        messages=[
            {"role": "user", "content": "Say hello"}
        ]
    )

    print(response.choices[0].message.content)

except RateLimitError:
    print("❌ OpenAI unavailable: insufficient quota.")

except Exception as e:
    print(f"❌ OpenAI error: {e}")
 