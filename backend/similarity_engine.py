"""
backend/similarity_engine.py

Core NLP engine for comparing semantic similarity of text using Sentence Transformers.
"""

from typing import List, Tuple
import numpy as np

try:
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
except ImportError:
    SentenceTransformer = None
    cosine_similarity = None

from .utils import FileProcessingError


class SimilarityEngine:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the sentence transformer model.
        'all-MiniLM-L6-v2' is chosen for a good balance of speed and accuracy.
        """
        if SentenceTransformer is None:
            raise FileProcessingError(
                "sentence-transformers or scikit-learn is not installed. Cannot run Similarity Engine."
            )
        
        # Load the model (downloads automatically on first run if not cached)
        self.model = SentenceTransformer(model_name)

    def get_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Returns embeddings for a list of text segments.
        """
        if not texts:
            return np.array([])
        return self.model.encode(texts, show_progress_bar=False)

    def compare_embeddings(self, embeddings1: np.ndarray, embeddings2: np.ndarray) -> np.ndarray:
        """
        Computes cosine similarity matrix between two sets of embeddings.
        """
        if len(embeddings1) == 0 or len(embeddings2) == 0:
            return np.array([[]])
        
        return cosine_similarity(embeddings1, embeddings2)

    def find_similar_paragraphs(self, 
                                paras1: List[str], 
                                paras2: List[str], 
                                threshold: float = 0.75) -> Tuple[List[dict], float]:
        """
        Compares two lists of paragraphs and returns highly similar pairs
        and an overall similarity metric based on paragraph overlap.
        
        Returns:
            - matches: List of dicts with 'para1', 'para2', and 'score'
            - overall_similarity: float between 0 and 1
        """
        if not paras1 or not paras2:
            return [], 0.0

        embeds1 = self.get_embeddings(paras1)
        embeds2 = self.get_embeddings(paras2)

        sim_matrix = self.compare_embeddings(embeds1, embeds2)
        
        matches = []
        matched_indices1 = set()
        matched_indices2 = set()

        # Find best match for each paragraph in doc 1
        for i, row in enumerate(sim_matrix):
            best_idx = np.argmax(row)
            best_score = float(row[best_idx])
            
            if best_score >= threshold:
                matches.append({
                    'para1': paras1[i],
                    'para2': paras2[best_idx],
                    'score': best_score,
                    'idx1': i,
                    'idx2': best_idx
                })
                matched_indices1.add(i)
                matched_indices2.add(best_idx)

        # Calculate a weighted overall similarity.
        # This is a basic approach: average of the best scores for paragraphs that matched,
        # scaled by the proportion of the document that had matches.
        
        if not matches:
            return [], 0.0
            
        total_matched_paras = len(matched_indices1) + len(matched_indices2)
        total_paras = len(paras1) + len(paras2)
        
        coverage = total_matched_paras / total_paras if total_paras > 0 else 0
        
        avg_match_score = sum(m['score'] for m in matches) / len(matches)
        
        # Overall similarity is a combination of how much matched, and how well it matched
        overall_similarity = coverage * avg_match_score

        return matches, overall_similarity

