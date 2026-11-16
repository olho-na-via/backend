import logging
import os

from config import PASTA_DO_PROJETO


def configurar_logs():
    pasta = os.path.join(PASTA_DO_PROJETO, "logs")
    os.makedirs(pasta, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(pasta, "olho_na_via.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        encoding="utf-8",
    )
