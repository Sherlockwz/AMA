import json
import os
import statistics
from collections import defaultdict
from typing import Dict, List, Union, Optional, Any
import requests
import nltk
from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
import dotenv

dotenv.load_dotenv()

# Download required NLTK data
try:
    nltk.download("punkt", quiet=True)
    nltk.download("wordnet", quiet=True)
    nltk.download("punkt_tab", quiet=True)
except Exception as e:
    print(f"Error downloading NLTK data: {e}")

class LocomoEvaluator:
    """LoCoMo Evaluator with three metrics: F1, BLEU, and LLM Judge"""
    
    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize the evaluator
        """
        self.api_key = api_key or os.getenv("AMA_LLM_API_KEY", "")
        self.api_url = api_url or os.getenv("AMA_LLM_BASE_URL", "")
        
        # LLM Judge prompt template
        self.accuracy_prompt = """
        Your task is to label an answer to a question as 'CORRECT' or 'WRONG'. You will be given the following data:
            (1) a question (posed by one user to another user), 
            (2) a 'gold' (ground truth) answer, 
            (3) a generated answer
        which you will score as CORRECT/WRONG.

        The point of the question is to ask about something one user should know about the other user based on their prior conversations.
        The gold answer will usually be a concise and short answer that includes the referenced topic, for example:
        Question: Do you remember what I got the last time I went to Hawaii?
        Gold answer: A shell necklace
        The generated answer might be much longer, but you should be generous with your grading - as long as it touches on the same topic as the gold answer, it should be counted as CORRECT. 

        For time related questions, the gold answer will be a specific date, month, year, etc. The generated answer might be much longer or use relative time references (like "last Tuesday" or "next month"), but you should be generous with your grading - as long as it refers to the same date or time period as the gold answer, it should be counted as CORRECT. Even if the format differs (e.g., "May 7th" vs "7 May"), consider it CORRECT if it's the same date.

        Now it's time for the real question:
        Question: {question}
        Gold answer: {gold_answer}
        Generated answer: {generated_answer}

        First, provide a short (one sentence) explanation of your reasoning, then finish with CORRECT or WRONG. 
        Do NOT include both CORRECT and WRONG in your response, or it will break the evaluation script.

        Just return the label CORRECT or WRONG in a json format with the key as "label".
        """

    def simple_tokenize(self, text: str) -> List[str]:
        """Simple tokenization function"""
        text = str(text)
        return text.lower().replace(".", " ").replace(",", " ").replace("!", " ").replace("?", " ").split()

    def calculate_f1_score(self, prediction: str, reference: str) -> float:
        """
        Calculate token-based F1 score
        
        Args:
            prediction: Predicted answer
            reference: Reference answer
            
        Returns:
            F1 score (0.0-1.0)
        """
        if not prediction or not reference:
            return 0.0
            
        prediction = str(prediction).strip()
        reference = str(reference).strip()
        
        # Calculate token sets
        pred_tokens = set(self.simple_tokenize(prediction))
        ref_tokens = set(self.simple_tokenize(reference))
        common_tokens = pred_tokens & ref_tokens
        
        if not pred_tokens or not ref_tokens:
            return 0.0
            
        precision = len(common_tokens) / len(pred_tokens)
        recall = len(common_tokens) / len(ref_tokens)
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        return f1

    def calculate_bleu_score(self, prediction: str, reference: str) -> Dict[str, float]:
        """
        Calculate BLEU scores (multiple n-gram settings)
        
        Args:
            prediction: Predicted answer
            reference: Reference answer
            
        Returns:
            Dictionary containing different n-gram BLEU scores
        """
        if not prediction or not reference:
            return {"bleu1": 0.0, "bleu2": 0.0, "bleu3": 0.0, "bleu4": 0.0}
            
        prediction = str(prediction).strip()
        reference = str(reference).strip()
        
        pred_tokens = nltk.word_tokenize(prediction.lower())
        ref_tokens = [nltk.word_tokenize(reference.lower())]
        
        weights_list = [(1, 0, 0, 0), (0.5, 0.5, 0, 0), (0.33, 0.33, 0.33, 0), (0.25, 0.25, 0.25, 0.25)]
        smooth = SmoothingFunction().method1
        
        scores = {}
        for n, weights in enumerate(weights_list, start=1):
            try:
                score = sentence_bleu(ref_tokens, pred_tokens, weights=weights, smoothing_function=smooth)
            except Exception as e:
                print(f"Error calculating BLEU score: {e}")
                score = 0.0
            scores[f"bleu{n}"] = score
            
        return scores

    def evaluate_llm_judge(self, question: str, gold_answer: str, generated_answer: str) -> int:
        """
        Use LLM as a judge to evaluate answer quality
        
        Args:
            question: Question
            gold_answer: Reference answer
            generated_answer: Generated answer
            
        Returns:
            1 for correct, 0 for wrong
        """
        if not self.api_key:
            print("Warning: No API key provided for LLM judge evaluation")
            return 0
            
        # Prepare request headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # Prepare data
        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert grader that determines if answers to questions match a gold standard answer.",
                },
                {
                    "role": "user",
                    "content": self.accuracy_prompt.format(
                        question=question, gold_answer=gold_answer, generated_answer=generated_answer
                    ),
                }
            ],
            "temperature": 0.0,
        }
        
        try:
            # Send request
            response = requests.post(
                url=self.api_url,
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
            
            response.raise_for_status()
            response_json = response.json()
            
            # Parse response
            content = response_json["choices"][0]["message"]["content"]
            try:
                # Try to parse as JSON
                label_data = json.loads(content)
                label = label_data["label"]
            except json.JSONDecodeError:
                # If not JSON, search for CORRECT/WRONG in text
                if "CORRECT" in content.upper():
                    label = "CORRECT"
                elif "WRONG" in content.upper():
                    label = "WRONG"
                else:
                    # If unclear, default to WRONG
                    label = "WRONG"
                    
            return 1 if label == "CORRECT" else 0
            
        except Exception as e:
            print(f"Error in LLM judge evaluation: {e}")
            return 0

    def evaluate_single(self, question: str, gold_answer: str, generated_answer: str) -> Dict[str, Any]:
        """
        Evaluate all metrics for a single QA pair
        
        Args:
            question: Question
            gold_answer: Reference answer
            generated_answer: Generated answer
            
        Returns:
            Dictionary containing all evaluation metrics
        """
        # Calculate F1 score
        f1_score = self.calculate_f1_score(generated_answer, gold_answer)
        
        # Calculate BLEU scores
        bleu_scores = self.calculate_bleu_score(generated_answer, gold_answer)
        
        # Calculate LLM Judge score
        llm_score = self.evaluate_llm_judge(question, gold_answer, generated_answer)
        
        return {
            "f1_score": f1_score,
            "bleu1_score": bleu_scores["bleu1"],
            "bleu2_score": bleu_scores["bleu2"],
            "bleu3_score": bleu_scores["bleu3"],
            "bleu4_score": bleu_scores["bleu4"],
            "llm_score": llm_score,
            "question": question,
            "gold_answer": gold_answer,
            "generated_answer": generated_answer
        }

    def evaluate_batch(self, data: List[Dict[str, Any]], skip_category_5: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch evaluate data
        
        Args:
            data: List of evaluation data, each element contains question, answer, response, category fields
            skip_category_5: Whether to skip data with category 5
            
        Returns:
            Evaluation results grouped by category
        """
        results = defaultdict(list)
        
        index = 1
        for item in data:
            question = str(item["question"])
            gold_answer = str(item["answer"])
            generated_answer = str(item["response"])
            category = str(item["category"])
            
            # Skip category 5
            if skip_category_5 and category == "5":
                continue
                
            # Evaluate single item
            evaluation_result = self.evaluate_single(question, gold_answer, generated_answer)
            evaluation_result["category"] = category
            
            results[category].append(evaluation_result)
            if index % 25 == 0:
                print(f"Evaluated {index} items")
            index += 1
            
        return dict(results)

    def calculate_statistics(self, results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, Union[float, Dict[str, float]]]]:
        """
        Calculate statistics
        
        Args:
            results: Evaluation results
            
        Returns:
            Dictionary containing statistics
        """
        # Collect all metrics
        all_metrics = []
        all_categories = []
        
        for category, items in results.items():
            for item in items:
                all_metrics.append({
                    "f1_score": item["f1_score"],
                    "bleu1_score": item["bleu1_score"],
                    "bleu2_score": item["bleu2_score"],
                    "bleu3_score": item["bleu3_score"],
                    "bleu4_score": item["bleu4_score"],
                    "llm_score": item["llm_score"]
                })
                all_categories.append(int(category))
        
        if not all_metrics:
            return {}
            
        # Initialize aggregation
        aggregates = defaultdict(list)
        category_aggregates = defaultdict(lambda: defaultdict(list))
        
        # Collect values for each metric
        for metrics, category in zip(all_metrics, all_categories):
            for metric_name, value in metrics.items():
                aggregates[metric_name].append(value)
                category_aggregates[category][metric_name].append(value)
        
        # Calculate overall statistics
        overall_results = {}
        for metric_name, values in aggregates.items():
            overall_results[metric_name] = {
                "mean": statistics.mean(values),
                "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                "median": statistics.median(values),
                "min": min(values),
                "max": max(values),
                "count": len(values),
            }
        
        # Calculate statistics for each category
        category_results = {}
        for category in sorted(category_aggregates.keys()):
            category_results[f"category_{category}"] = {}
            for metric_name, values in category_aggregates[category].items():
                if values:
                    category_results[f"category_{category}"][metric_name] = {
                        "mean": statistics.mean(values),
                        "std": statistics.stdev(values) if len(values) > 1 else 0.0,
                        "median": statistics.median(values),
                        "min": min(values),
                        "max": max(values),
                        "count": len(values),
                    }
        
        return {
            "overall": overall_results,
            **category_results
        }

    def print_summary(self, statistics: Dict[str, Dict[str, Union[float, Dict[str, float]]]]):
        """
        Print evaluation results summary
        
        Args:
            statistics: Statistics results
        """
        print("=== LoCoMo Evaluation Results Summary ===")
        
        # Print overall results
        if "overall" in statistics:
            print("\nOverall Average Scores:")
            overall = statistics["overall"]
            print(f"  F1: {overall['f1_score']['mean']:.4f}")
            print(f"  BLEU-1: {overall['bleu1_score']['mean']:.4f}")
            print(f"  BLEU-2: {overall['bleu2_score']['mean']:.4f}")
            print(f"  BLEU-3: {overall['bleu3_score']['mean']:.4f}")
            print(f"  BLEU-4: {overall['bleu4_score']['mean']:.4f}")
            print(f"  LLM Judge: {overall['llm_score']['mean']:.4f}")
        
        # Print results for each category
        print("\nAverage Scores by Category:")
        for key, value in statistics.items():
            if key.startswith("category_"):
                category = key.replace("category_", "")
                print(f"  Category {category}:")
                print(f"    F1: {value['f1_score']['mean']:.4f}")
                print(f"    BLEU-1: {value['bleu1_score']['mean']:.4f}")
                print(f"    LLM Judge: {value['llm_score']['mean']:.4f}")


