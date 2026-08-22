from __future__ import annotations

import json
import sqlite3
import re
import tiktoken
import numpy as np
import time
from collections import deque
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from StoreFunc.Faiss import faissFunc
from StoreFunc.SQLite import sqliteFunc
from Settings import prompt
from Model import model

def split_sentences(text: str) -> list[str]:
    """
    Split input text into a list of sentences by periods, question marks, exclamation marks, etc.
    Supports mixed Chinese and English text, does not split by commas.
    """
    if not text:
        return []

    # Match Chinese/English sentence-ending punctuation (including . ! ?)
    parts = re.split(r'([。．\.！!？?])', text)

    sentences = []
    current = ''
    for part in parts:
        if not part.strip():
            continue
        current += part.strip()
        # If part is sentence-ending punctuation, consider one sentence complete
        if re.match(r'[。．\.！!？?]', part):
            sentences.append(current.strip())
            current = ''
    if current:
        sentences.append(current.strip())

    # Remove empty strings
    return [s for s in sentences if s]

class AMA:
    """
    ============================================================
    Automatic Memory Agent (AMA)
    ============================================================
    Core interface for automatic memory management.
    Handles initialization of user-specific memory tables
    and FAISS indices for semantic retrieval.
    """

    def __init__(self, user: str, memoryWindowSize: int = 1e5, memoryWindowLength: int = 20, modelMemory: str = "gpt-4o-mini", temperature: float = 0.0, turnRetrieve: int = 1, data_dir: str | None = None):
        """
        Initialize the Automatic Memory Agent for a specific user.

        Args:
        -----
        user : str
            The unique name or identifier of this agent/user.
        """
        self.user_id = user
        self.user = sqliteFunc.normalize_table_name(user)
        self.memoryWindow = deque()
        self.memoryAgent = model.memoryAgent(model = modelMemory, temperature = 0.0)
        self.lengthOfMemoryWindow = memoryWindowLength
        self.SizeOfMemoryWindow = memoryWindowSize
        self.memoryKnowledge = ""
        self.factSql = f"{self.user}Fact"
        self.episodeSql = f"{self.user}Episode"
        self.sentenceSql = f"{self.user}Sentence"
        self.turnOfRetrieve = turnRetrieve
        self.retrieveContents = []
        self.data_dir = data_dir
        print(f"🧠 Initializing AMA for user: {self.user_id} (table key: {self.user})")

        sqliteFunc.set_data_dir(data_dir)
        faissFunc.set_data_dir(data_dir)

        # Step 1: Initialize SQLite database
        sqliteFunc.createDb()

        # Step 2: Create user table
        sqliteFunc.createTable(self.user)
        sqliteFunc.createFactKnowledgeTable(self.factSql)
        sqliteFunc.createTableEpisode(self.episodeSql)
        sqliteFunc.createSentenceTable(self.sentenceSql)

        # Step 3: Create FAISS indices (text + fact)
        faissFunc.makeTwoTypesIndex(user=self.user)
        faissFunc.loadFaissIndex(user=self.user, dim=3072, embedType="sentence")
        
        # Step 4: Find latest dialogue index in DB
        last_record = sqliteFunc.queryLastRecord(self.user)

        if last_record and last_record.get("dia_id"):
            last_dia_id = last_record["dia_id"]  # e.g. "D12:80"
            match = re.match(r"D(\d+):\d+", last_dia_id)
            if match:
                current_num = int(match.group(1))
                self.noDialogue = f"D{current_num + 1}"
            else:
                self.noDialogue = "D1"
        else:
            # If database is empty or no dia_id, start from D1
            self.noDialogue = "D1"

        self.indexEpisode = 1  # The starting index of episode in current dia_id
        self.turnOfDialogue = 1  # The turn of dialogue in current dia_id
        print(f"💬 Latest dialogue index initialized as: {self.noDialogue}")
        print(f"✅ AMA initialization complete for user: {self.user_id}\n")

    def countMemoryTokens(self, model: str = "gpt-4o-mini") -> int:
        """
        Count the total number of tokens currently stored in the memory window.

        Args:
        -----
        model_name : str, optional
            Name of the model to use for tokenization (default: gpt-4o-mini).

        Returns:
        --------
        int
            Total number of tokens across all memory items.
        """
        # Ensure window not empty
        if not self.memoryWindow:
            print("⚠️ Memory window is empty — token count = 0")
            return 0

        try:
            # Load tokenizer
            encoding = tiktoken.encoding_for_model(model)
        except Exception:
            # If model is unknown, use general encoder
            print(f"⚠️ Unknown model '{model}', using cl100k_base tokenizer instead.")
            encoding = tiktoken.get_encoding("cl100k_base")

        total_tokens = 0

        for idx, mem in enumerate(self.memoryWindow):
            # Serialize each memory object to string
            json_str = json.dumps(mem, ensure_ascii=False)
            num_tokens = len(encoding.encode(json_str))
            total_tokens += num_tokens
            print(f"🧩 Memory[{idx}] = {num_tokens} tokens")

        print(f"🧠 Total tokens in memory window: {total_tokens}")
        return total_tokens
    
    def clearMemoryWindow(self):
        # Clear the memoryWindow
        self.memoryWindow = deque()

    def clearAllMemory(self):
        # Clear all memory from both SQLite and FAISS
        sqliteFunc.deleteTable(self.user)
        sqliteFunc.deleteTable(self.sentenceSql)
        sqliteFunc.deleteTable(self.episodeSql)
        sqliteFunc.deleteTable(self.factSql)
        faissFunc.deleteUserFaissIndices(self.user)
        self.clearMemoryWindow()
        print(f"🗑️ Cleared all memory for user: {self.user_id}")
    
    def adjustMemoryWindow(self, model: str = "gpt-4o-mini"):
        """
        Dynamically adjust the memory window size based on both record count and total token usage.

        Rules:
        ----
        1. If len(memoryWindow) > lengthOfMemoryWindow * 2 → trigger shrinking;
        2. If countMemoryTokens() > SizeOfMemoryWindow → trigger shrinking;
        3. When shrinking, prioritize removing oldest records (pop from left) until both conditions are met.
        """

        if not self.memoryWindow:
            print("⚠️ Memory window is empty — no adjustment needed.")
            return

        # === 1. Get current statistics ===
        total_tokens = self.countMemoryTokens(model=model)
        record_count = len(self.memoryWindow)

        # === 2. Set thresholds ===
        max_records = int(self.lengthOfMemoryWindow * 2)
        max_tokens = int(self.SizeOfMemoryWindow)

        print(f"📊 Memory check → {record_count} records, {total_tokens} tokens.")
        print(f"🧩 Limits → max_records={max_records}, max_tokens={max_tokens}")

        # === 3. Check if cleanup is needed ===
        if record_count <= max_records and total_tokens <= max_tokens:
            print("✅ Memory window within limits. No adjustment needed.")
            return

        # === 4. Execute shrinking logic ===
        removed = 0
        while len(self.memoryWindow) > self.lengthOfMemoryWindow or total_tokens > max_tokens:
            oldest = self.memoryWindow.popleft()
            removed += 1

            # Update token count in real-time (calling countMemoryTokens is too heavy)
            oldest_tokens = len(
                tiktoken.encoding_for_model(model).encode(json.dumps(oldest, ensure_ascii=False))
            )
            total_tokens -= oldest_tokens
            if total_tokens < 0:
                total_tokens = 0

            # Early termination check
            if len(self.memoryWindow) <= self.lengthOfMemoryWindow and total_tokens <= max_tokens:
                break

        print(f"⚠️ Memory window adjusted → removed {removed} oldest records.")
        print(f"📉 After adjustment: {len(self.memoryWindow)} records, {total_tokens} tokens remaining.")


    def retrieve(self, operator: int, input: str = None, topK: int = 10):
        """
        Retrieve memories based on operator type.
        """
        if operator == 1:
            return self.retrieveSingleChannel(message = input, topK = topK, typeEm="fact")
        elif operator == 2:
            return self.retrieveSingleChannel(message = input, topK = topK, typeEm="text")
        elif operator == 3:
            return self.retrieveDualChannel(message = input, topK = topK)
        else:
            print(f"⚠️ Invalid operator={operator}. Expected 1 or 2 or 3.")
            return []
    
    def retrieveSingleChannel(self, message: str = None, topK: int = 10, typeEm: str = "text"):
        """
        Single-channel retrieval (Operator 2)
        Retrieve in single channel (text or keyword),
        using temperature-scaled softmax (τ=0.07) + μ−σ filtering,
        without writing scores to records.
        """
        if not message:
            print("⚠️ retrieveSingleChannel() requires at least one of `message`.")
            return []

        # === 1. Retrieval channel ===
        print(f"🔍 [Single-channel: fact] user={self.user}, topK={topK}")

        if typeEm == "text":
            numK = topK
        elif typeEm == "fact":
            numK = int(topK*2.5)
        # === 2. FAISS retrieval ===
        idList, scoreList = faissFunc.searchFaissIndex(
            user = self.user,
            queryText = message,
            topK = numK,
            embedType= typeEm
        )
        print("Retrieved results from FAISS index.IDs:", idList)

        if not idList or not scoreList:
            print("⚠️ No results found in FAISS index.")
            return []

        # === 3. Query database ===
        if typeEm == "text":
            records = sqliteFunc.queryByIdList(user=self.user, idList=idList)
        elif typeEm == "fact":
            records = sqliteFunc.queryByIdList(user=self.factSql, idList=idList)
        else:
            print(f"⚠️ Invalid typeEm={typeEm}. Expected 'text' or 'fact'.")

        return records

    def retrieveDualChannel(self, message: str = None, topK: int = 10):
        """
        Dual-channel retrieval (Operator 3, simplified)
        Retrieve from both text and keyword channels simultaneously.
        No softmax filtering, no deduplication or merging.
        Keep complete retrieval results for Filter-Agent to process.
        """

        if not message :
            print("⚠️ retrieveDualChannel() requires at least one of `message` or `fact`.")
            return {"text_match_results": [], "fact_match_results": []}

        print(f"🔍 [Dual-channel:text+fact] user={self.user}, topK={topK}")

        # === 1. FAISS dual-channel retrieval ===
        textIds, textScores = faissFunc.searchFaissIndex(
            user=self.user,
            queryText=message,
            topK = topK,
            embedType="text"
        )

        factIds, factScores = faissFunc.searchFaissIndex(
            user=self.user,
            queryText=message,
            topK = int(topK*2.5),
            embedType="fact"
        )

        # === 2. Query SQLite database ===
        textRecords = sqliteFunc.queryByIdList(user=self.user, idList=textIds)
        factRecords = sqliteFunc.queryByIdList(user=self.factSql, idList=factIds)

        print(f"✅ Retrieved results: text({len(textRecords)}) + fact({len(factRecords)}).")

        # === 3. Return complete structure ===
        return {
            "text_match_results": textRecords,
            "fact_match_results": factRecords
        }

    def refresh(self, operator: int, data):
        """
        Refresh memory dispatcher.
        Operator mapping:
          4 = Update
          5 = Delete
        """

        # Dispatch operator
        if operator == 4:
            return self.refreshUpdate(data)
        elif operator == 5:
            return self.refreshDelete(data)
        else:
            print(f"⚠️ Invalid operator={operator}. Expected 4 or 5.")
            return False

    def refreshUpdate(self, data):
        """
        Update multiple memory records (Operator 4)
        Batch update existing memory records and sync update FAISS index.
        """
        if not data:
            print("⚠️ Update needs data items.")
            return False

        items = data.get("dataList")
        timestamp = data.get("timestamp")
        for item in items:
            id = item["id"]
            resultText = sqliteFunc.queryById(user=self.factSql, recordId=id)
            contentFact = resultText["content"]
            contentTem = item["new_content"]
            content = f"Fact knowledge: < {contentFact} > has been updated to < {contentTem} >, timestamp:{timestamp}"
            sqliteFunc.updateMetaOnly(user=self.factSql, recordId=id, new_meta=content)

            noText = resultText["diaNO"]
            sqliteFunc.updateMetaOnly(user=self.user, recordId=noText, new_meta=content)
            resultEpisode = sqliteFunc.queryById(user=self.user, recordId=noText)
            noEpisode = resultEpisode["episode"]
            sqliteFunc.updateMetaOnly(user=self.episodeSql, recordId=noEpisode, new_meta=content)

        return True

    def refreshDelete(self, data):
        """
        Delete multiple memory records (Operator 5)
        Batch delete memories (sync delete from both SQLite and FAISS).

        Args:
            idList (list): List of record IDs to delete, e.g. [1, 5, 9]
        """
        if not data:
            print("⚠️ Delete requires data items.")
            return False

        items = data.get("dataList")
        timestamp = data.get("timestamp")
        for item in items:
            id = item["id"]
            resultText = sqliteFunc.queryById(user=self.factSql, recordId=id)
            contentFact = resultText["content"]
            content = f"Fact knowledge: < {contentFact} > has been deleted, timestamp:{timestamp}"
            sqliteFunc.updateMetaOnly(user=self.factSql, recordId=id, new_meta=content)
            
            noText = resultText["diaNO"]
            sqliteFunc.updateMetaOnly(user=self.user, recordId=noText, new_meta=content)
            resultEpisode = sqliteFunc.queryById(user=self.user, recordId=noText)
            noEpisode = resultEpisode["episode"]
            sqliteFunc.updateMetaOnly(user=self.episodeSql, recordId=noEpisode, new_meta=content)

        return True

    def constructFullWrite(self, data: dict):
        # ========== 1. Parse fields ==========
        user = self.user
        content = data.get("content", "")
        fact = data.get("fact", "")
        source = data.get("source", "user")
        related_id = data.get("related_id", None)
        dia_id = data.get("dia_id", None)
        timestamp = data.get("timestamp")
        episode = data.get("episode", None)
        meta = data.get("meta", "")

        # ========== 2. Auto-fill timestamp ==========
        if not timestamp or timestamp == "empty":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ========== 3. Convert JSON / list ==========
        if isinstance(related_id, list):
            related_id = json.dumps(related_id)
        if isinstance(meta, dict):
            meta = json.dumps(meta)

        # ========== 4. Write to database ==========
        conn = sqlite3.connect(sqliteFunc.get_db_path(), timeout=10)
        cursor = conn.cursor()

        cursor.execute(f"""
            INSERT INTO {user} 
            (content, fact, source, related_id, dia_id, timestamp, episode, meta)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (content, fact, source, related_id, dia_id, timestamp, episode, meta))

        conn.commit()
        recordId = cursor.lastrowid
        faissFunc.addToFaissIndex(user = self.user, text = content, id = recordId, embedType="text")
        print(f"✅ FullWrite: record {recordId} inserted into '{user}' successfully.")

        conn.close()
        return recordId

    def constructFactWrite(self, data: dict):
        # ---------- 1. Basic fields ----------
        user = self.factSql
        facts = data.get("facts", [])
        timestamp = data.get("timestamp")
        meta = data.get("meta", "")
        dia_id = data.get("dia_id", "")
        dia_NO = data.get("dia_NO","")

        if not user or not facts:
            print("⚠️ Missing user or facts; nothing to write.")
            return []

        # ---------- 2. Auto-fill timestamp ----------
        if not timestamp or timestamp == "empty":
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ---------- 3. Unify meta format ----------
        if isinstance(meta, dict):
            meta = json.dumps(meta)

        # ---------- 4. Construct batch data ----------
        batch_data = []
        content_data = []
        for f in facts:
            entry = {
                "content": f['content'],
                "dia_id": dia_id,
                "dia_NO": dia_NO,
                "timestamp": timestamp,
                "meta": meta
            }
            batch_data.append(entry)
            content_data.append(entry.get("content"))

        # ---------- 5. Write to database ----------
        conn = sqlite3.connect(sqliteFunc.get_db_path(), timeout=10)
        cursor = conn.cursor()

        inserted_ids = []
        for entry in batch_data:

            cursor.execute(f"""
                INSERT INTO {user} (content, diaNO, dia_id, timestamp, meta)
                VALUES (?, ?, ?, ?, ?);
            """, (
                entry["content"],
                dia_NO,
                dia_id,
                timestamp,
                meta,
            ))

            inserted_ids.append(cursor.lastrowid)
        
        faissFunc.addBatchToFaissIndex(user = self.user, texts = content_data,ids = inserted_ids)
        conn.commit()
        conn.close()

        print(f"✅ FactWrite: inserted {len(inserted_ids)} records into '{user}' successfully.")
        return inserted_ids

    def constructEpisodicWrite(self, data):
        user = self.episodeSql
        text = data.get("content", "")
        content = json.dumps(data)
        meta = ""
        sentenceList = split_sentences(text)
        recordId = sqliteFunc.insertRecordEpisode(user, content, meta)

        conn = sqlite3.connect(sqliteFunc.get_db_path(), timeout=10)
        cursor = conn.cursor()

        sentenceIdList = []
        for sentence in sentenceList:
            cursor.execute(f'''
                INSERT INTO {self.sentenceSql} (content, episodeID)
                VALUES (?, ?);
            ''', (
                sentence,
                recordId,
            ))

            sentenceIdList.append(cursor.lastrowid)

        faissFunc.addBatchToSentencesIndex(user = self.user, texts = sentenceList, ids = sentenceIdList)
        conn.commit()
        conn.close()

        print(f"✅ EpisodeWrite: inserted 1 record into '{user}' successfully.")

    def queryLastRecord(self, user: str):
        """
        Query the last inserted memory record for this user.
        """
        record = sqliteFunc.queryLastRecord(user=user)
        if record:
            print(f"🕵️ Last record for user '{user}': ID={record['id']}")
        else:
            print(f"⚠️ No records found for user '{user}'.")
        return record

    def forwardUser(self, userInput, showUsage: bool = False):
        """
        Forward pipeline: from retrieval → Judge -> refresh → construct.
        Integrate the entire AMA process, from user input to memory update.
        """
        print("\n===============================")
        print(f"🚀 AMA Forward Start | User: {self.user}")
        print("===============================")

        if isinstance(userInput, dict):
            userInput = json.dumps(userInput)
        elif isinstance(userInput, str):
            pass

        # === 1. Retrieval stage ===
        retrieve_decision = self.memoryAgent.inferenceRetrieve(
            memoryWindow=list(self.memoryWindow),
            userInput=userInput,
            showUsage=showUsage
        )

        operator_r = retrieve_decision.get("operator", 1)
        retrievals = []

        retrievals = self.retrieve(
                operator = operator_r,
                input = retrieve_decision.get("retrieveQuery",""),
                topK = retrieve_decision.get("topK", 10),
        )

        print("Retrieval results:")
        if operator_r == 1 or operator_r == 2:
            for item in retrievals:
                print(item)
                print("\n")
        elif operator_r == 3:
            print("Text match results:")
            for item in retrievals.get("text_match_results", []):
                print(item)
                print("\n")

            print("fact match results:")
            for thing in retrievals.get("fact_match_results", []):
                print(thing)
                print("\n")

        turnRetrieve = 1
        judge_decision = self.memoryAgent.inferenceJudge(
            retrievals = retrievals,
            memoryWindow = list(self.memoryWindow),
            userInput = userInput,
            showUsage = showUsage,
        )

        operator_j = judge_decision.get("operator", -1)

        operator_more = 0
        if operator_j == -1:
            pass
        elif operator_j == 9:
            while turnRetrieve < self.turnOfRetrieve and operator_j == 9:
                if operator_r != 3:
                    operator_r = 3
                    retrievals = self.retrieve(
                        operator = operator_r,
                        input = retrieve_decision.get("retrieveQuery",""),
                        topK = retrieve_decision.get("topK", 10),
                    )

                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )

                    operator_j = judge_decision.get("operator", -1)
                    turnRetrieve += 1
                elif operator_r == 3 and operator_more == 0:
                    queryEpisode = retrieve_decision.get("retrieveQuery","")
                    num = retrieve_decision.get("topK", 10)
                    idListEpisodeSentence,distanceList = faissFunc.searchFaissIndex(user=self.user, queryText=queryEpisode, topK=num, embedType="sentence")

                    resultSentence = sqliteFunc.queryByIdList(self.sentenceSql, idListEpisodeSentence)

                    listEpisode = []
                    for item in resultSentence:
                        listEpisode.append(item["episodeID"])

                    unique_episode = list(dict.fromkeys(listEpisode))

                    episodes = sqliteFunc.queryByIdList(self.episodeSql, unique_episode)

                    retrievals["episodes_results"] = episodes

                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )

                    operator_j = judge_decision.get("operator", -1)
                    turnRetrieve += 1
                    operator_more = 1

                elif operator_r == 3 and operator_more == 1:
                    fact_retrival = retrievals.get("fact_match_results", [])
                    textMoreList = []
                    text_retrival = retrievals.get("text_match_results", [])

                    for item in text_retrival:
                        textMoreList.append(item["id"])
    
                    for item in fact_retrival:
                        textMoreList.append(item["diaNO"])

                    unique_text = list(dict.fromkeys(textMoreList))

                    textMore = sqliteFunc.queryByIdList(self.user, unique_text)

                    retrievals["text_match_results"] = []
                    retrievals["text_match_results"] = textMore

                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )
                    turnRetrieve += 1
                    operator_more = 2
                    operator_j = judge_decision.get("operator", -1)
                elif operator_r == 3 and operator_more == 2 :
                    text_retrival = retrievals.get("text_match_results", [])
                    idList = []
                    for item in text_retrival:
                        if item["id"] > 1:
                            idList.append(item["id"] - 1)
                            idList.append(item['id'])
                            idList.append(item['id'] + 1)
                        else:
                            idList.append(item['id'])
                            idList.append(item['id'] + 1)

                    unique_text = list(dict.fromkeys(idList))

                    textMore = sqliteFunc.queryByIdList(self.user, unique_text)

                    retrievals["text_match_results"] = []
                    retrievals["text_match_results"] = textMore
                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )
                    turnRetrieve += 1
                    operator_j = judge_decision.get("operator", -1)

        if operator_j == -2:
            if operator_r == 1:
                refresh_decision = self.memoryAgent.inferenceRefresh(
                    retrievals=retrievals,
                    userInput=userInput,
                    showUsage=showUsage
                )

                operator_f = refresh_decision.get("operator", -1)

                if operator_f == -1:
                    pass
                else:
                    self.refresh(operator_f, refresh_decision) 

            elif operator_r == 2:
                text_retrival = retrievals
                fact_list = []
                for item in text_retrival:
                    fact = item["fact"]
                    fact = json.loads(fact)
                    for f in fact:
                        fact_list.append(f)
                refresh_decision = self.memoryAgent.inferenceRefresh(
                    retrievals=fact_list,
                    userInput=userInput,
                    showUsage=showUsage
                )

                operator_f = refresh_decision.get("operator", -1)

                if operator_f == -1:
                    pass
                else:
                    self.refresh(operator_f, refresh_decision) 

            elif operator_r == 3:
                fact_retrival = retrievals.get("fact_match_results", [])
                refresh_decision = self.memoryAgent.inferenceRefresh(
                    retrievals=fact_retrival,
                    userInput=userInput,
                    showUsage=showUsage
                )

                operator_f = refresh_decision.get("operator", -1)

                if operator_f == -1:
                    pass
                else:
                    self.refresh(operator_f, refresh_decision)
 
        def run_judgeEpisode():
            inferenceDecision = self.memoryAgent.inferenceJudgeEpisode(list(self.memoryWindow), userInput, showUsage)
            operator_e = inferenceDecision.get("should_end", False)
            reason = inferenceDecision.get("reason", "")
            return {
                "operator_e" : operator_e,
                "reason" : reason
            }

        def ConstructFactAndRaw():
            factData = self.memoryAgent.inferenceConstruct(list(self.memoryWindow),retrievals=retrievals, userInput=userInput, showUsage=showUsage)
            factData["dia_id"] = f"{self.noDialogue}:{self.turnOfDialogue}"
            factData['meta'] = ""
            res =  self.queryLastRecord(self.user)
            if res is not None:
                factData['dia_NO'] = res['id'] + 1
            else:
                factData['dia_NO'] = 1

            factids = self.constructFactWrite(factData)

            epi = self.queryLastRecord(self.episodeSql)
            if epi is not None:
                factData['episode'] = epi['id'] + 1
            else:
                factData['episode'] = 1

            factlist = factData.get("facts", [])
            listFact = []

            index = 0
            for f in factlist:
                con = f['content']
                conId = factids[index]
                index += 1
                listFact.append({f"id:{conId}":con})

            inputTem = ""
            inputOfUser = None
            if isinstance(userInput, dict):
                inputOfUser = userInput
            elif isinstance(userInput, str):
                stripped = userInput.strip()
                if stripped.startswith("{") and stripped.endswith("}"):
                    try:
                        parsed = json.loads(userInput)
                        if isinstance(parsed, dict):
                            inputOfUser = parsed
                    except Exception:
                        inputOfUser = None

            if (
                inputOfUser is not None
                and inputOfUser.get("speaker") is not None
                and inputOfUser.get("text") is not None
            ):
                speaker = inputOfUser.get("speaker")
                text = inputOfUser.get("text")
                inputTem = f"{speaker}: {text}\n"

                if inputOfUser.get("img_url") is not None:
                    inputTem = inputTem + f"img_url: {inputOfUser.get('img_url')}\n"
                if inputOfUser.get("blip_caption") is not None:
                    inputTem = inputTem + f"blip_caption: {inputOfUser.get('blip_caption')}\n"
                if inputOfUser.get("query") is not None:
                    inputTem = inputTem + f"img_query: {inputOfUser.get('query')}\n"
            else:
                inputTem = userInput if isinstance(userInput, str) else json.dumps(userInput, ensure_ascii=False)

            listFact = json.dumps(listFact)
            rawData = {
                "timestamp": factData.get("timestamp"),
                "content": inputTem,
                "related_id": factData.get("related_id"),
                "source": factData.get("source"),
                "meta": "",
                "dia_id": factData.get("dia_id"),
                "episode": factData.get("episode"),
                "fact" : listFact,
            }

            self.constructFullWrite(rawData)

        # === Parallel execution of two stages ===
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_judge = executor.submit(run_judgeEpisode)
            future_construct = executor.submit(ConstructFactAndRaw)
            judgeEpisode_decision = future_judge.result()
            construct_decision = future_construct.result()

        operator_e = judgeEpisode_decision.get("operator_e")
        
        if operator_e == "true":
            EpisodeCon = self.memoryAgent.inferenceGenerateEpisode(list(self.memoryWindow), judgeEpisode_decision.get("reason"), showUsage)
            self.constructEpisodicWrite(data=EpisodeCon)
        else:
            pass

        # === 4. Update short-term memory window ===

        output = "Retrieval results:\n" + json.dumps(retrievals) + "\nMemory Window:\n" + json.dumps(list(self.memoryWindow))
        self.retrieveContents = retrievals
        print("===============================")
        print(f"✅ AMA Forward Complete | Dialogue turn = {self.turnOfDialogue}")
        print("===============================\n")

        print("Retrieval results:\n",retrievals)
        print("Memory Window:\n",self.memoryWindow)

        self.memoryWindow.append({
            "role": "user",
            "content": userInput,
            "dia_id": f"{self.noDialogue}:{self.turnOfDialogue}",
        })
        self.adjustMemoryWindow()

        self.turnOfDialogue += 1
        
        return output

    def forwardRobot(self, robotOutput: str, showUsage: bool = False, timeInput: str = None):
        """
        Forward pipeline for assistant output: only the Construct stage.
        Execute only the construct stage, used to generate or update memory from robot response.

        Args:
            robotOutput (str): Current robot output (assistant reply content).
            showUsage (bool): Whether to display token usage statistics.
            timeInput (str): Optional time string (auto-generate current time if empty).

        Returns:
            dict: Complete information containing Construct stage output.
        """
        print("\n===============================")
        print(f"🤖 AMA Forward (Robot) Start | User: {self.user}")
        print("===============================")


        def ConstructFactAndRaw():
            factData = self.memoryAgent.inferenceConstruct(list(self.memoryWindow), retrievals=self.retrieveContents, userInput="Assitant:" + robotOutput, showUsage=showUsage)
            factData["dia_id"] = f"{self.noDialogue}:{self.turnOfDialogue}"
            factData['meta'] = ""
            res =  self.queryLastRecord(self.user)
            if res is not None:
                factData['dia_NO'] = res['id'] + 1
            else:
                factData['dia_NO'] = 1

            factids = self.constructFactWrite(factData)

            epi = self.queryLastRecord(self.episodeSql)
            if epi is not None:
                factData['episode'] = epi["id"] + 1
            else:
                factData['episode'] = 1

            factlist = factData.get("facts", [])
            listFact = []

            index = 0
            for f in factlist:
                con = f['content']
                conId = factids[index]
                index += 1
                listFact.append({f"id:{conId}":con})

            listFact = json.dumps(listFact)
            rawData = {
                "timestamp": factData.get("timestamp"),
                "content": robotOutput,
                "related_id": factData.get("related_id"),
                "source": factData.get("source"),
                "meta": "",
                "dia_id": factData.get("dia_id"),
                "episode": factData.get("episode"),
                "fact" : listFact,
            }

            self.constructFullWrite(rawData)
            return {
                "status": "success",
                "factCount": len(factlist),
            }
            return {
                "status": "success",
                "factCount": len(factlist),
            }

        construct_decision = ConstructFactAndRaw()
        print(f"🧩 Construct done")

        # === 2. Update timestamp ===
        if timeInput and timeInput != "Unknown time":
            timeWindow = timeInput
        else:
            timeWindow = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())

        # === 3. Update short-term memory window ===
        self.memoryWindow.append({
            "role": "assistant",
            "content": robotOutput,
            "dia_id": f"{self.noDialogue}:{self.turnOfDialogue}",
            "time": timeWindow,
        })
        self.adjustMemoryWindow()

        print("===============================")
        print(f"✅ AMA Forward (Robot) Complete | Dialogue turn = {self.turnOfDialogue}")
        print("===============================\n")

        # === Output result ===
        output = {
            "constructDecision": construct_decision,
            "memoryWindow": list(self.memoryWindow)
        }

        print("Memory Window:\n", self.memoryWindow)
        self.turnOfDialogue += 1
        return output

    def forwardRetrieve(self, userInput: str, showUsage: bool = False, strongRetrieve: bool = False):
        retrieve_decision = self.memoryAgent.inferenceRetrieve(
            memoryWindow=list(self.memoryWindow),
            userInput=userInput,
            showUsage=showUsage
        )

        operator_r = retrieve_decision.get("operator", 1)
        retrievals = []

        if strongRetrieve == True:
            operator_r = 3

        retrievals = self.retrieve(
                operator = operator_r,
                input = retrieve_decision.get("retrieveQuery",""),
                topK = retrieve_decision.get("topK", 10),
        )

        print("Retrieval results:")
        if operator_r == 1 or operator_r == 2:
            for item in retrievals:
                print(item)
                print("\n")
        elif operator_r == 3:
            print("Text match results:")
            for item in retrievals.get("text_match_results", []):
                print(item)
                print("\n")

            print("fact match results:")
            for thing in retrievals.get("fact_match_results", []):
                print(thing)
                print("\n")

        turnRetrieve = 1
        judge_decision = self.memoryAgent.inferenceJudge(
            retrievals = retrievals,
            memoryWindow = list(self.memoryWindow),
            userInput = userInput,
            showUsage = showUsage,
        )

        operator_j = judge_decision.get("operator", -1)

        operator_more = 0
        if operator_j == -1:
            pass
        elif operator_j == 9:
            while turnRetrieve < self.turnOfRetrieve and operator_j == 9:
                if operator_r != 3:
                    operator_r = 3
                    retrievals = self.retrieve(
                        operator = operator_r,
                        input = retrieve_decision.get("retrieveQuery",""),
                        topK = retrieve_decision.get("topK", 10),
                    )

                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )

                    operator_j = judge_decision.get("operator", -1)
                    turnRetrieve += 1
                elif operator_r == 3 and operator_more == 0:
                    queryEpisode = retrieve_decision.get("retrieveQuery","")
                    num = retrieve_decision.get("topK", 10)
                    idListEpisodeSentence,distanceList = faissFunc.searchFaissIndex(user=self.user, queryText=queryEpisode, topK=num, embedType="sentence")

                    resultSentence = sqliteFunc.queryByIdList(self.sentenceSql, idListEpisodeSentence)

                    listEpisode = []
                    for item in resultSentence:
                        listEpisode.append(item["episodeID"])

                    unique_episode = list(dict.fromkeys(listEpisode))

                    episodes = sqliteFunc.queryByIdList(self.episodeSql, unique_episode)

                    retrievals["episodes_results"] = episodes

                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )

                    operator_j = judge_decision.get("operator", -1)
                    turnRetrieve += 1
                    operator_more = 1

                elif operator_r == 3 and operator_more == 1:
                    fact_retrival = retrievals.get("fact_match_results", [])
                    textMoreList = []
                    text_retrival = retrievals.get("text_match_results", [])

                    for item in text_retrival:
                        textMoreList.append(item["id"])
    
                    for item in fact_retrival:
                        textMoreList.append(item["diaNO"])

                    unique_text = list(dict.fromkeys(textMoreList))

                    textMore = sqliteFunc.queryByIdList(self.user, unique_text)

                    retrievals["text_match_results"] = []
                    retrievals["text_match_results"] = textMore

                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )
                    turnRetrieve += 1
                    operator_more = 2
                    operator_j = judge_decision.get("operator", -1)
                elif operator_r == 3 and operator_more == 2 :
                    text_retrival = retrievals.get("text_match_results", [])
                    idList = []
                    for item in text_retrival:
                        if item["id"] > 1:
                            idList.append(item["id"] - 1)
                            idList.append(item['id'])
                            idList.append(item['id'] + 1)
                        else:
                            idList.append(item['id'])
                            idList.append(item['id'] + 1)

                    unique_text = list(dict.fromkeys(idList))

                    textMore = sqliteFunc.queryByIdList(self.user, unique_text)

                    retrievals["text_match_results"] = []
                    retrievals["text_match_results"] = textMore
                    judge_decision = self.memoryAgent.inferenceJudge(
                        retrievals = retrievals,
                        memoryWindow = list(self.memoryWindow),
                        userInput = userInput,
                        showUsage = showUsage,
                    )
                    turnRetrieve += 1
                    operator_j = judge_decision.get("operator", -1)

                
        if operator_r == 3:
            textResult = retrievals.get("text_match_results", [])
            factResult = retrievals.get("fact_match_results", [])

            for item in textResult:
                item['content'] = item['content'] + "\ntimestamp:" + item['timestamp']
                item.pop('timestamp',None)
                item.pop('fact')
                item.pop('source')
            for thing in factResult:
                thing['content'] = thing['content'] + "\ntimestamp:" + thing['timestamp']
                thing.pop('timestamp',None)
                thing.pop('diaNO')
        else:
            Result = retrievals
            for item in Result:
                item['content'] = item['content'] + "\ntimestamp:" + item['timestamp']
                item.pop('timestamp',None)

        print(retrievals)
        # === 4. Construct JSON output ===
        result = {
            "retrievals": retrievals,
            "memoryWindow": list(self.memoryWindow)
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    def judgeAndGenerate(self):
        resText = self.queryLastRecord(self.user)
        numOfEpisode = resText["episode"]
        epiRes = self.queryLastRecord(self.episodeSql)
        if epiRes is None:
            idOfEpisode = 1
        else:
            idOfEpisode = epiRes["id"]

        if numOfEpisode != idOfEpisode:
            EpisodeCon = self.memoryAgent.inferenceGenerateEpisode(list(self.memoryWindow), "The dialogue ends.", showUsage = True)
            self.constructEpisodicWrite(data=EpisodeCon)



if __name__ == "__main__":
    pass
