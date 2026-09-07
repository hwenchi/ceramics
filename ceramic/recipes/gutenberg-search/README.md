# Gutenberg Paragraph Search

Full-text search over 25 public-domain novels, indexed at paragraph granularity using SQLite's FTS5 extension with BM25 ranking.

`install.sh` fetches the novels from Project Gutenberg (the list is in `install.sh`) and builds the index. To add more books, drop `.txt` files into the corpus directory and run `install.sh` again.
