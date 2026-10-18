# AION-generated replaceable cognitive proposal component
ROUTES = {'research_investigation': 'research_investigation', 'document_evidence': 'research_investigation', 'software_tool': 'product_delivery', 'data_decision': 'strategic_decision', 'mathematical_reasoning': 'learning_apprenticeship'}

def route(objective_family):
    if objective_family in ROUTES:
        return ROUTES[objective_family]
    return 'bounded_task'
