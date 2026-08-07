import random
from database import fetch


QUESTION_BANK = [

    {
        "category": "trust",
        "difficulty": 5,
        "question": "اگر بفهمی کسی که خیلی دوستش داری یک راز مهم از گذشته‌اش را از تو پنهان کرده، حتی اگر روی رابطه شما تاثیر نداشته باشد، چه واکنشی نشان می‌دهی؟"
    },

    {
        "category": "conflict",
        "difficulty": 4,
        "question": "اگر در یک بحث بفهمی حق با تو نیست، معمولا سریع عذرخواهی می‌کنی یا نیاز داری اول خودت را آرام کنی؟ چرا؟"
    },

    {
        "category": "scenario",
        "difficulty": 5,
        "question": "فرض کن کسی که دوستش داری در یک موقعیت سخت تصمیمی می‌گیرد که از نظر تو اشتباه است. حمایت می‌کنی یا مخالفت؟"
    },

    {
        "category": "values",
        "difficulty": 5,
        "question": "اگر مجبور باشی بین رسیدن به بزرگ‌ترین هدف زندگی‌ات و بودن کنار کسی که دوستش داری یکی را انتخاب کنی، چه انتخابی می‌کنی؟"
    },

    {
        "category": "personality",
        "difficulty": 4,
        "question": "چه چیزی درباره شخصیتت وجود دارد که فکر می‌کنی بیشتر آدم‌ها دیر متوجه آن می‌شوند؟"
    },

    {
        "category": "jealousy",
        "difficulty": 5,
        "question": "اگر ببینی کسی که دوستش داری با فرد دیگری خیلی صمیمی صحبت می‌کند، اولین واکنش احساسی تو چیست؟"
    },

    {
        "category": "relationship",
        "difficulty": 4,
        "question": "به نظر تو در یک رابطه، عشق مهم‌تر است یا تلاش روزانه برای حفظ رابطه؟ چرا؟"
    },

    {
        "category": "future",
        "difficulty": 5,
        "question": "اگر آینده‌ای که برای خودت تصور کردی با خواسته‌های کسی که دوستش داری متفاوت باشد، چه کار می‌کنی؟"
    },

    {
        "category": "moral",
        "difficulty": 5,
        "question": "اگر دوست صمیمی‌ات کاری انجام دهد که از نظر اخلاقی اشتباه است اما به تو کمک بزرگی کرده، طرف او را می‌گیری یا کارش را محکوم می‌کنی؟"
    },

    {
        "category": "deep",
        "difficulty": 5,
        "question": "چه ترسی داری که معمولا به دیگران نشان نمی‌دهی؟"
    },

    {
        "category": "fun",
        "difficulty": 3,
        "question": "اگر یک روز بتوانی ذهن کسی را بخوانی، اولین کسی که انتخاب می‌کنی چه کسی است و چرا؟"
    },

    {
        "category": "scenario",
        "difficulty": 4,
        "question": "اگر بفهمی کسی که دوستش داری در مورد یک موضوع کوچک به تو دروغ گفته، مسئله را بزرگ می‌کنی یا از آن عبور می‌کنی؟"
    },

]



async def seed_questions():

    existing = await fetch(
        "SELECT COUNT(*) FROM questions"
    )

    if existing[0]["count"] > 0:
        return


    from database import execute


    for q in QUESTION_BANK:

        await execute(
            """
            INSERT INTO questions
            (
                category,
                difficulty,
                question
            )

            VALUES
            ($1,$2,$3)
            """,

            q["category"],
            q["difficulty"],
            q["question"]
        )



async def random_questions(amount=6):

    rows = await fetch(
        """
        SELECT question
        FROM questions

        ORDER BY RANDOM()

        LIMIT $1
        """,

        amount
    )

    return [
        r["question"]
        for r in rows
    ]