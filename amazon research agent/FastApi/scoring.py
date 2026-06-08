def calculate_score(product):

    score = 0

    rating = product.get("rating", 0)
    reviews = product.get("ratings_total", 0)

    score += rating * 20

    if reviews > 10000:
        score += 30

    elif reviews > 1000:
        score += 20

    elif reviews > 100:
        score += 10

    if product.get("amazons_choice"):
        score += 20

    if product.get("sponsored"):
        score -= 10

    return round(score, 2)