def classify_score(final_score: float) -> str:
    if final_score >= 80:
        return "Highly Relevant"
    if final_score >= 60:
        return "Worth Checking"
    if final_score >= 40:
        return "Low Priority"
    return "Filtered"
