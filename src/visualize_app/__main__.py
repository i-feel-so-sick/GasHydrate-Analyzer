"""
Package entry point for the ThermoViz application.
"""

import logging
import sys

from visualize_app.ui import MainWindow
from visualize_app.utils import setup_logging


def main() -> None:
    """Run the desktop application."""
    try:
        setup_logging(level=logging.INFO)

        logger = logging.getLogger(__name__)
        logger.info("Starting Experimental Data Visualization Application")

        app = MainWindow()
        app.mainloop()

        logger.info("Application closed normally")

    except Exception as exc:
        logging.error("Critical error in main: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
