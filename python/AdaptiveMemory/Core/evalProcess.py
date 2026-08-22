
import json
import sqlite3
import re
import tiktoken
import numpy as np
import time
import argparse
from collections import deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from StoreFunc.Faiss import faissFunc
from StoreFunc.SQLite import sqliteFunc
from Settings import prompt
from Model import model
from AMA import AMA

def main(user_id: int):
    """
    user_id: Used to generate AMA(user=...) name, and index = user_id - 1
    """
    index = user_id - 1

    # ---------- Load data ----------
    with open("locomo10.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    conversations = data[index].get("conversation", {})
    k = 1

    # ---------- Iterate through all sessions ----------
    while f"session_{k}" in conversations:
        conversation = conversations.get(f"session_{k}")
        date_time = conversations.get(f"session_{k}_date_time", "Unknown time")

        if not conversation:
            print(f"⚠️ session_{k} is empty, skip.")
            k += 1
            continue

        print(f"\n============================")
        print(f"🗓 Processing session_{k} | {date_time}")
        print(f"============================")

        # User name and final prompt are based on user_id
        memoryAgent = AMA(user=f"TaskClass{user_id}_Next")

        # ---------- Iterate through each dialogue turn ----------
        for i, session in enumerate(conversation, start=1):
            speaker = session.get("speaker")
            text = session.get("text", "")
            image = session.get("blip_caption", "")
            image_title = session.get("query", "")
            img_url = session.get("img_url", "")

            temp_dict = {
                "speaker": speaker,
                "text": text,
                "timestamp": date_time,
            }

            if image:
                temp_dict["blip_caption"] = image
            if image_title:
                temp_dict["query"] = image_title
            if img_url:
                temp_dict["img_url"] = img_url

            print(json.dumps(temp_dict, ensure_ascii=False))
            print(f"\n=== Round {k}-{i} ===")
            try:
                out = memoryAgent.forwardUser(temp_dict, showUsage=True)
            except Exception as e:
                print(f"❌ Error in session_{k}, round {i}: {e}")

        memoryAgent.judgeAndGenerate()
        k += 1

    print(f"\n✅ TaskClass{user_id} processed successfully.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process LoCoMo sessions for AMA pipeline.")
    parser.add_argument("--user_id", type=int, required=True, help="User ID number (e.g., 10)")
    args = parser.parse_args()

    main(user_id=args.user_id)
