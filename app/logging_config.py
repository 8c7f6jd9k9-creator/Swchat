import logging, sys

def configure_logging():
    root = logging.getLogger()
    if root.handlers:
        return  # already configured (e.g. re-imported under pytest)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
