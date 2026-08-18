"""Quick model health check — pings every configured model and reports OK/FAIL."""
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def check_groq():
    from groq import Groq
    c = Groq(api_key=os.getenv("GROQ_API_KEY"))
    for m in ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "llama-3.1-8b-instant"]:
        try:
            c.chat.completions.create(model=m, messages=[{"role": "user", "content": "ok"}], max_tokens=3)
            print(f"[GROQ] {m} -> OK")
        except Exception as e:
            print(f"[GROQ] {m} -> FAIL: {str(e)[:140]}")

def check_openrouter():
    from openai import OpenAI
    c = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    # VERIFIED-LIVE 2026-07-26 free text models + Qwen-VL vision models.
    for m in ["nvidia/nemotron-3-ultra-550b-a55b:free",
              "nvidia/nemotron-3-super-120b-a12b:free",
              "openai/gpt-oss-20b:free",
              "qwen/qwen3-vl-32b-instruct",
              "qwen/qwen3-vl-8b-instruct"]:

        try:
            c.chat.completions.create(model=m, messages=[{"role": "user", "content": "ok"}], max_tokens=3, timeout=30)
            print(f"[OPENROUTER] {m} -> OK")
        except Exception as e:
            print(f"[OPENROUTER] {m} -> FAIL: {str(e)[:140]}")

def check_gemini():
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        genai.GenerativeModel("gemini-2.0-flash").generate_content("ok")
        print("[GEMINI] gemini-2.0-flash -> OK")
    except Exception as e:
        print(f"[GEMINI] gemini-2.0-flash -> FAIL: {str(e)[:140]}")

if __name__ == "__main__":
    print("=== MODEL HEALTH CHECK ===")
    check_groq()
    check_openrouter()
    check_gemini()