def main():

    output_file = "./outputForLocomo/output_locomo_merged.json"

    # ---------- Read and merge files ----------
    merged = []

    for i in range(1, 11):  # From 1 to 10
        file_name = f"./outputForLocomo/output_locomo_{i}.json"
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                data = json.load(f)
                merged.extend(data)
            print(f"✅ Loaded {file_name} ({len(data)} records)")
        except FileNotFoundError:
            print(f"⚠️ File {file_name} not found, skipping.")
        except json.JSONDecodeError as e:
            print(f"❌ File {file_name} JSON parsing error: {e}")

    # ---------- Re-index ----------
    for idx, item in enumerate(merged, start=1):
        item["index"] = idx

    # ---------- Write output ----------
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Merge completed, total {len(merged)} records, output file: {output_file}")

    # ---------- Optional: Read sample ----------
    with open(output_file, "r", encoding="utf-8") as f:
        sample = json.load(f)

    """Example usage"""
    # Create evaluator
    evaluator = LocomoEvaluator()
    
    sample_data = sample
    # Batch evaluate
    results = evaluator.evaluate_batch(sample_data)
    
    # Calculate statistics
    stats = evaluator.calculate_statistics(results)
    
    # Print results
    evaluator.print_summary(stats)


if __name__ == "__main__":
    main()
