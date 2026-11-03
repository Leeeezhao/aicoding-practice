"""技能/城市同义词表。可按需扩展。"""

SKILL_ALIASES = {
    "k8s": "kubernetes",
    "kube": "kubernetes",
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "postgres": "postgresql",
    "psql": "postgresql",
    "torch": "pytorch",
    "tf": "tensorflow",
    "golang": "go",
}

CITY_ALIASES = {
    "帝都": "北京",
    "魔都": "上海",
    "羊城": "广州",
    "鹏城": "深圳",
}


def normalize_skill(token: str) -> str:
    t = token.strip().lower()
    return SKILL_ALIASES.get(t, t)


def normalize_city(token: str) -> str:
    t = token.strip()
    return CITY_ALIASES.get(t, t)
