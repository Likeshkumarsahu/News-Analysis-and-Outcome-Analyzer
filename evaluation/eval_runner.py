"""
Run this independently to evaluate the pipeline.
Usage: python evaluation/eval_runner.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluation.ragas_eval import run_evaluation, print_scores

print("Starting RAGAS evaluation...")
scores = run_evaluation()
if scores:
    print_scores(scores)
else:
    print("Evaluation failed — check logs above.")