# ContextKit Technical Curriculum

A study guide for understanding the concepts and technologies used in building this LLM context management system.

## Core Computer Science Concepts

### Content-Addressed Storage
- **What it is**: Files stored and retrieved by their content hash rather than filename/path
- **Study areas**: 
  - Git internals (uses SHA-1 content addressing)
  - IPFS (InterPlanetary File System)
  - Merkle trees and hash-based data structures
- **Why important**: Enables deduplication, integrity verification, and immutable references

### Cryptographic Hashing
- **Focus on**: BLAKE3, SHA-256, hash collision resistance
- **Study areas**:
  - Hash function properties (deterministic, avalanche effect, one-way)
  - BLAKE3 vs SHA-256 performance characteristics
  - Content fingerprinting and integrity checking
- **Application**: Every artifact, chat, and schema gets a unique, stable identifier

### Vector Embeddings & Semantic Search
- **What it is**: Converting text to high-dimensional numerical vectors for similarity comparison
- **Study areas**:
  - Word embeddings (Word2Vec, GloVe)
  - Transformer-based embeddings (BERT, sentence-transformers)
  - Cosine similarity and vector space models
  - Approximate nearest neighbor search
- **Libraries used**: sentence-transformers, scikit-learn
- **Application**: Finding relevant context based on semantic meaning, not just keywords

## Data Management & Storage

### SQLite for Metadata
- **Study areas**:
  - Embedded databases vs client-server databases
  - SQL query optimization
  - Indexing strategies
  - ACID properties
- **Application**: Stores chat metadata, project info, tags for fast filtering

### Schema Evolution & Migration
- **Study areas**:
  - Database schema versioning
  - Forward/backward compatibility
  - Migration strategies (additive vs breaking changes)
  - Schema diff algorithms
- **Application**: Detecting when database schemas change and assessing ContextPack compatibility

### JSON Normalization
- **Study areas**:
  - Canonical JSON representation
  - Key sorting for deterministic serialization
  - Data structure normalization techniques
- **Application**: Creating stable schema fingerprints regardless of key ordering

## Natural Language Processing

### Text Processing & Parsing
- **Study areas**:
  - Regular expressions for pattern matching
  - Markdown parsing and AST manipulation
  - Code block extraction from mixed content
  - Language detection heuristics
- **Application**: Extracting SQL, Python, JavaScript from chat transcripts

### Tokenization & Token Estimation
- **Study areas**:
  - Subword tokenization (BPE, SentencePiece)
  - OpenAI's tiktoken library
  - Token limits in LLM APIs
- **Application**: Estimating ContextPack sizes to fit within model context windows

### Prompt Engineering
- **Study areas**:
  - Structured prompting techniques
  - Few-shot vs zero-shot prompting
  - Chain-of-thought reasoning
  - System vs user message roles
- **Application**: Creating effective prompts for LLM-powered summarization

## Software Architecture & Design

### Command Line Interface Design
- **Study areas**:
  - CLI design principles (Unix philosophy)
  - Argument parsing and validation
  - Rich terminal output and formatting
- **Libraries used**: Typer, Rich
- **Application**: User-friendly `ctx` command with subcommands

### Plugin Architecture & Extensibility
- **Study areas**:
  - Modular design patterns
  - Dependency injection
  - Strategy pattern for different backends
- **Application**: Swappable vector stores (FAISS → scikit-learn), multiple LLM providers

### Configuration Management
- **Study areas**:
  - Environment variable handling
  - Configuration file formats (YAML, TOML, JSON)
  - Secrets management
- **Libraries used**: python-dotenv, ruamel.yaml
- **Application**: API keys, database connections, feature flags

## Development Tools & Practices

### Python Packaging & Distribution
- **Study areas**:
  - pyproject.toml vs setup.py
  - Dependency management and version pinning
  - Entry points and console scripts
  - Virtual environments
- **Application**: Installable `ctx` CLI tool

### Error Handling & Graceful Degradation
- **Study areas**:
  - Exception handling strategies
  - Fallback mechanisms
  - Circuit breaker patterns
- **Application**: LLM summarization falls back to heuristic when API unavailable

### Testing & Validation
- **Study areas**:
  - Unit testing vs integration testing
  - Property-based testing
  - Schema validation
- **Application**: Validating extracted artifacts, testing hash consistency

## Domain-Specific Knowledge

### Database Introspection
- **Study areas**:
  - SQL information_schema tables
  - Database metadata queries
  - Cross-database compatibility (PostgreSQL, MySQL, SQLite)
- **Application**: Automatically extracting table/column information for schema fingerprinting

### Language Detection & Code Analysis
- **Study areas**:
  - Programming language syntax patterns
  - Static code analysis techniques
  - Abstract syntax trees (ASTs)
- **Application**: Categorizing code blocks, extracting imports/table references

### Information Retrieval
- **Study areas**:
  - TF-IDF scoring
  - Hybrid search (keyword + semantic)
  - Relevance ranking algorithms
  - Query expansion techniques
- **Application**: Finding the most relevant ContextPacks for a given prompt

## Advanced Topics (For Deep Understanding)

### Distributed Systems Concepts
- **Study areas**:
  - Content-addressable networks
  - Merkle DAGs (Directed Acyclic Graphs)
  - Conflict-free replicated data types (CRDTs)
- **Future application**: Multi-user collaboration, distributed context sharing

### Machine Learning Operations (MLOps)
- **Study areas**:
  - Model versioning and deployment
  - Feature stores
  - A/B testing for ML systems
- **Future application**: Learning which contexts are most useful, improving retrieval

### Information Theory
- **Study areas**:
  - Entropy and information content
  - Compression algorithms
  - Similarity measures and distance metrics
- **Application**: Understanding why certain contexts are more "informative" than others

## Recommended Learning Path

1. **Start with**: Hashing, content addressing, and basic NLP
2. **Build foundation**: SQL, JSON processing, CLI design
3. **Add complexity**: Vector embeddings, semantic search
4. **Advanced topics**: Schema evolution, prompt engineering
5. **System design**: Error handling, configuration, extensibility

## Key Libraries to Explore

- **blake3**: Fast cryptographic hashing
- **sentence-transformers**: Text embeddings
- **typer**: Modern CLI framework
- **pydantic**: Data validation and serialization
- **psycopg**: PostgreSQL adapter
- **ruamel.yaml**: YAML processing with comment preservation
- **tiktoken**: OpenAI tokenization
- **scikit-learn**: Machine learning utilities

Understanding these concepts will give you the foundation to extend ContextKit, debug issues, and build similar content-addressed systems for other domains.
