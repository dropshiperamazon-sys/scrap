"""Default search targets. Edit these lists for your own campaign."""

CITIES = [
    "New York City, NY",
    "Los Angeles, CA",
    "Chicago, IL",
    "Houston, TX",
    "Phoenix, AZ",
]

CATEGORIES = [
    "Furniture Store",
    "Modern Furniture",
    "Luxury Furniture",
    "Commercial Furniture",
    "Home Furniture",
]


def build_queries(cities: list[str] | None = None, categories: list[str] | None = None) -> list[str]:
    """Cross a list of cities with a list of categories into Maps search strings."""
    cities = cities or CITIES
    categories = categories or CATEGORIES
    return [f"{category} in {city}" for city in cities for category in categories]
