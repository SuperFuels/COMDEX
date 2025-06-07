from sqlalchemy.orm import Session

def run_query(prompt: str, db: Session) -> dict:
    """
    TODO: Replace this stub with your AI + DB logic.
    It must return a dict with keys:
      - analysisText: str
      - visualPayload: { products: list, chartData: list }
    """
    # placeholder echo:
    return {
        "analysisText": f"🖥️ You asked: {prompt}",
        "visualPayload": {
            "products": [],      # e.g. list of { title, description, ... }
            "chartData": []      # e.g. time-series data for graphs
        }
    }
