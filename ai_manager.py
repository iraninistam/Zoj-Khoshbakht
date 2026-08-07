import json
import httpx

from config import (
    GEMINI_API_KEY,
    GEMINI_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_MODEL,
    CLAUDE_API_KEY,
    CLAUDE_MODEL
)

from database import add_log
from questions import random_questions



async def gemini(prompt):

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
        f"?key={GEMINI_API_KEY}"
    )


    payload = {

        "contents":[
            {
                "parts":[
                    {
                        "text":prompt
                    }
                ]
            }
        ]

    }


    async with httpx.AsyncClient(timeout=40) as client:

        r = await client.post(
            url,
            json=payload
        )

        r.raise_for_status()

        data = r.json()


    return (
        data["candidates"][0]
        ["content"]
        ["parts"][0]
        ["text"]
    )



async def deepseek(prompt):

    headers = {

        "Authorization":
        f"Bearer {DEEPSEEK_API_KEY}"

    }


    payload = {

        "model": DEEPSEEK_MODEL,

        "messages":[

            {
                "role":"user",
                "content":prompt
            }

        ]

    }


    async with httpx.AsyncClient(timeout=40) as client:

        r = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers=headers,
            json=payload
        )

        r.raise_for_status()

        data=r.json()


    return data["choices"][0]["message"]["content"]



async def ask_ai(prompt):

    providers = [

        ("Gemini",gemini),

        ("DeepSeek",deepseek)

    ]


    for name,provider in providers:


        try:

            result = await provider(prompt)


            await add_log(
                name,
                "OK",
                "AI response successful"
            )


            return result


        except Exception as e:


            await add_log(
                name,
                "FAILED",
                str(e)
            )


    await add_log(
        "AI",
        "OFFLINE",
        "All AI providers failed"
    )


    return None



async def generate_questions(amount=6):


    prompt = f"""

Create {amount} challenging Persian blind date questions.

Rules:

- psychological
- scenario based
- reveal personality
- avoid boring questions
- make people explain WHY

Return ONLY JSON array.

"""


    result = await ask_ai(prompt)


    if result:


        try:

            clean=result.replace("```json","")
            clean=clean.replace("```","")

            return json.loads(clean)


        except:

            pass



    return await random_questions(amount)



async def compatibility_analysis(text):


    prompt=f"""

Analyze this blind date.

Give:
- communication compatibility
- values
- possible problems
- short conclusion

Persian language.

{text}

"""


    result=await ask_ai(prompt)


    return result or "AI unavailable. Manual review required."