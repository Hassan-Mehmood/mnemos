import asyncio

import httpx
import streamlit as st

BASE_URL = "http://localhost:8000"

st.title("FastAPI Chat App")


async def call_api(message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/chats/invoke", json={"message": message}, timeout=30
        )
        response.raise_for_status()
        return response.json()


user_input = st.text_input("Enter your message")

if st.button("Send"):
    if user_input:
        try:
            result = asyncio.run(call_api(user_input))
            st.write("Response:", result.get("response"))
        except Exception as e:
            st.error(f"Error: {e}")
