import argparse
import json
import os
from AMA import AMA
from Model import model

def main(user_id: int):
    """
      - index = user_id - 1
      - memory = AMA(f"TaskClass{user_id}_Next")
      - path = ./outputForLocomo/output_locomo_{user_id}.json
    """
    index_in_data = user_id - 1


    with open("locomo10.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    qa_list = data[index_in_data].get("qa", [])
    memory = AMA(f"TaskClass{user_id}_Next", turnRetrieve=3)

    output_path = f"./outputForLocomo/output_locomo_{user_id}.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    index = 1
    for item in qa_list:
        if index > 0:
            question = item.get("question", "")
            answer = item.get("answer", "")
            category = item.get("category", "")

            if category == 5:
                index += 1
                continue 


            memoInfo = memory.forwardRetrieve(question, showUsage=True, strongRetrieve=True)

            chatExam = model.chatAgent(temperature=0.0)
            result = chatExam.chat(question, memoryInfo=memoInfo, showUsage=True)
            result = json.loads(result)

            thing = {
                "index": index,
                "question": question,
                "answer": answer,
                "response": result.get('answer'),
                "category": category,
                "evidence": result.get('evidence'),
            }

            memory.clearMemoryWindow()


            if not os.path.exists(output_path):
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump([], f, ensure_ascii=False, indent=4)


            if os.path.getsize(output_path) == 0:
                file_data = []
            else:
                with open(output_path, "r", encoding="utf-8") as f:
                    file_data = json.load(f)


            file_data.append(thing)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(file_data, f, ensure_ascii=False, indent=4)

        index += 1

    print("Prompt Token Count:", memory.memoryAgent.promptToken)
    print("Completion Token Count:", memory.memoryAgent.completionToken)
    print(f"\n✅ TaskClass{user_id} processed successfully. Output saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run LoCoMo QA evaluation with AMA memory agent.")
    parser.add_argument("--user_id", type=int, required=True, help="User ID number (e.g., 5)")
    args = parser.parse_args()

    main(user_id=args.user_id)
        
