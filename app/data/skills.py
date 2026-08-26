"""Skill taxonomy.

Maps a canonical skill name to the surface forms that should match it in
resume/job text. Keeping this as data (not code) means you can later move it
to a database table or swap it for a spaCy PhraseMatcher / NER model without
touching the extraction logic.
"""

SKILL_TAXONOMY: dict[str, list[str]] = {
    # --- Languages ---
    "Python": ["python", "python3"],
    "C++": ["c++", "cpp", "c plus plus"],
    "C": ["c language", "ansi c"],
    "Java": ["java"],
    "JavaScript": ["javascript", "js", "es6"],
    "TypeScript": ["typescript", "ts"],
    "Go": ["golang", "go lang", "go programming"],
    "Rust": ["rust"],
    "SQL": ["sql"],
    "Bash": ["bash", "shell scripting", "shell script"],
    "R": ["r language", "rstats", "r programming"],
    "Scala": ["scala"],
    "Kotlin": ["kotlin"],
    "MATLAB": ["matlab"],
    # --- Backend / API ---
    "FastAPI": ["fastapi", "fast api"],
    "Flask": ["flask"],
    "Django": ["django", "django rest framework", "drf"],
    "REST API": ["rest", "restful", "rest api", "restful api"],
    "GraphQL": ["graphql"],
    "gRPC": ["grpc"],
    "Node.js": ["node.js", "nodejs", "node js"],
    "Express.js": ["express.js", "expressjs", "express js"],
    "Spring Boot": ["spring boot", "springboot"],
    "Pydantic": ["pydantic"],
    "SQLAlchemy": ["sqlalchemy"],
    "Celery": ["celery"],
    "WebSockets": ["websocket", "websockets"],
    "Microservices": ["microservice", "microservices"],
    "OAuth2": ["oauth", "oauth2", "oauth 2.0"],
    "JWT": ["jwt", "json web token"],
    # --- Frontend ---
    "React": ["react", "react.js", "reactjs"],
    "Next.js": ["next.js", "nextjs"],
    "Vue.js": ["vue", "vue.js", "vuejs"],
    "Angular": ["angular"],
    "HTML": ["html", "html5"],
    "CSS": ["css", "css3"],
    "Tailwind CSS": ["tailwind", "tailwindcss", "tailwind css"],
    "Streamlit": ["streamlit"],
    # --- Databases ---
    "PostgreSQL": ["postgresql", "postgres", "psql"],
    "MySQL": ["mysql"],
    "SQLite": ["sqlite"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch", "elastic search"],
    "Cassandra": ["cassandra"],
    "DynamoDB": ["dynamodb"],
    "Pinecone": ["pinecone"],
    "FAISS": ["faiss"],
    "ChromaDB": ["chromadb", "chroma db"],
    "Vector Databases": ["vector database", "vector db", "vector store"],
    # --- ML / AI ---
    "Machine Learning": [
        "machine learning",
        "ml",
        "supervised learning",
        "unsupervised learning",
    ],
    "Deep Learning": ["deep learning", "neural network", "neural networks"],
    "NLP": ["nlp", "natural language processing"],
    "Computer Vision": ["computer vision", "opencv", "image processing"],
    "PyTorch": ["pytorch", "torch"],
    "TensorFlow": ["tensorflow", "tf.keras"],
    "Keras": ["keras"],
    "Scikit-learn": ["scikit-learn", "sklearn", "scikit learn"],
    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "XGBoost": ["xgboost"],
    "LightGBM": ["lightgbm"],
    "Hugging Face": ["hugging face", "huggingface", "transformers library"],
    "Transformers": ["transformer", "transformers", "bert", "attention mechanism"],
    "LLMs": ["llm", "llms", "large language model", "gpt-4", "gpt4"],
    "RAG": ["rag", "retrieval augmented generation", "retrieval-augmented"],
    "LangChain": ["langchain", "lang chain"],
    "LlamaIndex": ["llamaindex", "llama index"],
    "Sentence Transformers": ["sentence transformers", "sentence-transformers", "sbert"],
    "Embeddings": ["embedding", "embeddings", "word2vec", "text embedding"],
    "Prompt Engineering": ["prompt engineering", "prompting"],
    "MLOps": ["mlops", "ml ops", "model deployment", "model serving"],
    "spaCy": ["spacy"],
    "OpenCV": ["opencv"],
    "Feature Engineering": ["feature engineering", "feature extraction"],
    "Recommendation Systems": [
        "recommendation system",
        "recommender system",
        "collaborative filtering",
    ],
    # --- Data ---
    "Data Analysis": ["data analysis", "data analytics", "exploratory data analysis", "eda"],
    "Power BI": ["power bi", "powerbi", "dax", "power query"],
    "Tableau": ["tableau"],
    "Excel": ["excel", "pivot table", "pivottable"],
    "Apache Spark": ["spark", "pyspark", "apache spark"],
    "Airflow": ["airflow", "apache airflow"],
    "Kafka": ["kafka", "apache kafka"],
    "ETL": ["etl", "elt", "data pipeline"],
    "Data Warehousing": ["data warehouse", "data warehousing", "snowflake", "bigquery"],
    "Statistics": ["statistics", "statistical analysis", "hypothesis testing", "a/b testing"],
    # --- DevOps / Cloud ---
    "Docker": ["docker", "dockerfile", "containerization"],
    "Docker Compose": ["docker compose", "docker-compose"],
    "Kubernetes": ["kubernetes", "k8s", "eks", "helm"],
    "AWS": ["aws", "amazon web services", "ec2", "s3", "rds", "lambda", "ecs", "ecr"],
    "Azure": ["azure", "microsoft azure"],
    "GCP": ["gcp", "google cloud"],
    "CI/CD": ["ci/cd", "cicd", "continuous integration", "continuous deployment"],
    "GitHub Actions": ["github actions"],
    "Jenkins": ["jenkins"],
    "Terraform": ["terraform"],
    "Linux": ["linux", "ubuntu", "unix"],
    "Nginx": ["nginx"],
    "Git": ["git", "github", "gitlab", "version control"],
    "Monitoring": ["prometheus", "grafana", "observability", "monitoring"],
    # --- CS fundamentals ---
    "Data Structures": ["data structure", "data structures", "dsa"],
    "Algorithms": ["algorithm", "algorithms", "dynamic programming", "graph algorithms"],
    "System Design": ["system design", "distributed systems", "scalability"],
    "Object-Oriented Programming": ["oop", "object oriented", "object-oriented"],
    "Testing": ["unit test", "unit testing", "pytest", "test driven", "tdd"],
    "Agile": ["agile", "scrum", "kanban", "jira"],
    # --- Domain / engineering (kept, since plenty of resumes are non-CS) ---
    "PLC Programming": ["plc", "siemens plc", "simatic", "ladder logic", "tia portal"],
    "SCADA": ["scada", "hmi"],
    "Automation": ["industrial automation", "process automation"],
    "Preventive Maintenance": ["preventive maintenance", "predictive maintenance", "mtbf", "mttr"],
    "Root Cause Analysis": ["root cause analysis", "rca", "5-why", "5 why", "fishbone"],
    "Six Sigma": ["six sigma", "lean manufacturing", "kaizen"],
}

# Bare tokens that are far more often something else than a skill. They are
# never matched on their own; the longer aliases above still catch the real
# thing (e.g. "r programming" for R).
SKIP_BARE_ALIASES: set[str] = {"r", "c language", "go"}

# Reverse index built once at import: alias -> canonical name.
ALIAS_TO_CANONICAL: dict[str, str] = {}
for canonical, aliases in SKILL_TAXONOMY.items():
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.strip().lower()] = canonical

ALL_SKILLS: list[str] = sorted(SKILL_TAXONOMY.keys())


def canonicalise(skill: str) -> str:
    """Map any known surface form to its canonical name.

    Unknown skills are returned trimmed but otherwise untouched, so the system
    still works with skills that are not in the taxonomy yet.
    """
    key = skill.strip().lower()
    return ALIAS_TO_CANONICAL.get(key, skill.strip())


def canonicalise_all(skills: list[str]) -> list[str]:
    """Canonicalise a list, dropping blanks and duplicates but keeping order."""
    out: list[str] = []
    seen: set[str] = set()
    for s in skills:
        c = canonicalise(s)
        if c and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out
