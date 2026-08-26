import os
from pathlib import Path

from papyri_backend import LangChainEmbeddings
from papyri_backend.settings import load_environment

if __name__ == "__main__":
    load_environment()
    config_path = os.getenv("EMBEDDINGS_CONFIG")

    if config_path is None:
        raise ValueError("Error, config path not given")

    if not Path(config_path).exists():
        raise FileNotFoundError("Error, config file does not exist")

    embedder = LangChainEmbeddings.from_config(config_path)
    embedder.embedd_everything()
