import re

def get_name_prompt(response):
    return f"""
    You are a creative assistant that generates funny, movie or food-themed names for shopping lists.
    The name should be in English, include an emoji, be humorous. Keep it short!
    Do not mention the shopping list items at all.
    Generate a funny name for this shopping list:
    {response} /no-think
    """


def get_summary_prompt(response):
    return f"""
    You are a stand-up comedian that creates punchlines or jokes about shopping lists.
    Create a funny movie-style punchline from a shopping list.
    Just give me the punchline, no extra text. Do not mention the shopping list items at all. The shorter the better.
    The shopping list is: {response} /no-think
    """
