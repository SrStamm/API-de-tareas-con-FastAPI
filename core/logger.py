import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler()
    ]
)

# filename='app.log'
# Podria agregarse para guardar los logs en un archivo, pero debe sacarse 'handlers'

logger = logging.getLogger("task_api")