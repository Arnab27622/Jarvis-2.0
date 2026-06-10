import asyncio
from assistant.core.llm_manager import LLMManager

async def main():
    llm = LLMManager()
    res = await llm.get_response_async("what is the first manga in Manga's I've Finished Reading section")
    print('=== LLM RESPONSE ===')
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
