def sql_query_verifier(query):
    # forbidden
    if ";" in query.rstrip(";"):
        raise ValueError("One statement only")

    if not query.upper().startswith("SELECT "):
        raise ValueError("Only SELECT queries are allowed")

    # check syntax validation
    return True
