import requests
import json
import re
import time
from Settings import prompt
from Settings.config import api_key,base_url

class memoryAgent:
    """
    memoryAgent: A lightweight wrapper for model interaction in the AMA framework.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.8):
        """
        Initialize the memoryAgent with a specific model.
        
        Args:
            model (str): The model name used for inference, e.g., "gpt-4o" or "gpt-4o-mini".
            temperature (float): Sampling temperature for response generation. Default is 0.8.
        """

        # Authentication & basic API settings
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.promptToken = 0
        self.completionToken = 0
        # Internal message buffer (for continuous dialogue)
        self.messages = []

        print(f"✅ memoryAgent initialized with model: {self.model}")

    def inference(self, messages: list, showUsage: bool = False) -> str:
        """
        Perform one inference call using the specified message list.

        Args:
            messages (list): A list of messages in OpenAI chat format, e.g.
                             [
                                 {"role": "system", "content": "You are a helpful assistant."},
                                 {"role": "user", "content": "Explain the difference between CPU and GPU."}
                             ]
            showUsage (bool, optional): Whether to print token usage information. Default is False.

        Returns:
            str: The assistant's generated reply.
        """

        # === 1. Build request body ===
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature
        }

        # === 2. Send the request ===
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=60,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return ""

        # === 3. Parse the response ===
        try:
            resJson = response.json()
            assistantReply = resJson['choices'][0]['message']['content']
        except (KeyError, json.JSONDecodeError) as e:
            print(f"⚠️ Failed to parse response: {e}")
            print("Raw response:", response.text)
            return ""

        # === 4. Optionally print token usage info ===
        if showUsage and "usage" in resJson:
            usage = resJson["usage"]
            promptToks = usage.get("prompt_tokens", 0)
            completionToks = usage.get("completion_tokens", 0)
            totalToks = usage.get("total_tokens", 0)
            print(f"📊 Token usage → prompt: {promptToks}, completion: {completionToks}, total: {totalToks}")
            self.promptToken += promptToks
            self.completionToken += completionToks
        elif showUsage:
            print("⚠️ No token usage info in response.")

        # === 5. Print & return result ===
        print(f"🧠 Assistant: {assistantReply}")
        return assistantReply
    
    def inferenceRetrieve(self, memoryWindow, userInput: str, showUsage: bool = False):
        """
        Perform retrieval operator decision based on memoryWindow and userInput.
        """

        # === 1. Format memoryWindow ===
        try:
            mwStr = json.dumps(memoryWindow, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to format memoryWindow: {e}")
            mwStr = str(memoryWindow or "<EMPTY>")

        # === 2. Load prompt template (with placeholders) ===
        basePromptTemplate = prompt.retrievePromptEN  # e.g. version with {memory_window} & {user_input}

        # === 3. Safely fill the prompt ===
        try:
            filledPrompt = basePromptTemplate.format(
                memory_window=mwStr,
                user_input=userInput
            )
        except KeyError as e:
            print(f"❌ Prompt .format() key error: {e}")
            print("⚠️ Please ensure JSON braces are escaped as {{ }} inside retrievePromptEN.")
            filledPrompt = basePromptTemplate  # fallback to raw prompt

        # === 4. Build message sequence ===
        messages = [
            {"role": "system", "content": filledPrompt},
        ]

        # === 5. Model call ===
        print("——————————————————————🧠 Retrieval Decision Start——————————————————————")
        rawReply = self.inference(messages=messages, showUsage=showUsage)

        # === 6. Try to parse JSON ===
        try:
            parsed = json.loads(rawReply)
            print("✅ Parsed retrieval operator decision successfully.")
            return parsed
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON reply. Returning raw output.")
            print("Raw output:\n", rawReply)
            return {"raw": rawReply, "operator": None}

    def inferenceJudge(self, retrievals, memoryWindow=None, userInput: str = "", showUsage: bool = False):
        """
        Perform Judge operation decision (8: OneMoreShot, -1: PassThrough, -2: Conflict)
        Determine whether the retrieval results and short-term memory are sufficient to answer user input, and check for conflicts.

        Args:
            retrievals (list | dict): Retrieved memory records (may be empty)
            memoryWindow (list | dict | None): Current short-term memory window (may be empty)
            userInput (str): Current user input text
            showUsage (bool): Whether to display token usage statistics

        Returns:
            dict: Model output JSON object containing operator, reason, and other fields
        """

        print("——————————————————————🧩 Judge Information——————————————————————")

        import json

        # === 1️⃣ Format memoryWindow and retrievals ===
        try:
            memStr = json.dumps(memoryWindow or [], ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to format memoryWindow: {e}")
            memStr = str(memoryWindow or "<EMPTY>")

        try:
            retStr = json.dumps(retrievals or [], ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to format retrievals: {e}")
            retStr = str(retrievals or "<EMPTY>")

        # === 2️⃣ Merge into unified information block (for LLM judgment) ===
        combined_info = (
            "===== Combined Information =====\n"
            "The following content comes from related information sources.\n"
            "They together form the available semantic context. Please judge comprehensively whether they are sufficient to answer the user input.\n"
            "The field 'dia_id' only indicates the dialogue turn order and has no relation to topic or semantic relevance. Please ignore it.\n\n"
            f"[MemoryWindow]\n{memStr}\n\n[Retrievals]\n{retStr}"
        )

        # === 3️⃣ Load and fill Judge Prompt (with placeholders) ===
        basePromptTemplate = prompt.judgePromptEN
        try:
            filledPrompt = basePromptTemplate.format(
                information=combined_info,
                user_input=userInput
            )
        except KeyError as e:
            print(f"❌ Prompt .format() key error: {e}")
            print("⚠️ Please ensure JSON braces in judgePromptEN are escaped as {{ }}.")
            filledPrompt = basePromptTemplate

        # === 4️⃣ Build messages ===
        messages = [
            {"role": "system", "content": filledPrompt},
        ]

        # === 5️⃣ Model inference ===
        print("——————————————————————⚖️ Judge Reasoning Start——————————————————————")
        rawReply = self.inference(messages=messages, showUsage=showUsage)

        # === 6️⃣ Try to parse JSON output ===
        try:
            parsed = json.loads(rawReply)
            print("✅ Parsed Judge decision successfully.")
            return parsed
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON reply. Returning raw text.")
            print("Raw output:\n", rawReply)
            return {"raw": rawReply, "operator": None}

    def inferenceRefresh(self, retrievals, userInput: str = "", showUsage: bool = False):
        """
        Perform refresh operator decision (-1: No-Op, 4: Update, 5: Delete)
        Determine refresh operation type based on retrieval results and user input.

        Args:
            retrievals (list | dict): Retrieved factKnowledge memory records (may be empty)
            userInput (str): Current user input (optional)
            showUsage (bool): Whether to display token usage statistics

        Returns:
            dict: Model output JSON object containing operator, dataList, reason, and other info
        """

        print("——————————————————————🧩 Refresh Information——————————————————————")

        import json

        # 1️⃣ Format retrievals
        try:
            factStr = json.dumps(retrievals or [], ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ Failed to format retrievals: {e}")
            factStr = str(retrievals or "<EMPTY>")

        # 2️⃣ Fill Prompt
        basePromptTemplate = prompt.refreshPromptEN
        try:
            filledPrompt = basePromptTemplate.format(
                fact_knowledge=factStr,
                user_input=userInput or "<EMPTY>"
            )
        except KeyError as e:
            print(f"❌ Prompt .format() key error: {e}")
            print("⚠️ Please ensure JSON braces in refreshPromptEN are escaped as {{ }}.")
            filledPrompt = basePromptTemplate

        # 3️⃣ Build messages
        messages = [
            {"role": "system", "content": filledPrompt},
        ]

        # 4️⃣ Call inference
        print("——————————————————————⚙️ Refresh Reasoning Start——————————————————————")
        rawReply = self.inference(messages=messages, showUsage=showUsage)

        # 5️⃣ Try to parse JSON output
        try:
            parsed = json.loads(rawReply)
            print("✅ Parsed Refresh decision successfully.")
            return parsed
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON reply. Returning raw text.")
            print("Raw output:\n", rawReply)
            return {"raw": rawReply, "operator": None}


    def inferenceConstruct(self, memoryWindow, retrievals, userInput: str, showUsage: bool = False):
        """
        Perform Fact Inference based on memoryWindow, retrievals, and current user input.

        Args:
            memoryWindow (list | dict | None): Current short-term memory window (may be empty)
            retrievals (list | dict | None): Retrieved relevant information (may be empty)
            userInput (str): Current user input
            showUsage (bool): Whether to display token usage

        Returns:
            dict: Model output JSON object containing facts, source, timestamp, and other fields
        """

        print("——————————————————————Construct Information——————————————————————")

        # === 1️⃣ Format memoryWindow and retrievals ===
        try:
            mwStr = json.dumps(memoryWindow or [], ensure_ascii=False, indent=2)
        except Exception:
            mwStr = str(memoryWindow or "<EMPTY>")

        try:
            retStr = json.dumps(retrievals or [], ensure_ascii=False, indent=2)
        except Exception:
            retStr = str(retrievals or "<EMPTY>")

        # === 2️⃣ Load Construct Prompt (Fact-only mode) ===
        basePrompt = prompt.constructPromptEN_FTF  # or constructPromptCN_FTF for Chinese

        # === 3️⃣ Fill prompt with format ===
        formattedPrompt = basePrompt.format(
            memory_window=mwStr,
            retrievals=retStr,
            user_input=userInput
        )

        # === 4️⃣ Build messages ===
        messages = [
            {"role": "system", "content": formattedPrompt}
        ]

        # === 5️⃣ Call inference ===
        rawReply = self.inference(messages=messages, showUsage=showUsage)

        # === 6️⃣ Try to parse JSON output ===
        try:
            parsed = json.loads(rawReply)
            return parsed
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON reply. Returning raw text.")
            print("Raw output:", rawReply)
            return {"raw": rawReply}

    def inferenceJudgeEpisode(self, conversationHistory, newMessages, showUsage: bool = False):
        """
        Perform episodic boundary detection based on dialogue continuity.

        Args:
            conversationHistory (list | dict | None): Existing conversation history (may be empty)
            newMessages (list | dict | None): Newly added dialogue messages
            showUsage (bool): Whether to display token usage statistics

        Returns:
            dict: Model output containing keys:
                  - should_end (bool)
                  - reason (str)
                  - confidence (float)
                  - topic_summary (str, optional)
                  or {"raw": <rawReply>} if JSON parsing fails
        """

        print("——————————————————————Episodic Boundary Judgment——————————————————————")

        # === 1️⃣ Serialize input ===
        try:
            convStr = json.dumps(conversationHistory or [], ensure_ascii=False, indent=2)
        except Exception:
            convStr = str(conversationHistory or "<EMPTY>")

        try:
            newStr = json.dumps(newMessages or [], ensure_ascii=False, indent=2)
        except Exception:
            newStr = str(newMessages or "<EMPTY>")

        # === 2️⃣ Load boundary detection Prompt ===
        basePrompt = prompt.judgeEpisodePromptEN

        # === 3️⃣ Fill prompt template ===
        formattedPrompt = basePrompt.format(
            conversation_history=convStr,
            new_messages=newStr
        )

        # === 4️⃣ Build messages (only one system prompt) ===
        messages = [
            {"role": "system", "content": formattedPrompt}
        ]

        # === 5️⃣ Call inference ===
        rawReply = self.inference(messages=messages, showUsage=showUsage)
    
        # === 6️⃣ Try to parse JSON output ===
        try:
            parsed = json.loads(rawReply)
            return parsed
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON reply. Returning raw text.")
            print("Raw output:", rawReply)
            return {"raw": rawReply}

    def inferenceGenerateEpisode(self, conversation, boundaryReason: str = "", showUsage: bool = False):
        """
        Perform episodic memory generation based on conversation and boundary reason.

        Args:
            conversation (list | str | dict): The conversation content (can be a list of messages, a dict, or plain text).
            boundaryReason (str): The reason for boundary detection (helps guide episodic summarization).
            showUsage (bool): Whether to display token usage statistics.

        Returns:
            dict: Model output JSON object containing:
                  {
                    "title": str,
                    "content": str,
                    "timestamp": str
                  }
                  or {"raw": <rawReply>} if JSON parsing fails.
        """

        print("——————————————————————Episodic Memory Generation——————————————————————")

        # === 1️⃣ Serialize conversation content ===
        try:
            convStr = json.dumps(conversation, ensure_ascii=False, indent=2)
        except Exception:
            convStr = str(conversation or "<EMPTY>")

        # === 2️⃣ Load Episode Prompt ===
        basePrompt = prompt.generateEpisodePrompt

        # === 3️⃣ Fill template ===
        formattedPrompt = basePrompt.format(
            conversation=convStr,
            boundary_reason=boundaryReason or "No explicit boundary reason provided."
        )

        # === 4️⃣ Build messages ===
        messages = [
            {"role": "system", "content": formattedPrompt}
        ]

        # === 5️⃣ Model inference ===
        rawReply = self.inference(messages=messages, showUsage=showUsage)

        # === 6️⃣ Try to parse JSON output ===
        try:
            parsed = json.loads(rawReply)
            return parsed
        except json.JSONDecodeError:
            print("⚠️ Failed to parse JSON reply. Returning raw text.")
            print("Raw output:", rawReply)
            return {"raw": rawReply}

class chatAgent:
    """
    chatAgent: A lightweight model for chat testing.
    """

    def __init__(self, model: str = "gpt-4o-mini", temperature: float = 0.8):
        """
        Initialize the chatAgent with a specific model.
        
        Args:
            model (str): The model name used for inference, e.g., "gpt-4o" or "gpt-4o-mini".
            temperature (float): Sampling temperature for response generation. Default is 0.8.
        """

        # Authentication & basic API settings
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.temperature = temperature
        self.messages = [
            {"role": "system", "content": "You are a helpful assistant"},
        ]
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        # Internal message buffer (for continuous dialogue)
        self.messages = []

        print(f"✅ chatAgent initialized with model: {self.model}")

    def chat(self, userInput: str, showUsage: bool = False, memoryInfo: str = "") -> str:
        """
        Perform one inference call using qaPromptEN.
        """

        # === 1️⃣ Build complete Prompt ===
        full_prompt = prompt.QANemoriPrompt.format(memoryInfo=memoryInfo or "None", userInput=userInput)

        # === 2️⃣ Build message list ===
        self.messages = [
            {"role": "system", "content": full_prompt},
        ]

        # === 3️⃣ Build request body ===
        payload = {
            "model": self.model,
            "messages": self.messages,
            "temperature": self.temperature
        }

        # === 4️⃣ Send request ===
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                data=json.dumps(payload)
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return ""

        # === 5️⃣ Parse response ===
        try:
            res_json = response.json()
            assistant_reply = res_json["choices"][0]["message"]["content"].strip()
        except (KeyError, json.JSONDecodeError) as e:
            print(f"⚠️ Failed to parse response: {e}")
            print("Raw response:", response.text)
            return ""

        # === 6️⃣ Optionally print token usage info ===
        if showUsage:
            usage = res_json.get("usage", {})
            if usage:
                print(f"📊 Token usage → prompt: {usage.get('prompt_tokens', 0)}, "
                      f"completion: {usage.get('completion_tokens', 0)}, "
                      f"total: {usage.get('total_tokens', 0)}")
            else:
                print("⚠️ No token usage info in response.")

        # === 7️⃣ Clear context (keep clean) ===
        self.messages = [{"role": "system", "content": "You are a helpful assistant"}]

        # === 8️⃣ Output result ===
        print(f"🧠 Assistant: {assistant_reply}")
        return assistant_reply


if __name__ == "__main__":
    agent = memoryAgent(model="gpt-4o-mini", temperature=0.0)
    memoryWindow = [      


    ]
    retrievals = [    

    ]
    userInput = json.dumps(               {
          "speaker": "Caroline",
          "dia_id": "D4:3",
          "text": "Thanks, Melanie! This necklace is super special to me - a gift from my grandma in my home country, Sweden. She gave it to me when I was young, and it stands for love, faith and strength. It's like a reminder of my roots and all the love and support I get from my family."
        },    
    )

    reason = "The dialogue has ended."
    generate = agent.inferenceConstruct(memoryWindow, retrievals, userInput)
